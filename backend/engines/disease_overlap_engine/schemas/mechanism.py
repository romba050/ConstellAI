
from pydantic import BaseModel, Field
from typing import Optional, Literal

Direction = Literal["activate", "inhibit", "unknown"]
ModelType = Literal["in_vitro", "in_vivo", "clinical", "unknown"]

class Mechanism(BaseModel):
    gene: str = Field(..., description="gene/protein symbol, normalized")
    pathway: str = Field(..., description="pathway cluster name (normalized)")
    direction: Direction = "unknown"
    domain: str = Field(..., description="oncology/diabetes/cardiology/immunology/metabolic/other")
    tissue: Optional[str] = None
    subtype: Optional[str] = None
    model: ModelType = "unknown"
    confidence: float = 0.6
    is_negative: bool = False
    source_snippet: Optional[str] = None
