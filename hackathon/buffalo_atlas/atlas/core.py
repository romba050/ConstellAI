"""Deterministic MEDR5 core adapter. Scores never come from the LLM."""
import importlib.util
import math
from .data import REPO, dataset, valid_refs, provenance, sources
from .priors import repurposing_prior, frequent_flyer

_path = REPO / 'backend' / 'engines' / 'rare_disease_mimic_engine' / 'scoring.py'
_spec = importlib.util.spec_from_file_location('medr5_preserved_scoring', _path)
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)
KNOWN_DIRECTIONS = legacy.POSITIVE_DISEASE_DIRECTIONS | legacy.NEGATIVE_DISEASE_DIRECTIONS
KNOWN_EFFECTS = legacy.INHIBIT_EFFECTS | legacy.ACTIVATE_EFFECTS
UNCERTAINTY_PENALTIES = {'preclinical_animal': .30, 'preclinical_cellular': .25, 'human_cellular': .15,
                         'human_observational': .20, 'human_randomized_trial': .05, 'review': .35}

def build_disease_signature(disease):
    return [dict(x) for x in disease.get('signature', []) if valid_refs(x.get('source_ids'))
            and isinstance(x.get('weight'), (int,float)) and math.isfinite(x['weight']) and x['weight'] > 0]

def score_direction_alignment(direction, effect, source_ids):
    if not valid_refs(source_ids) or legacy.normalize_token(direction,'unknown') not in KNOWN_DIRECTIONS or legacy.normalize_token(effect,'unknown') not in KNOWN_EFFECTS:
        return None
    return legacy.effect_alignment_score(direction, effect)

def _effects(candidate):
    return {x['target']: x for x in candidate.get('effects',[]) if valid_refs(x.get('source_ids'))}

def score_coverage(signature, candidate):
    effects = _effects(candidate)
    total = sum(x['weight'] for x in signature)
    hits = [x for x in signature if x['target'] in effects and
            (score_direction_alignment(x['direction'], effects[x['target']]['effect'], effects[x['target']]['source_ids']) or 0) > 0]
    return round(sum(x['weight'] for x in hits)/total,3) if total else None

def score_spillover(signature, candidate):
    targets = {x['target'] for x in signature}
    listed = list({x['target']:x for x in candidate.get('spillover',[])+candidate.get('effects',[])
                   if x['target'] not in targets and valid_refs(x.get('source_ids'))}.values())
    invalid = any(not valid_refs(x.get('source_ids')) for x in candidate.get('spillover',[]))
    return dict(items=listed, known_count=len(listed), penalty=round(.22*len(listed),3),
                inventory_complete=False, unknown=bool(candidate.get('spillover_unknown') or invalid),
                explanation='0.22 heuristic penalty per sourced off-signature mechanism. The inventory is incomplete; zero listed mechanisms is not evidence of selectivity or safety.')

def score_evidence(candidate, signature=None):
    effects = list(_effects(candidate).values())
    if signature is not None:
        targets = {x['target'] for x in signature}
        effects = [e for e in effects if e['target'] in targets]
    refs = [r for effect in effects for r in effect['source_ids']]
    rows = provenance(refs) if refs else []
    types = sorted({s['evidence_type'] for s in rows})
    penalties = [min(UNCERTAINTY_PENALTIES.get(sources()[r]['evidence_type'], .50) for r in e['source_ids']) for e in effects]
    return dict(level=' + '.join(t.replace('_',' ') for t in types) if types else 'Unknown / insufficient evidence',
                uncertainty_penalty=round(sum(penalties)/len(penalties),3) if penalties else None,
                sources=rows, clinical_efficacy_established=False,
                explanation='Heuristic uncertainty penalties: animal 0.30; preclinical cells 0.25; human cells 0.15; observational 0.20; RCT 0.05; review 0.35. Averaged over matched causal-axis effects; irrelevant evidence cannot improve fit. These are policy weights, not calibrated probabilities; human cells are not clinical trials.')

