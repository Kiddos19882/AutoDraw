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

    $stageCases = @(
        @{
            Name = "vertical"
            Monitor = "/AutoDraw_Stage20/data/results/brush_behavior_tests/experiment-20261105-192426-b10-paired_renderer_vertical_single_stroke-6f2227c7/monitor_report.json"
            RunId = "c860234f-995a-4789-9ac2-e05b322fe742"
        },
        @{
            Name = "diagonal"
            Monitor = "/AutoDraw_Stage20/data/results/brush_behavior_tests/experiment-20261105-192602-b10-paired_renderer_diagonal_single_stroke-0e61bc40/monitor_report.json"
            RunId = "f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f"
        }
    )

    foreach ($case in $stageCases) {
        $caseOutput = Join-Path $outputDir ("stage-level-" + $case.Name)
        New-Item -ItemType Directory -Force -Path $caseOutput | Out-Null
        $caseDom = Join-Path $env:RUNNER_TEMP ("stage-level-" + $case.Name + "-dom.html")
        $caseStderr = Join-Path $env:RUNNER_TEMP ("stage-level-" + $case.Name + "-edge-stderr.log")
        $monitorQuery = [uri]::EscapeDataString($case.Monitor)
        $caseUrl = "http://127.0.0.1:8765/AutoDraw_Stage20/tests/game_renderer_reference.html?monitor=$monitorQuery"
        $caseArgs = @(
            "--headless", "--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--no-sandbox",
            "--disable-dev-shm-usage", "--dump-dom",
            "--user-data-dir=$(Join-Path $env:RUNNER_TEMP ('egret-stage-' + $case.Name + '-profile'))",
            $caseUrl
        )
        $caseBrowser = Start-Process -FilePath $edgePath -ArgumentList $caseArgs -RedirectStandardOutput $caseDom -RedirectStandardError $caseStderr -PassThru -Wait
        if ($caseBrowser.ExitCode -ne 0) {
            if (Test-Path $caseDom) { Copy-Item $caseDom (Join-Path $caseOutput "page-dom-diagnostic.html") -Force }
            if (Test-Path $caseStderr) { Copy-Item $caseStderr (Join-Path $caseOutput "edge-stderr.log") -Force }
            throw "Stage-level $($case.Name) browser probe exited with code $($caseBrowser.ExitCode)."
        }

        $caseHtml = Get-Content -Raw $caseDom
        if ($caseHtml -notmatch 'data-reference-status="complete"' -or
            $caseHtml -notmatch 'data-fixture-count="1"' -or
            $caseHtml -notmatch 'data-webgl-status="complete"') {
            Copy-Item $caseDom (Join-Path $caseOutput "page-dom-diagnostic.html") -Force
            if (Test-Path $caseStderr) { Copy-Item $caseStderr (Join-Path $caseOutput "edge-stderr.log") -Force }
            $statusMatch = [regex]::Match($caseHtml, '<p id="renderer-status"[^>]*>(.*?)</p>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
            if ($statusMatch.Success) {
                Write-Host "Stage-level $($case.Name) status: $([System.Net.WebUtility]::HtmlDecode($statusMatch.Groups[1].Value))"
            }
            throw "Stage-level $($case.Name) browser probe did not complete."
        }

        $caseManifestMatch = [regex]::Match($caseHtml, '<pre id="renderer-manifest-json"[^>]*>(.*?)</pre>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if (-not $caseManifestMatch.Success) { throw "Stage-level $($case.Name) manifest is missing." }
        $caseManifestJson = [System.Net.WebUtility]::HtmlDecode($caseManifestMatch.Groups[1].Value)
        $caseManifest = $caseManifestJson | ConvertFrom-Json
        $variants = @($caseManifest.fixtures[0].stageLevelCompositor)
        $variantA = $variants | Where-Object { $_.id -eq "A" } | Select-Object -First 1
        $variantB = $variants | Where-Object { $_.id -eq "B" } | Select-Object -First 1
        $variantC = $variants | Where-Object { $_.id -eq "C" } | Select-Object -First 1
        $variantD = $variants | Where-Object { $_.id -eq "D" } | Select-Object -First 1
        if ($caseManifest.runtimeProfile.sourceRunId -ne $case.RunId -or
            $caseManifest.stageLevelCompositor.status -ne "generated_four_offline_variants" -or
            $caseManifest.stageLevelCompositor.variantCount -ne 4 -or
            $caseManifest.fixtures.Count -ne 1 -or $variants.Count -ne 4 -or
            $null -eq $variantA -or $null -eq $variantB -or $null -eq $variantC -or $null -eq $variantD -or
            $variantA.backend -ne "WebGL" -or $variantB.backend -ne "WebGL" -or
            $variantC.backend -ne "Canvas2D" -or $variantD.backend -ne "Canvas2D" -or
            $variantA.rendererBackend -notmatch "Egret WebGLRenderer" -or
            [Math]::Abs([double]$variantA.placement.x - 1022.375) -gt 0.0001 -or
            [double]$variantA.placement.y -ne 216 -or
            [double]$variantB.placement.x -ne 1022 -or
            [double]$variantB.placement.y -ne 216 -or
            [double]$variantA.placement.width -ne 1380 -or
            [double]$variantA.placement.height -ne 720 -or
            [int]$variantA.comparisonToA.differingPixels -ne 0) {
            Set-Content -Path (Join-Path $caseOutput "manifest-invalid.json") -Value $caseManifestJson -Encoding utf8
            throw "Stage-level $($case.Name) output failed run binding, A-D backend, placement or baseline self-comparison validation."
        }
        Set-Content -Path (Join-Path $caseOutput "manifest.json") -Value $caseManifestJson -Encoding utf8

        $casePngMatches = [regex]::Matches($caseHtml, $pngPattern)
        if ($casePngMatches.Count -ne 7) {
            Copy-Item $caseDom (Join-Path $caseOutput "page-dom-diagnostic.html") -Force
            throw "Stage-level $($case.Name) expected 7 PNG links (3 board references + 4 A-D variants), found $($casePngMatches.Count)."
        }
        $stagePngCount = 0
        foreach ($match in $casePngMatches) {
            $pngName = [System.IO.Path]::GetFileName($match.Groups[2].Value)
            if ($pngName -notlike "stage-level-*.png") { continue }
            $pngBytes = [Convert]::FromBase64String($match.Groups[1].Value)
            [System.IO.File]::WriteAllBytes((Join-Path $caseOutput $pngName), $pngBytes)
            $stagePngCount++
        }
        if ($stagePngCount -ne 4) { throw "Stage-level $($case.Name) expected four A-D PNGs, saved $stagePngCount." }
        Write-Host "Stage-level $($case.Name): run $($case.RunId), four A-D variants, four PNGs saved."
    }

} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}