
import json
import re
from typing import List

from pydantic import ValidationError
from schemas.mechanism import Mechanism
from engine.llm.llm_client import generate as llm_generate

# fallback regex extractor (conservative)
GENE_ALIASES = {
    "AMPK": ["ampk", "amp activated protein kinase", "amp-activated protein kinase"],
    "MTOR": ["mtor", "mammalian target of rapamycin"],
    "ULK1": ["ulk1", "unc-51 like autophagy activating kinase 1"],
    "SESTRIN2": ["sestrin2", "sestrin 2"],
    "PI3K": ["pi3k", "phosphoinositide 3-kinase"],
    "AKT": ["akt", "protein kinase b"],
}

def _norm(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def _detect_domain(t: str) -> str:
    if any(k in t for k in ["diabetes", "metformin", "insulin", "glucose", "sglt2"]): return "diabetes"
    if any(k in t for k in ["immune", "immuno", "cytokine", "autoimmun"]): return "immunology"
    if any(k in t for k in ["cardio", "heart", "vascular", "myocard"]): return "cardiology"
    if any(k in t for k in ["cancer", "tumor", "carcinoma", "neoplasm"]): return "oncology"
    if any(k in t for k in ["metabolic", "obese", "lipid", "masld", "fatty liver", "energy metabolism"]): return "metabolic"
    return "other"

def _detect_model(t: str) -> str:
    if any(k in t for k in ["mouse", "murine", "rat"]): return "in_vivo"
    if any(k in t for k in ["clinical", "patient", "randomized"]): return "clinical"
    if any(k in t for k in ["cell line", "in vitro", "organoid"]): return "in_vitro"
    return "unknown"

def _fallback_extract(paper: str, max_out: int) -> List[Mechanism]:
    t = _norm(paper)
    out = []
    for gene, aliases in GENE_ALIASES.items():
        if any(a in t for a in aliases):
            direction = "unknown"
            if any(k in t for k in ["inhibit", "suppression", "downregulat"]): direction = "inhibit"
            elif any(k in t for k in ["activate", "activation", "upregulat"]): direction = "activate"
            is_negative = any(k in t for k in ["no effect", "failed", "toxicity", "adverse", "no significant"])
            conf = 0.8 if "significant" in t else 0.6
            if is_negative: conf -= 0.2
            out.append(Mechanism(
                gene=gene,
                pathway=gene,  # clustered later
                direction=direction,
                domain=_detect_domain(t),
                model=_detect_model(t),
                confidence=max(0.0, min(float(conf), 1.0)),
                is_negative=is_negative,
                source_snippet=paper[:280]
            ))
            if len(out) >= max_out:
                break
    return out

# llm extraction (json only)
SYSTEM_RULES = (
    "you are a biomedical information extraction system. "
    "return only valid json. no markdown. no commentary. no trailing text."
)

JSON_SCHEMA_HINT = """output json schema:
{
  "mechanisms": [
    {
      "gene": "string (normalized gene symbol like AMPK, MTOR, ULK1, SESTRIN2, PI3K, AKT, etc.)",
      "pathway": "string (normalized pathway or axis label, e.g. energy_sensing_axis, pi3k_akt_axis, igf_axis, etc.)",
      "direction": "activate|inhibit|unknown",
      "domain": "oncology|diabetes|cardiology|immunology|metabolic|other",
      "tissue": "string or null",
      "subtype": "string or null",
      "model": "in_vitro|in_vivo|clinical|unknown",
      "confidence": "float 0..1",
      "is_negative": "true|false",
      "source_snippet": "short supporting excerpt"
    }
  ]
}
"""

def _llm_extract_one(paper: str, cfg) -> List[Mechanism]:
    max_out = int(cfg.get("extraction", {}).get("max_mechanisms_per_paper", 8))
    prompt = (
        SYSTEM_RULES + "\n\n" +
        JSON_SCHEMA_HINT + "\n\n" +
        "extract mechanisms from this abstract. include only mechanisms explicitly supported. "
        "if none, return {\"mechanisms\": []}.\n\n" +
        "abstract:\n" + paper.strip()[:5000]
    )

    txt = (llm_generate(cfg, prompt) or "").strip()

    try:
        data = json.loads(txt)
    except Exception:
        return []

    mechs = data.get("mechanisms", [])
    out: List[Mechanism] = []
    for m in mechs[:max_out]:
        try:
            out.append(Mechanism(**m))
        except ValidationError:
            continue
    return out

def extract(papers, cfg) -> List[Mechanism]:
    max_out = int(cfg.get("extraction", {}).get("max_mechanisms_per_paper", 8))
    min_conf = float(cfg.get("extraction", {}).get("min_confidence", 0.55))
    llm_enabled = bool(cfg.get("llm", {}).get("enabled", False))

    all_mechs: List[Mechanism] = []
    for p in papers:
        if not p or len(p) < 40:
            continue

        ms = _llm_extract_one(p, cfg) if llm_enabled else []
        if not ms:
            ms = _fallback_extract(p, max_out=max_out)

        for m in ms:
            if float(m.confidence) >= min_conf:
                all_mechs.append(m)

    return all_mechs
