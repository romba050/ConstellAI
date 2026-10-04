"""Time, persistence, ownership and public-source trust boundaries for Pulse."""
import hashlib
import io
import json
import tempfile
import threading
import unittest
from dataclasses import replace
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx

from atlas.pulse.models import PulseResponse
from atlas.pulse.__main__ import main as pulse_cli
from atlas.pulse.service import LEASE_SECONDS, PulseService
from atlas.pulse.sources import (
    FetchResult, InvalidPayload, PublicSources, WATCHLIST, matched_genes,
    parse_paper, parse_trial,
)


ROOT = Path(__file__).resolve().parent.parent


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 4, 10, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


def paper_raw(identifier="12345", title="STXBP1 mouse model paper", revision="2026-09-01"):
    return {"source": "MED", "id": identifier, "title": title,
            "firstPublicationDate": "2026-08-01", "dateOfRevision": revision,
            "abstractText": "STXBP1 was examined in a mouse model. Seizure activity was measured.",
            "hasAbstract": None}


def trial_raw(nct="NCT06983158", status="TERMINATED", updated="2026-06-10", title="STXBP1 registry study"):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": title},
        "statusModule": {"overallStatus": status, "lastUpdatePostDateStruct": {"date": updated}},
        "descriptionModule": {"briefSummary": "A registry entry concerning STXBP1."},
        "conditionsModule": {"conditions": ["STXBP1-related disorder"]},
        "designModule": {"studyType": "INTERVENTIONAL"},
    }, "hasResults": False}


class Providers:
    def __init__(self):
        self.calls = []
        self.results = {
            "europe_pmc": FetchResult([parse_paper(paper_raw())], True, "90-day window; 1/2 pages, 50/page; complete."),
            "clinicaltrials_gov": FetchResult([parse_trial(trial_raw())], True, "1/2 gene pages, 50/page; tracked IDs checked."),
        }

    def fetch(self, provider, now, known):
        self.calls.append((provider, now, known))
        value = self.results[provider]
        if isinstance(value, Exception):
            raise value
        return value

    def mapping(self):
        return {provider: lambda now, known, p=provider: self.fetch(p, now, known) for provider in self.results}


class PulseServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.clock, self.sources = Clock(), Providers()
        self.cache = Path(self.temp.name) / "cache"
        self.bootstrap = Path(self.temp.name) / "missing-bootstrap.json"
        self.service = self.make_service()

    def make_service(self, **kwargs):
        config = {"cache_dir": self.cache, "bootstrap_path": self.bootstrap,
                  "clock": self.clock, "providers": self.sources.mapping(), "enabled": True, "ai_enabled": False}
        config.update(kwargs)
        return PulseService(**config)

    def test_cached_read_never_fetches_and_flags_are_current(self):
        result = self.service.snapshot()
        self.assertEqual(result.state, "pending")
        self.assertEqual(result.watchlist, WATCHLIST)
        self.assertEqual(result.total_records, 0)
        self.assertEqual(self.sources.calls, [])
        self.service.scheduler_running = True
        self.service.enabled = False
        result = self.service.snapshot()
        self.assertEqual(result.state, "disabled")
        self.assertTrue(result.scheduler_running)
        self.assertFalse(result.scheduler_enabled)
        self.assertIsNone(result.next_check_at)
        self.assertFalse(self.service.tick())
        self.assertEqual(self.sources.calls, [])

    def test_six_hour_boundary_restart_and_overlap_deduplication(self):
        self.assertTrue(self.service.tick())
        first = self.service.snapshot()
        self.assertEqual(first.state, "ok")
        self.assertEqual(first.total_records, 2)
        self.assertTrue(all(i.change_type == "discovered" and not i.changes for i in first.items))
        self.assertIn("not newly published", " ".join(first.limitations))
        self.clock.advance(hours=5, minutes=59, seconds=59)
        restarted = self.make_service()
        self.assertFalse(restarted.tick())
        self.assertEqual(restarted.snapshot().items, first.items)
        self.clock.advance(seconds=1)
        self.assertTrue(restarted.tick())
        second = restarted.snapshot()
        self.assertEqual(second.total_records, 2)
        self.assertEqual(len(self.sources.calls), 4)
        before = {i.id: i for i in first.items}
        for item in second.items:
            self.assertEqual(item.first_seen_at, before[item.id].first_seen_at)
            self.assertEqual(item.changed_at, before[item.id].changed_at)
            self.assertEqual(item.change_type, "discovered")
            self.assertNotEqual(item.last_seen_at, before[item.id].last_seen_at)
        self.assertEqual(second.next_check_at, "2026-10-04T22:00:00Z")

    def test_manual_force_is_hourly_and_explicit_cli_force_bypasses_timing(self):
        self.service.tick()
        self.clock.advance(minutes=59)
        self.service.refresh(force=True)
        self.assertEqual(len(self.sources.calls), 2)
        self.clock.advance(minutes=1)
        self.service.refresh(force=True)
        self.assertEqual(len(self.sources.calls), 4)
        self.service.refresh(force=True)
        self.assertEqual(len(self.sources.calls), 4)
        self.service.run_once(force=True)
        self.assertEqual(len(self.sources.calls), 6)

    def test_status_title_date_diffs_are_real_and_first_seen_is_preserved(self):
        self.service.tick()
        original = {i.id: i for i in self.service.snapshot().items}
        changed = parse_trial(trial_raw(status="WITHDRAWN", updated="2026-10-04", title="STXBP1 revised registry study"))
        self.sources.results["clinicaltrials_gov"].records = [changed]
        self.clock.advance(hours=6)
        self.service.tick()
        item = next(i for i in self.service.snapshot().items if i.kind == "trial")
        self.assertEqual(item.change_type, "updated")
        self.assertEqual(item.first_seen_at, original[item.id].first_seen_at)
        self.assertEqual({c.field for c in item.changes}, {"overall_status", "source_updated_on", "title"})
        status = next(c for c in item.changes if c.field == "overall_status")
        self.assertEqual((status.before, status.after), ("TERMINATED", "WITHDRAWN"))

    def test_failed_provider_retains_records_success_date_and_attempt_due_time(self):
        self.service.tick()
        previous = self.service.snapshot()
        self.sources.results["europe_pmc"] = RuntimeError("Authorization: Bearer secret-key and private URL")
        self.clock.advance(hours=6)
        self.assertTrue(self.service.tick())
        result = self.service.snapshot()
        self.assertEqual(result.state, "partial")
        self.assertEqual(result.total_records, previous.total_records)
        self.assertEqual(result.last_success_at, previous.last_success_at)
        states = {p.id: p for p in result.providers}
        old = {p.id: p for p in previous.providers}
        self.assertEqual(states["europe_pmc"].state, "error")
        self.assertEqual(states["europe_pmc"].last_success_at, old["europe_pmc"].last_success_at)
        self.assertNotEqual(states["clinicaltrials_gov"].last_success_at, old["clinicaltrials_gov"].last_success_at)
        self.assertEqual(result.next_check_at, "2026-10-04T22:00:00Z")
        self.assertNotIn("secret-key", result.model_dump_json())
        self.assertFalse(self.service.tick())

    def test_partial_valid_records_do_not_remove_previous_search_results(self):
        self.service.tick()
        old = {i.id: i for i in self.service.snapshot().items}
        self.clock.advance(hours=6)
        new = parse_paper(paper_raw("12346", "CPLX1 recent publication"))
        self.sources.results["europe_pmc"] = FetchResult([new], False, "2/2 pages, 50/page, truncated at 100 records.")
        self.service.tick()
        result = self.service.snapshot()
        self.assertEqual(result.state, "partial")
        self.assertEqual(result.total_records, 3)
        self.assertEqual(next(i for i in result.items if i.id == "europe_pmc:MED:12345"), old["europe_pmc:MED:12345"])
        self.assertEqual(next(p for p in result.providers if p.id == "europe_pmc").last_success_at, "2026-10-04T10:00:00Z")

    def test_invalid_source_identity_and_titles_are_withheld(self):
        good = parse_paper(paper_raw())
        invalid = [replace(good, title=""), replace(good, id="europe_pmc:MED:invented"),
                   replace(good, url="https://example.com/secret"), replace(good, matched_genes=["SCN1A"])]
        self.sources.results["europe_pmc"] = FetchResult(invalid, True, "1/2 pages.")
        self.sources.results["clinicaltrials_gov"] = FetchResult([], True, "Empty valid query.")
        self.service.tick()
        result = self.service.snapshot()
        self.assertEqual(result.total_records, 0)
        self.assertEqual(next(p for p in result.providers if p.id == "europe_pmc").state, "error")
        self.assertNotIn("invented", result.model_dump_json())
        self.assertNotIn("example.com", result.model_dump_json())

    def test_unexpected_check_error_rolls_back_and_persists_sanitized_failure(self):
        self.service.tick()
        old = self.service.snapshot()
        self.clock.advance(hours=6)
        with patch.object(self.service, "_changes", side_effect=RuntimeError("private source body")):
            self.assertTrue(self.service.tick())
        result = self.service.snapshot()
        self.assertEqual(result.state, "error")
        self.assertEqual(result.items, old.items)
        self.assertEqual(result.last_success_at, old.last_success_at)
        self.assertEqual(result.last_attempt_at, "2026-10-04T16:00:00Z")
        self.assertNotIn("private source body", result.model_dump_json())
        self.assertFalse(self.service.tick())

    def test_gene_filter_limit_and_counts_use_cached_records(self):
        cplx = parse_paper(paper_raw("999", "Complexin-1 mouse study"))
        self.sources.results["europe_pmc"].records.append(cplx)
        self.service.tick()
        self.assertEqual(self.service.snapshot(" cplx1 ", limit=0).total_records, 1)
        self.assertEqual(self.service.snapshot(" cplx1 ", limit=0).items, [])
        unknown = self.service.snapshot("SCN1A")
        self.assertEqual((unknown.total_records, unknown.unreviewed_count, unknown.items), (0, 0, []))
        self.assertIn("SCN1A is not monitored", " ".join(unknown.limitations))
        self.assertEqual(self.service.snapshot(limit=1).total_records, 3)
        self.assertEqual(len(self.service.snapshot(limit=1).items), 1)
        self.assertEqual(len(self.sources.calls), 2)

    def test_bootstrap_preserves_dates_overrides_flags_and_does_not_invent_updates(self):
        self.service.tick()
        original = self.service.snapshot()
        original.scheduler_enabled, original.scheduler_running = False, True
        self.bootstrap.write_text(original.model_dump_json(), encoding="utf-8")
        seeded = self.make_service(cache_dir=Path(self.temp.name) / "seeded")
        result = seeded.snapshot()
        self.assertTrue(result.scheduler_enabled)
        self.assertFalse(result.scheduler_running)
        self.assertEqual(result.last_success_at, original.last_success_at)
        self.assertEqual(result.items, original.items)
        self.clock.advance(hours=6)
        seeded.tick()
        for item in seeded.snapshot().items:
            self.assertEqual(item.change_type, "discovered")
            self.assertEqual(item.changed_at, original.items[0].changed_at)
            self.assertEqual(item.changes, [])
        # Internal baseline is now complete: a genuine subsequent status change is recorded.
        self.clock.advance(hours=6)
        self.sources.results["clinicaltrials_gov"].records = [parse_trial(trial_raw(status="COMPLETED"))]
        seeded.tick()
        trial = next(i for i in seeded.snapshot().items if i.kind == "trial")
        self.assertEqual([c.field for c in trial.changes], ["overall_status"])

    def test_invalid_bootstrap_is_all_or_nothing(self):
        self.service.tick()
        original = self.service.snapshot().model_dump()
        original["items"][-1]["url"] = "https://example.com/unsafe"
        self.bootstrap.write_text(json.dumps(original), encoding="utf-8")
        seeded = self.make_service(cache_dir=Path(self.temp.name) / "seeded")
        result = seeded.snapshot()
        self.assertEqual(result.total_records, 0)
        self.assertIsNone(result.last_success_at)
        self.assertIn("was not imported", " ".join(result.limitations))

    def test_partial_bootstrap_keeps_provider_freshness_and_rejects_unresolved_draft_quotes(self):
        self.service.tick()
        response = self.service.snapshot()
        response.state = "partial"
        response.providers[0].state = "partial"
        response.providers[0].error = "Configured search was truncated."
        self.bootstrap.write_text(response.model_dump_json(), encoding="utf-8")
        seeded = self.make_service(cache_dir=Path(self.temp.name) / "partial")
        result = seeded.snapshot()
        self.assertEqual(result.state, "partial")
        self.assertEqual(result.providers, response.providers)
        self.assertEqual(result.last_success_at, response.last_success_at)
        invalid = response.model_dump()
        paper = next(i for i in invalid["items"] if i["kind"] == "paper")
        paper["draft_claims"] = [{"statement": "Invented response.", "quote": "This quote never appeared.", "evidence_type": "human_clinical"}]
        self.bootstrap.write_text(json.dumps(invalid), encoding="utf-8")
        rejected = self.make_service(cache_dir=Path(self.temp.name) / "invalid-quote").snapshot()
        self.assertEqual(rejected.total_records, 0)
        self.assertIsNone(rejected.last_success_at)

    def test_shipped_public_bootstrap_imports_complete_shape_ids_and_actual_dates(self):
        path = ROOT / "data/curated/pulse-bootstrap.json"
        response = PulseResponse.model_validate_json(path.read_text(encoding="utf-8"))
        self.assertTrue(response.items, "The shipped bootstrap must contain an actual public-source check.")
        seeded = self.make_service(cache_dir=Path(self.temp.name) / "shipped", bootstrap_path=path)
        result = seeded.snapshot(limit=5000)
        self.assertEqual(result.state, response.state)
        self.assertEqual(result.total_records, response.total_records)
        self.assertEqual(result.items, sorted(response.items, key=lambda i: (i.changed_at, i.id), reverse=True))
        self.assertEqual(result.providers, sorted(response.providers, key=lambda p: p.id))
        self.assertEqual(result.last_attempt_at, response.last_attempt_at)
        self.assertEqual(result.last_success_at, response.last_success_at)
        self.assertEqual(result.watchlist, WATCHLIST)
        self.assertEqual(self.sources.calls, [])
        self.assertEqual({i.id for i in result.items if i.kind == "trial"} & {
            "clinicaltrials_gov:NCT05462054", "clinicaltrials_gov:NCT06983158"}, {
            "clinicaltrials_gov:NCT05462054", "clinicaltrials_gov:NCT06983158"})

    def test_cli_export_contains_complete_response_and_explicit_force_requires_once(self):
        self.service.tick()
        output = Path(self.temp.name) / "export.json"
        with patch("atlas.pulse.__main__.PulseService", return_value=self.service), patch("sys.argv", ["pulse", "--export", str(output)]), redirect_stdout(io.StringIO()):
            self.assertEqual(pulse_cli(), 0)
        exported = PulseResponse.model_validate_json(output.read_text(encoding="utf-8"))
        self.assertEqual(exported.total_records, len(exported.items))
        self.assertEqual(exported.items, self.service.snapshot(limit=5000).items)
        self.assertEqual(len(self.sources.calls), 2)
        with patch("atlas.pulse.__main__.PulseService", return_value=self.service), patch("sys.argv", ["pulse", "--once", "--force", "--export", str(output)]), redirect_stdout(io.StringIO()):
            self.assertEqual(pulse_cli(), 0)
        self.assertEqual(len(self.sources.calls), 4)
        with patch("sys.argv", ["pulse", "--force"]), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                pulse_cli()
        self.assertEqual(error.exception.code, 2)

    def test_active_process_lease_blocks_another_worker_and_explicit_force(self):
        entered, release = threading.Event(), threading.Event()
        original = self.sources.results["europe_pmc"]
        def blocking(now, known):
            entered.set()
            if not release.wait(timeout=5):
                raise TimeoutError("test lease wait")
            return original
        first = self.make_service(providers={**self.sources.mapping(), "europe_pmc": blocking})
        outcome = []
        worker = threading.Thread(target=lambda: outcome.append(first.tick()))
        worker.start()
        self.assertTrue(entered.wait(timeout=5))
        try:
            second = self.make_service()
            self.assertFalse(second.tick())
            self.assertEqual(second.run_once(force=True).state, "running")
            self.assertEqual(self.sources.calls, [])
        finally:
            release.set()
            worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(outcome, [True])
        self.assertEqual(first.snapshot().state, "ok")

    def test_expired_worker_cannot_overwrite_new_owner(self):
        old = self.sources.results["europe_pmc"]
        new = FetchResult([parse_paper(paper_raw(title="STXBP1 newer source title"))], True, "1/2 pages complete.")
        def replaced_owner(now, known):
            self.clock.advance(seconds=LEASE_SECONDS + 1)
            self.sources.results["europe_pmc"] = new
            replacement = self.make_service()
            replacement.run_once(force=True)
            return old
        original = self.make_service(providers={**self.sources.mapping(), "europe_pmc": replaced_owner})
        self.assertTrue(original.tick())
        result = original.snapshot()
        self.assertEqual(next(i for i in result.items if i.kind == "paper").title, "STXBP1 newer source title")
        self.assertEqual(result.last_attempt_at, "2026-10-04T10:10:01Z")
        self.assertEqual(result.state, "ok")

    def test_abandoned_lease_is_visible_and_restart_retries_at_due_time(self):
        self.assertIsNotNone(self.service._acquire())
        self.clock.advance(seconds=LEASE_SECONDS + 1)
        restarted = self.make_service()
        self.assertEqual(restarted.snapshot().state, "error")
        self.assertIn("lease expired", " ".join(restarted.snapshot().limitations))
        self.assertFalse(restarted.tick())
        self.clock.advance(seconds=6 * 3600 - LEASE_SECONDS - 1)
        self.assertTrue(restarted.tick())
        self.assertEqual(restarted.snapshot().state, "ok")

    def test_ai_defaults_off_and_optional_drafts_are_bounded_exact_unreviewed_quotes(self):
        self.sources.results["europe_pmc"].records = [parse_paper(paper_raw(str(i))) for i in range(101, 106)]
        with patch("atlas.pulse.service.llm.available", return_value=True), patch("atlas.pulse.service.llm._json") as transport:
            self.service.tick()
        transport.assert_not_called()
        enabled = self.make_service(ai_enabled=True, cache_dir=Path(self.temp.name) / "ai")
        payload = {"claims": [
            {"statement": "The abstract reports a mouse model.", "quote": "STXBP1 was examined in a mouse model.", "evidence_type": "preclinical"},
            {"statement": "Unsupported draft.", "quote": "Invented patient response.", "evidence_type": "human_clinical"},
            {"statement": "Oversized quote.", "quote": "x" * 301, "evidence_type": "unknown"},
        ]}
        with patch("atlas.pulse.service.llm.available", return_value=True), patch("atlas.pulse.service.llm._json", return_value=payload) as transport:
            enabled.tick()
        self.assertEqual(transport.call_count, 3)
        result = enabled.snapshot()
        drafts = [c for i in result.items for c in i.draft_claims]
        self.assertEqual(len(drafts), 3)
        self.assertTrue(all(c.review_status == "unreviewed" for c in drafts))
        for item in result.items:
            for claim in item.draft_claims:
                self.assertIn(claim.quote, item.excerpt)
                self.assertLessEqual(len(claim.quote), 300)
        self.assertNotIn("candidate_treatments", result.model_dump())

    def test_ai_transport_uses_existing_strict_responses_and_failure_cannot_spoil_fetch(self):
        self.service.ai_enabled = True
        response = SimpleNamespace(status="completed", error=None, incomplete_details=None, output=[],
            output_text=json.dumps({"claims": [{"statement": "The source describes a mouse model.",
                "quote": "STXBP1 was examined in a mouse model.", "evidence_type": "preclinical"}]}))
        create = Mock(return_value=response)
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch("atlas.pulse.service.llm.available", return_value=True), patch("atlas.pulse.service.llm.CHAT_TRANSPORT", False), patch("atlas.pulse.service.llm._client", client):
            self.service.tick()
        options = create.call_args.kwargs
        self.assertFalse(options["store"])
        self.assertEqual(options["text"]["format"]["name"], "pulse_unreviewed_drafts")
        self.assertTrue(options["text"]["format"]["strict"])
        self.assertLessEqual(options["timeout"], 25)
        self.clock.advance(hours=6)
        self.sources.results["europe_pmc"].records = [parse_paper(paper_raw(title="STXBP1 updated mouse title"))]
        with patch("atlas.pulse.service.llm.available", return_value=True), patch("atlas.pulse.service.llm._json", side_effect=RuntimeError("secret key")):
            self.service.tick()
        self.assertEqual(self.service.snapshot().state, "ok")
        self.assertEqual(next(i for i in self.service.snapshot().items if i.kind == "paper").draft_claims, [])

    def test_pulse_cannot_modify_reviewed_evidence_graph_or_weights(self):
        paths = [ROOT / "atlas/analysis/evidence.json", ROOT / "atlas/analysis/weights.json",
                 ROOT / "atlas/analysis/graph.py", ROOT / "atlas/analysis/ranking.py"]
        hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        self.service.tick()
        self.assertEqual(hashes, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


class PulseSourceTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()

    def adapter(self, handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        return PublicSources(client=client)

    def test_source_parsers_require_real_identity_title_dates_and_status(self):
        for source in ({}, {**paper_raw(), "id": "fake"}, {**paper_raw(), "title": ""},
                       {**paper_raw(), "firstPublicationDate": "2026-02-30"}):
            with self.assertRaises((InvalidPayload, ValueError)):
                parse_paper(source)
        for source in ({}, trial_raw(nct="invented"), trial_raw(title=""), trial_raw(status="CURED")):
            with self.assertRaises(InvalidPayload):
                parse_trial(source)
        with self.assertRaises(InvalidPayload):
            parse_trial(trial_raw(), expected_id="NCT05462054")

    def test_source_fields_have_safe_text_real_dates_and_exact_watch_matches(self):
        raw = paper_raw(title="<i>MUNC18-1</i> model")
        raw["abstractText"] = "<p>A complexin-1 model &amp; a mouse assay.</p>"
        paper = parse_paper(raw)
        self.assertEqual(paper.title, "MUNC18-1 model")
        self.assertEqual(paper.excerpt, "A complexin-1 model & a mouse assay.")
        self.assertEqual(paper.matched_genes, ["STXBP1", "CPLX1"])
        self.assertEqual(paper.source_updated_on, "2026-09-01")
        self.assertIn("2026-08-01", paper.summary)
        self.assertEqual(matched_genes("Complexin-10, preSTXBP1, CPLX10"), [])
        no_abstract = parse_paper({k: v for k, v in paper_raw().items() if k != "abstractText"})
        self.assertIsNone(no_abstract.excerpt)
        raw_trial = trial_raw(title="Neurodevelopmental registry")
        raw_trial["protocolSection"]["descriptionModule"] = {}
        raw_trial["protocolSection"]["conditionsModule"] = {}
        raw_trial["protocolSection"]["eligibilityModule"] = {"eligibilityCriteria": "A confirmed CPLX1 variant."}
        self.assertEqual(parse_trial(raw_trial).matched_genes, ["CPLX1"])

    def test_europe_pmc_core_cursor_pagination_window_and_stable_dedup(self):
        requests = []
        def handler(request):
            requests.append(request)
            cursor = request.url.params.get("cursorMark")
            if cursor == "*":
                result, next_cursor = [paper_raw(str(i)) for i in range(50)], "page-2"
            else:
                result, next_cursor = [paper_raw("49"), paper_raw("50")], "page-3"
            return httpx.Response(200, json={"hitCount": 52, "resultList": {"result": result}, "nextCursorMark": next_cursor})
        source = self.adapter(handler)
        first = source.europe_pmc(self.clock())
        second = source.europe_pmc(self.clock(), {r.id: r.comparison for r in first.records})
        self.assertTrue(first.complete)
        self.assertEqual(len(first.records), 51)
        self.assertEqual({r.id for r in first.records}, {r.id for r in second.records})
        self.assertEqual(len(requests), 4)
        for request in requests:
            self.assertEqual(request.url.params["format"], "json")
            self.assertEqual(request.url.params["resultType"], "core")
            self.assertEqual(request.url.params["pageSize"], "50")
            self.assertIn("FIRST_PDATE:[2026-07-06 TO 2026-10-04]", request.url.params["query"])
        self.assertEqual(requests[1].url.params["cursorMark"], "page-2")
        self.assertIn("52 reported hits", first.coverage)

    def test_europe_pmc_truncation_and_invalid_or_failed_page_never_claim_complete(self):
        def truncated(request):
            cursor = request.url.params["cursorMark"]
            return httpx.Response(200, json={"hitCount": 101, "resultList": {"result": [paper_raw(str(i)) for i in range(50)]},
                                           "nextCursorMark": "page-2" if cursor == "*" else "page-3"})
        result = self.adapter(truncated).europe_pmc(self.clock())
        self.assertFalse(result.complete)
        self.assertIn("2/2 pages", result.coverage)
        def failed(request):
            if request.url.params["cursorMark"] != "*":
                return httpx.Response(503, text="secret patient data")
            return httpx.Response(200, json={"hitCount": 51, "resultList": {"result": [paper_raw()]}, "nextCursorMark": "page-2"})
        result = self.adapter(failed).europe_pmc(self.clock())
        self.assertFalse(result.complete)
        self.assertEqual(len(result.records), 1)
        self.assertNotIn("secret patient data", result.error)
        for payload in ({"hitCount": 2, "resultList": {"result": []}},
                        {"hitCount": 1, "resultList": {"result": [{"id": "fake"}]}},
                        {"hitCount": True, "resultList": {"result": []}}):
            result = self.adapter(lambda request, p=payload: httpx.Response(200, json=p)).europe_pmc(self.clock())
            self.assertFalse(result.complete)
            self.assertEqual(result.records, [])

    def test_trials_pages_exact_ids_dedup_and_unmatched_query_hits(self):
        requests = []
        def handler(request):
            requests.append(request)
            if request.url.path.endswith("/NCT05462054"):
                return httpx.Response(200, json=trial_raw("NCT05462054", "WITHDRAWN"))
            if request.url.path.endswith("/NCT06983158"):
                return httpx.Response(200, json=trial_raw())
            if "pageToken" in request.url.params:
                return httpx.Response(200, json={"totalCount": 3, "studies": [trial_raw("NCT05462054", "WITHDRAWN")]})
            unrelated = trial_raw("NCT00000001", title="Unrelated registry")
            unrelated["protocolSection"]["descriptionModule"] = {}
            unrelated["protocolSection"]["conditionsModule"] = {}
            return httpx.Response(200, json={"totalCount": 3, "studies": [trial_raw(), unrelated], "nextPageToken": "page-2"})
        result = self.adapter(handler).clinicaltrials_gov(self.clock())
        self.assertTrue(result.complete)
        self.assertEqual(len(result.records), 2)
        self.assertEqual(len(requests), 4)
        self.assertEqual(requests[1].url.params["pageToken"], "page-2")
        self.assertIn('"complexin-1"', requests[0].url.params["query.term"])
        self.assertIn("2/2 fetched", result.coverage)

    def test_trials_search_failure_still_checks_exact_ids_and_sanitizes_errors(self):
        def handler(request):
            if request.url.path.endswith("/NCT05462054"):
                return httpx.Response(200, json=trial_raw("NCT05462054", "WITHDRAWN"))
            if request.url.path.endswith("/NCT06983158"):
                return httpx.Response(200, json=trial_raw())
            return httpx.Response(403, text="secret URL token")
        result = self.adapter(handler).clinicaltrials_gov(self.clock())
        self.assertFalse(result.complete)
        self.assertEqual(len(result.records), 2)
        self.assertNotIn("secret URL token", result.error)
        self.assertIn("2/2 fetched", result.coverage)

    def test_response_byte_limit_and_mismatched_exact_id_fail_closed(self):
        oversized = self.adapter(lambda request: httpx.Response(200, content=b"x" * 2_000_001))
        result = oversized.europe_pmc(self.clock())
        self.assertFalse(result.complete)
        self.assertEqual(result.records, [])
        def wrong_id(request):
            if request.url.path.endswith("/studies"):
                return httpx.Response(200, json={"totalCount": 0, "studies": []})
            return httpx.Response(200, json=trial_raw("NCT00000001"))
        result = self.adapter(wrong_id).clinicaltrials_gov(self.clock())
        self.assertFalse(result.complete)
        self.assertEqual(result.records, [])
        self.assertIn("0/2 fetched", result.coverage)


if __name__ == "__main__":
    unittest.main()
