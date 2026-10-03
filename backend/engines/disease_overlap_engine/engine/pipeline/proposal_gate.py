
def evaluate(candidates, cfg):
    mode = cfg.get("mode", "exploratory")
    gate = cfg.get("proposal_gate", {})

    min_w = float(gate.get("exploratory_min_weighted_evidence", 1.4)) if mode == "exploratory" else float(gate.get("decision_min_weighted_evidence", 2.6))
    max_conflict = float(gate.get("max_direction_conflict", 0.45))
    max_neg = int(gate.get("max_negative_hits", 1)) if mode == "decision" else int(gate.get("max_negative_hits", 2))

    out = []
    for c in candidates:
        reasons = []
        if c["weighted_evidence"] < min_w:
            reasons.append("insufficient net evidence")
        if c["direction_conflict"] > max_conflict:
            reasons.append("directionality conflict across studies")
        if c["negative_hits"] > max_neg:
            reasons.append("too much negative evidence")

        if reasons:
            out.append({
                "status": "rejected" if mode == "decision" else "exploratory_signal",
                "pathway": c["pathway"],
                "domains": c["domains"],
                "weighted_evidence": c["weighted_evidence"],
                "risk_explanation": reasons,
                "supporting_mechanisms": c["supporting_mechanisms"],
            })
        else:
            out.append({
                "status": "proposed",
                "pathway": c["pathway"],
                "domains": c["domains"],
                "weighted_evidence": c["weighted_evidence"],
                "recommendation": "preclinical validation only",
                "supporting_mechanisms": c["supporting_mechanisms"],
            })
    return out
