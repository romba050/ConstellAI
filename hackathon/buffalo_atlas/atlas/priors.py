"""Small cited evidence priors and local connectivity correction, not ML predictions."""
import math
from .data import dataset, valid_refs, provenance

PRIOR_WEIGHTS={'clinical_symptom_evidence':.80,'preclinical_mechanism':.30}

def repurposing_prior(disease_id, candidate_id, relationships=None):
    records=dataset().get('known_relationships',[]) if relationships is None else relationships
    rows=[r for r in records if r['disease_id']==disease_id and r['candidate_id']==candidate_id and valid_refs(r.get('source_ids'))]
    return dict(score=max((PRIOR_WEIGHTS.get(r['kind'],0) for r in rows),default=None),
                status='Cited direct-pair evidence' if rows else 'Unknown / no curated direct-pair evidence',
                relationships=rows,sources=provenance(list(dict.fromkeys(s for r in rows for s in r['source_ids']))) if rows else [],
                explanation='Disease-specific evidence prior: clinical symptom RCT 0.80; preclinical mechanism 0.30; no evidence = unknown. These are ordinal policy weights, not probabilities, clinical efficacy predictions or MEDR5 mechanistic fit. A known symptomatic effect does not imply causal restoration. No neighboring-disease treatment transfer.')

def frequent_flyer(candidate, mechanism_score, relationships=None):
    records=dataset().get('known_relationships',[]) if relationships is None else relationships
    diseases={r['disease_id'] for r in records if r['candidate_id']==candidate['id'] and valid_refs(r.get('source_ids'))}
    degree=len(diseases)
    factor=1/math.sqrt(max(1,degree))
    targets={e['target'] for e in candidate.get('effects',[])+candidate.get('spillover',[]) if valid_refs(e.get('source_ids'))}
    return dict(local_disease_degree=degree,recorded_target_breadth=len(targets),factor=round(factor,4),
                adjusted_priority=round(mechanism_score*factor,3) if mechanism_score is not None and mechanism_score>0 else mechanism_score,
                scope='Only curated cited pair records; not a global drug-degree inventory',
                explanation='Connectivity correction = positive mechanistic priority / sqrt(max(1, unique cited disease associations)). It can only decrease positive priority. Original mechanistic fit and clinical safety remain separate. Polypharmacology already incurs off-signature penalties; target count is not rewarded or penalized twice. Unknown/unrecorded links are not evidence of specificity.')
