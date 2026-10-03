from .data import dataset, disease_by_id, sources, provenance
from .graph import build_graph
from .core import rank_repurposing_candidates, rank_complementary_candidates, find_mechanistic_surrogates, propose_next_experiment, score_candidate
from .benchmark import report
from .graph_reasoning import score_from_graph,rank_from_graph

def disease_bundle(id):
    disease=disease_by_id(id)
    if disease is None:
        raise ValueError('Disease not in curated pilot')
    graph=build_graph(disease)
    ranking=rank_from_graph(disease,graph,dataset()['interventions'])
    primary=ranking['ranked'][0] if ranking['ranked'] else None
    trials=[t for t in dataset()['trials'] if t['disease']==id]
    org=sources()[disease['organization']]
    patient=[dict(title='Connect with the patient organization',text=org['source'],url=org['source_url'],source_ids=[org['id']]),
             dict(title='Bring a cited disease overview to a treating clinician',text='Use this overview to discuss questions; it is not a treatment recommendation.',url=sources()[disease['source_ids'][0]]['source_url'],source_ids=disease['source_ids'])]
    for trial in trials:
        patient.append(dict(title='Review the registered study',text=trial['id']+' · '+trial['status'].replace('_',' ').lower()+
                ' · checked '+dataset()['retrieved_at']+'. Recheck registry and contact the study team; no eligibility claim.',url=sources()[trial['id']]['source_url'],source_ids=trial['source_ids']))
    researcher=[dict(title='Top repurposing hypothesis' if primary else 'Resolve the evidence gap',text=primary['name']+' — '+primary['summary'] if primary else ranking['reason']),
                dict(title='Evidence required before advancing',text='Independent model replication, functional rescue, exposure/delivery and context-specific toxicology. Mechanistic fit does not establish clinical safety.'),
                dict(title='Patient-powered program resources',text='Explore Buffalo Initiative resources; no pilot-specific Buffalo affiliation is asserted.',url=sources()['buffalo']['source_url'])]
    comparisons=[score_from_graph(disease,c,graph) for c in dataset()['interventions'] if id in c['disease_ids']]
    hero=dataset()['hero_journey'] if id=='angelman' else None
    programmes=[dict(p,provenance=provenance(p['source_ids'])) for p in dataset().get('research_programmes',[]) if p['disease_id']==id]
    resources=provenance(disease.get('patient_resource_ids',[])) if disease.get('patient_resource_ids') else []
    graph_refs=list(dict.fromkeys(r for item in graph['nodes']+graph['edges'] for r in item['source_ids']))
    return dict(disease=disease,graph=graph,ranking=ranking,comparison=comparisons,hero_journey=hero,benchmark=report(),
                research_programmes=programmes,patient_resources=resources,source_policy=dataset().get('source_policy',{}),
                complementary=rank_complementary_candidates(disease,primary,evaluated_rows=comparisons) if primary else dict(candidates=[],explanation='No eligible primary to complement.'),
                surrogates=find_mechanistic_surrogates(disease,primary,evaluated_rows=comparisons) if primary else [], experiment=propose_next_experiment(disease,primary),
                next_steps=dict(patient=patient,researcher=researcher),trials=trials,
                studies=[sources()[r] for r in disease['study_ids']], sources=provenance(list(dict.fromkeys(graph_refs+disease.get('patient_resource_ids',[])))),
                snapshot_date=dataset()['retrieved_at'],physiology=dict(candidates=[],reason='No disease-specific sourced physiology surrogate passed this pilot gate. The core supports physiology candidates with the same evidence requirements.'),
                disclaimer='Research decision support — not medical advice. Therapeutic hypotheses require experimental and clinical validation.')
