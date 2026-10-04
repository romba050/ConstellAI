"""Bounded public Europe PMC and ClinicalTrials.gov v2 adapters.

Only source-supplied identities/titles are accepted. Empty, invalid or truncated
responses are distinguished from complete success. No disappearance/removal is
inferred from bounded searches. No patient information or API key is needed.
"""
import html
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from html.parser import HTMLParser
from urllib.parse import quote

import httpx

WATCHLIST = ["STXBP1", "CPLX1", "MUNC18-1", "complexin-1", "NCT05462054", "NCT06983158"]
PROVIDER_IDS = ("europe_pmc", "clinicaltrials_gov")
PROVIDER_NAMES = {"europe_pmc": "Europe PMC", "clinicaltrials_gov": "ClinicalTrials.gov"}
LOOKBACK_DAYS = 90
PAGE_SIZE = 50
MAX_PAGES = 2
TIMEOUT_SECONDS = 10.0
PROVIDER_BUDGET_SECONDS = 60.0
MAX_RECORDS = 120
MAX_RESPONSE_BYTES = 2_000_000
EUROPE_PMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
TRIALS_URL = "https://clinicaltrials.gov/api/v2/studies"


@dataclass(frozen=True)
class FetchedRecord:
    id: str
    provider: str
    kind: str
    title: str
    url: str
    matched_genes: list[str]
    source_updated_on: str | None
    summary: str
    excerpt: str | None
    comparison: dict[str, str | None] = field(default_factory=dict)


@dataclass
class FetchResult:
    records: list[FetchedRecord]
    complete: bool
    coverage: str
    error: str | None = None


class InvalidPayload(ValueError):
    pass


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"p", "br", "div", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag.lower() in {"p", "div"}:
            self.parts.append(" ")


def plain_text(value, max_length=12000):
    if not isinstance(value, str):
        raise InvalidPayload("Source text field is not a string")
    parser = _Text()
    parser.feed(value[:max_length * 2])
    return re.sub(r"\s+", " ", html.unescape("".join(parser.parts))).strip()[:max_length]


def matched_genes(text):
    matches = []
    if re.search(r"\b(?:STXBP1|MUNC18[-\s]?1)\b", text, re.I):
        matches.append("STXBP1")
    if re.search(r"\b(?:CPLX1|COMPLEXIN[-\s]?1)\b", text, re.I):
        matches.append("CPLX1")
    return matches


def _date(value):
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise InvalidPayload("Source date field is invalid")
    date.fromisoformat(value)
    return value


def parse_paper(raw):
    if not isinstance(raw, dict):
        raise InvalidPayload("Paper record is invalid")
    source, external_id = raw.get("source"), raw.get("id")
    if source == "MED" and isinstance(external_id, str) and re.fullmatch(r"\d{1,12}", external_id):
        pass
    elif source == "PMC" and isinstance(external_id, str) and re.fullmatch(r"PMC\d{1,12}", external_id):
        pass
    elif source == "PPR" and isinstance(external_id, str) and re.fullmatch(r"PPR\d{1,12}", external_id):
        pass
    else:
        raise InvalidPayload("Paper source identity is missing or invalid")
    title = plain_text(raw.get("title"), 2000)
    if not title:
        raise InvalidPayload("Paper title is missing")
    abstract = plain_text(raw.get("abstractText", ""))
    published = _date(raw.get("firstPublicationDate"))
    source_updated = _date(raw.get("dateOfRevision")) if raw.get("dateOfRevision") else published
    identifier = f"europe_pmc:{source}:{external_id}"
    url = f"https://europepmc.org/article/{source}/{quote(external_id, safe='')}"
    summary = (f"Source publication date: {published}. " if published else "Source publication date unavailable. ")
    summary += (abstract[:320] if abstract else "No source abstract was returned.")
    return FetchedRecord(identifier, "europe_pmc", "paper", title, url,
        matched_genes(title + " " + abstract), source_updated, summary, abstract or None,
        {"title": title, "publication_date": published, "source_updated_on": source_updated, "abstract": abstract or None})


