from dataclasses import dataclass
from typing import Dict, List

@dataclass
class MedicalHypothesis:
    hypothesis_id: str
    claim: str
    target: str
    indication: str
    priors: Dict
    falsifiers: List[str]