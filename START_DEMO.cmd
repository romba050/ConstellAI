@echo off
setlocal
cd /d "%~dp0"
echo ConstellAI therapeutic research demo: http://127.0.0.1:8800
echo Press Ctrl+C to stop. Add OPENAI_API_KEY to .env and restart for optional AI.
echo Pulse checks public papers and trials every 6 hours while this server runs.
where uv >nul 2>nul
if not errorlevel 1 (
  uv run uvicorn atlas.server:app --host 127.0.0.1 --port 8800
) else (
  python -m uvicorn atlas.server:app --host 127.0.0.1 --port 8800
)
if errorlevel 1 (
  echo Install dependencies with uv sync, or follow README.md for the small demo runtime.
  pause
)
