param(
    [int]$Port = 8010
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $ProjectRoot "logs"
$pidFile = Join-Path $logDir "server.pid"

$processIds = @()

if (Test-Path -LiteralPath $pidFile) {
    $pidText = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pidText -match "^\d+$") {
        $processIds += [int]$pidText
    }
}

$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($connection in $connections) {
    if ($connection.OwningProcess) {
        $processIds += [int]$connection.OwningProcess
    }
}

$processIds = $processIds | Sort-Object -Unique

if (-not $processIds) {
    Write-Host "No service process found on port $Port."
    exit 0
}

foreach ($processId in $processIds) {
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $processId -Force
        Write-Host "Stopped process $processId."
    }
}

if (Test-Path -LiteralPath $pidFile) {
    Remove-Item -LiteralPath $pidFile -Force
}

