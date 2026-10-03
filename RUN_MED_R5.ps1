# RUN_MED_R5.ps1 (FULL REPLACEMENT)
$ErrorActionPreference = "Stop"

function Kill-ListenPort([int]$Port) {
  $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($null -eq $conns) { return }
  $pids = $conns | Select-Object -ExpandProperty OwningProcess -ErrorAction SilentlyContinue | Sort-Object -Unique
  foreach ($procId in $pids) {
    try { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } catch {}
  }
}

# use the physical script folder, not MyInvocation
$Root = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($Root)) {
  $Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
}
if ([string]::IsNullOrWhiteSpace($Root)) {
  $Root = (Get-Location).Path
}

$Root = [System.IO.Path]::GetFullPath($Root)
$BackendPath = [System.IO.Path]::GetFullPath((Join-Path $Root "backend"))
$FrontendPath = [System.IO.Path]::GetFullPath((Join-Path $Root "frontend"))

$BackendPort = 8787
$FrontendPort = 5173
$HostIp = "127.0.0.1"
$FrontendUrl = "http://$HostIp`:$FrontendPort"

Write-Host "[DEBUG] script root: $Root"
Write-Host "[DEBUG] backend path: $BackendPath"
Write-Host "[DEBUG] frontend path: $FrontendPath"

if (!(Test-Path -LiteralPath $BackendPath -PathType Container)) {
  throw "backend folder not found: $BackendPath"
}
if (!(Test-Path -LiteralPath $FrontendPath -PathType Container)) {
  throw "frontend folder not found: $FrontendPath"
}

Write-Host "[INFO] killing any listener on backend port $BackendPort ..."
Kill-ListenPort -Port $BackendPort

# ---------- BACKEND CMD ----------
$backendCmdPath = Join-Path $env:TEMP ("medr5_backend_" + [Guid]::NewGuid().ToString("N") + ".cmd")

$backendCmd = @"
@echo off
title MED-R5 BACKEND (8787)
cd /d "$BackendPath"
echo [BACKEND] WD: %CD%

if exist ".venv\Scripts\python.exe" goto VENV_OK
echo [BACKEND] creating venv...
python -m venv .venv
:VENV_OK

call ".venv\Scripts\activate.bat"
echo [BACKEND] venv activated.

if not exist "requirements.txt" goto RUN_SERVER
if exist ".venv\.pip_installed.stamp" goto RUN_SERVER

echo [BACKEND] pip install (first run)...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo OK > ".venv\.pip_installed.stamp"

:RUN_SERVER
echo [BACKEND] running uvicorn on http://$HostIp`:$BackendPort
python -m uvicorn app:app --app-dir "$BackendPath" --host $HostIp --port $BackendPort --reload
"@

Set-Content -Path $backendCmdPath -Value $backendCmd -Encoding ASCII

# ---------- FRONTEND CMD ----------
$frontendCmdPath = Join-Path $env:TEMP ("medr5_frontend_" + [Guid]::NewGuid().ToString("N") + ".cmd")

$frontendCmd = @"
@echo off
title MED-R5 FRONTEND (5173)
cd /d "$FrontendPath"
echo [FRONTEND] WD: %CD%

if exist "node_modules\" goto RUN_FRONT
echo [FRONTEND] npm install...
npm install

:RUN_FRONT
echo [FRONTEND] running vite on http://$HostIp`:$FrontendPort
npm run dev -- --host $HostIp --port $FrontendPort
"@

Set-Content -Path $frontendCmdPath -Value $frontendCmd -Encoding ASCII

Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "`"$backendCmdPath`""
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "`"$frontendCmdPath`""

Write-Host "[INFO] waiting for frontend: $FrontendUrl"
$ok = $false
for ($i = 0; $i -lt 120; $i++) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 $FrontendUrl
    if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
      $ok = $true
      break
    }
  } catch {}
  Start-Sleep -Seconds 1
}

if ($ok) { Start-Process $FrontendUrl }
Write-Host "[INFO] done."