def parse_trial(raw, expected_id=None):
    if not isinstance(raw, dict) or not isinstance(raw.get("protocolSection"), dict):
        raise InvalidPayload("Trial protocol record is missing")
    protocol = raw["protocolSection"]
    identification, status = protocol.get("identificationModule"), protocol.get("statusModule")
    if not isinstance(identification, dict) or not isinstance(status, dict):
        raise InvalidPayload("Trial identity or status module is missing")
    nct = identification.get("nctId")
    if not isinstance(nct, str) or not re.fullmatch(r"NCT\d{8}", nct) or (expected_id and nct != expected_id):
        raise InvalidPayload("Trial identity is invalid or mismatched")
    title = plain_text(identification.get("briefTitle"), 2000)
    if not title:
        raise InvalidPayload("Trial title is missing")
    overall = status.get("overallStatus")
    allowed = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED", "TERMINATED",
               "WITHDRAWN", "SUSPENDED", "ENROLLING_BY_INVITATION", "AVAILABLE", "NO_LONGER_AVAILABLE",
               "TEMPORARILY_NOT_AVAILABLE", "APPROVED_FOR_MARKETING", "WITHHELD", "UNKNOWN"}
    if overall not in allowed:
        raise InvalidPayload("Trial source status is missing or invalid")
    updated = status.get("lastUpdatePostDateStruct", {})
    if not isinstance(updated, dict):
        raise InvalidPayload("Trial source update date is invalid")
    updated = _date(updated.get("date"))
    description = protocol.get("descriptionModule", {})
    conditions = protocol.get("conditionsModule", {})
    design = protocol.get("designModule", {})
    eligibility = protocol.get("eligibilityModule", {})
    if any(not isinstance(module, dict) for module in (description, conditions, design, eligibility)):
        raise InvalidPayload("Trial source module is invalid")
    brief = plain_text(description.get("briefSummary", ""))
    criteria = plain_text(eligibility.get("eligibilityCriteria", ""))
    detailed = plain_text(description.get("detailedDescription", ""))
    listed = conditions.get("conditions", [])
    if not isinstance(listed, list) or any(not isinstance(c, str) for c in listed):
        raise InvalidPayload("Trial conditions are invalid")
    study_type = design.get("studyType")
    if study_type is not None and study_type not in {"INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS"}:
        raise InvalidPayload("Trial study type is invalid")
    has_results = raw.get("hasResults")
    if has_results is not None and not isinstance(has_results, bool):
        raise InvalidPayload("Trial results flag is invalid")
    summary = f"Registry status: {overall}. " + (f"Last posted update: {updated}. " if updated else "Posted update date unavailable. ")
    summary += "Registration and status do not establish efficacy, eligibility or access. " + brief[:320]
    return FetchedRecord(f"clinicaltrials_gov:{nct}", "clinicaltrials_gov", "trial", title,
        f"https://clinicaltrials.gov/study/{nct}", matched_genes(" ".join([title, brief, detailed, criteria, *listed])),
        updated, summary.strip(), brief or None,
        {"title": title, "overall_status": overall, "source_updated_on": updated, "study_type": study_type,
         "results_posted": str(has_results).lower() if has_results is not None else None})


