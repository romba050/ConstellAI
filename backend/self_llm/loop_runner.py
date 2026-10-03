from __future__ import annotations

from typing import Any, Dict, List

from .engine import generate_proposal
from .proposal_ranker import rank_proposals


def run_loop(iterations: int = 5, hint: str = '') -> List[Dict[str, Any]]:
    safe_iterations = max(1, min(int(iterations or 5), 10))
    results: List[Dict[str, Any]] = []
    for _ in range(safe_iterations):
        try:
            results.append(generate_proposal(hint))
        except Exception as exc:
            results.append({'error': str(exc)})
    ranked_ok = rank_proposals([row for row in results if isinstance(row, dict) and 'institutional_score' in row])
    ranked_errors = [row for row in results if 'institutional_score' not in row]
    return ranked_ok + ranked_errors
