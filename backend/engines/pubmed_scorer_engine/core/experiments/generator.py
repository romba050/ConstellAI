"""
Experiment generation logic
"""

def generate_experiments(hypothesis, decision_policy):
    """
    Generates experiments ONLY if allowed by policy.
    """

    if decision_policy["status"] == "DISCARDED":
        return {
            "experiments": [],
            "note": "Hypothesis discarded by decision gate. No experiments generated."
        }

    # cheap falsification only
    experiments = [
        {
            "type": "cheap_falsification",
            "estimated_cost_eur": 15000,
            "estimated_duration_weeks": 6,
            "kill_condition": "no_target_engagement"
        }
    ]

    return {
        "experiments": experiments
    }
