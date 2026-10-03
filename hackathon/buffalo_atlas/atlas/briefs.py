"""Cited text exports generated entirely from the cached public evidence."""
from .api import disease_bundle
from .data import provenance

def citation_text(s):
    lines=[s.get('title') or s['source'],s['source_url'],s['evidence_type']+'; checked '+s['retrieved_at'],
           'Claim: '+s.get('extracted_claim',s['summary']), 'Study/record: '+s.get('study_design','Design not extracted')]
    if s.get('pmid'):
        lines += ['PMID: '+s['pmid']+'; DOI: '+str(s.get('doi') or 'unavailable'),
                  str(s.get('journal') or 'Journal unavailable')+'; '+str(s.get('publication_year') or 'Year unavailable'),
                  'Authors: '+'; '.join(s.get('authors',[])),
                  'Publication types: '+'; '.join(s.get('publication_types',[])),
                  'Sample/denominator: '+(s.get('sample_size',{}).get('reported') or s.get('sample_size',{}).get('location') or 'Not extracted')]
    lines.append('Uncertainty: '+s.get('uncertainty','Not independently reviewed'))
    return '\n'.join(lines)

def brief(disease_id, kind='evidence'):
    b=disease_bundle(disease_id)
    rows=[f"MEDR5 Atlas: {b['disease']['name']}",b['disclaimer'],f"Evidence snapshot: {b['snapshot_date']}"]
    if kind=='collaboration':
        h=b['hero_journey']
        if not h:
            raise ValueError('No curated collaboration journey')
        rows += [h['collaboration']['title'],h['collaboration']['action'],
                 'Anchor: neuronal UBE3A loss. Neighbor: Prader-Willi paternal-region expression loss. Shared model context does not imply shared treatment.',
                 *h['collaboration']['deliverables'],h['asset']['availability'],h['collaboration']['limitation'],
                 'Patient communities: https://angelman.org/ and https://www.pwsausa.org/']
        refs=provenance(h['collaboration']['source_ids'])
    elif kind=='evidence':
        p=b['ranking']['ranked'][0] if b['ranking']['ranked'] else None
        rows += [f"Causal gene / mechanism: {b['disease']['gene']} / {b['disease']['mechanism']}",
                 f"Hypothesis: {p['name']}; heuristic priority {p['priority_score']}; coverage of {len(b['disease']['signature'])} curated axis(es), not whole disease or efficacy." if p else b['ranking']['reason'],
                 'Clinical safety / quantitative organ burden unknown. Mechanistic fit does not establish safety.',
                 *['Unresolved: '+s for s in b['disease']['unresolved']],
                 *[f"{a['title']}: {a['text']}\n{a.get('url','')}" for a in b['next_steps']['patient']]]
        refs=list({s['id']:s for n in b['graph']['nodes'] for s in n['provenance']}.values())
    else:
        raise ValueError('Unknown brief type')
    rows += [f"Proposed research experiment: {b['experiment']['question']}",f"Falsifier: {b['experiment']['falsifier']}",
             'Sources:',*[citation_text(s) for s in refs]]
    return dict(text='\n\n'.join(rows),filename=f'MEDR5-Atlas-{disease_id}-{kind}-brief.txt')
