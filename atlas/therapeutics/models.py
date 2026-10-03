"""Signed disease deviations and observed intervention effects, not binding predictions."""
from dataclasses import dataclass
import math


def signed_direction(value):
    """Return +1/-1 only for explicit direction; never give unknown partial credit."""
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if token in {"up", "gain", "gain_of_function", "overactive", "high", "elevated",
                 "increase", "activate", "restore", "boost", "agonize"}:
        return 1
    if token in {"down", "loss", "loss_of_function", "underactive", "low", "reduced",
                 "reduce", "inhibit", "suppress", "block", "antagonize"}:
        return -1
    return None


@dataclass(frozen=True)
class TherapeuticTarget:
    id: str
    label: str
    disease_direction: int | None
    weight: float
    source_ids: tuple[str, ...]
    context: str

    def __post_init__(self):
        if not math.isfinite(self.weight) or self.weight <= 0:
            raise ValueError("Target weights must be finite and positive")
        if self.disease_direction not in (None, -1, 1):
            raise ValueError("Direction must be signed or unknown")

    @property
    def desired_direction(self):
        return -self.disease_direction if self.disease_direction is not None else None


@dataclass(frozen=True)
class InterventionEffect:
    id: str
    target: str
    label: str
    direction: int | None
    source_ids: tuple[str, ...]
    relation: str
    context: str
    claim_kind: str = "direct_source_report"

    def __post_init__(self):
        if self.direction not in (None, -1, 1):
            raise ValueError("Effect must be signed or unknown")


@dataclass(frozen=True)
class Intervention:
    id: str
    name: str
    kind: str
    summary: str
    effects: tuple[InterventionEffect, ...]
    spillover: tuple[InterventionEffect, ...] = ()
    # A curated list is never assumed to be a complete selectivity inventory.
    inventory_complete: bool = False
    warnings: tuple[dict, ...] = ()
