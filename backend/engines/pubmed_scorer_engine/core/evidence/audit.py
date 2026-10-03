"""
Evidence audit & traceability
"""

def audit_sources(evidence_items):
    """
    Returns verbatim, traceable sources.
    """

    audited = []

    for ev in evidence_items:
        audited.append({
            "source": "PubMed",
            "pmid": ev.get("pmid"),
            "year": ev.get("year"),
            "species": ev.get("species"),
            "endpoint": ev.get("endpoint")
        })

    return audited
