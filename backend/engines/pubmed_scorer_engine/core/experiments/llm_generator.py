import json
import requests


LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b"


def generate_experiments_llm(
    hypothesis: str,
    failure_modes: list[str],
    max_experiments: int = 5,
):
    """
    Generate novel, cheap falsification experiments using
    local LLaMA 3.1 8B via LM Studio (OpenAI-compatible API).
    """

    prompt = f"""
You are a translational biomedical scientist.

Hypothesis:
{hypothesis}

Known failure modes:
{", ".join(failure_modes)}

Task:
Propose {max_experiments} DISTINCT, CHEAP falsification experiments.

Rules:
- each experiment must be falsifiable
- cost under €25,000
- duration under 8 weeks
- human-relevant if possible
- avoid generic experiments
- output JSON ONLY (no prose, no markdown)

JSON schema:
[
  {{
    "name": "string",
    "tests": "string",
    "cost_eur": integer,
    "duration": "string",
    "kill_if": "string"
  }}
]
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a careful scientific assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 700,
    }

    try:
        response = requests.post(
            LMSTUDIO_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
    except requests.exceptions.RequestException as e:
        print("LM Studio request failed:", e)
        return []

    if response.status_code != 200:
        print("LM Studio error:", response.text)
        return []

    try:
        text = response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        print("Malformed LM Studio response:", response.text)
        return []

    # Defensive cleanup
    if text.startswith("```"):
        text = text.split("```")[1].strip()

    try:
        experiments = json.loads(text)
    except Exception:
        print("Failed to parse JSON from LLM:")
        print(text)
        return []

    cleaned = []
    for e in experiments:
        if not all(k in e for k in ["name", "tests", "cost_eur", "duration", "kill_if"]):
            continue
        if not isinstance(e["cost_eur"], int) or e["cost_eur"] > 25000:
            continue
        cleaned.append(e)

    return cleaned[:max_experiments]
