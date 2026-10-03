"""Reviewed provenance contract. A valid URL does not establish scientific truth."""
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from .models import Intervention, InterventionEffect, signed_direction

ROOT = Path(__file__).resolve().parent
HOSTS = {"pubmed.ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov",
         "medlineplus.gov", "dailymed.nlm.nih.gov", "www.ebi.ac.uk"}
MECHANISTIC_TYPES = {"authoritative_disease_reference", "preclinical_animal", "preclinical_cellular",
                     "human_cellular", "human_observational", "human_randomized_trial", "review"}


def valid_source(source):
    required = ("id", "source_url", "source_family", "evidence_type", "extracted_claim",
                "claim_kind", "verification_status", "retrieved_at", "uncertainty", "study_design")
    if not all(source.get(key) for key in required):
        return False
    url = urlparse(source["source_url"])
    if url.scheme != "https" or url.hostname not in HOSTS or url.username or url.password:
        return False
    if source["claim_kind"] not in {"direct_source_report", "inferred_relationship"}:
        return False
    if url.hostname == "pubmed.ncbi.nlm.nih.gov" or source.get("pmid"):
        pmid = source.get("pmid")
        if not isinstance(pmid, str) or not pmid.isdigit():
            return False
        if url.hostname != "pubmed.ncbi.nlm.nih.gov" or url.path != f"/{pmid}/":
            return False
        if not all(source.get(key) for key in ("title", "journal", "authors", "publication_year",
                                               "publication_types", "sample_size", "metadata_source_url")):
            return False
    return True


class EvidenceRegistry:
    def __init__(self, sources):
        self.sources = {source["id"]: source for source in sources}
        if len(self.sources) != len(sources):
            raise ValueError("Duplicate source identifiers")

    def resolve(self, source_ids, *, mechanistic=False):
        if not isinstance(source_ids, (list, tuple)) or not source_ids:
            return None
        rows = []
        for sid in dict.fromkeys(source_ids):
            source = self.sources.get(sid)
            if not source or not valid_source(source):
                return None
            if mechanistic and (source["evidence_type"] not in MECHANISTIC_TYPES or
                                source["claim_kind"] != "direct_source_report"):
                return None
            rows.append(source)
        return rows

    def effect_direction(self, effect):
        rows = self.resolve(effect.source_ids, mechanistic=True)
        if not rows or any(row["evidence_type"] == "authoritative_disease_reference" for row in rows):
            return None
        if effect.claim_kind != "direct_source_report" or not effect.context or not effect.relation:
            return None
        return effect.direction


@lru_cache(maxsize=1)
def catalog():
    return json.loads((ROOT / "evidence.json").read_text(encoding="utf-8"))


def registry():
    return EvidenceRegistry(catalog()["sources"])


def interventions(profile_id):
    result = []
    for row in catalog()["interventions"]:
        if profile_id not in row["profile_ids"]:
            continue
        def effects(key):
            return tuple(InterventionEffect(
                id=e["id"], target=e["target"], label=e["label"],
                direction=signed_direction(e.get("direction")), source_ids=tuple(e.get("source_ids", [])),
                relation=e["relation"], context=e["context"], claim_kind=e["claim_kind"]
            ) for e in row.get(key, []))
        result.append(Intervention(
            id=row["id"], name=row["name"], kind=row["kind"], summary=row["summary"],
            effects=effects("effects"), spillover=effects("spillover"),
            inventory_complete=row.get("inventory_complete", False), warnings=tuple(row.get("warnings", []))
        ))
    return result
