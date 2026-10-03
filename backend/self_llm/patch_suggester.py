from __future__ import annotations

import os

import requests

LM_URL = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1/chat/completions')
MODEL = os.getenv('LM_STUDIO_MODEL', 'meta-llama-3.1-8b-instruct')
REQUEST_TIMEOUT_SECONDS = int(os.getenv('LM_STUDIO_TIMEOUT_SECONDS', '120'))


def suggest_patch(proposal):
    prompt = f"""
You are generating a software patch suggestion.

Proposal:
{proposal}

Return structured output with these exact sections:
FILE
CHANGE
CODE_SNIPPET
"""
    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': 'You generate patch suggestions for biomedical software.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.3,
    }
    response = requests.post(LM_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']
