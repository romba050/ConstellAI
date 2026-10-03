import requests

def generate(cfg, prompt: str) -> str:
    llm = cfg.get("llm", {})
    url = llm.get("llamacpp_url")
    timeout = int(llm.get("timeout_sec", 60))

    payload = {
        "model": llm.get("model", "local-model"),
        "messages": [
            {"role": "system", "content": "you are a biomedical information extraction system. return only valid json."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 800
    }

    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    return data["choices"][0]["message"]["content"]
