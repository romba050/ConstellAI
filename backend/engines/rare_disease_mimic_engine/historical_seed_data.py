from __future__ import annotations

from typing import List

from .historical_schema import (
    DiseaseToDrugPattern,
    DiscoveryThinking,
    FailureSetback,
    HistoricalReplayCase,
    HistoricalSource,
    MedicineDesignLogic,
    TargetHypothesis,
)


def get_seed_historical_cases() -> List[HistoricalReplayCase]:
    rett = HistoricalReplayCase(
        case_id="rett_demo_history",
        disease_name="rett syndrome",
        discovery_year=1966,
        summary=(
            "seed training case for replaying how rare-disease interpretation, "
            "first medicine logic, later improvement logic, and setbacks are stored"
        ),
        discovery=DiscoveryThinking(
            year=1970,
            doctor_researcher_view=(
                "neurodevelopmental disorder with severe functional regression; "
                "early thinking focused on symptom clusters before deeper mechanism clarity"
            ),
            suspected_mechanism=(
                "broad neuronal signaling and plasticity disruption with incomplete target certainty"
            ),
            dominant_symptom_model="regression, cognition, movement, and communication impairment",
            suspected_targets=[
                TargetHypothesis(
                    target="BDNF",
                    direction="down",
                    rationale="plasticity support and neuronal function",
                    confidence="medium",
                ),
                TargetHypothesis(
                    target="CREB1",
                    direction="down",
                    rationale="transcriptional support for neuronal signaling",
                    confidence="medium",
                ),
            ],
            unknowns=[
                "root upstream mechanism incompletely specified at early timepoint",
                "unclear whether symptom model or mechanism model should dominate first intervention logic",
            ],
        ),
        first_medicine=MedicineDesignLogic(
            medicine_name="first-generation symptomatic approach",
            year_started=1970,
            year_first_used=1972,
            medicine_type="supportive / early mechanistic attempt",
            role="first_medicine",
            why_created=(
                "created to capture the strongest tractable symptom-mechanism bridge available at the time"
            ),
            target_logic=[
                TargetHypothesis(
                    target="CREB1",
                    direction="activate",
                    rationale="attempt to improve neuronal signaling function",
                    confidence="medium",
                )
            ],
            mechanism_summary="choose tractable signaling-support path before full disease mechanism is known",
            expected_benefit="partial symptom improvement and proof-of-direction",
            limitations=[
                "partial coverage only",
                "weak upstream control",
                "did not fully close disease deviation",
            ],
            outcome="partial",
        ),
        later_medicines=[
            MedicineDesignLogic(
                medicine_name="later generation more targeted approach",
                year_started=1985,
                year_first_used=1990,
                medicine_type="improved mechanism-led design",
                role="improved_medicine",
                why_created="created after observing limits of partial symptomatic logic",
                target_logic=[
                    TargetHypothesis(
                        target="BDNF",
                        direction="activate",
                        rationale="close more of the remaining neuroplasticity gap",
                        confidence="medium",
                    ),
                    TargetHypothesis(
                        target="HDAC2",
                        direction="inhibit",
                        rationale="reduce opposing transcriptional pressure",
                        confidence="medium",
                    ),
                ],
                mechanism_summary="move from partial support to stronger gap-closing target logic",
                expected_benefit="higher coverage and stronger disease-mechanism fit",
                why_better_than_previous=(
                    "more powerful because it closes deviation left by the first approach"
                ),
                limitations=["still imperfect upstream control"],
                outcome="partial",
            )
        ],
        failures=[
            FailureSetback(
                label="over-symptom framing",
                phase="early discovery",
                year=1973,
                reason="too much weight on surface symptoms and too little on mechanism",
                consequence="weak first-pass intervention logic",
                lesson="store symptom model and mechanism model separately during replay",
            ),
            FailureSetback(
                label="partial target closure",
                phase="optimization",
                year=1980,
                reason="first design did not close remaining deviation targets",
                consequence="later-generation medicine needed",
                lesson="track uncovered gap explicitly after first medicine selection",
            ),
        ],
        patterns=[
            DiseaseToDrugPattern(
                pattern_id="pattern_rett_primary_then_gapfill",
                pattern_summary="rare neurodevelopmental case often starts with partial tractable target, then moves to gap-fill logic",
                trigger_features=["neurodevelopmental", "plasticity_loss", "partial_first_fit"],
                first_medicine_logic="choose tractable primary path even when full upstream certainty is absent",
                improvement_logic="later medicine improves by closing explicit residual deviation",
                failure_logic="first pass often fails by underweighting upstream mechanism and uncovered gap",
                reusable_rule="store primary-first then deviation-fill rule and reuse for similar new rare diseases",
                confidence="medium",
            )
        ],
        sources=[
            HistoricalSource(
                source_id="seed_qpdf_logic",
                title="q.pdf training direction seed",
                year=2026,
                kind="review",
                citation="internal seed derived from q.pdf workflow direction",
            )
        ],
        tags=["neurodevelopmental", "rare", "primary_first", "deviation_fill"],
    )

    fragile_x = HistoricalReplayCase(
        case_id="fragile_x_demo_history",
        disease_name="fragile x syndrome",
        discovery_year=1969,
        summary="seed training case for storing discovery-to-improved-medicine logic",
        discovery=DiscoveryThinking(
            year=1970,
            doctor_researcher_view=(
                "thought process centered on developmental/cognitive dysfunction with incomplete molecular clarity"
            ),
            suspected_mechanism="synaptic dysregulation with signaling imbalance",
            dominant_symptom_model="cognitive and developmental dysfunction",
            suspected_targets=[
                TargetHypothesis(
                    target="GSK3B",
                    direction="up",
                    rationale="possible signaling overactivity",
                    confidence="low",
                ),
                TargetHypothesis(
                    target="CREB1",
                    direction="down",
                    rationale="reduced supportive transcriptional activity",
                    confidence="medium",
                ),
            ],
        ),
        first_medicine=MedicineDesignLogic(
            medicine_name="first mechanistic-support attempt",
            year_started=1971,
            year_first_used=1974,
            medicine_type="early mechanism-guided candidate",
            role="first_medicine",
            why_created="designed to stabilize the most plausible signaling imbalance available at the time",
            target_logic=[
                TargetHypothesis(
                    target="GSK3B",
                    direction="inhibit",
                    rationale="reduce overactive signaling branch",
                    confidence="medium",
                )
            ],
            mechanism_summary="start with the most tractable imbalance rather than full disease closure",
            expected_benefit="partial pathway normalization",
            limitations=["weak breadth", "residual gap left untreated"],
            outcome="partial",
        ),
        later_medicines=[
            MedicineDesignLogic(
                medicine_name="broader second-generation mechanism fit",
                year_started=1988,
                year_first_used=1994,
                medicine_type="improved mechanism-led design",
                role="improved_medicine",
                why_created="created to address residual deviation left by narrower first medicine",
                target_logic=[
                    TargetHypothesis(
                        target="GSK3B",
                        direction="inhibit",
                        rationale="retain successful primary component",
                        confidence="medium",
                    ),
                    TargetHypothesis(
                        target="CREB1",
                        direction="activate",
                        rationale="close remaining support deficit",
                        confidence="medium",
                    ),
                ],
                mechanism_summary="preserve useful first logic, then add missing target logic",
                expected_benefit="higher disease coverage than first medicine",
                why_better_than_previous="stronger because it combines preserved hit logic with explicit deviation rescue",
                limitations=["possible added complexity or spillover"],
                outcome="partial",
            )
        ],
        failures=[
            FailureSetback(
                label="narrow first design",
                phase="first medicine",
                year=1975,
                reason="first medicine focused on one tractable branch only",
                consequence="remaining gap persisted",
                lesson="store preserved hit logic separately from missing-gap logic",
            )
        ],
        patterns=[
            DiseaseToDrugPattern(
                pattern_id="pattern_fragilex_preserve_and_extend",
                pattern_summary="effective next medicine often preserves what worked and extends into the remaining gap",
                trigger_features=["signaling_imbalance", "narrow_first_design", "gap_rescue"],
                first_medicine_logic="start with tractable imbalance control",
                improvement_logic="keep winning logic and extend into missing targets",
                failure_logic="do not throw away first-hit logic when designing next-generation medicine",
                reusable_rule="preserve hit logic, then add targeted deviation rescue",
                confidence="medium",
            )
        ],
        sources=[
            HistoricalSource(
                source_id="seed_qpdf_logic_2",
                title="q.pdf replay logic seed",
                year=2026,
                kind="review",
                citation="internal seed derived from q.pdf historical replay intention",
            )
        ],
        tags=["rare", "signaling", "preserve_hit_logic", "gap_rescue"],
    )

    return [rett, fragile_x]
