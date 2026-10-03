"""MEDR5's deterministic signed coverage and add-on rules, extracted in isolation.

Unknown no longer receives the legacy helper's partial positive alignment.
Weights are explicit research heuristics, not potency or treatment probabilities.
"""
from collections import defaultdict

WRONG_DIRECTION_WEIGHT = 0.85
SPILLOVER_WEIGHT = 0.22
ADDON_SPILLOVER_WEIGHT = 0.20
REDUNDANCY_WEIGHT = 0.18
COMPLEXITY_PENALTY = 0.06


def effect_view(effect, evidence):
    return {"id": effect.id, "target": effect.target, "label": effect.label,
            "direction": evidence.effect_direction(effect), "relation": effect.relation,
            "context": effect.context, "claim_kind": effect.claim_kind,
            "source_ids": list(effect.source_ids), "sources": evidence.resolve(effect.source_ids) or []}


def score_candidate(targets, candidate, evidence, unresolved=()):
    if len({target.id for target in targets}) != len(targets):
        raise ValueError("Duplicate targets would inflate coverage")
    total = sum(target.weight for target in targets)
    target_ids = {target.id for target in targets}
    grouped = defaultdict(list)
    for effect in candidate.effects + candidate.spillover:
        grouped[effect.target].append(effect)
    unknown, covered, opposed, remaining, matches = [], [], [], [], []
    for target in targets:
        effects = grouped.get(target.id, [])
        desired = target.desired_direction if evidence.resolve(target.source_ids, mechanistic=True) else None
        directions = {evidence.effect_direction(e) for e in effects}
        if desired is None:
            unknown.append(f"Unknown disease direction/provenance for {target.label}.")
        if effects and (None in directions or len(directions) != 1):
            unknown.append(f"Missing, unsigned or conflicting intervention evidence for {target.label}.")
        direction = next(iter(directions)) if len(directions) == 1 else None
        alignment = desired * direction if desired is not None and direction is not None else None
        relation = {"target": target.id, "label": target.label, "desired_direction": desired,
                    "observed_direction": direction, "alignment": alignment,
                    "status": "matched" if alignment == 1 else "opposed" if alignment == -1 else "unknown",
                    "edges": [effect_view(e, evidence) for e in effects]}
        if effects:
            matches.append(relation)
        if alignment == 1:
            covered.append(target)
        else:
            remaining.append({"target": target.id, "label": target.label, "weight": target.weight,
                              "reason": "wrong_direction" if alignment == -1 else
                                        "unknown_direction_or_evidence" if effects or desired is None else "no_curated_effect"})
        if alignment == -1:
            opposed.append(target)

    causal_unknown = bool(unknown)
    spill_items = []
    for target_id, effects in sorted(grouped.items()):
        if target_id in target_ids:
            continue
        directions = {evidence.effect_direction(e) for e in effects}
        if None in directions or len(directions) != 1:
            unknown.append(f"Unresolved provenance/direction for off-signature effect {target_id}.")
        else:
            spill_items.append({"target": target_id, "label": effects[0].label,
                               "direction": next(iter(directions)),
                               "edges": [effect_view(e, evidence) for e in effects]})

    if not candidate.effects:
        unknown.append("No sourced intervention effects available.")
        causal_unknown = True
    if not any(m["alignment"] is not None for m in matches):
        unknown.append("No signed causal-axis overlap to evaluate.")
        causal_unknown = True
    known_coverage = sum(t.weight for t in covered) / total if total else 0
    opposed_fraction = sum(t.weight for t in opposed) / total if total else 0
    penalty = SPILLOVER_WEIGHT * len(spill_items)
    fit = None if unknown or not total else round(known_coverage - WRONG_DIRECTION_WEIGHT * opposed_fraction - penalty, 3)
    overlap_weight = sum(t.weight for t in targets if t.id in grouped)
    direction_match = None if causal_unknown or not overlap_weight else round(
        (sum(t.weight for t in covered) - sum(t.weight for t in opposed)) / overlap_weight, 3)

    # Unrelated papers or an oncology label cannot strengthen causal-axis evidence.
    matched_refs = [sid for m in matches for e in m["edges"] if e["direction"] is not None
                    for sid in e["source_ids"]]
    causal_sources = evidence.resolve(tuple(dict.fromkeys(matched_refs)), mechanistic=True) or []
    warnings = [{**warning, "sources": evidence.resolve(warning.get("source_ids"))}
                for warning in candidate.warnings if evidence.resolve(warning.get("source_ids"))]
    incomplete = not candidate.inventory_complete
    uncertainties = list(dict.fromkeys(unknown +
        (["Off-target/selectivity inventory is incomplete; the listed spillover penalty is a lower bound."] if incomplete else []) +
        ["Expression direction is not a measured magnitude, phenotype rescue or clinical benefit.",
         "Exposure, developmental timing and disease-context clinical risk remain unresolved."]))
    ranking_status = "withheld" if fit is None or opposed or not covered or fit <= 0 else (
        "provisional" if candidate.kind == "existing_drug" else "research_comparator")
    return {
        "candidate_intervention": {"id": candidate.id, "name": candidate.name, "kind": candidate.kind,
                                   "summary": candidate.summary},
        "ranking_status": ranking_status, "rank": None,
        "mechanistic_fit": {"score": fit, "status": "unknown" if fit is None else "partial" if incomplete else "known_effects_only",
                            "unit": "heuristic score on curated axes; not a probability"},
        "direction_match": {"value": direction_match, "status": "unknown" if direction_match is None else "known",
                            "scale": "-1 opposes desired direction; +1 matches", "items": matches},
        "mechanistic_coverage": {"value": None if causal_unknown or not total else round(known_coverage, 3),
                                 "known_lower_bound": round(known_coverage, 3),
                                 "covered_targets": [t.id for t in covered], "axis_count": len(targets),
                                 "scope": "Curated molecular axes only; never a fraction of disease biology rescued."},
        "spillover": {"items": spill_items, "known_count": len(spill_items), "listed_penalty": round(penalty, 3),
                      "inventory_status": "incomplete" if incomplete else "curated_scope_only",
                      "unresolved": [u for u in unknown if "off-signature" in u]},
        "wrong_direction_effects": {"items": [m for m in matches if m["status"] == "opposed"],
                                    "status": "unknown" if direction_match is None else "known",
                                    "penalty": None if direction_match is None else round(WRONG_DIRECTION_WEIGHT * opposed_fraction, 3)},
        "evidence_strength": {"status": "sourced" if causal_sources else "unknown",
                              "types": sorted({s["evidence_type"] for s in causal_sources}),
                              "sources": causal_sources, "clinical_benefit_established": False,
                              "scope": "Evidence for listed intervention effects; not variant-specific treatment evidence."},
        "remaining_deviation": {"targets": remaining, "unresolved_biology": list(unresolved),
                                "modeled_uncovered_fraction": round(1 - known_coverage, 3) if total and not causal_unknown else None,
                                "scope": "No modeled directional coverage is not proof of absence of a drug effect."},
        "clinical_safety_evidence": {"status": "not_established_for_this_disease", "warnings": warnings,
                                     "drug_interactions": "unknown", "assessment_score": None},
        "uncertainty": {"status": "unknown" if unknown else "partial", "items": uncertainties},
    }


