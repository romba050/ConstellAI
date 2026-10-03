from __future__ import annotations

import os
from typing import Any, Dict

import requests

from .architecture_mapper import build_architecture_map
from .impact_estimator import estimate_institutional_score
from .institution_simulator import simulate_institutions
from .prompt_builder import build_prompt
from .proposal_store import save_proposal
from .system_maturity import evaluate_system

LM_URL = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1/chat/completions')
MODEL = os.getenv('LM_STUDIO_MODEL', 'meta-llama-3.1-8b-instruct')
REQUEST_TIMEOUT_SECONDS = int(os.getenv('LM_STUDIO_TIMEOUT_SECONDS', '120'))


def call_llm(prompt: str) -> str:
    payload = {
        'model': MODEL,
        'messages': [
            {
                'role': 'system',
                'content': (
                    'You improve biomedical research software for institutional adoption. '
                    'Return structured, concise proposals only.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.4,
    }
    try:
        response = requests.post(LM_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f'lm studio request failed at {LM_URL}. make sure lm studio is running and the model is loaded. raw error: {exc}'
        ) from exc
    try:
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as exc:
        raise RuntimeError(f'lm studio returned an unexpected payload: {exc}') from exc


def generate_proposal(hint: str = '') -> Dict[str, Any]:
    architecture = build_architecture_map()
    prompt = build_prompt(architecture, hint)
    proposal = call_llm(prompt)
    base_score = estimate_institutional_score(proposal)
    simulation = simulate_institutions(proposal)
    blended_score = round((base_score + float(simulation['average_score'])) / 2, 1)
    file_path = save_proposal(proposal, blended_score)
    system = evaluate_system()
    return {
        'proposal': proposal,
        'institutional_score': blended_score,
        'institution_breakdown': simulation['institution_scores'],
        'system_maturity': system,
        'file': file_path,
        'architecture_snapshot': architecture,
    }
