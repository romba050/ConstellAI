import datetime
import json
from pathlib import Path

ROOT = Path(__file__).parent
STORE = ROOT / 'proposals'
STORE.mkdir(exist_ok=True)


def save_proposal(text, score):
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = STORE / f'proposal_{ts}.json'
    payload = {
        'created': ts,
        'score': score,
        'proposal': text,
        'status': 'pending',
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return str(path)
