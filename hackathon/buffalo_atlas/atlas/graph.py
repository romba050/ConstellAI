from .data import dataset, sources, provenance, valid_refs

NODE_TYPES={'Disease','Gene','Variant','Phenotype','Study','Patient Group','Trial','Drug','Intervention','Pathway','Experiment','Asset','Research Team'}

def validate_graph(graph):
    ids=[n['id'] for n in graph['nodes']]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate graph node')
    edges=[e['id'] for e in graph['edges']]
    if len(edges)!=len(set(edges)):
        raise ValueError('Duplicate graph edge')
    for item in graph['nodes']+graph['edges']:
        if not valid_refs(item.get('source_ids')) or not item.get('provenance') or not item.get('confidence'):
            raise ValueError('Graph assertion without provenance')
        if item.get('provenance') != provenance(item['source_ids']):
            raise ValueError('Graph provenance does not match source registry')
    for n in graph['nodes']:
        if n['type'] not in NODE_TYPES:
            raise ValueError('Unknown graph node type')
    for e in graph['edges']:
        if e['source'] not in ids or e['target'] not in ids:
            raise ValueError('Dangling graph edge')
    return True

def build_graph(disease):
    nodes,edges=[],[]
    def node(id,type,label,refs,description='',status='curated_source_assertion'):
        if any(n['id']==id for n in nodes):
            return
        nodes.append(dict(id=id,type=type,label=label,source_ids=refs,provenance=provenance(refs),description=description,status=status,
                          confidence='Sourced assertion; experimental context applies' if status!='hypothesis' else 'Unvalidated research hypothesis'))
    def edge(a,b,type,refs,description='',status='curated_source_assertion'):
        edges.append(dict(id=f'e:{len(edges)}',source=a,target=b,type=type,source_ids=refs,provenance=provenance(refs),description=description,status=status,
                          confidence='Source-specific evidence; not causal certainty' if status!='hypothesis' else 'Unvalidated research hypothesis'))
    did=disease['id']; gene='gene:'+disease['gene']; refs=disease['source_ids']
    node(did,'Disease',disease['name'],refs,disease['mechanism'])
    node(gene,'Gene',disease['gene'],refs,disease['mechanism'])
    edge(did,gene,'DISEASE_CAUSED_BY_GENE',refs,disease['mechanism'])
    for axis in disease.get('signature',[]):
        if axis['target']==disease['gene']:
            edges[-1].update(causal_direction=axis['direction'],signature_weight=axis['weight'],target_symbol=axis['target'],source_ids=axis['source_ids'],provenance=provenance(axis['source_ids']))
    variant=did+':variant-class'
    node(variant,'Variant',disease['gene']+' '+disease['direction'].replace('_',' '),refs,'Mechanism class only; not an individual patient variant or inferred HGVS classification.')
    edge(did,variant,'DISEASE_HAS_MECHANISM_CLASS',refs,disease['mechanism'])
    edge(variant,gene,'VARIANT_CLASS_AFFECTS_GENE',refs,disease['direction'])
    for i,p in enumerate(disease['phenotypes']):
        id=f'{did}:phenotype:{i}'; node(id,'Phenotype',p,refs)
        edge(did,id,'DISEASE_HAS_PHENOTYPE',refs,'Reported disease feature; not diagnostic by itself.')
    org=disease['organization']; s=sources()[org]
    node(org,'Patient Group',s['source'],[org],s['summary'])
    edge(org,did,'PATIENT_GROUP_SUPPORTS_DISEASE',[org],s['summary'])
    for sid in disease['study_ids']:
        s=sources()[sid]; node(sid,'Study',s['identifier'] or s['source'],[sid],s['summary'])
        edge(sid,did,'STUDY_EXAMINES_DISEASE',[sid],s['summary'])
    for t in dataset()['trials']:
        if t['disease']!=did:
            continue
        node(t['id'],'Trial',t['id'],t['source_ids'],t['title']+' · '+t['status']+' · registry update '+t['last_updated'])
        iid='trial-intervention:'+t['intervention']; node(iid,'Intervention',t['intervention'],t['source_ids'],'Investigational trial intervention; not assumed equivalent to a published comparator.')
        edge(t['id'],did,'TRIAL_STUDIES_DISEASE',t['source_ids'],t['title'])
        edge(t['id'],iid,'TRIAL_TESTS_INTERVENTION',t['source_ids'],t['status']+' as retrieved '+dataset()['retrieved_at']+'; recheck registry before acting.')
    for c in dataset()['interventions']:
        if did not in c['disease_ids']:
            continue
        node(c['id'],'Drug' if c['kind']=='drug' else 'Intervention',c['name'],c['source_ids'],c['summary'])
        next(n for n in nodes if n['id']==c['id'])['spillover_unknown']=c.get('spillover_unknown',False)
        for ef in c['effects']:
            target='gene:'+ef['target']
            if target==gene:
                edge(c['id'],target,'INTERVENTION_INCREASES_GENE_EXPRESSION',ef['source_ids'],ef['context'],'preclinical_observation')
                edges[-1].update(mechanistic_effect=ef['effect'],target_symbol=ef['target'])
                for sid in ef['source_ids']:
                    edge(sid,c['id'],'STUDY_SUPPORTS_RELATION',[sid],'Source supports the experimental perturbation effect.','preclinical_observation')
        for i,sp in enumerate(c['spillover']):
            target='spillover:'+sp['target']; node(target,'Pathway',sp['target'],sp['source_ids'],'Sourced off-signature mechanism; not a measured toxicity score.')
            edge(c['id'],target,'INTERVENTION_AFFECTS_OFF_SIGNATURE_BIOLOGY',sp['source_ids'],sp['effect'],'preclinical_observation')
            edges[-1].update(mechanistic_effect=sp['effect'],target_symbol=sp['target'])
    if did=='angelman':
        node('ube3a-unsilencing','Pathway','Paternal UBE3A unsilencing',['huang2012','meng2015'],'Antisense-transcript reduction is an experimental route to restore paternal expression.')
        edge(gene,'ube3a-unsilencing','GENE_LINKED_TO_MECHANISM',['huang2012','meng2015'],'UBE3A restoration mechanism, not whole-disease efficacy.','preclinical_observation')
        node('experiment:angelman','Experiment','Selective rescue versus spillover',['huang2012','meng2015','king2013','fink2017'],'A proposed cellular falsification experiment.','hypothesis')
        edge('experiment:angelman','topotecan','EXPERIMENT_PROPOSES_COMPARISON',['huang2012','meng2015','king2013','fink2017'],'Proposed comparison, not completed experimental evidence.','hypothesis')
        hero=dataset()['hero_journey'];neighbor=hero['neighbor'];asset=hero['asset'];counter=hero['counterexample']
        node(neighbor['id'],'Disease',neighbor['name'],neighbor['source_ids'],neighbor['mechanism']+' '+neighbor['caveat'])
        node('gene:SNORD116','Gene','SNORD116 region',['pws-nlm'],'One relevant region in complex PWS biology; not a single-gene explanation of all PWS.')
        edge(neighbor['id'],'gene:SNORD116','DISEASE_INVOLVES_IMPRINTED_REGION',['pws-nlm'],'Loss of paternal expression; not UBE3A deficiency.')
        node('cluster:imprinting','Pathway','15q genomic imprinting',['paired-ipsc2010','pws-nlm','angelman-nlm'],hero['cluster_name'])
        edge(did,'cluster:imprinting','SHARES_IMPRINTING_MODEL_CONTEXT',['paired-ipsc2010'],'Shared imprinting research context; no shared drug response implied.')
        edge(neighbor['id'],'cluster:imprinting','SHARES_IMPRINTING_MODEL_CONTEXT',['paired-ipsc2010'],'Different parental-expression defects; same published paired model approach.')
        node(neighbor['organization'],'Patient Group',sources()[neighbor['organization']]['source'],[neighbor['organization']])
        edge(neighbor['organization'],neighbor['id'],'PATIENT_GROUP_SUPPORTS_DISEASE',[neighbor['organization']])
        node(asset['id'],'Asset',asset['name'],asset['source_ids'],asset['availability'])
        edge(did,asset['id'],'HAS_PUBLISHED_MODEL_APPROACH',asset['source_ids'],'Published method, not guaranteed available cell inventory.')
        edge(neighbor['id'],asset['id'],'HAS_PUBLISHED_MODEL_APPROACH',asset['source_ids'],'Published paired models; procurement and collaborator availability unverified.')
        node('paired-ipsc2010','Study','PMID:20876107',['paired-ipsc2010'],sources()['paired-ipsc2010']['summary'])
        edge('paired-ipsc2010',asset['id'],'STUDY_DESCRIBES_ASSET',['paired-ipsc2010'])
        node('team:chamberlain','Research Team',asset['researcher'],['paired-ipsc2010'],'Published research team; no partnership or current availability claimed.')
        edge('team:chamberlain',asset['id'],'PUBLICATION_TEAM_DESCRIBED_MODEL',['paired-ipsc2010'])
        node(counter['id'],'Disease',counter['name'],counter['source_ids'],counter['distinction'])
        node('variant:ube3a-dose-gain','Variant','Maternal UBE3A dosage gain',counter['source_ids'],'Published copy-number context; not a blanket functional classification for all Dup15q.')
        edge(counter['id'],'variant:ube3a-dose-gain','DISEASE_HAS_DOSAGE_CONTEXT',counter['source_ids'])
        edge('variant:ube3a-dose-gain',gene,'VARIANT_CLASS_INCREASES_DOSAGE',counter['source_ids'])
        edge(counter['id'],did,'NOT_IN_SAME_RESTORATION_CLUSTER',counter['source_ids']+['angelman-nlm'],counter['explanation'],'inference')
        edge(asset['id'],'experiment:angelman','MODEL_APPROACH_MAY_SUPPORT_EXPERIMENT',['paired-ipsc2010','fink2017'],'Proposed model reuse requires procurement, genotype and ethics checks.','hypothesis')
    for item in nodes+edges:
        item['classification']='HYPOTHESIS' if item['status']=='hypothesis' else 'INFERENCE' if item['status']=='inference' else 'CLINICAL EVIDENCE' if any(p['evidence_type']=='human_randomized_trial' for p in item['provenance']) else 'FACT'
        item['observed_or_inferred']='proposed' if item['classification']=='HYPOTHESIS' else 'inferred' if item['classification']=='INFERENCE' else 'source-reported observation'
        item['contradictory_evidence']='Not systematically reviewed. Context limitations are reported in linked sources.'
        if did=='angelman' and item.get('source_ids') and 'meng2015' in item['source_ids']:
            item['contradictory_evidence']='Meng et al. report incomplete phenotype rescue; restored expression alone does not establish complete functional rescue.'
    graph=dict(nodes=nodes,edges=edges)
    validate_graph(graph)
    return graph
