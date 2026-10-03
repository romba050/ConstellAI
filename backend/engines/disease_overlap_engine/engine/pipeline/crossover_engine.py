
from collections import defaultdict

def _direction_conflict_ratio(items):
    acts = sum(1 for i in items if i.get("direction") == "activate")
    inh = sum(1 for i in items if i.get("direction") == "inhibit")
    total = acts + inh
    if total == 0:
        return 0.0
    frac = acts / total
    return min(frac, 1.0 - frac)

def find(mechanisms, cfg):
    buckets = defaultdict(list)
    for m in mechanisms:
        buckets[m.pathway].append(m)

    cands = []
    for pathway, items in buckets.items():
        domains = sorted(set(i.domain for i in items))
        if len(domains) < 2:
            continue

        weighted = sum(float(i.confidence) * (-1.0 if i.is_negative else 1.0) for i in items)
        neg = sum(1 for i in items if i.is_negative)

        d_items = [i.model_dump() for i in items]
        conflict = _direction_conflict_ratio(d_items)

        cands.append({
            "pathway": pathway,
            "domains": domains,
            "weighted_evidence": float(weighted),
            "negative_hits": int(neg),
            "direction_conflict": float(conflict),
            "supporting_mechanisms": d_items[:12],
        })

    cands.sort(key=lambda c: c["weighted_evidence"], reverse=True)
    return cands
