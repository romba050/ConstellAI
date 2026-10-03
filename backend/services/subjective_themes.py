from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List


_POSITIVE_KEYS = [
    "helped",
    "better",
    "improved",
    "clearer",
    "focus",
    "energy",
    "calm",
    "sleep better",
    "benefit",
]
_NEGATIVE_KEYS = [
    "anxiety",
    "insomnia",
    "headache",
    "nausea",
    "worse",
    "flush",
    "fatigue",
    "palpitations",
    "sweat",
    "sweating",
]
_DOSING_KEYS = [
    "dose",
    "dosage",
    "mg",
    "capsule",
    "capsules",
    "daily",
    "twice",
    "timing",
]
_ONSET_KEYS = [
    "days",
    "weeks",
    "months",
    "immediate",
    "instantly",
    "after",
    "within",
]
_STACK_KEYS = [
    "stack",
    "combine",
    "combined",
    "with",
    "together",
]


def parse_query_items(query: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"[,\n]+", str(query or "")) if p.strip()]
    return parts or ([str(query or "").strip()] if str(query or "").strip() else [])


def _fetch_forum_blob_one(term: str) -> str:
    try:
        from engines.compound_subjective_engine.data_sources.forum_scraper import fetch_forum_posts
    except Exception:
        return ""
    try:
        return str(fetch_forum_posts(term) or "")
    except Exception:
        return ""


def fetch_subjective_blob(query: str) -> str:
    parts = parse_query_items(query)
    chunks: List[str] = []
    for part in parts[:5]:
        text = _fetch_forum_blob_one(part)
        if text:
            chunks.append(f"## {part}\n{text}")
    return "\n\n".join(chunks).strip()


def _clean_lines(raw_text: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for line in str(raw_text or "").splitlines():
        line = re.sub(r"\s+", " ", line).strip(" -\t\r\n")
        if len(line) < 12:
            continue
        low = line.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(line)
    return out


def extract_subjective_themes(raw_text: str, max_examples_per_bucket: int = 4) -> Dict[str, List[str]]:
    lines = _clean_lines(raw_text)
    buckets = {
        "positives": [],
        "negatives": [],
        "dosing": [],
        "onset": [],
        "stack_context": [],
        "other": [],
    }

    for line in lines:
        low = line.lower()
        matched = False

        if any(k in low for k in _POSITIVE_KEYS):
            buckets["positives"].append(line)
            matched = True
        if any(k in low for k in _NEGATIVE_KEYS):
            buckets["negatives"].append(line)
            matched = True
        if any(k in low for k in _DOSING_KEYS):
            buckets["dosing"].append(line)
            matched = True
        if any(k in low for k in _ONSET_KEYS):
            buckets["onset"].append(line)
            matched = True
        if any(k in low for k in _STACK_KEYS):
            buckets["stack_context"].append(line)
            matched = True

        if not matched:
            buckets["other"].append(line)

    out: Dict[str, List[str]] = {}
    for key, values in buckets.items():
        out[key] = values[:max_examples_per_bucket]
    return out


def summarize_subjective_themes(raw_text: str, label: str = "") -> Dict[str, object]:
    themes = extract_subjective_themes(raw_text)
    counts = {k: len(v) for k, v in themes.items()}
    top = Counter({k: v for k, v in counts.items() if v > 0}).most_common()
    top_labels = [k for k, _ in top[:3]]
    return {
        "label": label.strip(),
        "themes": themes,
        "counts": counts,
        "top_labels": top_labels,
        "has_data": any(counts.values()),
    }


def format_subjective_summary(summary: Dict[str, object], label: str = "") -> str:
    themes = summary.get("themes", {}) if isinstance(summary.get("themes", {}), dict) else {}
    top_labels = summary.get("top_labels", []) if isinstance(summary.get("top_labels", []), list) else []
    name = (label or summary.get("label") or "").strip()

    lines = [f"SUBJECTIVE REPORTS FOR {name.upper() if name else 'QUERY'}:"]
    if not summary.get("has_data"):
        lines.append("- no subjective discussions captured yet from current lightweight forum ingestion.")
        return "\n".join(lines).strip() + "\n"

    if top_labels:
        lines.append(f"- top recurring theme buckets: {', '.join(top_labels)}")

    label_map = {
        "positives": "common positives",
        "negatives": "common negatives / side effects",
        "dosing": "dosing / timing discussion",
        "onset": "time-to-effect discussion",
        "stack_context": "stack / combination context",
        "other": "other recurring mentions",
    }

    for key in ["positives", "negatives", "dosing", "onset", "stack_context", "other"]:
        vals = themes.get(key, [])
        if not vals:
            continue
        lines.append(f"- {label_map.get(key, key)}:")
        for item in vals[:4]:
            lines.append(f"  - {item}")

    return "\n".join(lines).strip() + "\n"
