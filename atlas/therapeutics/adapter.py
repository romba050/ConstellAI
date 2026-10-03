"""Join an exact ConstellAI disease identity to a curator-reviewed signed mechanism.

Inheritance, ClinVar pathogenicity counts, pathway similarity and LLM effect
profiles are intentionally insufficient to assign an intervention direction.
"""
from .evidence import catalog, registry
from .models import TherapeuticTarget, signed_direction


def adapt_disease(disease, variant=None, mechanism=None):
    evidence = registry()
    profile = next((p for p in catalog()["profiles"] if p["disease_id"] == disease["id"]), None)
    problems = []
    if profile and not set(profile["genes"]).issubset(set(disease["genes"])):
        profile = None
        problems.append("The curated causal gene does not match the ConstellAI disease record.")
    if not profile:
        problems.append("No reviewed signed therapeutic mechanism or intervention edges for this disease.")
    elif mechanism and mechanism != profile["id"]:
        problems.append("The requested mechanism has no reviewed direction for this disease.")

    # Variant identity is not functional direction. No variant-specific rescue
    # evidence is curated in this integration, including the public ClinVar example.
    variant_record = next((v for v in catalog()["variant_examples"] if v["id"] == variant), None)
    if variant:
        problems.append("Variant-specific functional direction and rescue context are not reviewed; ranking withheld.")

    targets = []
    for row in profile["targets"] if profile else []:
        refs = tuple(row.get("source_ids", []))
        direction = signed_direction(row.get("disease_direction"))
        if not evidence.resolve(refs, mechanistic=True):
            problems.append(f"Missing mechanistic provenance for {row['label']}.")
            direction = None
        if problems:
            direction = None
        targets.append(TherapeuticTarget(row["id"], row["label"], direction, row["weight"], refs, row["context"]))
    if not targets:
        targets = [TherapeuticTarget(f"gene:{gene}", gene, None, 1.0, (),
                                    "Causal gene identity from the atlas; functional direction is unknown.")
                   for gene in disease["genes"]]
    if len({t.id for t in targets}) != len(targets):
        raise ValueError("Duplicate signed therapeutic targets")
    return {
        "disease": {"id": disease["id"], "name": disease["name"], "genes": disease["genes"]},
        "profile_id": profile["id"] if profile else None,
        "status": "unknown" if problems or not targets else "disease_level_research_context",
        "context": {
            "mechanism": mechanism or (profile["id"] if profile else "unknown"),
            "variant": variant or None,
            "variant_direction": "unknown",
            "variant_sources": evidence.resolve(variant_record["source_ids"]) if variant_record else [],
            "scope": profile["scope"] if profile else "No therapeutic mechanism curated.",
            "assumptions": profile["assumptions"] if profile else [],
            "patient_specific": False,
        },
        "targets": targets,
        "unresolved": profile["unresolved"] if profile else ["Causal functional direction and intervention evidence"],
        "uncertainty": list(dict.fromkeys(problems)),
    }


def target_view(target, evidence):
    return {
        "id": target.id, "label": target.label, "disease_direction": target.disease_direction,
        "desired_direction": target.desired_direction, "weight": target.weight,
        "context": target.context, "source_ids": list(target.source_ids),
        "sources": evidence.resolve(target.source_ids) or [],
    }
