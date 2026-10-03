from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_SRC = PROJECT_ROOT / 'frontend' / 'src'
APP_FILE = BACKEND_ROOT / 'app.py'


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def scan_frontend_components() -> List[str]:
    if not FRONTEND_SRC.exists():
        return []
    return sorted([p.name for p in FRONTEND_SRC.glob('*.jsx') if p.is_file()], key=str.lower)


def scan_backend_engines() -> List[str]:
    engines_dir = BACKEND_ROOT / 'engines'
    if not engines_dir.exists():
        return []
    return sorted([p.name for p in engines_dir.iterdir() if p.is_dir()], key=str.lower)


def scan_services() -> List[str]:
    services_dir = BACKEND_ROOT / 'services'
    if not services_dir.exists():
        return []
    return sorted([p.name for p in services_dir.glob('*.py') if p.is_file()], key=str.lower)


def scan_api_endpoints() -> List[str]:
    text = _safe_read(APP_FILE)
    pattern = re.compile(r'@app\.(get|post|put|delete|patch)\("([^"]+)"')
    return [f'{method.upper()} {route}' for method, route in pattern.findall(text)]


def scan_data_roots() -> List[str]:
    data_dir = BACKEND_ROOT / 'data'
    if not data_dir.exists():
        return []
    rows: List[str] = []
    for path in sorted(data_dir.rglob('*')):
        if path.is_file():
            rows.append(str(path.relative_to(BACKEND_ROOT)).replace('\\', '/'))
        if len(rows) >= 50:
            break
    return rows


def build_architecture_map() -> Dict[str, List[str]]:
    return {
        'frontend_components': scan_frontend_components(),
        'backend_engines': scan_backend_engines(),
        'services': scan_services(),
        'api_endpoints': scan_api_endpoints(),
        'data_roots': scan_data_roots(),
    }
