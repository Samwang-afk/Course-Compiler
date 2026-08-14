$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
$req = Join-Path $PSScriptRoot "requirements.txt"

if (-not (Test-Path $venvPy)) {
    Write-Host "[learning-kb] creating venv ..."
    uv venv --python 3.14 $venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[learning-kb] python 3.14 unavailable, falling back to uv-managed 3.12 ..."
        uv venv --python 3.12 $venv
        if ($LASTEXITCODE -ne 0) { Write-Host "venv creation failed"; exit 1 }
    }
}
Write-Host "[learning-kb] installing dependencies (first run may take a while) ..."
uv pip install --python $venvPy -r $req
if ($LASTEXITCODE -ne 0) { Write-Host "dependency install failed"; exit 1 }
Write-Host "[learning-kb] setup done. Scripts run via scripts/run.ps1"
