"""Pulse contract: discovered records remain outside reviewed therapeutic evidence."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION = "constellai-pulse-v1"


class PulseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecordChange(PulseModel):
    field: str
    before: str | None
    after: str | None


class DraftClaim(PulseModel):
    statement: str
    quote: str
    evidence_type: Literal["human_clinical", "preclinical", "mechanistic_inference", "unknown"]
    review_status: Literal["unreviewed"] = "unreviewed"


class PulseItem(PulseModel):
    id: str
    provider: Literal["europe_pmc", "clinicaltrials_gov"]
    kind: Literal["paper", "trial"]
    title: str
    url: str
    matched_genes: list[str]
    source_updated_on: str | None = None
    first_seen_at: str
    last_seen_at: str
    changed_at: str
    change_type: Literal["discovered", "updated"]
    review_status: Literal["unreviewed"] = "unreviewed"
    summary: str
    changes: list[RecordChange] = Field(default_factory=list)
    excerpt: str | None = None
    draft_claims: list[DraftClaim] = Field(default_factory=list)


class ProviderStatus(PulseModel):
    id: Literal["europe_pmc", "clinicaltrials_gov"]
    name: str
    state: Literal["pending", "ok", "partial", "error"]
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    record_count: int = Field(default=0, ge=0)
    error: str | None = None
    coverage: str


class PulseResponse(PulseModel):
    schema_version: Literal["constellai-pulse-v1"] = SCHEMA_VERSION
    state: Literal["pending", "running", "ok", "partial", "error", "disabled"]
    scheduler_enabled: bool
    scheduler_running: bool
    interval_hours: int = 6
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    next_check_at: str | None = None
    watchlist: list[str]
    providers: list[ProviderStatus]
    unreviewed_count: int = Field(ge=0)
    total_records: int = Field(ge=0)
    items: list[PulseItem]
    limitations: list[str]
