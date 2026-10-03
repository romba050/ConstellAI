from __future__ import annotations

from pathlib import Path
from typing import Dict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_SRC = PROJECT_ROOT / 'frontend' / 'src'
APP_FILE = BACKEND_ROOT / 'app.py'


def _count_files(folder: Path, pattern: str) -> int:
    if not folder.exists():
        return 0
    return sum(1 for _ in folder.glob(pattern))


def check_ui() -> int:
    score = 25
    jsx_count = _count_files(FRONTEND_SRC, '*.jsx')
    js_count = _count_files(FRONTEND_SRC, '*.js')
    if (FRONTEND_SRC / 'App.jsx').exists():
        score += 20
    score += min(jsx_count * 3, 30)
    score += min(js_count * 2, 10)
    return min(score, 100)


def check_backend() -> int:
    score = 30
    engines_dir = BACKEND_ROOT / 'engines'
    services_dir = BACKEND_ROOT / 'services'
    engine_dirs = [path for path in engines_dir.iterdir() if path.is_dir()] if engines_dir.exists() else []
    service_files = [path for path in services_dir.glob('*.py')] if services_dir.exists() else []
    score += min(len(engine_dirs) * 8, 40)
    score += min(len(service_files) * 4, 20)
    return min(score, 100)


def check_api() -> int:
    if not APP_FILE.exists():
        return 10
    text = APP_FILE.read_text(encoding='utf-8', errors='ignore')
    endpoint_count = text.count('@app.')
    return min(25 + endpoint_count * 3, 100)


def evaluate_system() -> Dict[str, float]:
    ui = check_ui()
    backend = check_backend()
    api = check_api()
    overall = round((ui + backend + api) / 3, 1)
    return {
        'ui_score': ui,
        'backend_score': backend,
        'api_score': api,
        'system_maturity': overall,
    }
