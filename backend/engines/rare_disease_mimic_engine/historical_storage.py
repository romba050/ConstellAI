from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from .historical_schema import (
    DiseaseToDrugPattern,
    HistoricalReplayCase,
    ReplayMemoryBank,
    ReplayPredictionInput,
    ReplayPredictionResult,
    TargetHypothesis,
    utc_now_iso,
)


class HistoricalReplayStore:
    def __init__(self, bank_path: Path) -> None:
        self.bank_path = Path(bank_path)
        self.bank_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> ReplayMemoryBank:
        if not self.bank_path.exists():
            return ReplayMemoryBank()
        try:
            raw = json.loads(self.bank_path.read_text(encoding="utf-8"))
            return ReplayMemoryBank.model_validate(raw)
        except Exception:
            return ReplayMemoryBank()

    def save(self, bank: ReplayMemoryBank) -> ReplayMemoryBank:
        bank_dict = bank.model_dump(mode="json")
        self.bank_path.write_text(
            json.dumps(bank_dict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return bank

    def replace_cases(self, cases: Iterable[HistoricalReplayCase]) -> ReplayMemoryBank:
        bank = self.load()
        bank.cases = list(cases)
        bank.pattern_index = build_pattern_index(bank.cases)
        bank.metadata["last_case_refresh_at"] = utc_now_iso()
        return self.save(bank)

    def upsert_case(self, case: HistoricalReplayCase) -> ReplayMemoryBank:
        bank = self.load()
        found = False
        updated_cases: List[HistoricalReplayCase] = []
        for existing in bank.cases:
            if existing.case_id == case.case_id:
                case.updated_at = utc_now_iso()
                updated_cases.append(case)
                found = True
            else:
                updated_cases.append(existing)
        if not found:
            case.created_at = utc_now_iso()
            case.updated_at = case.created_at
            updated_cases.append(case)

        bank.cases = updated_cases
        bank.pattern_index = build_pattern_index(bank.cases)
        bank.metadata["last_case_upsert_at"] = utc_now_iso()
        return self.save(bank)

    def get_case(self, case_id: str) -> Optional[HistoricalReplayCase]:
        bank = self.load()
        for case in bank.cases:
            if case.case_id == case_id:
                return case
        return None

    def record_replay(self, replay: ReplayPredictionResult) -> ReplayMemoryBank:
        bank = self.load()
        bank.replay_runs.append(replay)
        bank.metadata["last_replay_at"] = utc_now_iso()
        return self.save(bank)

    def append_hit_logic(
        self,
        replay_id: str,
        disease_name: str,
        reusable_rule: str,
        confidence: str = "medium",
        source_ids: Optional[List[str]] = None,
    ) -> ReplayMemoryBank:
        bank = self.load()
        target_case = None
        for case in bank.cases:
            if case.disease_name.lower() == disease_name.lower():
                target_case = case
                break

        if target_case is None:
            target_case = HistoricalReplayCase(
                case_id=f"auto_{slugify(disease_name)}",
                disease_name=disease_name,
                summary="auto-created from replay hit logic",
            )
            bank.cases.append(target_case)

        pattern = DiseaseToDrugPattern(
            pattern_id=f"stored_logic_{slugify(replay_id)}",
            pattern_summary=f"stored hit logic from replay {replay_id}",
            reusable_rule=reusable_rule,
            confidence=confidence,  # type: ignore[arg-type]
            source_ids=source_ids or [],
        )
        target_case.patterns.append(pattern)
        target_case.updated_at = utc_now_iso()
        bank.pattern_index = build_pattern_index(bank.cases)
        bank.metadata["last_hit_logic_store_at"] = utc_now_iso()
        return self.save(bank)


def slugify(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_") or "item"


def build_pattern_index(cases: Iterable[HistoricalReplayCase]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for case in cases:
        keys = set()
        keys.add(slugify(case.disease_name))
        keys.update(slugify(tag) for tag in case.tags)
        for pattern in case.patterns:
            keys.update(slugify(feature) for feature in pattern.trigger_features)
        for key in keys:
            index.setdefault(key, [])
            if case.case_id not in index[key]:
                index[key].append(case.case_id)
    return index


def feature_tokens_from_input(replay_input: ReplayPredictionInput) -> List[str]:
    tokens = {slugify(replay_input.disease_name)}
    for feature in replay_input.candidate_features:
        tokens.add(slugify(feature))
    for target in replay_input.suspected_targets:
        tokens.add(slugify(target.target))
        if target.direction:
            tokens.add(slugify(f"{target.target}_{target.direction}"))
    return sorted(t for t in tokens if t)


def match_cases_for_replay(
    bank: ReplayMemoryBank,
    replay_input: ReplayPredictionInput,
    max_cases: int = 5,
) -> List[HistoricalReplayCase]:
    tokens = feature_tokens_from_input(replay_input)
    scores: dict[str, int] = {}

    for token in tokens:
        for case_id in bank.pattern_index.get(token, []):
            scores[case_id] = scores.get(case_id, 0) + 1

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    case_map = {case.case_id: case for case in bank.cases}
    return [case_map[case_id] for case_id, _ in ranked[:max_cases] if case_id in case_map]


def build_replay_prediction(
    bank: ReplayMemoryBank,
    replay_id: str,
    replay_input: ReplayPredictionInput,
) -> ReplayPredictionResult:
    matches = match_cases_for_replay(bank, replay_input)
    matched_patterns: List[str] = []
    first_logic_parts: List[str] = []
    improve_parts: List[str] = []
    fail_parts: List[str] = []

    for case in matches:
        for pattern in case.patterns:
            matched_patterns.append(pattern.pattern_id)
            if pattern.first_medicine_logic:
                first_logic_parts.append(pattern.first_medicine_logic)
            if pattern.improvement_logic:
                improve_parts.append(pattern.improvement_logic)
            if pattern.failure_logic:
                fail_parts.append(pattern.failure_logic)

    return ReplayPredictionResult(
        replay_id=replay_id,
        input=replay_input,
        matched_case_ids=[case.case_id for case in matches],
        matched_pattern_ids=matched_patterns,
        predicted_first_medicine_logic=" | ".join(first_logic_parts[:3]),
        predicted_improvement_logic=" | ".join(improve_parts[:3]),
        predicted_failure_logic=" | ".join(fail_parts[:3]),
        confidence="medium" if matches else "low",
        stored_logic_note=(
            "if replay becomes a hit, store reusable rule back into pattern memory"
        ),
    )
