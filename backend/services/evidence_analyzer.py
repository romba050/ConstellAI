# backend/services/evidence_analyzer.py
from __future__ import annotations

import re
import time
from typing import Any, Dict, List

import requests

from services.evidence_db import EvidenceDB
from services.pubmed_client import fetch_pubmed_abstracts, search_pubmed
from services.llm_client import chat_json, LLMError
from services.subjective_themes import (
    fetch_subjective_blob,
    format_subjective_summary,
    summarize_subjective_themes,
)


SYSTEM_EVIDENCE = (
    "You are a biomedical research triage analyst. "
    "You must be conservative and avoid overclaiming. "
    "You only use the provided abstracts. "
    "You output strict JSON only."
)


def pubmed_search(query: str, retmax: int = 10) -> Dict[str, Any]:
    r = search_pubmed(query, retmax=retmax)
    return {"pmids": r["pmids"], "total": r["total"], "cached": r.get("cached", False)}


def pubmed_get_article(pmid: str) -> Dict[str, Any] | None:
    arts = fetch_pubmed_abstracts([pmid])
    return arts[0] if arts else None


def _clean_term(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _split_target_terms(values: List[str] | None) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values or []:
        for part in re.split(r"[,\n;/]+", str(value or "")):
            term = _clean_term(part).upper()
            if not term or term in seen:
                continue
            seen.add(term)
            out.append(term)
    return out


def _build_compound_queries(compound: str, context: str = "", targets: List[str] | None = None) -> List[str]:
    compound = _clean_term(compound)
    context = _clean_term(context)
    target_terms = _split_target_terms(targets)

    queries: List[str] = []
    seen = set()

    def push(q: str) -> None:
        q = _clean_term(q)
        if not q:
            return
        key = q.lower()
        if key in seen:
            return
        seen.add(key)
        queries.append(q)

    if compound:
        push(compound)

    for target in target_terms[:2]:
        push(f"{compound} {target}")

    if context:
        push(f"{compound} {context}")

    if context and target_terms:
        for target in target_terms[:2]:
            push(f"{compound} {target} {context}")

    return queries[:5]


def _safe_search_pubmed(query: str, retmax: int = 5, retries: int = 2, backoff_seconds: float = 0.8) -> Dict[str, Any]:
    last_error = ""
    for attempt in range(retries + 1):
        try:
            sr = search_pubmed(query, retmax=retmax)
            return {"ok": True, "pmids": sr.get("pmids", []) or [], "error": ""}
        except requests.HTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            last_error = f"http_{status}" if status else "http_error"
            if status == 429 and attempt < retries:
                time.sleep(backoff_seconds * (attempt + 1))
                continue
            return {"ok": False, "pmids": [], "error": last_error}
        except Exception as exc:
            last_error = str(exc)
            return {"ok": False, "pmids": [], "error": last_error}
    return {"ok": False, "pmids": [], "error": last_error or "unknown_error"}


def _collect_pubmed_union(queries: List[str], retmax_per_query: int = 5) -> Dict[str, Any]:
    seen_pmids = set()
    ordered_pmids: List[str] = []
    query_hits: List[Dict[str, Any]] = []
    rate_limited = False
    had_error = False

    for idx, q in enumerate(queries):
        sr = _safe_search_pubmed(q, retmax=retmax_per_query)
        pmids = sr.get("pmids", []) or []
        err = sr.get("error", "") or ""
        if err:
            had_error = True
        if err == "http_429":
            rate_limited = True
        query_hits.append({"query": q, "count": len(pmids), "pmids": pmids[:], "error": err})
        for pmid in pmids:
            if pmid not in seen_pmids:
                seen_pmids.add(pmid)
                ordered_pmids.append(pmid)

        if idx < len(queries) - 1:
            time.sleep(0.25)

    arts = fetch_pubmed_abstracts(ordered_pmids) if ordered_pmids else []
    return {
        "queries": query_hits,
        "pmids": ordered_pmids,
        "articles": arts,
        "rate_limited": rate_limited,
        "had_error": had_error,
    }


def analyze_compound_target(
    compound: str,
    target: str,
    disease: str = "",
    drug: str = "",
    max_papers: int = 8,
    use_llm: bool = True,
) -> Dict[str, Any]:
    compound = (compound or "").strip()
    target = (target or "").strip().upper()
    disease = (disease or "").strip()
    drug = (drug or "").strip()

    query = _build_query(compound=compound, target=target, disease=disease, drug=drug)

    db = EvidenceDB.get()
    cached = db.get_compound_target(compound=compound, target=target, query=query)
    if cached:
        out = dict(cached["result"])
        out["pmids"] = cached["pmids"]
        out["query"] = query
        out["cached"] = True
        return out

    sr = _safe_search_pubmed(query, retmax=max_papers)
    pmids = sr["pmids"]
    arts = fetch_pubmed_abstracts(pmids) if pmids else []

    if not arts:
        caution = "no pubmed hits returned for this query"
        if sr.get("error") == "http_429":
            caution = "pubmed rate-limited this query; partial or retry-later result"
        out = {
            "query": query,
            "direction": "UNKNOWN",
            "confidence": 0.0,
            "key_findings": [],
            "cautions": [caution],
            "pmids": [],
            "cached": False,
        }
        db.put_compound_target(compound, target, query, out, [])
        return out

    if use_llm:
        try:
            out = _llm_summarize_compound_target(compound, target, disease, drug, arts)
        except LLMError:
            out = _fallback_summarize(compound, target, arts)
    else:
        out = _fallback_summarize(compound, target, arts)

    out["query"] = query
    out["pmids"] = [a["pmid"] for a in arts if a.get("pmid")]
    out["cached"] = False

    db.put_compound_target(compound, target, query, out, out["pmids"])
    return out


def analyze_compound(
    compound: str,
    context: str = "",
    targets: List[str] | None = None,
    max_papers: int = 8,
    use_llm: bool = True,
) -> Dict[str, Any]:
    compound = (compound or "").strip()
    targets = [t.strip().upper() for t in (targets or []) if t.strip()]
    context = (context or "").strip()

    queries = _build_compound_queries(compound=compound, context=context, targets=targets)
    union = _collect_pubmed_union(queries, retmax_per_query=max(2, min(4, max_papers)))
    arts = union["articles"][:max_papers]
    pmids = [a["pmid"] for a in arts if a.get("pmid")]

    subjective_raw = fetch_subjective_blob(compound)
    subjective_struct = summarize_subjective_themes(subjective_raw, label=compound)
    subjective_summary = format_subjective_summary(subjective_struct, label=compound)

    if not arts:
        tried = ", ".join([row["query"] for row in union["queries"][:4]])
        note = "no pubmed hits across expanded query set; try simpler target/context terms."
        if union.get("rate_limited"):
            note = "pubmed rate-limited part of the expanded query set; returned no usable abstracts this run."
        return {
            "objective_summary": (
                f"OBJECTIVE EVIDENCE FOR {compound.upper()}:\n"
                f"- no pubmed abstracts returned across expanded queries.\n"
                f"- tried: {tried}\n"
            ),
            "subjective_summary": subjective_summary,
            "pmids": [],
            "notes": note + " subjective lane uses lightweight forum ingestion.",
        }

    if use_llm:
        try:
            js = _llm_summarize_compound(compound, context, targets, arts)
            obj = _format_objective(js)
            notes = js.get("notes", "")
            if union.get("rate_limited"):
                notes = (notes + " | pubmed rate-limit encountered; summary uses partial query-union results").strip(" |")
            else:
                notes = (notes + " | expanded pubmed query union active").strip(" |")
            if subjective_struct.get("has_data"):
                notes = (notes + " | subjective forum lane active").strip(" |")
            else:
                notes = (notes + " | subjective forum lane sparse").strip(" |")
            return {
                "objective_summary": obj,
                "subjective_summary": subjective_summary,
                "pmids": pmids,
                "notes": notes,
            }
        except LLMError:
            pass

    tops = arts[: min(5, len(arts))]
    mech_lines = []
    for a in tops:
        t = (a.get("title") or "").strip()
        if t:
            mech_lines.append(f"- {t} (PMID {a.get('pmid', '')})")
    obj = f"OBJECTIVE EVIDENCE FOR {compound.upper()}:\n" + "\n".join(mech_lines) + "\n"
    notes = "fallback objective mode with expanded pubmed query union; subjective lane uses lightweight forum ingestion."
    if union.get("rate_limited"):
        notes = "fallback objective mode using partial results after pubmed rate limiting; subjective lane uses lightweight forum ingestion."
    return {
        "objective_summary": obj,
        "subjective_summary": subjective_summary,
        "pmids": pmids,
        "notes": notes,
    }


def _build_query(compound: str, target: str, disease: str, drug: str) -> str:
    parts = [compound, target]
    if disease:
        parts.append(disease)
    if drug:
        parts.append(drug)
    parts.append("(inhibit OR inhibition OR activate OR activation OR modulate OR modulation)")
    return " ".join([p for p in parts if p]).strip()


def _llm_summarize_compound_target(
    compound: str,
    target: str,
    disease: str,
    drug: str,
    arts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    blob = _abstract_blob(arts, max_chars=12000)

    prompt = f"""
TASK:
Given PubMed abstracts, triage whether COMPOUND modulates TARGET.

INPUTS:
- compound: {compound}
- target: {target}
- disease_context: {disease or "none"}
- reference_drug: {drug or "none"}

ABSTRACTS:
{blob}

OUTPUT JSON SCHEMA (strict):
{{
  "direction": "INHIBITS" | "ACTIVATES" | "MIXED" | "UNKNOWN",
  "confidence": number,
  "key_findings": [string, ...],
  "cautions": [string, ...]
}}

RULES:
- If evidence is indirect, set direction to MIXED or UNKNOWN and lower confidence.
- Prefer human/clinical evidence over cell/animal; reflect that in confidence.
- Do NOT invent study details not present in abstracts.
- JSON only.
""".strip()

    js = chat_json(SYSTEM_EVIDENCE, prompt)
    return _sanitize_ct(js)


def _llm_summarize_compound(
    compound: str,
    context: str,
    targets: List[str],
    arts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    blob = _abstract_blob(arts, max_chars=14000)

    prompt = f"""
TASK:
Summarize objective evidence for COMPOUND from PubMed abstracts, conservative triage.

INPUTS:
- compound: {compound}
- context: {context or "none"}
- targets_of_interest: {", ".join(targets) if targets else "none"}

ABSTRACTS:
{blob}

OUTPUT JSON SCHEMA (strict):
{{
  "objective": {{
    "mechanisms": [string, ...],
    "human_data": [string, ...],
    "safety": [string, ...]
  }},
  "subjective": {{
    "positives": [string, ...],
    "negatives": [string, ...],
    "contradictions": [string, ...]
  }},
  "notes": string
}}

RULES:
- Do not overclaim efficacy.
- If evidence is mostly in vitro, say so.
- JSON only.
""".strip()

    js = chat_json(SYSTEM_EVIDENCE, prompt)
    return _sanitize_compound(js)


def _fallback_summarize(compound: str, target: str, arts: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = " ".join([(a.get("title", "") + " " + a.get("abstract", "")) for a in arts]).lower()
    inhibits = any(w in text for w in ["inhibit", "inhibition", "suppressed", "blocked", "antagonist"])
    activates = any(w in text for w in ["activate", "activation", "enhanced", "increased", "agonist"])

    if inhibits and activates:
        direction = "MIXED"
        conf = 0.35
    elif inhibits:
        direction = "INHIBITS"
        conf = 0.45
    elif activates:
        direction = "ACTIVATES"
        conf = 0.45
    else:
        direction = "UNKNOWN"
        conf = 0.2

    key = []
    for a in arts[:3]:
        t = (a.get("title") or "").strip()
        if t:
            key.append(f"{t} (PMID {a.get('pmid', '')})")

    return {
        "direction": direction,
        "confidence": conf,
        "key_findings": key,
        "cautions": ["heuristic fallback; verify manually"],
    }


def _abstract_blob(arts: List[Dict[str, Any]], max_chars: int) -> str:
    chunks = []
    for a in arts:
        pmid = a.get("pmid", "")
        title = (a.get("title") or "").strip()
        abst = (a.get("abstract") or "").strip()
        if not (title or abst):
            continue
        chunks.append(f"[PMID {pmid}] {title}\n{abst}")
    blob = "\n\n".join(chunks)
    return blob[:max_chars]


def _sanitize_ct(js: Dict[str, Any]) -> Dict[str, Any]:
    direction = str(js.get("direction", "UNKNOWN")).upper()
    if direction not in {"INHIBITS", "ACTIVATES", "MIXED", "UNKNOWN"}:
        direction = "UNKNOWN"
    try:
        conf = float(js.get("confidence", 0.0))
    except Exception:
        conf = 0.0
    conf = max(0.0, min(conf, 1.0))

    kf = js.get("key_findings", [])
    ca = js.get("cautions", [])
    if not isinstance(kf, list):
        kf = []
    if not isinstance(ca, list):
        ca = []
    kf = [str(x)[:240] for x in kf][:6]
    ca = [str(x)[:240] for x in ca][:6]

    return {"direction": direction, "confidence": conf, "key_findings": kf, "cautions": ca}


def _sanitize_compound(js: Dict[str, Any]) -> Dict[str, Any]:
    obj = js.get("objective", {}) if isinstance(js.get("objective", {}), dict) else {}
    sub = js.get("subjective", {}) if isinstance(js.get("subjective", {}), dict) else {}

    def _lst(d: Dict[str, Any], k: str, n: int) -> List[str]:
        v = d.get(k, [])
        if not isinstance(v, list):
            return []
        return [str(x)[:240] for x in v][:n]

    out = {
        "objective": {
            "mechanisms": _lst(obj, "mechanisms", 8),
            "human_data": _lst(obj, "human_data", 6),
            "safety": _lst(obj, "safety", 8),
        },
        "subjective": {
            "positives": _lst(sub, "positives", 6),
            "negatives": _lst(sub, "negatives", 6),
            "contradictions": _lst(sub, "contradictions", 6),
        },
        "notes": str(js.get("notes", ""))[:400],
    }
    return out


def _format_objective(js: Dict[str, Any]) -> str:
    o = js.get("objective", {})
    mech = o.get("mechanisms", [])
    hum = o.get("human_data", [])
    saf = o.get("safety", [])
    lines = ["OBJECTIVE EVIDENCE:"]
    if mech:
        lines.append("- mechanisms:")
        lines += [f"  - {x}" for x in mech]
    if hum:
        lines.append("- human data:")
        lines += [f"  - {x}" for x in hum]
    if saf:
        lines.append("- safety:")
        lines += [f"  - {x}" for x in saf]
    return "\n".join(lines).strip() + "\n"


def _format_subjective(js: Dict[str, Any]) -> str:
    s = js.get("subjective", {})
    pos = s.get("positives", [])
    neg = s.get("negatives", [])
    con = s.get("contradictions", [])
    lines = ["SUBJECTIVE REPORTS (NOT WIRED; PLACEHOLDER STRUCTURE):"]
    if pos:
        lines.append("- common positives:")
        lines += [f"  - {x}" for x in pos]
    if neg:
        lines.append("- common negatives:")
        lines += [f"  - {x}" for x in neg]
    if con:
        lines.append("- contradictions:")
        lines += [f"  - {x}" for x in con]
    return "\n".join(lines).strip() + "\n"
