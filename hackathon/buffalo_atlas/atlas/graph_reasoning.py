"""Project sourced typed edges into the preserved MEDR5 numerical adapter."""
import copy
from .graph import validate_graph,build_graph
from .core import score_candidate

def score_from_graph(disease,candidate,graph=None,relationships=None):
    graph=build_graph(disease) if graph is None else graph
    validate_graph(graph)
    d=copy.deepcopy(disease);c=copy.deepcopy(candidate);used=[]
    causal=[e for e in graph['edges'] if e['source']==d['id'] and e['type']=='DISEASE_CAUSED_BY_GENE']
    for axis in d['signature']:
        edge=next((e for e in causal if e.get('target_symbol')==axis['target']),None)
        if edge:
            axis.update(direction=edge.get('causal_direction','unknown'),weight=edge.get('signature_weight',0),source_ids=edge['source_ids'])
            used.append(edge['id'])
        else:
            axis['source_ids']=[]
    mechanisms=[e for e in graph['edges'] if e['source']==c['id'] and 'mechanistic_effect' in e]
    for key in ('effects','spillover'):
        for effect in c.get(key,[]):
            edge=next((e for e in mechanisms if e.get('target_symbol')==effect['target']),None)
            if edge:
                effect.update(effect=edge['mechanistic_effect'],source_ids=edge['source_ids'])
                used.append(edge['id'])
            else:
                effect['source_ids']=[]
    node=next((n for n in graph['nodes'] if n['id']==c['id']),None)
    c['spillover_unknown']=node.get('spillover_unknown',True) if node else True
    row=score_candidate(d,c,relationships)
    row.update(reasoning_basis='Direction, coverage and spillover projected from cited typed graph edges; remaining deviation and experiment use this gated result.',graph_edge_ids=list(dict.fromkeys(used)))
    return row

def rank_from_graph(disease,graph,candidates):
    rows=[score_from_graph(disease,c,graph) for c in candidates if disease['id'] in c['disease_ids'] and c['role']=='repurposing_hypothesis']
    ranked=sorted([r for r in rows if r['eligible']],key=lambda r:(-r['frequent_flyer']['adjusted_priority'],r['id']))
    return dict(ranked=ranked,withheld=[r for r in rows if not r['eligible']],reason=None if ranked else 'No sourced, direction-aligned causal repurposing hypothesis is eligible in this curated pilot.')
