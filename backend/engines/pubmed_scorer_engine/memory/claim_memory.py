import json
import hashlib
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path("memory")
DISCARDED_FILE = MEMORY_DIR / "discarded_claims.json"

# bump this ONLY when thresholds / evidence logic change
GATE_VERSION = "v1_score0.60_risk0.40_pubmed"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _load():
    if DISCARDED_FILE.exists():
        try:
            return json.loads(DISCARDED_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(records):
    DISCARDED_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def hash_claim(text: str) -> str:
    return hashlib.sha256(normalize_claim(text).encode("utf-8")).hexdigest()


def is_discarded_before(claim_text: str) -> bool:
    h = hash_claim(claim_text)
    records = _load()
    return any(
        r.get("hash") == h and r.get("gate_version") == GATE_VERSION
        for r in records
    )


def record_discard(claim_text: str, reason: str):
    records = _load()
    h = hash_claim(claim_text)

    # do not duplicate
    for r in records:
        if r.get("hash") == h and r.get("gate_version") == GATE_VERSION:
            return

    records.append({
        "hash": h,
        "claim": normalize_claim(claim_text),
        "gate_version": GATE_VERSION,
        "discard_reason": reason,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

    _save(records)
