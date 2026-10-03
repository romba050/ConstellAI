"""Tiny frozen positive-link ablation. No training or embeddings; abstentions count."""
import copy
from .data import dataset, disease_by_id, valid_refs
from .core import score_candidate

def evaluate(mode='relation_only'):
    if mode not in {'relation_only','source_disjoint'}:
        raise ValueError('Unknown benchmark mode')
    data=dataset();positives=[r for r in data['known_relationships'] if valid_refs(r['source_ids'])]
    folds=[]
    for held in positives:
        records=[r for r in positives if (r['candidate_id'],r['disease_id'])!=(held['candidate_id'],held['disease_id'])]
        pool=copy.deepcopy(data['interventions'])
        for c in pool:
            # Never prefilter the pool using the known positive disease membership.
            c['disease_ids']=[]
            if mode=='source_disjoint':
                withheld=set(held['source_ids'])
                for key in ('effects','spillover','risk'):
                    for effect in c.get(key,[]):
                        effect['source_ids']=[s for s in effect.get('source_ids',[]) if s not in withheld]
                c['source_ids']=[s for s in c['source_ids'] if s not in withheld]
        d=disease_by_id(held['disease_id'])
        rows=[score_candidate(d,c,records) for c in pool]
        eligible=sorted([r for r in rows if r['eligible']],key=lambda r:(-r['frequent_flyer']['adjusted_priority'],r['id']))
        ranked_ids=[r['id'] for r in eligible]
        target=next(r for r in rows if r['id']==held['candidate_id'])
        rank=ranked_ids.index(held['candidate_id'])+1 if held['candidate_id'] in ranked_ids else None
        # Also check whether this candidate is eligible for the wrong pilot disease.
        candidate=next(c for c in pool if c['id']==held['candidate_id'])
        wrong=[other['id'] for other in data['diseases'] if other['id']!=d['id'] and score_candidate(other,candidate,records)['eligible']]
        folds.append(dict(candidate_id=held['candidate_id'],disease_id=held['disease_id'],kind=held['kind'],
                          held_source_ids=held['source_ids'],prior_after_withholding=target['repurposing_prior']['score'],
                          rank=rank,eligible_pool_size=len(eligible),candidate_pool_size=len(pool),wrong_disease_eligible=wrong,
                          gate_reason=target['gate_reason'],claim=held['claim']))
    n=len(folds)
    strata={}
    for kind in sorted({f['kind'] for f in folds}):
        group=[f for f in folds if f['kind']==kind]
        strata[kind]=dict(n=len(group),hit_at_1=sum(f['rank']==1 for f in group)/len(group),
                         hit_at_3=sum(f['rank'] is not None and f['rank']<=3 for f in group)/len(group),
                         mrr=sum(1/f['rank'] if f['rank'] else 0 for f in group)/len(group),abstentions=sum(f['rank'] is None for f in group))
    return dict(mode=mode,folds=folds,n=n,strata=strata,hit_at_1=sum(f['rank']==1 for f in folds)/n if n else None,
                hit_at_3=sum(f['rank'] is not None and f['rank']<=3 for f in folds)/n if n else None,
                mrr=sum(1/f['rank'] if f['rank'] else 0 for f in folds)/n if n else None,
                abstentions=sum(f['rank'] is None for f in folds),wrong_disease_eligible=sum(len(f['wrong_disease_eligible']) for f in folds),
                limitations='Four frozen curated positives: three preclinical mechanism observations and one clinical symptom RCT. Not four proven disease-modifying repurposing successes. No trained model, broad negative set, tuning or clinical generalization claim. Relation-only ablation retains mechanism features derived from the same positive sources and therefore leaks source-derived information; source-disjoint mode removes those source refs from scored features and measures honest abstention. Pool is tiny; ranking recovery is a diagnostic only.')

def report():
    return dict(relation_only=evaluate('relation_only'),source_disjoint=evaluate('source_disjoint'))

if __name__=='__main__':
    import json
    print(json.dumps(report(),indent=2))