def complementary_candidates(targets, primary, candidates):
    """Reward only closure of remaining axes; reject redundancy and opposed effects."""
    if primary is None:
        return {"primary": None, "proposed": [], "evaluated": [], "status": "unknown",
                "reason": "No direction-supported primary candidate to compare."}
    primary_id = primary["candidate_intervention"]["id"]
    primary_covered = set(primary["mechanistic_coverage"]["covered_targets"])
    primary_spill = {item["target"] for item in primary["spillover"]["items"]}
    total = sum(target.weight for target in targets)
    weights = {target.id: target.weight / total for target in targets} if total else {}
    evaluated = []
    for candidate in candidates:
        if candidate["candidate_intervention"]["id"] == primary_id:
            continue
        covered = set(candidate["mechanistic_coverage"]["covered_targets"])
        closure, duplicates = sorted(covered - primary_covered), sorted(covered & primary_covered)
        new_spill = sorted({s["target"] for s in candidate["spillover"]["items"]} - primary_spill)
        unknown = candidate["mechanistic_fit"]["score"] is None or primary["mechanistic_fit"]["score"] is None
        opposed = bool(candidate["wrong_direction_effects"]["items"] or primary["wrong_direction_effects"]["items"])
        closure_weight = sum(weights.get(t, 0) for t in closure)
        redundancy = REDUNDANCY_WEIGHT * sum(weights.get(t, 0) for t in duplicates)
        net = None if unknown or opposed else round(
            closure_weight - redundancy - ADDON_SPILLOVER_WEIGHT * len(new_spill) - COMPLEXITY_PENALTY, 3)
        proposed = bool(closure and net is not None and net > 0.05)
        evaluated.append({
            "candidate_intervention": candidate["candidate_intervention"], "status": "research_hypothesis" if proposed else "withheld",
            "deviation_closed": closure, "redundant_targets": duplicates, "new_spillover": new_spill,
            "closure_weight": round(closure_weight, 3), "redundancy_penalty": round(redundancy, 3),
            "complexity_penalty": COMPLEXITY_PENALTY, "net_gain": net,
            "reason": "Closes a remaining sourced axis; combination effects require validation." if proposed else
                      "Unknown evidence/direction or opposed effects." if unknown or opposed else
                      "No nonredundant remaining-axis closure." if not closure else "Gain does not clear the heuristic threshold.",
            "clinical_safety_evidence": "unknown; no interaction assessment or combination validation",
            "uncertainty": "Effects are not assumed additive; this is a directional set comparison, not synergy prediction.",
        })
    proposed = sorted([row for row in evaluated if row["status"] == "research_hypothesis"], key=lambda row: -row["net_gain"])
    return {"primary": primary_id, "status": "research_hypothesis" if proposed else "no_supported_add_on",
            "proposed": proposed, "evaluated": evaluated,
            "reason": "An add-on must close a remaining sourced molecular axis. Shared restoration alone is redundancy."}
