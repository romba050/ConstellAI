# backend/services/evidence_db.py (FULL REPLACEMENT)
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import SETTINGS


class EvidenceDB:
    _inst: Optional["EvidenceDB"] = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> "EvidenceDB":
        with cls._lock:
            if cls._inst is None:
                cls._inst = EvidenceDB()
            return cls._inst

    def __init__(self) -> None:
        base = Path(__file__).resolve().parent.parent
        default_path = base / "data" / "evidence_cache.sqlite"
        db_path = Path(SETTINGS.evidence_db_path) if SETTINGS.evidence_db_path else default_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._mu = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._mu:
            c = self._conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS pubmed_search (
                    query TEXT NOT NULL,
                    retmax INTEGER NOT NULL,
                    pmids_json TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    created_ms INTEGER NOT NULL,
                    PRIMARY KEY (query, retmax)
                );
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS pubmed_article (
                    pmid TEXT PRIMARY KEY,
                    title TEXT,
                    abstract TEXT,
                    journal TEXT,
                    year INTEGER,
                    authors_json TEXT,
                    fetched_ms INTEGER NOT NULL
                );
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS compound_target_evidence (
                    compound TEXT NOT NULL,
                    target TEXT NOT NULL,
                    query TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    pmids_json TEXT NOT NULL,
                    created_ms INTEGER NOT NULL,
                    PRIMARY KEY (compound, target, query)
                );
                """
            )
            self._conn.commit()

    # ---- pubmed search cache ----
    def get_pubmed_search(self, query: str, retmax: int) -> Optional[Dict[str, Any]]:
        with self._mu:
            row = self._conn.execute(
                "SELECT pmids_json,total FROM pubmed_search WHERE query=? AND retmax=?",
                (query, retmax),
            ).fetchone()
            if not row:
                return None
            return {"pmids": json.loads(row["pmids_json"]), "total": int(row["total"])}

    def put_pubmed_search(self, query: str, retmax: int, pmids: List[str], total: int) -> None:
        with self._mu:
            self._conn.execute(
                "INSERT OR REPLACE INTO pubmed_search(query,retmax,pmids_json,total,created_ms) VALUES (?,?,?,?,?)",
                (query, retmax, json.dumps(pmids), int(total), int(time.time() * 1000)),
            )
            self._conn.commit()

    # ---- article cache ----
    def get_articles(self, pmids: List[str]) -> List[Dict[str, Any]]:
        if not pmids:
            return []
        with self._mu:
            q = f"SELECT * FROM pubmed_article WHERE pmid IN ({','.join(['?']*len(pmids))})"
            rows = self._conn.execute(q, pmids).fetchall()
            out = []
            for r in rows:
                out.append(
                    {
                        "pmid": r["pmid"],
                        "title": r["title"] or "",
                        "abstract": r["abstract"] or "",
                        "journal": r["journal"] or "",
                        "year": r["year"],
                        "authors": json.loads(r["authors_json"] or "[]"),
                    }
                )
            return out

    def put_article(self, art: Dict[str, Any]) -> None:
        with self._mu:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO pubmed_article(pmid,title,abstract,journal,year,authors_json,fetched_ms)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    art.get("pmid"),
                    art.get("title", ""),
                    art.get("abstract", ""),
                    art.get("journal", ""),
                    art.get("year"),
                    json.dumps(art.get("authors", [])),
                    int(time.time() * 1000),
                ),
            )
            self._conn.commit()

    # ---- compound-target evidence cache ----
    def get_compound_target(self, compound: str, target: str, query: str) -> Optional[Dict[str, Any]]:
        with self._mu:
            row = self._conn.execute(
                "SELECT result_json,pmids_json FROM compound_target_evidence WHERE compound=? AND target=? AND query=?",
                (compound, target, query),
            ).fetchone()
            if not row:
                return None
            return {"result": json.loads(row["result_json"]), "pmids": json.loads(row["pmids_json"])}

    def put_compound_target(self, compound: str, target: str, query: str, result: Dict[str, Any], pmids: List[str]) -> None:
        with self._mu:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO compound_target_evidence(compound,target,query,result_json,pmids_json,created_ms)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    compound,
                    target,
                    query,
                    json.dumps(result, ensure_ascii=False),
                    json.dumps(pmids),
                    int(time.time() * 1000),
                ),
            )
            self._conn.commit()