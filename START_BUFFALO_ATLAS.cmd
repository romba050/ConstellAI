@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 hackathon\buffalo_atlas\run.py
  goto done
)
where python >nul 2>&1
if not errorlevel 1 (
  python hackathon\buffalo_atlas\run.py
  goto done
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" hackathon\buffalo_atlas\run.py
  goto done
)
echo Python 3.10 or newer is required. Install it and run this launcher again.
:done
pause
