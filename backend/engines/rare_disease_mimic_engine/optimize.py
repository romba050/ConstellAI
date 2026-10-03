from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set, Tuple

from .scoring import effect_alignment_score


def _norm(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for value in values or []:
        token = str(value or "").strip().upper().replace(" ", "").replace("-", "")
        if token and token not in seen:
            out.append(token)
            seen.add(token)
    return out


def _score_increment(
    candidate,
    disease_directions: Dict[str, str],
    remaining: Set[str],
    covered: Set[str],
    spill: Set[str],
    spillover_weight: float,
) -> Dict[str, object]:
    effects = getattr(candidate, "effects", {}) or {}
    strengths = getattr(candidate, "strength_map", {}) or {}
    candidate_targets = set(_norm(getattr(candidate, "targets", [])))
    candidate_spill = set(_norm(getattr(candidate, "spillover_targets", []))) - set(disease_directions.keys())

    newly_covered: List[str] = []
    opposed: List[str] = []
    weighted_gain = 0.0
    wrong_way_penalty = 0.0

    for gene in candidate_targets:
        if gene not in disease_directions:
            continue
        align = effect_alignment_score(disease_directions.get(gene, "unknown"), effects.get(gene))
        strength = float(strengths.get(gene, 0.6) or 0.6)
        contribution = align * strength
        if gene in remaining and contribution > 0.1:
            newly_covered.append(gene)
            weighted_gain += contribution
        elif contribution < -0.05:
            opposed.append(gene)
            wrong_way_penalty += abs(contribution)

    new_spill = sorted(candidate_spill - spill)
    complexity_penalty = 0.08 if getattr(candidate, "kind", "compound") == "drug" else 0.04
    spill_penalty = len(new_spill) * float(spillover_weight)
    redundancy_penalty = max(0, len(candidate_targets & covered) - len(newly_covered)) * 0.03
    net_gain = round(weighted_gain - wrong_way_penalty - spill_penalty - complexity_penalty - redundancy_penalty, 3)

    return {
        "candidate": candidate,
        "newly_covered": sorted(newly_covered),
        "opposed": sorted(opposed),
        "new_spill": new_spill,
        "weighted_gain": round(weighted_gain, 3),
        "wrong_way_penalty": round(wrong_way_penalty, 3),
        "spill_penalty": round(spill_penalty, 3),
        "complexity_penalty": round(complexity_penalty, 3),
        "redundancy_penalty": round(redundancy_penalty, 3),
        "net_gain": net_gain,
    }


def _pick_best_candidate(
    pool: Sequence,
    disease_directions: Dict[str, str],
    remaining: Set[str],
    covered: Set[str],
    spill: Set[str],
    spillover_weight: float,
) -> Dict[str, object] | None:
    scored = [
        _score_increment(item, disease_directions, remaining, covered, spill, spillover_weight)
        for item in (pool or [])
    ]
    scored = [row for row in scored if row["newly_covered"]]
    if not scored:
        return None
    scored.sort(
        key=lambda row: (
            float(row["net_gain"]),
            len(row["newly_covered"]),
            -len(row["new_spill"]),
            -len(row["opposed"]),
        ),
        reverse=True,
    )
    return scored[0]


def choose_best_bundle(
    disease_genes: Sequence[str],
    primary,
    addon_pool: Sequence,
    max_bundle_items: int = 4,
    spillover_weight: float = 0.12,
    disease_directions: Dict[str, str] | None = None,
    planner_mode: str = "mode_a",
    bundle_strategy: str = "dynamic",
    include_physiology: bool = True,
) -> Dict[str, object]:
    genes = _norm(disease_genes)
    gene_set = set(genes)
    disease_directions = {g: str((disease_directions or {}).get(g, "unknown")) for g in genes}

    primary_targets = set(_norm(getattr(primary, "targets", []))) & gene_set
    primary_spill = set(_norm(getattr(primary, "spillover_targets", []))) - gene_set
    primary_name = getattr(primary, "name", None)
    primary_id = getattr(primary, "id", None)

    covered = set(primary_targets)
    spill = set(primary_spill)
    bundle_items = [primary] if primary_id else []
    logic_trace: List[Dict[str, object]] = []
    selection_reasoning: List[str] = []

    if primary_id:
        selection_reasoning.append(
            f"primary drug {primary_name} chosen first because it closes {', '.join(sorted(primary_targets)) or 'no target'}"
        )
        logic_trace.append(
            {
                "step": 1,
                "phase": "primary_drug",
                "selected_id": primary_id,
                "selected_name": primary_name,
                "selected_kind": getattr(primary, "kind", "drug"),
                "newly_covered": sorted(primary_targets),
                "new_spill": sorted(primary_spill),
                "net_gain": round(len(primary_targets) - (len(primary_spill) * spillover_weight), 3),
            }
        )

    remaining = set(genes) - covered
    base_pool = [item for item in list(addon_pool or []) if getattr(item, "id", None) != primary_id]
    drug_pool = [item for item in base_pool if getattr(item, "kind", "compound") == "drug"]
    support_pool = [item for item in base_pool if getattr(item, "kind", "compound") != "drug"]
    if not include_physiology:
        support_pool = [item for item in support_pool if getattr(item, "kind", "compound") != "physiology"]

    step = 2
    dynamic_cap = max(1, int(max_bundle_items or 1))
    max_extra_drugs = max(0, dynamic_cap - (1 if primary_id else 0))
    unlimited = str(bundle_strategy or "dynamic").strip().lower() == "unlimited"
    mode_b = str(planner_mode or "mode_a").strip().lower() == "mode_b"

    chosen_ids = {getattr(item, "id", "") for item in bundle_items}

    def _accept(row: Dict[str, object], phase: str) -> None:
        nonlocal step, remaining, covered, spill
        candidate = row["candidate"]
        bundle_items.append(candidate)
        chosen_ids.add(getattr(candidate, "id", ""))
        covered.update(row["newly_covered"])
        spill.update(row["new_spill"])
        remaining = set(genes) - covered
        logic_trace.append(
            {
                "step": step,
                "phase": phase,
                "selected_id": getattr(candidate, "id", None),
                "selected_name": getattr(candidate, "name", None),
                "selected_kind": getattr(candidate, "kind", "compound"),
                "newly_covered": row["newly_covered"],
                "new_spill": row["new_spill"],
                "opposed": row["opposed"],
                "net_gain": row["net_gain"],
                "weighted_gain": row["weighted_gain"],
            }
        )
        selection_reasoning.append(
            f"{phase.replace('_', ' ')} picked {getattr(candidate, 'name', 'unknown')} because it newly closes {', '.join(row['newly_covered']) or 'nothing'} with net gain {row['net_gain']}"
        )
        step += 1

    if not mode_b:
        drug_iterations = 0
        while drug_pool and remaining:
            if not unlimited and drug_iterations >= max_extra_drugs:
                break
            row = _pick_best_candidate(drug_pool, disease_directions, remaining, covered, spill, spillover_weight)
            if not row or float(row["net_gain"]) <= 0.05:
                break
            _accept(row, "drug_rinse")
            drug_iterations += 1
            drug_pool = [item for item in drug_pool if getattr(item, "id", None) not in chosen_ids]
            support_pool = [item for item in support_pool if getattr(item, "id", None) not in chosen_ids]
            if not unlimited and len(bundle_items) >= dynamic_cap:
                break

    while support_pool and remaining:
        if not unlimited and len(bundle_items) >= dynamic_cap:
            break
        row = _pick_best_candidate(support_pool, disease_directions, remaining, covered, spill, spillover_weight)
        if not row or float(row["net_gain"]) <= 0.03:
            break
        _accept(row, "support_fill")
        support_pool = [item for item in support_pool if getattr(item, "id", None) not in chosen_ids]

    bundle_ids = [getattr(item, "id", None) for item in bundle_items if getattr(item, "id", None)]
    bundle_names = [getattr(item, "name", None) for item in bundle_items if getattr(item, "name", None)]
    suggested_addon_ids = bundle_ids[1:] if len(bundle_ids) > 1 else []
    suggested_addon_names = bundle_names[1:] if len(bundle_names) > 1 else []
    uncovered = [g for g in genes if g not in covered]
    score = round(len(covered) - (len(spill) * spillover_weight) - (0.06 * max(0, len(bundle_items) - 1)), 3)

    return {
        "planner_mode": planner_mode,
        "bundle_strategy": bundle_strategy,
        "bundle_ids": bundle_ids,
        "bundle_names": bundle_names,
        "suggested_addon_ids": suggested_addon_ids,
        "suggested_addon_names": suggested_addon_names,
        "covered_genes": sorted(covered),
        "uncovered_genes": uncovered,
        "spillover_genes": sorted(spill),
        "spillover_count": len(spill),
        "coverage_ratio": round(len(covered) / max(1, len(genes)), 3),
        "score": score,
        "logic_trace": logic_trace,
        "selection_reasoning": selection_reasoning,
        "stop_reason": (
            "all disease deviation covered" if not uncovered else
            "unlimited stopped at no positive gain" if unlimited else
            "dynamic cap reached or no positive gain"
        ),
    }
