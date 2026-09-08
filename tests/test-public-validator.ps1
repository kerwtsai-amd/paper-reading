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

    Write-Host 'Public validator mode test PASSED.' -ForegroundColor Green
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
