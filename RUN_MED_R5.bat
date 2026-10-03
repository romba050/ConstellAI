@echo off
setlocal ENABLEEXTENSIONS
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%RUN_MED_R5.ps1"
endlocal