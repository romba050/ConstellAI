"""One-shot public-source checks for an external scheduler or bootstrap export."""
import argparse
import json
from pathlib import Path

from .service import PulseService


def main():
    parser = argparse.ArgumentParser(description="Check the ConstellAI Pulse public-source watchlist; all records remain unreviewed.")
    parser.add_argument("--once", action="store_true", help="Run one check if the persisted six-hour due time has passed.")
    parser.add_argument("--force", action="store_true", help="Explicitly bypass timing throttle for this CLI check; active process lease still applies.")
    parser.add_argument("--export", type=Path, help="Write a complete PulseResponse JSON snapshot to this named file.")
    args = parser.parse_args()
    if args.force and not args.once:
        parser.error("--force requires the explicit --once command")
    service = PulseService()
    snapshot = service.run_once(force=args.force) if args.once else service.snapshot(limit=5000)
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"state": snapshot.state, "records": snapshot.total_records,
                      "last_attempt_at": snapshot.last_attempt_at, "last_success_at": snapshot.last_success_at,
                      "providers": [{"id": p.id, "state": p.state, "records": p.record_count} for p in snapshot.providers]}, indent=2))
    return 0 if snapshot.state in {"ok", "disabled", "pending"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
