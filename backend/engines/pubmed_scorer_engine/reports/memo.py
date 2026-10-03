from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent / "templates" / "decision_memo_v5.txt"

def render_memo(context: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.format(**context)
