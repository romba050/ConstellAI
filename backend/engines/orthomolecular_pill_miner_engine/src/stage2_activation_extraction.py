# src/stage2_activation_extraction.py
import re
from collections import Counter

# Expanded list of oncology-relevant targets (will be auto-detected from abstracts)
ONCOLOGY_TARGETS = [
    "KIT", "PDGFRA", "PDGFRB", "PDGFR", "BCRABL", "ABL1", "EGFR", "HER2", "VEGFR",
    "PI3K", "AKT", "MTOR", "RAS", "RAF", "MEK", "ERK", "MAPK", "JAK", "STAT3", "STAT5",
    "SIRT1", "AMPK", "FOXO3", "NFKB", "P53", "MYC", "BCL2", "BAX", "CASP3", "PDL1"
]

def extract_activations(papers, min_freq=3):
    all_text = " ".join(p["text"].upper() for p in papers)
    counts = Counter()
    for gene in ONCOLOGY_TARGETS:
        count = len(re.findall(r'\b' + gene + r'\b', all_text))
        if count >= min_freq:
            counts[gene] = count
    targets = set(counts.keys())
    print(f"Extracted {len(targets)} modulated targets (freq ≥ {min_freq}): {targets}")
    return targets