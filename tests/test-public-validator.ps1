[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$sourceRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$testsRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$testRoot = Join-Path $testsRoot ".public-validator-test-$([guid]::NewGuid().ToString('N'))"
$testRoot = [System.IO.Path]::GetFullPath($testRoot)
$testsPrefix = $testsRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if (-not $testRoot.StartsWith($testsPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to create a test tree outside tests/: $testRoot"
}

try {
    $sourceValidator = Join-Path $sourceRoot '.agents/skills/paper-reading/scripts/validate-summary.ps1'
    $validatorDirectory = Join-Path $testRoot '.agents/skills/paper-reading/scripts'
    New-Item -ItemType Directory -Path $validatorDirectory -Force | Out-Null
    Copy-Item -LiteralPath $sourceValidator -Destination (Join-Path $validatorDirectory 'validate-summary.ps1')

    $sourceSummary = Get-ChildItem -LiteralPath $sourceRoot -Recurse -File -Filter 'summary.html' |
        Where-Object {
            $relative = [System.IO.Path]::GetRelativePath($sourceRoot, $_.FullName)
            @($relative -split '[\\/]').Count -eq 4
        } |
        Sort-Object FullName |
        Select-Object -First 1
    if ($null -eq $sourceSummary) {
        throw 'No source summary is available for the public-validator test.'
    }

    $paperDirectory = Join-Path $testRoot 'Test Topic/Test Subtopic/Test Paper'
    New-Item -ItemType Directory -Path $paperDirectory -Force | Out-Null
    Copy-Item -LiteralPath $sourceSummary.FullName -Destination (Join-Path $paperDirectory 'summary.html')
    $sourceAssets = Join-Path $sourceSummary.DirectoryName 'assets'
    if (Test-Path -LiteralPath $sourceAssets -PathType Container) {
        Copy-Item -LiteralPath $sourceAssets -Destination $paperDirectory -Recurse
    }

    $validator = Join-Path $validatorDirectory 'validate-summary.ps1'
    & pwsh -NoProfile -File $validator -PaperDirectory $paperDirectory -PublicCheck
    if ($LASTEXITCODE -ne 0) {
        throw 'PublicCheck should validate a publishable package without a local PDF.'
    }

    & pwsh -NoProfile -File $validator -PaperDirectory $paperDirectory
    if ($LASTEXITCODE -eq 0) {
        throw 'Default validation must still reject a paper package without a local PDF.'
    }

    $fixtureSummaryPath = Join-Path $paperDirectory 'summary.html'
    $validSummaryHtml = Get-Content -Raw -LiteralPath $fixtureSummaryPath -Encoding UTF8
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    $fontFailureFixtures = @(
        @{
            Name = 'wrong font stack'
            Find = '--mono: "Open Sans", "Noto Sans TC", sans-serif;'
            Replace = '--mono: Consolas, monospace;'
            Expected = 'Typography variable --mono must be'
        },
        @{
            Name = 'unexpected font stylesheet'
            Find = '&amp;display=swap'
            Replace = '&amp;display=block'
            Expected = 'Unexpected linked stylesheet'
        },
        @{
            Name = 'missing gstatic crossorigin'
            Find = '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            Replace = '<link rel="preconnect" href="https://fonts.gstatic.com">'
            Expected = 'fonts.gstatic.com preconnect must include crossorigin'
        },
        @{
            Name = 'CSS font import bypass'
            Find = '</head>'
            Replace = '<style>@import url("https://example.com/font.css");</style></head>'
            Expected = 'CSS @import is forbidden'
        }
    )

    foreach ($fontFailureFixture in $fontFailureFixtures) {
        $invalidSummaryHtml = $validSummaryHtml.Replace($fontFailureFixture.Find, $fontFailureFixture.Replace)
        if ($invalidSummaryHtml -ceq $validSummaryHtml) {
            throw "Font fixture '$($fontFailureFixture.Name)' could not mutate the selected summary."
        }
        [System.IO.File]::WriteAllText($fixtureSummaryPath, $invalidSummaryHtml, $utf8NoBom)
        $fontFailureOutput = (& pwsh -NoProfile -File $validator -PaperDirectory $paperDirectory -PublicCheck 2>&1 | Out-String)
        if ($LASTEXITCODE -eq 0) {
            throw "Font fixture '$($fontFailureFixture.Name)' should fail validation."
        }
        if ($fontFailureOutput -notmatch [regex]::Escape($fontFailureFixture.Expected)) {
            throw "Font fixture '$($fontFailureFixture.Name)' failed for the wrong reason: $fontFailureOutput"
        }
    }
    [System.IO.File]::WriteAllText($fixtureSummaryPath, $validSummaryHtml, $utf8NoBom)

    Write-Host 'Public validator mode and font-contract tests PASSED.' -ForegroundColor Green
}
finally {
    if (Test-Path -LiteralPath $testRoot) {
        $resolvedRemovalTarget = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $testRoot).Path)
        if (-not $resolvedRemovalTarget.StartsWith($testsPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove a test tree outside tests/: $resolvedRemovalTarget"
        }
        Remove-Item -LiteralPath $resolvedRemovalTarget -Recurse -Force
    }
}
