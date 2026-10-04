"""Deterministic curator-rating heuristic, separate from medical eligibility.

Scores are research-priority points. They are neither efficacy probabilities
nor validated clinical predictions. A high score never overrides an evidence
abstention, a rejected candidate, or an unresolved variant.
"""
import json
import math
from pathlib import Path

from .models import Assessment, Candidate, ScoreBreakdown, ScoreTerm

WEIGHTS_FILE = Path(__file__).with_name("weights.json")
POSITIVE_COMPONENTS = (
    "mechanism_alignment", "variant_effect_compatibility", "human_evidence",
    "preclinical_evidence", "phenotype_relevance", "evidence_quality",
)
RISK_COMPONENTS = (
    "toxicity_organ_burden", "drug_interactions", "off_target_spillover", "uncertainty",
)
INTERPRETATION = (
    "Ordinal curator ratings produce an auditable research-priority heuristic; "
    "this score is not a probability, an efficacy estimate, or a validated clinical model."
)


def load_weights(path=WEIGHTS_FILE):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_weights(config)
    return config


def validate_weights(config):
    if set(config["positive"]) != set(POSITIVE_COMPONENTS) or set(config["risk"]) != set(RISK_COMPONENTS):
        raise ValueError("Scoring config must contain the six positives and four disclosed risks")
    for values in (config["positive"].values(), config["risk"].values()):
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0
               for v in values):
            raise ValueError("Scoring weights must be finite nonnegative numbers")
    if config["unknown_positive_value"] != 0 or config["unknown_risk_value"] != 1:
        raise ValueError("Missing-data policy must be zero positive credit and full unknown risk")
    if not 0 <= config["research_threshold"] <= config["supported_threshold"] <= 100:
        raise ValueError("Invalid scoring thresholds")
    if not isinstance(config["config_version"], str) or not config["config_version"]:
        raise ValueError("Scoring config must have a version")


def _assessment(candidate, field):
    value = candidate[field] if isinstance(candidate, dict) else getattr(candidate, field)
    return value if isinstance(value, Assessment) else Assessment.model_validate(value)


def score_candidate(candidate, weights=None):
    """Score only disclosed assessments; the model cannot contribute a score."""
    config = load_weights() if weights is None else weights
    validate_weights(config)
    positive = []
    for component in POSITIVE_COMPONENTS:
        input_value = _assessment(candidate, component).value
        used = config["unknown_positive_value"] if input_value is None else input_value
        weight = float(config["positive"][component])
        positive.append(ScoreTerm(
            component=component, weight=weight, input_value=input_value, used_value=used,
            contribution=round(weight * used, 6), missing_policy="Unknown positive evidence receives zero credit.",
        ))
    risks = []
    for component in RISK_COMPONENTS:
        if component == "toxicity_organ_burden":
            values = [_assessment(candidate, field).value for field in ("toxicity", "organ_burden")]
            input_value = max(values) if all(v is not None for v in values) else None
            used = max(config["unknown_risk_value"] if v is None else v for v in values)
            policy = "Unknown risk receives full penalty; toxicity and organ burden share the worse rating."
        else:
            input_value = _assessment(candidate, component).value
            used = config["unknown_risk_value"] if input_value is None else input_value
            policy = "Unknown risk receives its full configured penalty."
        weight = float(config["risk"][component])
        risks.append(ScoreTerm(
            component=component, weight=weight, input_value=input_value, used_value=used,
            contribution=round(weight * used, 6), missing_policy=policy,
        ))
    positive_total = round(sum(t.contribution for t in positive), 6)
    penalty_total = round(sum(t.contribution for t in risks), 6)
    unclamped = round(positive_total - penalty_total, 6)
    return ScoreBreakdown(
        positive_components=positive, risk_penalties=risks,
        positive_total=positive_total, penalty_total=penalty_total,
        unclamped_score=unclamped, final_score=min(100.0, max(0.0, unclamped)),
        formula="clamp(sum(weight * positive rating) - sum(weight * risk severity), 0, 100)",
        config_version=config["config_version"], interpretation=INTERPRETATION,
    )


def rank_candidates(candidates: list[Candidate], weights=None):
    """Downgrade failed evidence gates, then rank eligible candidates stably.

    Curator rejection/insufficient classifications are never promoted. Thresholds
    can only downgrade a classification; score alone cannot support a therapy.
    """
    config = load_weights() if weights is None else weights
    validate_weights(config)
    reviewed = []
    for original in candidates:
        c = original.model_copy(deep=True)
        c.rank = None
        if c.status in {"supported_candidate", "research_hypothesis"}:
            eligible = (
                c.mechanism_alignment.value is not None and c.mechanism_alignment.value > 0
                and bool(c.mechanism_alignment.source_ids)
                and c.variant_effect_compatibility.value is not None and c.variant_effect_compatibility.value > 0
                and bool(c.variant_effect_compatibility.source_ids)
                and bool(c.mechanism_of_action.source_ids)
            )
            if not eligible or c.final_score < config["research_threshold"]:
                c.status = "insufficient_evidence"
                c.rationale += " Eligibility withheld: evidence gates or the research threshold were not met."
            elif c.status == "supported_candidate" and (
                c.final_score < config["supported_threshold"]
                or c.human_evidence.value is None or c.human_evidence.value <= 0
                or c.human_evidence.evidence_type not in {"human_clinical", "human_observational"}
                or not c.human_evidence.source_ids
            ):
                c.status = "research_hypothesis"
                c.rationale += " Support classification reduced: the supported-evidence gate was not met."
        reviewed.append(c)
    eligible = [c for c in reviewed if c.status in {"supported_candidate", "research_hypothesis"}]
    ineligible = [c for c in reviewed if c.status not in {"supported_candidate", "research_hypothesis"}]
    tie_key = lambda c: (-c.final_score, c.id.casefold(), c.id, c.compound_name.casefold())
    eligible.sort(key=tie_key)
    ineligible.sort(key=tie_key)
    for rank, candidate in enumerate(eligible, 1):
        candidate.rank = rank
    return eligible + ineligible
