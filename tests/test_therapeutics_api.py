"""Offline API regression checks use the actual bundled ConstellAI graph."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ["OPENAI_API_KEY"] = ""
from fastapi.testclient import TestClient
from atlas import server
from atlas.therapeutics.evidence import catalog

ROOT = Path(__file__).resolve().parents[1]


def offline_evidence(disease, **kwargs):
    """Explicit empty network fixture; not a claim that live evidence is absent."""
    return {
        "id": disease["id"], "fetched": "2026-10-04", "errors": ["Offline regression fixture"],
        "pubmed": {"papers": [], "claims": [], "count": 0, "query": "offline fixture", "url": "", "claim_method": "pattern"},
        "clinvar": [], "trials": {"studies": [], "count": 0, "query": "offline fixture", "url": ""},
        "grants": {"grants": [], "count": 0, "query": "offline fixture", "years": []},
        "investigators": [], "organizations": server.enrich.match_orgs(disease),
        "registries": [], "directories": [],
    }


class TherapeuticsAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(server.app)

    def get(self, disease="MONDO:0007113", **params):
        return self.client.get(f"/api/disease/{disease}/therapeutics", params=params)

    def test_endpoint_separates_all_requested_dimensions(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        row = data["candidates"][0]
        self.assertTrue({"candidate_intervention", "direction_match", "mechanistic_coverage", "spillover",
                         "wrong_direction_effects", "evidence_strength", "remaining_deviation", "uncertainty"}.issubset(row))
        self.assertEqual(row["candidate_intervention"]["id"], "topotecan")
        self.assertEqual(row["rank"], 1)
        self.assertIsNone(data["candidates"][1]["rank"])
        self.assertEqual(data["candidates"][1]["ranking_status"], "research_comparator")
        self.assertFalse(data["complementary"]["proposed"])

    def test_curated_mechanism_matches_default_response(self):
        self.assertEqual(self.get().json(), self.get(mechanism="ube3a-deficiency").json())

    def test_unknown_variant_or_mechanism_withholds_rank(self):
        for params in ({"variant": "unreviewed-variant"}, {"variant": "VCV000155984.20"}, {"mechanism": "unknown"}):
            with self.subTest(params=params):
                data = self.get(**params).json()
                self.assertEqual(data["status"], "unknown")
                self.assertFalse(any(row["rank"] for row in data["candidates"]))
                self.assertTrue(all(row["mechanistic_fit"]["score"] is None for row in data["candidates"]))
                self.assertFalse(data["complementary"]["proposed"])
                self.assertEqual(len(data["candidates"][0]["clinical_safety_evidence"]["warnings"]), 2)

    def test_existing_hero_diseases_return_unknown_without_new_therapy_claims(self):
        for did in ("MONDO:0033372", "MONDO:0012812"):
            data = self.get(did).json()
            self.assertEqual(data["status"], "unknown")
            self.assertEqual(data["candidates"], [])
            self.assertTrue(all(target["desired_direction"] is None for target in data["signed_targets"]))

    def test_missing_mechanistic_source_does_not_make_an_api_rank(self):
        sources = catalog()["sources"]
        damaged = [s for s in sources if s["id"] != "huang2012"]
        with patch.dict(catalog(), {"sources": damaged}):
            data = self.get().json()
            self.assertEqual(data["status"], "unknown")
            self.assertTrue(all(row["mechanistic_fit"]["score"] is None for row in data["candidates"]))

    def test_unknown_disease_and_oversized_queries(self):
        self.assertEqual(self.get("not-in-atlas").status_code, 404)
        self.assertEqual(self.get(variant="x" * 201).status_code, 422)
        self.assertEqual(self.get(mechanism="x" * 101).status_code, 422)

    def test_ui_flag_defaults_off_while_api_remains_available(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.client.get("/therapeutics").status_code, 404)
            self.assertEqual(self.client.get("/therapeutics/assets/panel.js").status_code, 404)
            self.assertEqual(self.get().status_code, 200)

    def test_flag_enables_only_isolated_panel_and_whitelisted_assets(self):
        with patch.dict(os.environ, {"MEDR5_THERAPEUTICS_ENABLED": "1"}):
            page = self.client.get("/therapeutics")
            self.assertEqual(page.status_code, 200)
            self.assertIn("Therapeutic Opportunities", page.text)
            self.assertEqual(self.client.get("/therapeutics/assets/panel.js").status_code, 200)
            self.assertEqual(self.client.get("/therapeutics/assets/panel.css").status_code, 200)
            for name in ("evidence.json", "server.py", "%2E%2E%2Fevidence.json"):
                self.assertEqual(self.client.get("/therapeutics/assets/" + name).status_code, 404)

    def test_therapeutics_does_not_mutate_atlas_or_fetch_live_evidence(self):
        before = json.dumps(server.atlas.diseases, sort_keys=True)
        with patch.object(server.enrich, "enrich", side_effect=AssertionError("Therapeutics must not call live enrichment")):
            self.assertEqual(self.get().status_code, 200)
        self.assertEqual(before, json.dumps(server.atlas.diseases, sort_keys=True))

    def test_clinical_safety_is_not_inferred_from_fit(self):
        row = self.get().json()["candidates"][0]
        self.assertGreater(row["mechanistic_fit"]["score"], 0)
        self.assertEqual(row["clinical_safety_evidence"]["status"], "not_established_for_this_disease")
        self.assertIsNone(row["clinical_safety_evidence"]["assessment_score"])
        self.assertFalse(row["evidence_strength"]["clinical_benefit_established"])
        self.assertEqual(row["clinical_safety_evidence"]["drug_interactions"], "unknown")


class PitchDemoPreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(server.app)

    def test_original_pitch_assets_and_graph_logic_are_byte_identical(self):
        baseline = json.loads((ROOT / "tests/fixtures/pitch_baseline_sha256.json").read_text())
        for relative, digest in baseline["sha256"].items():
            with self.subTest(path=relative):
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)

    def test_root_hero_is_identical_with_flag_on_or_off(self):
        original = (ROOT / "web/index.html").read_bytes()
        for flag in ("", "1"):
            with patch.dict(os.environ, {"MEDR5_THERAPEUTICS_ENABLED": flag}):
                self.assertEqual(self.client.get("/").content, original)
                self.assertNotIn(b"Therapeutic Opportunities", self.client.get("/").content)

    def test_actual_map_and_cplx1_search_still_work(self):
        graph = self.client.get("/api/atlas").json()
        self.assertEqual(graph["meta"]["counts"]["diseases"], 6457)
        self.assertEqual(len(graph["points"]), 6457)
        self.assertTrue(graph["edges"])
        hits = self.client.get("/api/search", params={"q": "CPLX1"}).json()["hits"]
        self.assertTrue(any(hit["id"] == "CPLX1" and hit["type"] == "gene" for hit in hits))
        gene = self.client.get("/api/entity/gene/CPLX1").json()
        self.assertIn("MONDO:0033372", gene["ids"])
        detail = self.client.get("/api/disease/MONDO:0033372").json()
        self.assertEqual(detail["neighbors"][0]["id"], "MONDO:0012812")

    def test_original_evidence_endpoint_still_returns_effect_and_sources(self):
        with patch.object(server.enrich, "enrich", side_effect=offline_evidence):
            response = self.client.get("/api/disease/MONDO:0033372/evidence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue({"pubmed", "clinvar", "trials", "grants", "effect", "errors"}.issubset(data))
        self.assertEqual(data["errors"], ["Offline regression fixture"])

    def test_original_cplx1_stxbp1_connection_evidence_ledger_still_works(self):
        with patch.object(server.enrich, "enrich", side_effect=offline_evidence), \
             patch.object(server.enrich, "comention", return_value=None):
            response = self.client.get("/api/connection", params={"a": "MONDO:0033372", "b": "MONDO:0012812"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["path"]["a_gene"][0]["gene"], "CPLX1")
        self.assertEqual(data["path"]["b_gene"][0]["gene"], "STXBP1")
        self.assertTrue(data["path"]["pathways"])
        ledger = {entry["id"]: entry for entry in data["evidence"]}
        for pathway in data["path"]["pathways"]:
            self.assertIn(pathway["e"], ledger)
            self.assertEqual(ledger[pathway["e"]]["source"], "Reactome")
        self.assertIn("CPLX1", data["brief"])
        self.assertIn("STXBP1", data["brief"])


if __name__ == "__main__":
    unittest.main()
