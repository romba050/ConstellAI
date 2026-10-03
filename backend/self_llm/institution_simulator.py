def simulate_institutions(proposal_text):
    text = proposal_text.lower()
    institutions = {
        'academic_lab': {
            'keywords': ['reproducibility', 'experiment', 'method', 'data'],
            'score': 50,
        },
        'hospital_unit': {
            'keywords': ['clinical', 'safety', 'patient', 'traceability'],
            'score': 50,
        },
        'pharma_team': {
            'keywords': ['target', 'validation', 'mechanism', 'assay'],
            'score': 50,
        },
        'biotech_startup': {
            'keywords': ['automation', 'speed', 'pipeline', 'optimization'],
            'score': 50,
        },
        'rare_disease_foundation': {
            'keywords': ['rare', 'genetic', 'orphan', 'therapy'],
            'score': 50,
        },
    }
    results = {}
    for name, data in institutions.items():
        score = data['score']
        for keyword in data['keywords']:
            if keyword in text:
                score += 10
        results[name] = min(score, 100)
    avg = sum(results.values()) / len(results)
    return {'institution_scores': results, 'average_score': round(avg, 1)}
