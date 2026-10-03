"""Check that every curated patient-organisation URL still resolves.

    uv run python -m atlas.check_orgs

Rewrites data/curated/patient_orgs.json with a `reachable` flag per entry and
the date of the check. Entries are hand-curated; this only verifies liveness.
"""
import datetime
import json
from concurrent.futures import ThreadPoolExecutor

import httpx

from .config import CURATED

FILE = CURATED / "patient_orgs.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}


def reachable(url):
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, headers=UA)
        return r.status_code < 400 or r.status_code in (401, 403, 405, 429, 503)  # bot walls still mean "exists"
    except Exception:
        return False


def main():
    data = json.loads(FILE.read_text())
    entries = data["organizations"] + data["cross_disease_registries"]
    with ThreadPoolExecutor(12) as ex:
        for e, ok in zip(entries, ex.map(reachable, [e["url"] for e in entries])):
            e["reachable"] = ok
            if not ok:
                print("unreachable:", e["name"], e["url"])
    data["verified"] = datetime.date.today().isoformat()
    FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"{sum(e['reachable'] for e in entries)}/{len(entries)} reachable")


if __name__ == "__main__":
    main()