def score_risk_burden(candidate):
    warnings = [x for x in candidate.get('risk',[]) if valid_refs(x.get('source_ids'))]
    return dict(score=None, status='Sourced warnings; quantitative burden unknown' if warnings else 'Unknown / insufficient evidence',
                warnings=warnings, explanation='No validated organ-burden scale is available. No numeric safety score is assigned. Label risks are context-specific, not personalised predictions.')

def find_remaining_deviation(disease, covered):
    return dict(uncovered_targets=[x['target'] for x in build_disease_signature(disease) if x['target'] not in covered],
                unresolved=list(disease.get('unresolved',[])),
                explanation='Coverage of a curated molecular axis does not establish phenotype rescue. Timing, delivery and unmodelled biology remain unresolved.')

def score_candidate(disease, candidate, relationships=None):
    signature = build_disease_signature(disease)
    effects = _effects(candidate)
    directions_known = bool(signature) and len(signature)==len(disease.get('signature',[])) and all(legacy.normalize_token(x['direction'],'unknown') in KNOWN_DIRECTIONS for x in signature)
    matches = [(x,effects[x['target']]) for x in signature if x['target'] in effects]
    alignments = [score_direction_alignment(x['direction'],e['effect'],e['source_ids']) for x,e in matches]
    all_effects_sourced = bool(candidate.get('effects')) and all(valid_refs(e.get('source_ids')) for e in candidate['effects'])
    eligible = directions_known and bool(matches) and all(a is not None for a in alignments) and all_effects_sourced
    spill = score_spillover(signature,candidate)
    evidence = score_evidence(candidate,signature)
    score = None
    covered, opposed = [], []
    if eligible:
        raw = legacy.score_intervention_against_disease(dict(id=candidate['id'],name=candidate['name'],kind=candidate['kind'],
              targets={x['target']:1.0 for x,e in matches}, effects={x['target']:e['effect'] for x,e in matches},
              spillover_targets=[x['target'] for x in spill['items']]),
              {x['target']:dict(weight=x['weight'],direction=x['direction']) for x in signature})
        total=sum(x['weight'] for x in signature)
        score=round((raw['raw_score']-raw['wrong_way_penalty'])/total-spill['penalty']-(evidence['uncertainty_penalty'] or 0),3)
        covered, opposed = raw['covered_genes'], raw['opposed_genes']
        eligible = not opposed and bool(covered) and score > 0 and not spill['unknown']
    return dict(candidate, eligible=eligible, priority_score=score, repurposing_prior=repurposing_prior(disease['id'],candidate['id'],relationships),
                frequent_flyer=frequent_flyer(candidate,score,relationships), coverage=score_coverage(signature,candidate) if directions_known else None,
                direction_alignment=round(sum(alignments)/len(alignments),3) if alignments and all(a is not None for a in alignments) else None,
                covered_targets=covered, opposed_targets=opposed, spillover=spill, evidence=evidence, risk_burden=score_risk_burden(candidate),
                remaining=find_remaining_deviation(disease,covered),
                explanation='Mechanistic priority = normalized signed coverage (wrong direction -0.85) - 0.22 per sourced irrelevant/spillover mechanism - evidence uncertainty. No reward for unrelated targets. These are explicit heuristics, not potency, efficacy or safety predictions. Unknown direction/evidence withholds ranking.',
                gate_reason=None if eligible else 'Ranking withheld: missing direction/evidence, opposed biology, no causal coverage, or unknown spillover inventory.')

def rank_repurposing_candidates(disease, candidates=None):
    pool = dataset()['interventions'] if candidates is None else candidates
    rows = [score_candidate(disease,c) for c in pool if disease['id'] in c.get('disease_ids',[]) and c.get('role')=='repurposing_hypothesis']
    ranked = sorted([r for r in rows if r['eligible']], key=lambda r:(-r['frequent_flyer']['adjusted_priority'],r['id']))
    return dict(ranked=ranked, withheld=[r for r in rows if not r['eligible']],
                reason=None if ranked else 'No sourced, direction-aligned causal repurposing hypothesis is eligible in this curated pilot.')

