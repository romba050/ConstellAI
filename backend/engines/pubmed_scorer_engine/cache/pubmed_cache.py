import json
import hashlib
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "pubmed_cache.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(cache):
    CACHE_FILE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def normalize_query(text: str) -> str:
    return " ".join(text.lower().strip().split())


def query_hash(text: str) -> str:
    return hashlib.sha256(normalize_query(text).encode("utf-8")).hexdigest()


def get_cached_pubmed(query: str):
    cache = _load()
    h = query_hash(query)
    return cache.get(h)


def store_cached_pubmed(query: str, pmids, evidence):
    cache = _load()
    h = query_hash(query)

    cache[h] = {
        "query": normalize_query(query),
        "pmids": pmids,
        "evidence": evidence,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    _save(cache)