class PublicSources:
    def __init__(self, client=None, monotonic=None):
        self.client = client
        self.monotonic = monotonic or time.monotonic

    def _json(self, client, url, params, deadline):
        remaining = deadline - self.monotonic()
        if remaining <= 0:
            raise TimeoutError("Provider budget exhausted")
        # Stream imposes a response-byte bound before JSON allocation.
        with client.stream("GET", url, params=params, timeout=min(TIMEOUT_SECONDS, remaining)) as response:
            response.raise_for_status()
            payload = bytearray()
            for chunk in response.iter_bytes():
                if self.monotonic() >= deadline or len(payload) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise InvalidPayload("Provider response exceeded bounded request budget")
                payload.extend(chunk)
        import json
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise InvalidPayload("Provider response is not an object")
        return data

    def _client(self):
        return self.client or httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=False,
            headers={"Accept": "application/json", "User-Agent": "ConstellAI-Pulse/1.0 (public research watchlist)"})

    def europe_pmc(self, now, known_records=None):
        start = (now.date() - timedelta(days=LOOKBACK_DAYS)).isoformat()
        end = now.date().isoformat()
        terms = '(STXBP1 OR CPLX1 OR "MUNC18-1" OR "complexin-1")'
        query = f"{terms} AND FIRST_PDATE:[{start} TO {end}] sort_date:y"
        records, pages, seen, hits, invalid, complete, error = {}, 0, 0, 0, 0, True, None
        deadline = self.monotonic() + PROVIDER_BUDGET_SECONDS
        client = self._client()
        try:
            cursor = "*"
            for _ in range(MAX_PAGES):
                data = self._json(client, EUROPE_PMC_URL, {"query": query, "format": "json", "resultType": "core",
                    "pageSize": PAGE_SIZE, "cursorMark": cursor}, deadline)
                result_list = data.get("resultList")
                hits = data.get("hitCount")
                if (not isinstance(result_list, dict) or not isinstance(result_list.get("result"), list)
                        or not isinstance(hits, (int, str)) or isinstance(hits, bool)):
                    raise InvalidPayload("Europe PMC search envelope is invalid")
                hits = int(hits)
                if hits < 0 or len(result_list["result"]) > PAGE_SIZE:
                    raise InvalidPayload("Europe PMC count or page size is invalid")
                pages += 1
                seen += len(result_list["result"])
                for raw in result_list["result"]:
                    try:
                        record = parse_paper(raw)
                        records[record.id] = record
                    except (InvalidPayload, ValueError, TypeError):
                        invalid += 1
                next_cursor = data.get("nextCursorMark")
                if hits <= seen or not result_list["result"] or not next_cursor or next_cursor == cursor:
                    if hits > seen:
                        complete = False
                    break
                if not isinstance(next_cursor, str):
                    raise InvalidPayload("Europe PMC cursor is invalid")
                cursor = next_cursor
                if pages == MAX_PAGES:
                    complete = False
            if invalid:
                complete, error = False, "Some Europe PMC records failed source identity or field validation."
        except Exception as exc:
            complete = False
            error = f"Europe PMC request unavailable ({type(exc).__name__}); retained earlier records."
        finally:
            if self.client is None:
                client.close()
        coverage = (f"First-publication window {start} through {end} (90 days, repeated overlap); "
                    f"core abstracts, {pages}/{MAX_PAGES} pages, {PAGE_SIZE} records/page, max100 search records, {hits} reported hits. "
                    + ("Search complete within configured window." if complete else "Coverage partial or truncated; no removals inferred."))
        return FetchResult(list(records.values())[:MAX_RECORDS], complete, coverage, error)

    def clinicaltrials_gov(self, now, known_records=None):
        records, pages, seen, total, invalid, complete, error = {}, 0, 0, None, 0, True, None
        deadline = self.monotonic() + PROVIDER_BUDGET_SECONDS
        client = self._client()
        query = 'STXBP1 OR CPLX1 OR "MUNC18-1" OR "complexin-1"'
        try:
            token = None
            for _ in range(MAX_PAGES):
                params = {"query.term": query, "format": "json", "pageSize": PAGE_SIZE, "countTotal": "true"}
                if token:
                    params["pageToken"] = token
                data = self._json(client, TRIALS_URL, params, deadline)
                total = data.get("totalCount")
                studies = data.get("studies", [] if total == 0 else None)
                if (not isinstance(studies, list) or len(studies) > PAGE_SIZE or not isinstance(total, int)
                        or isinstance(total, bool) or total < 0):
                    raise InvalidPayload("ClinicalTrials.gov search envelope is invalid")
                pages += 1
                seen += len(studies)
                for raw in studies:
                    try:
                        record = parse_trial(raw)
                        if record.matched_genes or record.id.split(":")[1] in WATCHLIST[-2:]:
                            records[record.id] = record
                    except (InvalidPayload, ValueError, TypeError):
                        invalid += 1
                token = data.get("nextPageToken")
                if not token:
                    if seen < total:
                        complete = False
                    break
                if not studies:
                    complete = False
                    break
                if not isinstance(token, str):
                    raise InvalidPayload("ClinicalTrials.gov page token is invalid")
                if pages == MAX_PAGES:
                    complete = False
        except Exception as exc:
            complete = False
            error = f"ClinicalTrials.gov search unavailable ({type(exc).__name__}); retained earlier records."
        # Exact tracked IDs remain checked even if the gene search failed.
        tracked_ok = 0
        for nct in WATCHLIST[-2:]:
            try:
                data = self._json(client, f"{TRIALS_URL}/{nct}", {"format": "json"}, deadline)
                record = parse_trial(data, expected_id=nct)
                records[record.id] = record
                tracked_ok += 1
            except Exception as exc:
                complete = False
                error = f"One or more tracked trial requests were unavailable ({type(exc).__name__}); retained earlier records."
        if self.client is None:
            client.close()
        if invalid:
            complete, error = False, "Some trial records failed source identity or field validation."
        coverage = (f"Four gene/synonym search terms, {pages}/{MAX_PAGES} pages, {PAGE_SIZE} records/page, "
                    f"{total if total is not None else 'unknown'} reported query hits; "
                    f"exact tracked IDs NCT05462054 and NCT06983158 ({tracked_ok}/2 fetched). "
                    + ("Search complete within configured query." if complete else "Coverage partial or truncated; no removals inferred."))
        return FetchResult(list(records.values())[:MAX_RECORDS], complete, coverage, error)

    def providers(self):
        return {"europe_pmc": self.europe_pmc, "clinicaltrials_gov": self.clinicaltrials_gov}
