def estimate_institutional_score(text):
    score = 50
    keywords = {
        'audit': 10,
        'traceability': 10,
        'reproducibility': 10,
        'evidence': 8,
        'clinical': 8,
        'safety': 6,
        'validation': 6,
        'workflow': 4,
        'institution': 4,
    }
    lower = text.lower()
    for key, value in keywords.items():
        if key in lower:
            score += value
    return min(score, 100)
