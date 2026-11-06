param(
    [string]$Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $OutputDir) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $env:TEMP "AutoDraw-Stage-Firefox-Local-$stamp"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

python -c "import selenium" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Selenium is missing. Install it with: python -m pip install selenium>=4.27"
}

$portInUse = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    throw "Port 8765 is already in use. Stop the existing listener before running this offline probe."
}

$server = $null
try {
    $server = Start-Process -FilePath "python" -ArgumentList @("-m", "http.server", "8765", "--bind", "127.0.0.1") -WorkingDirectory $Workspace -PassThru -WindowStyle Hidden

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:8765/AutoDraw_Stage20/tests/game_renderer_reference.html" -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $ready) { throw "Local HTTP server did not become ready." }

    $runner = Join-Path $Workspace "AutoDraw_Stage20\tests\run_egret_stage_reference_firefox.py"
    $runnerArgs = @($runner, "--base-url", "http://127.0.0.1:8765", "--output-dir", $OutputDir, "--workspace", $Workspace, "--headed")
    python @runnerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Local Firefox Stage A-D probe failed. Inspect the saved output directory: $OutputDir"
    }

    $archive = "$OutputDir.zip"
    Compress-Archive -Path (Join-Path $OutputDir "*") -DestinationPath $archive -Force
    Write-Host "Offline Firefox Stage A-D probe completed."
    Write-Host "Output directory: $OutputDir"
    Write-Host "Archive: $archive"
    Write-Host "No game was opened and no live drawing experiment was performed."
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}
