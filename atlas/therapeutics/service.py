"""Deterministic API service; no LLM, network requests or graph mutation."""
import os

from .adapter import adapt_disease, target_view
from .evidence import ROOT, interventions, registry
from .scoring import complementary_candidates, score_candidate

UI_ROOT = ROOT / "ui"


def ui_enabled():
    return os.getenv("MEDR5_THERAPEUTICS_ENABLED", "").strip().lower() in {"1", "true"}


def opportunities(disease, variant=None, mechanism=None):
    adapted = adapt_disease(disease, variant=variant, mechanism=mechanism)
    evidence = registry()
    targets = adapted.pop("targets")
    pool = interventions(adapted["profile_id"]) if adapted["profile_id"] else []
    rows = [score_candidate(targets, intervention, evidence, adapted["unresolved"]) for intervention in pool]
    ranked = sorted([row for row in rows if row["ranking_status"] == "provisional"],
                    key=lambda row: (-row["mechanistic_fit"]["score"], row["candidate_intervention"]["id"]))
    for rank, row in enumerate(ranked, 1):
        row["rank"] = rank
    return {
        "schema_version": "medr5-therapeutics-v1", **adapted,
        "signed_targets": [target_view(target, evidence) for target in targets],
        "candidates": ranked + [row for row in rows if row not in ranked],
        "complementary": complementary_candidates(targets, ranked[0] if ranked else None, rows),
        "evidence_scope": "Small, curator-reviewed MEDR5 pilot. No broad drug-target database was inferred from atlas similarity.",
        "method": {
            "name": "MEDR5 signed therapeutic coverage",
            "formula": "desired coverage - 0.85 * wrong-direction weight fraction - 0.22 * listed off-signature mechanisms",
            "unknown_policy": "Missing/conflicting direction or mechanistic provenance withholds the fit score and ranking.",
            "ranking": "Existing medicines with positive known-effect fit only; research comparators stay separate. All ranks are provisional.",
            "evidence_policy": "Evidence type/design/sample size/uncertainty are displayed separately; journal prestige is not a weight.",
        },
    }
