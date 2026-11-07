# Run the orchestrator on the native Codex harness (the default since 2026-11-07) without changing global CLI settings.
$ErrorActionPreference = 'Stop'
$taxProject = Split-Path -Parent $PSScriptRoot
$taxPython = $env:TAX_PYTHON
if (-not $taxPython) {
    $taxPython = (Get-Command python -ErrorAction Stop).Source
}
Push-Location $taxProject
try {
    & $taxPython agent/tools/orchestrate_codex.py @args --harness codex
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
