import requests
from config import LM_STUDIO_URL, LM_MODEL

def ask_llm(prompt: str) -> str:

    payload = {
        "model": LM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a biomedical research analyst."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500
    }

    response = requests.post(LM_STUDIO_URL, json=payload)

    try:
        data = response.json()
    except:
        return f"LLM error: {response.text}"

    # handle both formats
    if "choices" in data:
        return data["choices"][0]["message"]["content"]

    if "response" in data:
        return data["response"]

    return f"Unexpected LLM response: {data}"
