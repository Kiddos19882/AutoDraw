$ErrorActionPreference = "Stop"

$outputDir = Join-Path $env:RUNNER_TEMP "egret-renderer-reference"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$server = $null
$domPath = Join-Path $env:RUNNER_TEMP "egret-renderer-reference-dom.html"
$stderrPath = Join-Path $env:RUNNER_TEMP "egret-renderer-reference-edge-stderr.log"

function Save-FailureDiagnostics {
    if (Test-Path $domPath) {
        Copy-Item $domPath (Join-Path $outputDir "page-dom-diagnostic.html") -Force
    }
    if (Test-Path $stderrPath) {
        Copy-Item $stderrPath (Join-Path $outputDir "edge-stderr.log") -Force
        Write-Host "Headless Edge stderr:"
        Get-Content $stderrPath
    }
}

try {
    $server = Start-Process -FilePath "python" -ArgumentList @("-m", "http.server", "8765", "--bind", "127.0.0.1") -WorkingDirectory $env:GITHUB_WORKSPACE -PassThru -WindowStyle Hidden

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

    $bundleResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8765/AutoDraw_Stage20/gameEngine/mergeEngine_df2e5bc5.js" -TimeoutSec 10
    if ($bundleResponse.StatusCode -ne 200 -or $bundleResponse.Content.Length -lt 100000) {
        throw "Egret bundle HTTP check failed: status=$($bundleResponse.StatusCode), chars=$($bundleResponse.Content.Length)."
    }
    Write-Host "Egret bundle HTTP check: status=$($bundleResponse.StatusCode), chars=$($bundleResponse.Content.Length)."

    $edgeCandidates = @(
        (Join-Path \${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
    )
    $edgePath = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $edgePath) { throw "Microsoft Edge executable was not found on the Windows runner." }

    $browserArgs = @(
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--dump-dom",
        "--user-data-dir=$(Join-Path $env:RUNNER_TEMP 'egret-edge-profile')",
        "http://127.0.0.1:8765/AutoDraw_Stage20/tests/game_renderer_reference.html"
    )
    $browser = Start-Process -FilePath $edgePath -ArgumentList $browserArgs -RedirectStandardOutput $domPath -RedirectStandardError $stderrPath -PassThru -Wait
    if ($browser.ExitCode -ne 0) {
        Save-FailureDiagnostics
        throw "Headless Edge exited with code $($browser.ExitCode)."
    }

    $dom = Get-Content -Raw $domPath
    if ($dom -notmatch 'data-reference-status="complete"' -or $dom -notmatch 'data-fixture-count="18"') {
        Save-FailureDiagnostics
        $statusMatch = [regex]::Match($dom, '<p id="renderer-status"[^>]*>(.*?)</p>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if ($statusMatch.Success) {
            Write-Host "Renderer status from DOM: $([System.Net.WebUtility]::HtmlDecode($statusMatch.Groups[1].Value))"
        } else {
            Write-Host "Renderer status element was not present in dumped DOM."
        }
        Write-Host "Headless Edge DOM diagnostic (first 16000 characters):"
        Write-Host $dom.Substring(0, [Math]::Min(16000, $dom.Length))
        throw "Egret reference page did not report 18 completed fixtures; diagnostics saved to artifact."
    }

    $manifestMatch = [regex]::Match($dom, '<pre id="renderer-manifest-json"[^>]*>(.*?)</pre>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $manifestMatch.Success) {
        Save-FailureDiagnostics
        throw "Renderer fixture manifest was not serialized into the page DOM."
    }

    $manifestJson = [System.Net.WebUtility]::HtmlDecode($manifestMatch.Groups[1].Value)
    $manifest = $manifestJson | ConvertFrom-Json
    if ($manifest.fixtures.Count -ne 18) {
        Save-FailureDiagnostics
        throw "Expected 18 fixture entries in the manifest, found $($manifest.fixtures.Count)."
    }
    Set-Content -Path (Join-Path $outputDir "manifest.json") -Value $manifestJson -Encoding utf8

    $pngPattern = '<a(?=[^>]*href="data:image/png;base64,([^"]+)")(?=[^>]*download="([^"]+)")[^>]*>'
    $pngMatches = [regex]::Matches($dom, $pngPattern)
    if ($pngMatches.Count -ne 36) {
        Save-FailureDiagnostics
        throw "Expected 36 PNG download links, found $($pngMatches.Count)."
    }

    foreach ($match in $pngMatches) {
        $pngBytes = [Convert]::FromBase64String($match.Groups[1].Value)
        $pngName = [System.IO.Path]::GetFileName($match.Groups[2].Value)
        [System.IO.File]::WriteAllBytes((Join-Path $outputDir $pngName), $pngBytes)
    }

    Write-Host "Egret CanvasRenderer generated $($manifest.fixtures.Count) fixtures and $($pngMatches.Count) PNG files."
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}