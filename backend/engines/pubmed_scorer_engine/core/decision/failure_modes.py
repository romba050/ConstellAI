"""
Failure mode inference for translational research.
Conservative, schema-tolerant.
"""

def infer_failure_modes(evidence_items):
    """
    Infers common translational failure modes based on evidence composition.
    """

    failure_modes = []

    if not evidence_items:
        return ["no_evidence"]

    # tolerate both old and new schemas
    has_human = any(
        e.get("species") == "human" or e.get("model") == "human"
        for e in evidence_items
    )

    has_animal = any(
        e.get("species") == "animal" or e.get("model") == "animal"
        for e in evidence_items
    )

    if not has_human:
        failure_modes.append("no_direct_human_evidence")

    if has_animal and not has_human:
        failure_modes.append("animal_to_human_translation_risk")

    # surrogate endpoints increase risk
    if any(e.get("endpoint") == "surrogate" for e in evidence_items):
        failure_modes.append("surrogate_endpoint_dependency")

    # low replication signal
    if len(evidence_items) < 2:
        failure_modes.append("limited_replication")

    return failure_modes
