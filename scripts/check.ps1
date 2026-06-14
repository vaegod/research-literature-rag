$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python scripts/open_source_audit.py
& $Python -m ruff check .
& $Python -m pytest --cov=app --cov-report=term-missing

$DockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$DockerAvailable = $false
if ($DockerCommand) {
    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        docker info *> $null
        $DockerAvailable = $LASTEXITCODE -eq 0
    } catch {
        $DockerAvailable = $false
    } finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }
}

if ($DockerAvailable) {
    docker build . --tag research-literature-rag:local-check
} else {
    Write-Host "Docker daemon not available; skipped image build."
}
