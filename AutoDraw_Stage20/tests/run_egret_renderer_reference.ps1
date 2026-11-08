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

    $gameBundleResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8765/AutoDraw_Stage20/gameEngine/main.min_653f95bc.js" -TimeoutSec 20
    if ($gameBundleResponse.StatusCode -ne 200 -or $gameBundleResponse.Content.Length -lt 1000000) {
        throw "Game bundle HTTP check failed: status=$($gameBundleResponse.StatusCode), chars=$($gameBundleResponse.Content.Length)."
    }
    Write-Host "Game bundle HTTP check: status=$($gameBundleResponse.StatusCode), chars=$($gameBundleResponse.Content.Length)."

    $programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
    $edgeCandidates = @(
        (Join-Path $programFilesX86 "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
    )
    $edgePath = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $edgePath) { throw "Microsoft Edge executable was not found on the Windows runner." }

    $browserArgs = @(
        "--headless",
        "--enable-webgl",
        "--use-gl=angle",
        "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader",
        "--ignore-gpu-blocklist",
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
    if ($dom -notmatch 'data-reference-status="complete"' -or $dom -notmatch 'data-fixture-count="20"' -or $dom -notmatch 'data-webgl-status="complete"' -or $dom -notmatch 'data-webgl-comparison-count="20"') {
        Save-FailureDiagnostics
        $statusMatch = [regex]::Match($dom, '<p id="renderer-status"[^>]*>(.*?)</p>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if ($statusMatch.Success) {
            Write-Host "Renderer status from DOM: $([System.Net.WebUtility]::HtmlDecode($statusMatch.Groups[1].Value))"
        } else {
            Write-Host "Renderer status element was not present in dumped DOM."
        }
        Write-Host "Headless Edge DOM diagnostic (first 16000 characters):"
        Write-Host $dom.Substring(0, [Math]::Min(16000, $dom.Length))
        throw "Egret reference page did not report 20 fixtures and a completed WebGL probe; diagnostics saved to artifact."
    }

    $manifestMatch = [regex]::Match($dom, '<pre id="renderer-manifest-json"[^>]*>(.*?)</pre>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $manifestMatch.Success) {
        Save-FailureDiagnostics
        throw "Renderer fixture manifest was not serialized into the page DOM."
    }

    $manifestJson = [System.Net.WebUtility]::HtmlDecode($manifestMatch.Groups[1].Value)
    $manifest = $manifestJson | ConvertFrom-Json
    if ($manifest.fixtures.Count -ne 20) {
        Save-FailureDiagnostics
        throw "Expected 20 fixture entries in the manifest, found $($manifest.fixtures.Count)."
    }
    Set-Content -Path (Join-Path $outputDir "manifest.json") -Value $manifestJson -Encoding utf8

    $pngPattern = '<a(?=[^>]*href="data:image/png;base64,([^"]+)")(?=[^>]*download="([^"]+)")[^>]*>'
    $pngMatches = [regex]::Matches($dom, $pngPattern)
    if ($pngMatches.Count -ne 60) {
        Save-FailureDiagnostics
        throw "Expected 60 PNG download links (40 CanvasRenderer PNGs + 20 WebGL PNGs), found $($pngMatches.Count)."
    }

    foreach ($match in $pngMatches) {
        $pngBytes = [Convert]::FromBase64String($match.Groups[1].Value)
        $pngName = [System.IO.Path]::GetFileName($match.Groups[2].Value)
        [System.IO.File]::WriteAllBytes((Join-Path $outputDir $pngName), $pngBytes)
    }

    if ($manifest.webglProbe.status -ne "complete" -or $manifest.webglProbe.comparisonCount -ne 20 -or
        $manifest.runtimeProfile.canvasScaleFactor -ne 2 -or
        $manifest.runtimeProfile.canvasScaleX -ne 3 -or
        $manifest.runtimeProfile.canvasScaleY -ne 3) {
        Save-FailureDiagnostics
        throw "WebGL renderer did not complete all 20 comparisons or runtime scale profile differs from snapshot."
    }


    Write-Host "Egret actual BoardPane CanvasRenderer + WebGLRenderer generated $($manifest.fixtures.Count) fixtures, 20 WebGL comparisons and $($pngMatches.Count) PNG files."


    # ENGINE-001 offline temporal replay: do not substitute inputs from another run.
    $temporalInput = "AutoDraw_Stage20/data/results/brush_behavior_tests/game_monitor_bridge/bb261898-8296-41f5-a333-eb0b81016410/game-monitor-run-20261104T040548835772Z-6a17a297.json"
    $sourceBlob = (git rev-parse "HEAD:$temporalInput").Trim()
    if ($LASTEXITCODE -ne 0 -or $sourceBlob -ne "8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24") {
        throw "ENGINE-001 source Game Monitor blob changed unexpectedly: $sourceBlob"
    }
    $temporalDom = Join-Path $env:RUNNER_TEMP "egret-temporal-dom.html"
    $temporalStderr = Join-Path $env:RUNNER_TEMP "egret-temporal-edge-stderr.log"
    $temporalArgs = @($browserArgs)
    $temporalArgs[-1] = "http://127.0.0.1:8765/AutoDraw_Stage20/tests/game_renderer_reference.html?temporal=fill001"
    $temporalProcess = Start-Process -FilePath $edgePath -ArgumentList $temporalArgs -RedirectStandardOutput $temporalDom -RedirectStandardError $temporalStderr -PassThru -Wait
    if ($temporalProcess.ExitCode -ne 0) { throw "ENGINE-001 Edge temporal browser exited with $($temporalProcess.ExitCode)." }
    $temporalPage = Get-Content -Raw $temporalDom
    if ($temporalPage -notmatch 'data-temporal-status="complete"' -or $temporalPage -notmatch 'data-temporal-png-count="4"') {
        Copy-Item $temporalDom (Join-Path $outputDir "temporal-page-failure.html") -Force
        Copy-Item $temporalStderr (Join-Path $outputDir "temporal-edge-stderr.log") -Force
        throw "ENGINE-001 temporal HTML did not complete. See temporal-page-failure.html."
    }
    $temporalJsonMatch = [regex]::Match($temporalPage, '<pre id="renderer-manifest-json"[^>]*>(.*?)</pre>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $temporalJsonMatch.Success) { throw "ENGINE-001 temporal manifest was not exported." }
    $temporalJson = [System.Net.WebUtility]::HtmlDecode($temporalJsonMatch.Groups[1].Value)
    $temporalManifest = $temporalJson | ConvertFrom-Json
    if ($temporalManifest.status -ne "COMPLETE_OFFLINE_MEASUREMENT" -or
        $temporalManifest.strokeCount -ne 27 -or
        $temporalManifest.exactHistoricalChalk -ne 1260 -or
        $temporalManifest.screenProjection -ne "UNCALIBRATED" -or
        $temporalManifest.incremental.graphicsPathCount -le $temporalManifest.onePass.graphicsPathCount -or
        $null -eq $temporalManifest.webglPixelComparison.differingPixels) {
        throw "ENGINE-001 temporal manifest fails provenance or rendering guards."
    }
    Set-Content -Path (Join-Path $outputDir "engine001-temporal-accepted-only-v1.json") -Value $temporalJson -Encoding utf8
    $temporalLinks = [regex]::Matches($temporalPage, $pngPattern)
    if ($temporalLinks.Count -ne 4) { throw "ENGINE-001 requires 4 renderer PNGs, found $($temporalLinks.Count)." }
    foreach ($link in $temporalLinks) {
        $pngName = [System.IO.Path]::GetFileName($link.Groups[2].Value)
        if (-not $pngName.StartsWith("engine001-temporal-")) { throw "Unexpected temporal PNG name: $pngName" }
        [System.IO.File]::WriteAllBytes((Join-Path $outputDir $pngName), [Convert]::FromBase64String($link.Groups[1].Value))
    }
    Write-Host "ENGINE-001 accepted-only replay: 27 strokes, 1260 historical points, Canvas2D diff=$($temporalManifest.canvas2dPixelComparison.differingPixels), WebGL diff=$($temporalManifest.webglPixelComparison.differingPixels)."


    # ENGINE-001 native Painter endpoint variants: frozen run and plan, no
    # substitution of Stage/CSS transform or synthetic accepted points.
    $endpointPlan = "AutoDraw_Stage20/data/results/brush_behavior_tests/fill001/plans/fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1.json"
    $endpointPlanBlob = (git rev-parse "HEAD:$endpointPlan").Trim()
    if ($LASTEXITCODE -ne 0 -or $endpointPlanBlob -ne "ab54d5a322a642ba6a89a6c77111e4cfadf93232") {
        throw "ENGINE-001 pinned plan blob mismatch: $endpointPlanBlob"
    }
    $endpointDom = Join-Path $env:RUNNER_TEMP "egret-endpoint-dom.html"
    $endpointStderr = Join-Path $env:RUNNER_TEMP "egret-endpoint-edge-stderr.log"
    $endpointArgs = @($browserArgs)
    $endpointArgs[-1] = "http://127.0.0.1:8765/AutoDraw_Stage20/tests/game_renderer_reference.html?endpoint=fill001"
    $endpointProcess = Start-Process -FilePath $edgePath -ArgumentList $endpointArgs -RedirectStandardOutput $endpointDom -RedirectStandardError $endpointStderr -PassThru -Wait
    if ($endpointProcess.ExitCode -ne 0) { throw "ENGINE-001 endpoint browser exited with $($endpointProcess.ExitCode)." }
    $endpointPage = Get-Content -Raw $endpointDom
    if ($endpointPage -notmatch 'data-endpoint-status="complete"' -or $endpointPage -notmatch 'data-endpoint-png-count="15"') {
        Copy-Item $endpointDom (Join-Path $outputDir "endpoint-page-failure.html") -Force
        Copy-Item $endpointStderr (Join-Path $outputDir "endpoint-edge-stderr.log") -Force
        throw "ENGINE-001 native Painter endpoint browser did not complete."
    }
    $endpointJsonMatch = [regex]::Match($endpointPage, '<pre id="renderer-manifest-json"[^>]*>(.*?)</pre>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $endpointJsonMatch.Success) { throw "ENGINE-001 endpoint manifest was not exported." }
    $endpointJson = [System.Net.WebUtility]::HtmlDecode($endpointJsonMatch.Groups[1].Value)
    $endpointManifest = $endpointJson | ConvertFrom-Json
    if ($endpointManifest.status -ne "COMPLETE_OFFLINE_NATIVE_ENGINE_MEASUREMENT" -or
        $endpointManifest.runId -ne "6a17a297-ea14-4527-9527-bfd8de3bd335" -or
        $endpointManifest.screenProjection -ne "UNCALIBRATED" -or
        $endpointManifest.acceptedCount -ne 1260 -or
        $endpointManifest.strokeCount -ne 27 -or
        $endpointManifest.aggregate.'smooth-drawlast'.nativePainterPatchedCalls -ne 27 -or
        $endpointManifest.individual.Count -ne 3) {
        throw "ENGINE-001 endpoint manifest fails native renderer provenance."
    }
    Set-Content -Path (Join-Path $outputDir "engine001-native-endpoint-v1.json") -Value $endpointJson -Encoding utf8
    $endpointLinks = [regex]::Matches($endpointPage, $pngPattern)
    if ($endpointLinks.Count -ne 15) { throw "ENGINE-001 requires 15 renderer endpoint PNGs, found $($endpointLinks.Count)." }
    foreach ($link in $endpointLinks) {
        $pngName = [System.IO.Path]::GetFileName($link.Groups[2].Value)
        if (-not $pngName.StartsWith("engine001-endpoint-")) { throw "Unexpected endpoint PNG: $pngName" }
        [System.IO.File]::WriteAllBytes((Join-Path $outputDir $pngName), [Convert]::FromBase64String($link.Groups[1].Value))
    }
    Write-Host "ENGINE-001 native endpoint raster: 27 strokes, 3 variants, 3 isolated rows, 15 PNGs; screen UNCALIBRATED."

    python AutoDraw_Stage20/tests/run_egret_stage_reference_firefox.py --base-url "http://127.0.0.1:8765" --output-dir $outputDir --workspace $env:GITHUB_WORKSPACE --paired-renderer-experiment-root "AutoDraw_Stage20/data/results/brush_behavior_tests"
    if ($LASTEXITCODE -ne 0) { throw "Firefox Stage-level A-D browser probe failed." }

} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}