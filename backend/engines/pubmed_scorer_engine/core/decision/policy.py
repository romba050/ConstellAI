def determine_policy(decision):
    """
    Decision policy for research triage.

    Rules:
    - APPROVED:
        score >= 0.40 AND risk <= 40%
    - CHEAP_TEST_ONLY:
        score >= 0.20 AND risk <= 60%
    - DISCARDED:
        everything else
    """

    score = decision.get("decision_support_score", 0.0)
    risk_pct = decision.get("non_translation_risk", 1.0) * 100

    if score >= 0.40 and risk_pct <= 40:
        return {
            "status": "APPROVED",
            "reason": "meets_score_and_risk_thresholds",
        }

    if score >= 0.20 and risk_pct <= 60:
        return {
            "status": "CHEAP_TEST_ONLY",
            "reason": "borderline_candidate",
        }

    return {
        "status": "DISCARDED",
        "reason": "below_threshold",
    }
