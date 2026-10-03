def rank_proposals(proposals):
    return sorted(proposals, key=lambda item: item.get('institutional_score', 0), reverse=True)
