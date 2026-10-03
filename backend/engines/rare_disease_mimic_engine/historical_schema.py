from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


EvidenceLevel = Literal["low", "medium", "high", "unknown"]
OutcomeLabel = Literal["failed", "partial", "successful", "mixed", "unknown"]
RoleLabel = Literal["discovery", "first_medicine", "improved_medicine", "failure", "pattern"]
StudyKind = Literal["case_report", "mechanistic", "preclinical", "clinical", "review", "unknown"]


class HistoricalSource(BaseModel):
    source_id: str
    title: str
    year: Optional[int] = None
    kind: StudyKind = "unknown"
    citation: str = ""
    notes: str = ""


class TargetHypothesis(BaseModel):
    target: str
    direction: str = "unknown"
    rationale: str = ""
    confidence: EvidenceLevel = "unknown"
    source_ids: List[str] = Field(default_factory=list)


class DiscoveryThinking(BaseModel):
    year: Optional[int] = None
    doctor_researcher_view: str = ""
    suspected_mechanism: str = ""
    dominant_symptom_model: str = ""
    suspected_targets: List[TargetHypothesis] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    source_ids: List[str] = Field(default_factory=list)


class FailureSetback(BaseModel):
    label: str
    phase: str = ""
    year: Optional[int] = None
    reason: str = ""
    consequence: str = ""
    lesson: str = ""
    source_ids: List[str] = Field(default_factory=list)


class MedicineDesignLogic(BaseModel):
    medicine_name: str
    year_started: Optional[int] = None
    year_first_used: Optional[int] = None
    medicine_type: str = ""
    role: RoleLabel = "first_medicine"
    why_created: str = ""
    target_logic: List[TargetHypothesis] = Field(default_factory=list)
    mechanism_summary: str = ""
    expected_benefit: str = ""
    why_better_than_previous: str = ""
    limitations: List[str] = Field(default_factory=list)
    outcome: OutcomeLabel = "unknown"
    source_ids: List[str] = Field(default_factory=list)


class DiseaseToDrugPattern(BaseModel):
    pattern_id: str
    pattern_summary: str
    trigger_features: List[str] = Field(default_factory=list)
    first_medicine_logic: str = ""
    improvement_logic: str = ""
    failure_logic: str = ""
    reusable_rule: str = ""
    confidence: EvidenceLevel = "unknown"
    source_ids: List[str] = Field(default_factory=list)


class HistoricalReplayCase(BaseModel):
    case_id: str
    disease_name: str
    discovery_year: Optional[int] = None
    disease_group: str = "rare_disease"
    summary: str = ""
    discovery: DiscoveryThinking = Field(default_factory=DiscoveryThinking)
    first_medicine: Optional[MedicineDesignLogic] = None
    later_medicines: List[MedicineDesignLogic] = Field(default_factory=list)
    failures: List[FailureSetback] = Field(default_factory=list)
    patterns: List[DiseaseToDrugPattern] = Field(default_factory=list)
    sources: List[HistoricalSource] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class ReplayPredictionInput(BaseModel):
    disease_name: str
    discovery_year: Optional[int] = None
    candidate_features: List[str] = Field(default_factory=list)
    suspected_targets: List[TargetHypothesis] = Field(default_factory=list)
    notes: str = ""


class ReplayPredictionResult(BaseModel):
    replay_id: str
    input: ReplayPredictionInput
    matched_case_ids: List[str] = Field(default_factory=list)
    matched_pattern_ids: List[str] = Field(default_factory=list)
    predicted_first_medicine_logic: str = ""
    predicted_improvement_logic: str = ""
    predicted_failure_logic: str = ""
    confidence: EvidenceLevel = "unknown"
    hit: Optional[bool] = None
    hit_explanation: str = ""
    stored_logic_note: str = ""
    created_at: str = Field(default_factory=utc_now_iso)


class ReplayMemoryBank(BaseModel):
    schema_version: str = "historical_replay_v1"
    window_start_year: int = 1970
    window_end_year: int = 2005
    training_goal: str = (
        "replay historical rare-disease discovery to medicine-creation logic, "
        "store hit logic, then reuse patterns for new rare diseases"
    )
    cases: List[HistoricalReplayCase] = Field(default_factory=list)
    replay_runs: List[ReplayPredictionResult] = Field(default_factory=list)
    pattern_index: Dict[str, List[str]] = Field(default_factory=dict)
    metadata: Dict[str, str] = Field(default_factory=dict)