def rank_complementary_candidates(disease, primary, candidates=None, evaluated_rows=None):
    pool = dataset()['interventions'] if candidates is None else candidates
    targets = {x['target']:dict(weight=x['weight'],direction=x['direction']) for x in build_disease_signature(disease)}
    rows = []
    for c in pool:
        if c['id']==primary['id'] or disease['id'] not in c.get('disease_ids',[]):
            continue
        row = next((r for r in evaluated_rows if r['id']==c['id']),None) if evaluated_rows is not None else score_candidate(disease,c)
        if row is None:
            continue
        if not row['eligible']:
            continue
        evaluated = legacy.score_addon_candidate(dict(covered_genes=primary['covered_targets'],new_spillover=[x['target'] for x in primary['spillover']['items']]),
                     dict(id=c['id'],name=c['name'],covered_genes=row['covered_targets'],new_spillover=[x['target'] for x in row['spillover']['items']]), targets)
        if evaluated['net_gain'] > .05 and evaluated['deviation_closed']:
            rows.append(dict(evaluated, status='research_hypothesis'))
    return dict(candidates=sorted(rows,key=lambda x:-x['net_gain']),
                explanation='Add-ons must close a sourced remaining molecular target with net gain > 0.05. Shared UBE3A restoration alone is redundancy, not a justified bundle.')

def find_mechanistic_surrogates(disease, primary, evaluated_rows=None):
    out=[]
    for c in dataset()['interventions']:
        if c.get('role')!='mechanistic_comparator' or disease['id'] not in c.get('disease_ids',[]):
            continue
        row=next((r for r in evaluated_rows if r['id']==c['id']),None) if evaluated_rows is not None else score_candidate(disease,c)
        if row is None:
            continue
        overlap=sorted(set(primary['covered_targets']) & set(row['covered_targets']))
        if overlap:
            out.append(dict(id=c['id'],name=c['name'],overlap=overlap,summary=c['summary'],sources=provenance(c['source_ids']),
                            divergence=[x['target'] for x in primary['spillover']['items'] if x['target'] not in {y['target'] for y in row['spillover']['items']}],
                            risk_burden=row['risk_burden'], status='research_hypothesis',
                            explanation='Shared observed expression direction is not therapeutic equivalence. Compare cellular readouts to isolate mechanism; unlisted spillover remains unknown.'))
    return out

def propose_next_experiment(disease, primary=None):
    if disease['id']=='angelman' and primary:
        return dict(status='research_hypothesis', title='Separate UBE3A restoration from transcriptional spillover',
                    question='Does selective UBE3A restoration reproduce the neuronal functional change associated with topotecan?',
                    model='Disease-relevant neuronal models plus isogenic controls; research ethics and model validation required.',
                    arms=['Vehicle / non-targeting control','Topotecan perturbation','UBE3A-ATS antisense comparator'],
                    readouts=['Allele-specific UBE3A RNA/protein','Long-gene transcription sentinel panel','Neuronal electrophysiology / synaptic activity','Cell viability'],
                    early_kill='Do not advance if UBE3A restoration lacks reproducible functional rescue, or if transcriptional injury / loss of viability explains the signal.',
                    falsifier='If matched UBE3A restoration with antisense fails to reproduce the functional readout, UBE3A restoration alone may be insufficient in this model.',
                    sources=provenance(['huang2012','meng2015','king2013','fink2017']))
    return dict(status='research_hypothesis',title='Resolve the evidence gap before ranking', question=disease['unresolved'][0],
                model='Variant-appropriate experimental model; not a patient intervention.', arms=[],readouts=['Causal variant function','Direction of perturbation','Disease-relevant rescue readout'],
                early_kill='Withhold prioritisation until causal direction and sourced intervention effects are established.',
                falsifier='An inconsistent or opposite functional direction blocks advancement.',sources=provenance(disease['source_ids']))
