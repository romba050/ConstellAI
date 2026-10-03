from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_file_summary(path, max_lines=200):

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except:
        return ""

    lines = text.splitlines()

    return "\n".join(lines[:max_lines])


def scan_frontend():

    src = ROOT.parent / "frontend" / "src"

    files = []

    if not src.exists():
        return files

    for f in src.glob("*.jsx"):
        files.append({
            "name": f.name,
            "summary": read_file_summary(f)
        })

    return files


def scan_backend():

    backend = ROOT

    engines = backend / "engines"
    services = backend / "services"

    data = {
        "engines": [],
        "services": []
    }

    if engines.exists():
        for f in engines.glob("*.py"):
            data["engines"].append({
                "name": f.name,
                "summary": read_file_summary(f)
            })

    if services.exists():
        for f in services.glob("*.py"):
            data["services"].append({
                "name": f.name,
                "summary": read_file_summary(f)
            })

    return data