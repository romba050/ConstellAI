import json
import os

PATH = "knowledge/memory.json"

def load():
    if not os.path.exists(PATH):
        return {}
    with open(PATH, "r") as f:
        return json.load(f)

def save(mem):
    os.makedirs("knowledge", exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(mem, f, indent=2)
