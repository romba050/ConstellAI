# backend/services/llm_client.py (FULL REPLACEMENT)
from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from config import SETTINGS


class LLMError(RuntimeError):
    pass


def chat_json(system: str, user: str, timeout_s: int = 60) -> Dict[str, Any]:
    """
    Calls an OpenAI-compatible chat/completions endpoint (LM Studio).
    Returns parsed JSON if the model output is valid JSON, else raises.
    """
    payload = {
        "model": SETTINGS.lm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": SETTINGS.lm_temperature,
        "max_tokens": SETTINGS.lm_max_tokens,
    }

    try:
        r = requests.post(SETTINGS.lm_studio_url, json=payload, timeout=timeout_s)
    except Exception as e:
        raise LLMError(f"llm request failed: {e}") from e

    if r.status_code >= 400:
        raise LLMError(f"llm http {r.status_code}: {r.text[:500]}")

    try:
        data = r.json()
    except Exception as e:
        raise LLMError(f"llm non-json response: {r.text[:500]}") from e

    text: Optional[str] = None
    if isinstance(data, dict) and "choices" in data and data["choices"]:
        text = data["choices"][0]["message"]["content"]
    elif isinstance(data, dict) and "response" in data:
        text = data["response"]

    if not text:
        raise LLMError(f"llm unexpected payload: {str(data)[:500]}")

    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()

    try:
        return json.loads(text)
    except Exception as e:
        raise LLMError(f"llm output was not valid json: {text[:500]}") from e