def fetch_pubmed(target):
    return [
        {"source":"pubmed_123","species":"human","year":2021,"endpoint":"surrogate","weight":0.35,"limitation":"small cohort"},
        {"source":"pubmed_456","species":"mouse","year":2019,"endpoint":"tumor size","weight":0.30,"limitation":"animal model"}
    ]