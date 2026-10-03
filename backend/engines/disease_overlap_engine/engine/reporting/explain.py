
def humanize(result, cfg):
    mode = cfg.get("mode", "exploratory")
    p = result.get("pathway")
    doms = ", ".join(result.get("domains", []))
    score = float(result.get("weighted_evidence", 0.0))

    if result.get("status") == "proposed":
        return {
            "status": "proposed",
            "headline": f"{p} shows cross-domain convergence ({doms})",
            "why": f"weighted evidence {score:.2f} passed gate in mode={mode}",
            "what_next": "treat as hypothesis only; suggest preclinical validation planning"
        }

    if result.get("status") == "exploratory_signal":
        return {
            "status": "exploratory_signal",
            "headline": f"weak crossover signal on {p} ({doms})",
            "why_not": result.get("risk_explanation", []),
            "note": "exploratory signal is not a recommendation; raise evidence density before acting"
        }

    return {
        "status": "rejected",
        "headline": f"{p} rejected for decision mode ({doms})",
        "why_not": result.get("risk_explanation", []),
        "note": "rejected means insufficient support for decision-grade commitment"
    }
