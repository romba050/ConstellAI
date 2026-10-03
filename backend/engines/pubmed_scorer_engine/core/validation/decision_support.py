"""
Medical-grade decision support scoring + hard gate
"""

def evaluate_decision_support(evidence_items):
    """
    Computes:
    - decision_support_score (0.0–1.0)
    - non_translation_risk (0.0–1.0)
    """

    if not evidence_items:
        return {
            "decision_support_score": 0.0,
            "non_translation_risk": 1.0,
            "gate_passed": False,
            "gate_reason": "no_evidence"
        }

    score = 0.0
    risk = 0.5

    for ev in evidence_items:
        if ev.get("species") == "human":
            score += 0.15
            risk -= 0.05
        elif ev.get("species") == "animal":
            score += 0.05
            risk += 0.05
        else:
            risk += 0.1

    score = min(score, 1.0)
    risk = min(max(risk, 0.0), 1.0)

    gate_passed, gate_reason = apply_hard_gate(score, risk)

    return {
        "decision_support_score": round(score, 2),
        "non_translation_risk": round(risk, 2),
        "gate_passed": gate_passed,
        "gate_reason": gate_reason
    }


def apply_hard_gate(decision_support_score, non_translation_risk):
    """
    HARD GOVERNANCE GATE
    """

    if decision_support_score < 0.60:
        return False, "decision_support_score_below_0.60"

    if non_translation_risk > 0.40:
        return False, "non_translation_risk_above_0.40"

    return True, "pass"
