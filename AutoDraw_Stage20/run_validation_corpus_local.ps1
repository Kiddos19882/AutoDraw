# Offline corpus preparation; never launches game, bridge or executor.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $InputFolder,

    [ValidateRange(1, 20000)]
    [int] $CanvasWidth = 646,

    [ValidateRange(1, 20000)]
    [int] $CanvasHeight = 323,

    [ValidateSet("contain", "cover", "stretch")]
    [string] $FitMode = "contain",

    [string] $PaletteFile = "",

    [string] $OutputRoot = ""
)

$ErrorActionPreference = "Stop"
$stageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$inputDir = (Resolve-Path -LiteralPath $InputFolder -ErrorAction Stop).Path
if (-not (Test-Path -LiteralPath $inputDir -PathType Container)) {
    throw "InputFolder must be an existing folder with source images."
}

if (-not $PaletteFile) {
    $PaletteFile = Join-Path $stageRoot "data\palettes\profiles\Browser_palette.autodraw-palette.json"
}
$palette = (Resolve-Path -LiteralPath $PaletteFile -ErrorAction Stop).Path

if (-not $OutputRoot) {
    $runId = "{0}-{1}" -f (Get-Date -Format "yyyyMMdd-HHmmss"), ([guid]::NewGuid().ToString("N").Substring(0, 8))
    $OutputRoot = Join-Path $env:USERPROFILE "Documents\AutoDraw-Corpus-Runs\$runId"
}
$output = [System.IO.Path]::GetFullPath($OutputRoot)
if (Test-Path -LiteralPath $output) {
    throw "OutputRoot already exists. Choose a new empty output path; no existing evidence will be overwritten."
}

$launcher = Get-Command py -ErrorAction SilentlyContinue
$pyPrefix = @("-3")
if (-not $launcher) {
    $launcher = Get-Command python -ErrorAction SilentlyContinue
    $pyPrefix = @()
}
if (-not $launcher) {
    throw "Python 3 is required (py -3 or python). Install dependencies from source/preparation/requirements.txt first."
}

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = [string]::Join([System.IO.Path]::PathSeparator, @(
    $stageRoot,
    (Join-Path $stageRoot "source\preparation"),
    (Join-Path $stageRoot "source\executor"),
    $previousPythonPath
))
try {
    $generateArgs = @($pyPrefix) + @(
        (Join-Path $stageRoot "source\preparation\generate_validation_corpus.py"),
        "--input", $inputDir,
        "--palette", $palette,
        "--output-root", $output,
        "--canvas-width", [string]$CanvasWidth,
        "--canvas-height", [string]$CanvasHeight,
        "--fit-mode", $FitMode
    )
    & $launcher.Source @generateArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Candidate corpus generator failed (exit $LASTEXITCODE). Keep its console output for diagnosis."
    }

    $manifest = Join-Path $output "results\generated_validation_corpus_manifest.json"
    $audit = Join-Path $output "results\corpus_geometry_audit.json"
    $auditArgs = @($pyPrefix) + @(
        (Join-Path $stageRoot "source\preparation\audit_validation_corpus.py"),
        "--manifest", $manifest,
        "--output", $audit
    )
    & $launcher.Source @auditArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Candidate geometry audit failed (exit $LASTEXITCODE). Preserve source data and outputs."
    }

    Write-Host "OFFLINE CORPUS COMPLETE (not approved for CHALK validation)"
    Write-Host "Manifest: $manifest"
    Write-Host "Geometry audit: $audit"
    Write-Host "Output folder: $output"
    Write-Host "Share the manifest and audit JSON for review. Source images need not be uploaded."
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}
