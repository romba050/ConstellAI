# src/stage4_compound_overlap.py
from typing import Dict, Set

COMPOUND_DB = {
    "Apigenin": {
        "targets": ["KIT", "PDGFR", "AKT", "ERK"],
        "evidence": "Inhibits KIT and PDGFR autophosphorylation, suppresses downstream AKT/ERK",
        "role": "Dual RTK coverage with strong downstream convergence",
        "risk": 3
    },

    "Resveratrol": {
        "targets": ["SIRT1", "AMPK", "FOXO3", "MTOR"],
        "evidence": "Classic SIRT1 activator, indirect AMPK boost, mTOR inhibition",
        "role": "Metabolic/sirtuin axis coverage",
        "risk": 4
    },
    "Quercetin": {
        "targets": ["SIRT1", "AMPK", "FOXO3", "MTOR"],
        "evidence": "Activates AMPK/SIRT1, modulates FOXO3, mTOR suppression",
        "role": "Broad metabolic reprogramming",
        "risk": 3
    },
    "Curcumin": {
        "targets": ["PDGFR", "PDGFRA", "PDGFRB", "AKT", "ERK", "STAT3", "NFKB"],
        "evidence": "Interference with PDGF→PDGFR signaling; suppresses ERK/AKT readouts",
        "role": "PDGFR-side coverage + broad transcriptional stress/apoptosis",
        "risk": 6
    },
    "Diosmetin": {
        "targets": ["KIT", "AKT", "ERK"],
        "evidence": "Reported c-KIT signaling inhibition (kinase/cellular readouts)",
        "role": "KIT-side specificity (orthogonal to curcumin’s PDGFR bias)",
        "risk": 3
    },
    "Genistein": {
        "targets": ["KIT", "PDGFR", "AKT"],
        "evidence": "Tyrosine kinase inhibition on KIT/PDGFR",
        "role": "Dual RTK coverage",
        "risk": 4
    },
    "Berberine": {
        "targets": ["AMPK", "MTOR"],
        "evidence": "Strong AMPK activator, mTOR inhibition",
        "role": "Metabolic checkpoint coverage",
        "risk": 5
    },
    "Fisetin": {
        "targets": ["SIRT1", "AMPK", "MTOR"],
        "evidence": "SIRT1/AMPK activation, mTOR suppression",
        "role": "Senolytic + metabolic overlap",
        "risk": 3
    },
    "Quercetin": {  # already exists, but keep/enhance
        "targets": ["SIRT1", "AMPK", "FOXO3", "MTOR", "ROS", "TOP2A"],
        "evidence": "ROS modulation, topoisomerase inhibition, apoptosis induction in chemo models",
        "role": "ROS/apoptosis coverage + metabolic reprogramming",
        "risk": 3
    },
    "Resveratrol": {
        "targets": ["SIRT1", "AMPK", "FOXO3", "ROS"],
        "evidence": "ROS generation modulation, SIRT1 activation, synergistic with doxorubicin in cancer models",
        "role": "ROS and metabolic overlap",
        "risk": 4
    },
    "Epigallocatechin gallate": {  # EGCG
        "targets": ["ROS", "TOP2A", "AKT", "NFKB"],
        "evidence": "ROS induction, topoisomerase inhibition, NFKB suppression",
        "role": "Chemosensitization via ROS and anti-survival pathways",
        "risk": 5
    },
    # Add more as you like — the system will automatically pick the best stack
}

def find_overlapping_compounds(drug_targets: Set[str]):
    overlapping = {}
    print(f"  Checking overlap against {len(drug_targets)} targets: {drug_targets}")
    for name, data in COMPOUND_DB.items():
        overlap = set(data["targets"]) & drug_targets
        if overlap:
            overlapping[name] = {
                "targets": data["targets"],
                "overlap": list(overlap),
                "evidence": data["evidence"],
                "role": data["role"],
                "risk": data["risk"]
            }
            print(f"  Match: {name} overlaps on {list(overlap)}")
    return overlapping