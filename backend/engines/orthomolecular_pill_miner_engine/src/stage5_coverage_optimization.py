# src/stage5_coverage_optimization.py
from itertools import combinations

# Primary RTKs for orthogonality bonus
PRIMARY_RTKS = {"KIT", "PDGFRA", "PDGFRB", "PDGFR", "BCRABL", "ABL1", "EGFR"}

def optimize_combination(candidates, drug_targets, risk_threshold=30, drug_name=""):
    """
    Greedy set-cover with bonuses:
    - coverage
    - orthogonality at primary RTKs
    - class-specific bonus (chemo/ROS, metabolic/AMPK)
    - small penalty for RTK compounds on non-RTK drugs
    """
    best_set = []
    best_score = -1
    best_risk = float('inf')

    # Simple drug-class detection
    drug_lower = drug_name.lower()
    is_chemo = any(word in drug_lower for word in ["doxorubicin", "paclitaxel", "cisplatin", "etoposide"])
    is_metabolic = any(word in drug_lower for word in ["metformin", "berberine"])

    print(f"Optimizing for {drug_name} (chemo={is_chemo}, metabolic={is_metabolic})")

    for r in range(1, min(4, len(candidates) + 1)):  # max 3 compounds
        for combo in combinations(candidates.keys(), r):
            covered = set()
            total_risk = 0
            for c in combo:
                covered.update(candidates[c]["targets"])
                total_risk += candidates[c]["risk"]

            cov = len(covered & drug_targets) / len(drug_targets) if drug_targets else 0

            # Orthogonality bonus (more primary RTKs covered by different compounds)
            primary_covered = {c for c in combo if any(t in candidates[c]["targets"] for t in PRIMARY_RTKS)}
            ortho_bonus = len(primary_covered) * 0.25 if len(combo) > 1 else 0

            # Class-specific bonus
            class_bonus = 0
            if is_chemo:
                if any(any(kw in t.lower() or kw in c.lower() for kw in ["ros", "top2", "apoptosis", "chemo"])
                       for c in combo for t in candidates[c]["targets"]):
                    class_bonus += 0.6
            if is_metabolic:
                if any(any(kw in t for kw in ["AMPK", "SIRT1", "FOXO", "mTOR"])
                       for c in combo for t in candidates[c]["targets"]):
                    class_bonus += 0.6

            # Small penalty for RTK compounds on non-RTK drugs
            rtk_penalty = 0
            if is_chemo or is_metabolic:
                rtk_count = sum(1 for c in combo if any(t in candidates[c]["targets"] for t in PRIMARY_RTKS))
                rtk_penalty = -0.2 * rtk_count

            score = cov + ortho_bonus + class_bonus + rtk_penalty

            # Update best if better score or same score + lower risk
            if score > best_score or (abs(score - best_score) < 0.01 and total_risk < best_risk):
                if total_risk <= risk_threshold:
                    best_score = score
                    best_risk = total_risk
                    best_set = list(combo)

    # Final cap just in case
    if len(best_set) > 3:
        best_set = best_set[:3]

    print(f"Selected stack: {best_set} (score {best_score:.2f}, risk {best_risk})")
    return best_set, best_score