from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def scan_repo():

    backend = ROOT
    engines = backend / "engines"
    services = backend / "services"
    data = backend / "data"

    summary = {
        "engines": [],
        "services": [],
        "data_files": []
    }

    if engines.exists():
        for d in engines.iterdir():
            if d.is_dir():
                summary["engines"].append(d.name)

    if services.exists():
        for f in services.glob("*.py"):
            summary["services"].append(f.name)

    if data.exists():
        for f in data.rglob("*"):
            if f.is_file():
                summary["data_files"].append(str(f.relative_to(backend)))

    return summary