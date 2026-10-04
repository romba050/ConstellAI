"""Frozen constellai-analysis-v1 contract shared by API, mock, and frontend."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EvidenceType = Literal[
    "human_clinical", "human_observational", "preclinical",
    "mechanistic_inference", "regulatory_label", "trial_registry",
    "disease_reference", "official_resource", "unknown",
]
CandidateStatus = Literal[
    "supported_candidate", "research_hypothesis", "rejected", "insufficient_evidence",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class AnalyzeRequest(ContractModel):
    disease: str = Field(min_length=1, max_length=200)
    gene: str | None = Field(default=None, max_length=40)
    variant: str | None = Field(default=None, max_length=200)
    use_openai: bool = False


class Source(ContractModel):
    id: str
    title: str
    url: str
    evidence_type: EvidenceType
    reviewed_on: str
    scope: str
    excerpt: str = ""


class Claim(ContractModel):
    summary: str
    evidence_type: EvidenceType
    source_ids: list[str]


class Assessment(Claim):
    # Curated ordinal rating used by the disclosed heuristic, never an efficacy estimate.
    # Null means unreviewed/unknown; the ranking engine applies an explicit missing-data policy.
    value: float | None = Field(ge=0, le=1)


class Disease(ContractModel):
    id: str | None
    name: str
    source_ids: list[str]


class VariantEffect(Claim):
    effect: Literal[
        "variant_dependent", "loss_of_function", "gain_of_function",
        "dominant_negative", "unknown",
    ]
    scope: Literal["disease_context", "variant_specific", "unresolved"]


class ScoreTerm(ContractModel):
    component: str
    weight: float
    input_value: float | None
    used_value: float
    contribution: float
    missing_policy: str


class ScoreBreakdown(ContractModel):
    positive_components: list[ScoreTerm]
    risk_penalties: list[ScoreTerm]
    positive_total: float
    penalty_total: float
    unclamped_score: float
    final_score: float = Field(ge=0, le=100)
    formula: str
    config_version: str
    interpretation: str


class Candidate(ContractModel):
    id: str
    compound_name: str
    therapeutic_role: Literal["mechanism_targeting", "symptom_targeting", "research_tool"]
    mechanism_of_action: Claim
    mechanism_alignment: Assessment
    variant_effect_compatibility: Assessment
    human_evidence: Assessment
    preclinical_evidence: Assessment
    phenotype_relevance: Assessment
    evidence_quality: Assessment
    toxicity: Assessment
    organ_burden: Assessment
    drug_interactions: Assessment
    off_target_spillover: Assessment
    uncertainty: Assessment
    sources: list[Source]
    final_score: float = Field(ge=0, le=100)
    status: CandidateStatus
    rationale: str
    next_validation_step: str
    score_breakdown: ScoreBreakdown
    rank: int | None = Field(ge=1)


class RelatedDisease(ContractModel):
    disease: Disease
    gene: str
    shared_mechanism: Claim
    key_difference: Claim
    research_use: str
    atlas_url: str


class Experiment(ContractModel):
    title: str
    question: str
    design: str
    readouts: list[str]
    falsification: str
    prerequisites: list[str]
    source_ids: list[str]
    status: Literal["proposed_research", "expert_review_required"]


class CollaboratorAsset(ContractModel):
    name: str
    kind: Literal["patient_group", "study", "investigator", "published_model", "resource"]
    description: str
    url: str
    source_ids: list[str]
    access_status: str


class LLMProvenance(ContractModel):
    mode: Literal["cached_evidence", "openai_verified", "fallback"]
    model: str | None
    detail: str
    verified_claims: list[Claim]


class AnalyzeResponse(ContractModel):
    schema_version: Literal["constellai-analysis-v1"]
    disease: Disease
    gene: str | None
    variant: str | None
    variant_effect: VariantEffect
    functional_mechanism: Claim
    pathway: Claim
    candidate_treatments: list[Candidate]
    related_disease_evidence: list[RelatedDisease]
    recommended_next_experiment: Experiment
    collaborators_or_assets: list[CollaboratorAsset]
    sources: list[Source]
    conclusion: str
    best_hypothesis_id: str | None
    analysis_status: Literal["research_hypotheses_found", "insufficient_evidence"]
    limitations: list[str]
    evidence_reviewed_on: str
    llm: LLMProvenance
