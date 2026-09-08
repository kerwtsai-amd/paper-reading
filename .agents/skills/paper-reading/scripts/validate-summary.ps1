[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PaperDirectory,

    # GitHub Pages deliberately excludes local research PDFs. This mode keeps
    # every HTML, template, structure, image, and visible-content check while
    # omitting only checks that require the local PDF file itself.
    [switch]$PublicCheck
)

$ErrorActionPreference = 'Stop'
$validationErrors = [System.Collections.Generic.List[string]]::new()
$validationWarnings = [System.Collections.Generic.List[string]]::new()

function Add-ValidationError {
    param([string]$Message)
    $validationErrors.Add($Message)
}

function Add-ValidationWarning {
    param([string]$Message)
    $validationWarnings.Add($Message)
}

function Get-VisibleHtmlText {
    param([string]$Fragment)

    $visibleText = [regex]::Replace($Fragment, '(?is)<!--.*?-->', ' ')
    $visibleText = [regex]::Replace($visibleText, '(?is)<(?:script|style)\b[^>]*>.*?</(?:script|style)>', ' ')
    $visibleText = [regex]::Replace($visibleText, '<[^>]+>', ' ')
    $visibleText = [System.Net.WebUtility]::HtmlDecode($visibleText)
    $visibleText = [regex]::Replace($visibleText, '\s+', ' ')
    return $visibleText.Trim()
}

try {
    $resolvedPaperDirectory = (Resolve-Path -LiteralPath $PaperDirectory).Path
}
catch {
    Write-Error "Paper directory does not exist: $PaperDirectory"
    exit 1
}

$projectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))))
$canonicalTemplatePath = Join-Path $projectRoot 'html template/summary-template.html'
$canonicalTemplate = if (Test-Path -LiteralPath $canonicalTemplatePath -PathType Leaf) {
    Get-Content -Raw -LiteralPath $canonicalTemplatePath -Encoding UTF8
}
else {
    ''
}
$canonicalVersionMatch = [regex]::Match($canonicalTemplate, 'data-template-version\s*=\s*["'']([^"'']+)["'']', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
$canonicalStyleMatch = [regex]::Match($canonicalTemplate, '<meta\b[^>]*\bname\s*=\s*["'']paper-summary-template["''][^>]*\bcontent\s*=\s*["'']([^"'']+)["'']', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
$requiredFontStylesheet = 'https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700;800&family=Open+Sans:wght@400;500;600;700;800&display=swap'
$requiredFontPreconnects = @(
    'https://fonts.googleapis.com',
    'https://fonts.gstatic.com'
)
$requiredFontStack = '"Open Sans", "Noto Sans TC", sans-serif'
$relativePaperDirectory = [System.IO.Path]::GetRelativePath($projectRoot, $resolvedPaperDirectory)
$relativeSegments = @($relativePaperDirectory -split '[\\/]' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })

if ([System.IO.Path]::IsPathRooted($relativePaperDirectory) -or $relativePaperDirectory -eq '..' -or $relativePaperDirectory.StartsWith("..$([System.IO.Path]::DirectorySeparatorChar)")) {
    Add-ValidationError 'Paper directory is outside the Paper Reading project root.'
}
elseif ($relativeSegments.Count -ne 3) {
    Add-ValidationError "Paper directory must be exactly <Topic>/<Subtopic>/<Formal Paper Title>; found $($relativeSegments.Count) level(s): $relativePaperDirectory"
}

$summaryPath = Join-Path -Path $resolvedPaperDirectory -ChildPath 'summary.html'
$imagesDirectory = Join-Path -Path $resolvedPaperDirectory -ChildPath 'assets\images'

if (-not (Test-Path -LiteralPath $summaryPath -PathType Leaf)) {
    Add-ValidationError "Missing summary.html: $summaryPath"
}

if (-not (Test-Path -LiteralPath $imagesDirectory -PathType Container)) {
    Add-ValidationError "Missing assets/images directory: $imagesDirectory"
}

if (-not $PublicCheck) {
    $pdfFiles = @(Get-ChildItem -LiteralPath $resolvedPaperDirectory -File -Filter '*.pdf' -ErrorAction SilentlyContinue)
    if ($pdfFiles.Count -eq 0) {
        Add-ValidationError 'No PDF found in the paper directory.'
    }
    elseif ($pdfFiles.Count -gt 1) {
        Add-ValidationWarning "Found $($pdfFiles.Count) PDFs. Confirm which version is canonical."
    }

    $paperFolderName = Split-Path -Leaf $resolvedPaperDirectory
    $expectedPdfName = "$paperFolderName.pdf"
    $expectedPdfPath = Join-Path -Path $resolvedPaperDirectory -ChildPath $expectedPdfName
    $canonicalNameHasPathRisk = $expectedPdfPath.Length -ge 260 -or $expectedPdfName.Length -gt 255
    $matchingPdf = @($pdfFiles | Where-Object { $_.Name.Equals($expectedPdfName, [System.StringComparison]::OrdinalIgnoreCase) })
    if ($canonicalNameHasPathRisk) {
        Add-ValidationWarning "Canonical PDF path is $($expectedPdfPath.Length) characters and may exceed tool limits. Keep this note in the completion report, not summary.html."
    }
    if ($pdfFiles.Count -eq 1 -and $matchingPdf.Count -eq 0) {
        if ($canonicalNameHasPathRisk) {
            Add-ValidationWarning "A traceable safe PDF filename is being used. Found: $($pdfFiles[0].Name)"
        }
        else {
            Add-ValidationError "PDF must be named after the paper folder when no objective path-length exception exists. Expected: $expectedPdfName"
        }
    }
    elseif ($pdfFiles.Count -gt 1 -and $matchingPdf.Count -eq 0) {
        Add-ValidationError "Multiple PDFs found and none uses the canonical paper-folder name: $expectedPdfName"
    }

    foreach ($pdfFile in $pdfFiles) {
        if ($pdfFile.Length -lt 5) {
            Add-ValidationError "PDF is empty or truncated: $($pdfFile.Name)"
            continue
        }

        $pdfStream = $null
        try {
            $pdfStream = [System.IO.File]::OpenRead($pdfFile.FullName)
            $signatureBytes = New-Object byte[] 5
            $bytesRead = $pdfStream.Read($signatureBytes, 0, 5)
            $signature = [System.Text.Encoding]::ASCII.GetString($signatureBytes, 0, $bytesRead)
            if ($signature -ne '%PDF-') {
                Add-ValidationError "File does not begin with a PDF signature: $($pdfFile.Name)"
            }
        }
        catch {
            Add-ValidationError "Cannot open PDF $($pdfFile.Name): $($_.Exception.Message)"
        }
        finally {
            if ($null -ne $pdfStream) {
                $pdfStream.Dispose()
            }
        }
    }
}

if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {
    try {
        $html = Get-Content -Raw -LiteralPath $summaryPath -Encoding UTF8
    }
    catch {
        Add-ValidationError "Cannot read summary.html as UTF-8: $($_.Exception.Message)"
        $html = ''
    }

    if ($html -notmatch 'data-template-id\s*=\s*["'']paper-reading-summary["'']') {
        Add-ValidationError 'Missing required data-template-id="paper-reading-summary" marker.'
    }
    $summaryVersionMatch = [regex]::Match($html, 'data-template-version\s*=\s*["'']([^"'']+)["'']', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $summaryVersionMatch.Success) {
        Add-ValidationError 'Missing data-template-version marker.'
    }
    elseif ($canonicalVersionMatch.Success -and $summaryVersionMatch.Groups[1].Value -ne $canonicalVersionMatch.Groups[1].Value) {
        Add-ValidationError "Summary template version $($summaryVersionMatch.Groups[1].Value) does not match canonical version $($canonicalVersionMatch.Groups[1].Value)."
    }
    $summaryStyleMatch = [regex]::Match($html, '<meta\b[^>]*\bname\s*=\s*["'']paper-summary-template["''][^>]*\bcontent\s*=\s*["'']([^"'']+)["'']', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $summaryStyleMatch.Success) {
        Add-ValidationError 'Missing paper-summary-template meta marker.'
    }
    elseif ($canonicalStyleMatch.Success -and $summaryStyleMatch.Groups[1].Value -ne $canonicalStyleMatch.Groups[1].Value) {
        Add-ValidationError "Summary style marker $($summaryStyleMatch.Groups[1].Value) does not match canonical style $($canonicalStyleMatch.Groups[1].Value)."
    }
    if ($html -notmatch '(?i)<html\b[^>]*\blang\s*=\s*["'']zh-Hant["'']') {
        Add-ValidationError 'The root html element must declare lang="zh-Hant".'
    }
    if ($html -notmatch '(?i)<meta\b[^>]*\bname\s*=\s*["'']viewport["'']') {
        Add-ValidationError 'Missing responsive viewport meta tag.'
    }
    if ($html -notmatch 'mathjax@3\.2\.2/es5/tex-chtml\.js') {
        Add-ValidationError 'MathJax 3.2.2 loader is missing or changed.'
    }
    if ($html -notmatch 'inlineMath' -or $html -notmatch 'displayMath') {
        Add-ValidationError 'MathJax inline/display delimiter configuration is missing.'
    }

    foreach ($fontVariableName in @('sans', 'serif', 'mono')) {
        $fontVariableMatches = [regex]::Matches(
            $html,
            '(?im)--{0}\s*:\s*([^;}}]+)\s*;' -f [regex]::Escape($fontVariableName)
        )
        if ($fontVariableMatches.Count -ne 1) {
            Add-ValidationError "Typography variable --$fontVariableName must occur exactly once; found $($fontVariableMatches.Count)."
            continue
        }

        $declaredFontStack = [regex]::Replace($fontVariableMatches[0].Groups[1].Value.Trim(), '\s+', ' ')
        if ($declaredFontStack -cne $requiredFontStack) {
            Add-ValidationError "Typography variable --$fontVariableName must be $requiredFontStack; found: $declaredFontStack"
        }
    }

    if ($html -notmatch '(?is)\bbody\s*\{[^}]*\bfont-family\s*:\s*var\(--sans\)\s*;') {
        Add-ValidationError 'The body font-family must resolve through var(--sans).'
    }

    $fontFamilyMatches = [regex]::Matches($html, '(?im)\bfont-family\s*:\s*([^;}{]+)\s*;')
    $allowedFontFamilyValues = @('var(--sans)', 'var(--serif)', 'var(--mono)', $requiredFontStack)
    foreach ($fontFamilyMatch in $fontFamilyMatches) {
        $fontFamilyValue = [regex]::Replace($fontFamilyMatch.Groups[1].Value.Trim(), '\s+', ' ')
        if ($fontFamilyValue -cnotin $allowedFontFamilyValues) {
            Add-ValidationError "Unexpected font-family declaration '$fontFamilyValue'. All text must resolve to Open Sans + Noto Sans TC through the canonical variables."
        }
    }
    if ($html -match '(?i)@import\b') {
        Add-ValidationError 'CSS @import is forbidden; the canonical Google Fonts link is the only permitted linked stylesheet.'
    }
    if ($html -match '(?i)@font-face\b') {
        Add-ValidationError 'Inline @font-face declarations are forbidden; use only the canonical Google Fonts families.'
    }

    $remainingPlaceholders = [regex]::Matches($html, '\{\{[A-Z0-9_]+\}\}') | ForEach-Object { $_.Value } | Sort-Object -Unique
    if ($remainingPlaceholders.Count -gt 0) {
        Add-ValidationError "Unresolved template placeholders: $($remainingPlaceholders -join ', ')"
    }

    $requiredSectionRoles = @(
        'prerequisites',
        'problem',
        'insight',
        'method',
        'evidence',
        'critique',
        'extensions',
        'reference'
    )
    $rolePositions = [System.Collections.Generic.List[int]]::new()

    foreach ($sectionRole in $requiredSectionRoles) {
        $escapedRole = [regex]::Escape($sectionRole)
        $sectionMatches = [regex]::Matches(
            $html,
            '<section\b(?=[^>]*\bdata-section-role\s*=\s*["'']{0}["''])[^>]*>(.*?)</section>' -f $escapedRole,
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
        )

        if ($sectionMatches.Count -ne 1) {
            Add-ValidationError "Semantic role '$sectionRole' must occur exactly once; found $($sectionMatches.Count)."
            continue
        }

        $sectionMatch = $sectionMatches[0]
        $rolePositions.Add($sectionMatch.Index)
        $sectionTagMatch = [regex]::Match($sectionMatch.Value, '^<section\b[^>]*>', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        $sectionIdMatch = [regex]::Match($sectionTagMatch.Value, '\bid\s*=\s*["'']([^"'']+)["'']', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if (-not $sectionIdMatch.Success) {
            Add-ValidationError "Semantic role '$sectionRole' is missing an id for TOC navigation."
        }
        else {
            $sectionId = $sectionIdMatch.Groups[1].Value
            $tocPattern = 'href\s*=\s*["'']#{0}["'']' -f [regex]::Escape($sectionId)
            if ($html -notmatch $tocPattern) {
                Add-ValidationError "Table of contents does not link to semantic role '$sectionRole' (#$sectionId)."
            }
        }

        if ($sectionMatch.Groups[1].Value -notmatch '(?is)<h2\b[^>]*>\s*\S') {
            Add-ValidationError "Semantic role '$sectionRole' must have a non-empty h2."
        }
        $sectionBody = [regex]::Replace($sectionMatch.Groups[1].Value, '(?is)<(?:h2|span)\b[^>]*>.*?</(?:h2|span)>', ' ')
        $sectionText = Get-VisibleHtmlText -Fragment $sectionBody
        if ([string]::IsNullOrWhiteSpace($sectionText)) {
            Add-ValidationError "Semantic role '$sectionRole' has no reader-facing body content."
        }
        elseif ($sectionText.Length -lt 80) {
            Add-ValidationWarning "Semantic role '$sectionRole' is unusually short ($($sectionText.Length) characters)."
        }
    }

    for ($index = 1; $index -lt $rolePositions.Count; $index++) {
        if ($rolePositions[$index] -le $rolePositions[$index - 1]) {
            Add-ValidationError 'Semantic roles do not appear in the required reader-first order.'
            break
        }
    }

    $referenceMatch = [regex]::Match(
        $html,
        '<section\b(?=[^>]*\bdata-section-role\s*=\s*["'']reference["''])[^>]*>(.*?)</section>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    if ($referenceMatch.Success) {
        $paperInfoHtml = $referenceMatch.Groups[1].Value
        $paperInfoText = Get-VisibleHtmlText -Fragment $paperInfoHtml
        $pageCountFields = [regex]::Matches(
            $paperInfoHtml,
            '<(?:td|dd|span)\b[^>]*\bdata-summary-field\s*=\s*["'']pdf-page-count["''][^>]*>(.*?)</(?:td|dd|span)>',
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
        )

        if ($pageCountFields.Count -ne 1) {
            Add-ValidationError "Reference role must contain exactly one data-summary-field='pdf-page-count'; found $($pageCountFields.Count)."
        }
        else {
            $pageCountValue = Get-VisibleHtmlText -Fragment $pageCountFields[0].Groups[1].Value
            if ($pageCountValue -notmatch '^共\s*[1-9]\d*\s*頁$') {
                Add-ValidationError "Page-count field must contain only '共 N 頁'; found: $pageCountValue"
            }
        }

        $paperInfoOperationalPatterns = @(
            '(?:檔名|檔案|絕對路徑|下載流程|處理工具|頁碼對照)(?:說明|備註|紀錄|資訊|驗證)?[：:]',
            '檔案驗證',
            'PDF\s+(?:metadata|signature)',
            '%PDF-\d',
            'SHA-?(?:1|256|512)',
            '\b\d[\d,]*\s*bytes?\b',
            'Windows.{0,40}(?:禁止|不允許).*?字元',
            '絕對路徑',
            '\bPoppler\b',
            '無\s*(?:offset|頁碼偏移)',
            '頁碼.{0,48}(?:一致|相同)',
            '(?:landing page|PDF metadata|首頁).{0,24}交叉核對'
        )

        foreach ($paperInfoOperationalPattern in $paperInfoOperationalPatterns) {
            if ($paperInfoText -match $paperInfoOperationalPattern) {
                Add-ValidationError "Reference metadata contains operational/QA prose that must stay out of summary.html (matched: $paperInfoOperationalPattern)"
            }
        }
    }

    $updateDateMatches = [regex]::Matches(
        $html,
        '<time\b(?=[^>]*\bdata-summary-field\s*=\s*["'']last-updated["''])[^>]*\bdatetime\s*=\s*["''](\d{4}-\d{2}-\d{2})["''][^>]*>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    if ($updateDateMatches.Count -ne 1) {
        Add-ValidationError "Summary must contain exactly one marked update date; found $($updateDateMatches.Count)."
    }

    $visibleSummaryText = Get-VisibleHtmlText -Fragment $html
    $globalOperationalPatterns = @(
        '檔名說明[：:]',
        '檔案驗證[：:]',
        '每張圖.{0,80}(?:由|從)本地.{0,40}PDF.{0,40}(?:裁切|擷取)'
    )
    foreach ($globalOperationalPattern in $globalOperationalPatterns) {
        if ($visibleSummaryText -match $globalOperationalPattern) {
            Add-ValidationError "Visible summary content contains a production-process note (matched: $globalOperationalPattern)"
        }
    }

    $h1Count = [regex]::Matches($html, '<h1\b', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase).Count
    if ($h1Count -ne 1) {
        Add-ValidationError "Expected exactly one h1, found $h1Count."
    }

    $idMatches = [regex]::Matches($html, '\bid\s*=\s*["'']([^"'']+)["'']', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $duplicateIds = $idMatches |
        ForEach-Object { $_.Groups[1].Value } |
        Group-Object |
        Where-Object { $_.Count -gt 1 } |
        Select-Object -ExpandProperty Name
    if ($duplicateIds.Count -gt 0) {
        Add-ValidationError "Duplicate HTML ids: $($duplicateIds -join ', ')"
    }

    $knownIds = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    foreach ($idMatch in $idMatches) {
        [void]$knownIds.Add($idMatch.Groups[1].Value)
    }
    $internalLinkMatches = [regex]::Matches($html, '<a\b[^>]*\bhref\s*=\s*["'']#([^"'']+)["''][^>]*>', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    foreach ($internalLinkMatch in $internalLinkMatches) {
        $targetId = [System.Net.WebUtility]::HtmlDecode($internalLinkMatch.Groups[1].Value)
        if (-not $knownIds.Contains($targetId)) {
            Add-ValidationError "Internal link target does not exist: #$targetId"
        }
    }

    $statementCount = [regex]::Matches($html, '<(?:aside|div)\b[^>]*\bclass\s*=\s*["''][^"'']*\bstatement\b', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase).Count
    if ($statementCount -gt 10) {
        Add-ValidationError "Reader-first v2 forbids a callout wall; found $statementCount large statement callouts (maximum 10)."
    }
    elseif ($statementCount -gt 6) {
        Add-ValidationWarning "The article has $statementCount large statement callouts; normally keep six or fewer."
    }
    if ($html -match '(?i)<[^>]+\bclass\s*=\s*["''][^"'']*\bkey-card\b') {
        Add-ValidationError 'Reader-first v2 forbids dashboard key-card markup; use continuous prose or a flat takeaway list.'
    }
    if ($html -match '(?i)<section\b[^>]*\bid\s*=\s*["'']figures-guide["'']') {
        Add-ValidationError 'Reader-first v2 forbids a detached figure gallery; place figures at first explanatory use.'
    }

    $evidenceBlocks = [regex]::Matches(
        $html,
        '<(?<tag>aside|p|div)\b(?=[^>]*\bdata-kind\s*=\s*["''](?<kind>author-claim|experimental-fact|analysis|speculation)["''])[^>]*>(.*?)</\k<tag>>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    $expectedEvidenceLabels = @{
        'author-claim' = '作者主張'
        'experimental-fact' = '實驗事實'
        'analysis' = '分析'
        'speculation' = '推測'
    }
    foreach ($evidenceBlock in $evidenceBlocks) {
        $kind = $evidenceBlock.Groups['kind'].Value.ToLowerInvariant()
        $visibleEvidence = Get-VisibleHtmlText -Fragment $evidenceBlock.Groups[1].Value
        if ($visibleEvidence -notmatch ('(^|\s)' + [regex]::Escape($expectedEvidenceLabels[$kind]) + '(\s|$)')) {
            Add-ValidationError "Evidence block '$kind' is missing its visible Traditional Chinese label."
        }
        if ($kind -in @('author-claim', 'experimental-fact') -and $evidenceBlock.Value -notmatch '(?i)\bclass\s*=\s*["''][^"'']*\bsource-ref\b') {
            Add-ValidationError "Evidence block '$kind' must contain a source-ref."
        }
    }

    if ($html -match '(?i)\b(?:src|href)\s*=\s*["'']file://') {
        Add-ValidationError 'file:// URLs are not portable and are forbidden.'
    }
    if ($html -match '(?i)\b(?:src|href)\s*=\s*["''][A-Z]:[\\/]') {
        Add-ValidationError 'Absolute Windows paths are not portable and are forbidden.'
    }
    if ($html -match '(?i)\b(?:src|href)\s*=\s*["''][^"'']*(?:\.\.[\\/])') {
        Add-ValidationError 'Parent-directory references (../) are forbidden in summary resources.'
    }
    $fontStylesheetCount = 0
    $fontPreconnectCounts = @{
        'https://fonts.googleapis.com' = 0
        'https://fonts.gstatic.com' = 0
    }
    $linkTagMatches = [regex]::Matches($html, '<link\b[^>]*>', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    foreach ($linkTagMatch in $linkTagMatches) {
        $linkTag = $linkTagMatch.Value
        $linkRelMatch = [regex]::Match($linkTag, '\brel\s*=\s*["'']([^"'']+)["'']', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if (-not $linkRelMatch.Success) {
            continue
        }

        $linkRelations = @($linkRelMatch.Groups[1].Value -split '\s+' | ForEach-Object { $_.ToLowerInvariant() })
        $linkHrefMatch = [regex]::Match($linkTag, '\bhref\s*=\s*["'']([^"'']+)["'']', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        $linkHref = if ($linkHrefMatch.Success) {
            [System.Net.WebUtility]::HtmlDecode($linkHrefMatch.Groups[1].Value)
        }
        else {
            ''
        }

        if ($linkRelations -contains 'stylesheet') {
            $fontStylesheetCount++
            if ($linkHref -cne $requiredFontStylesheet) {
                Add-ValidationError "Unexpected linked stylesheet: $linkHref"
            }
        }

        if ($linkRelations -contains 'preconnect') {
            if ($linkHref -cnotin $requiredFontPreconnects) {
                Add-ValidationError "Unexpected preconnect target: $linkHref"
            }
            else {
                $fontPreconnectCounts[$linkHref]++
                if ($linkHref -ceq 'https://fonts.gstatic.com' -and $linkTag -notmatch '(?i)\bcrossorigin(?:\s*=\s*(?:["''][^"'']*["'']|[^\s>]+))?') {
                    Add-ValidationError 'The fonts.gstatic.com preconnect must include crossorigin.'
                }
            }
        }

        if ($linkRelations -contains 'preload' -and $linkTag -match '(?i)\bas\s*=\s*["'']font["'']') {
            Add-ValidationError "Font preloads are forbidden; use only the canonical Google Fonts stylesheet and preconnects: $linkHref"
        }
    }

    if ($fontStylesheetCount -ne 1) {
        Add-ValidationError "Summary must contain exactly one canonical Google Fonts stylesheet; found $fontStylesheetCount."
    }
    foreach ($requiredFontPreconnect in $requiredFontPreconnects) {
        if ($fontPreconnectCounts[$requiredFontPreconnect] -ne 1) {
            Add-ValidationError "Summary must contain exactly one preconnect to $requiredFontPreconnect; found $($fontPreconnectCounts[$requiredFontPreconnect])."
        }
    }

    $scriptSourceMatches = [regex]::Matches(
        $html,
        '<script\b[^>]*\bsrc\s*=\s*["'']([^"'']+)["''][^>]*>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    foreach ($scriptSourceMatch in $scriptSourceMatches) {
        $scriptSource = $scriptSourceMatch.Groups[1].Value
        if ($scriptSource -ne 'https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-chtml.js') {
            Add-ValidationError "Unexpected external script: $scriptSource"
        }
    }

    $imageMatches = [regex]::Matches(
        $html,
        '<img\b[^>]*\bsrc\s*=\s*["'']([^"'']+)["''][^>]*>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )

    foreach ($imageMatch in $imageMatches) {
        $imageTag = $imageMatch.Value
        $imageSource = [System.Net.WebUtility]::HtmlDecode($imageMatch.Groups[1].Value)

        if ($imageSource -notmatch '^assets/images/[A-Za-z0-9._~!$&''()+,;=@% -]+$') {
            Add-ValidationError "Image src must use assets/images/<filename>: $imageSource"
            continue
        }
        if ($imageTag -notmatch '\balt\s*=\s*["''][^"'']+["'']') {
            Add-ValidationError "Image is missing a descriptive alt attribute: $imageSource"
        }

        $relativeImagePath = $imageSource.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $absoluteImagePath = [System.IO.Path]::GetFullPath((Join-Path -Path $resolvedPaperDirectory -ChildPath $relativeImagePath))
        if (-not $absoluteImagePath.StartsWith($resolvedPaperDirectory, [System.StringComparison]::OrdinalIgnoreCase)) {
            Add-ValidationError "Image path escapes paper directory: $imageSource"
            continue
        }
        if (-not (Test-Path -LiteralPath $absoluteImagePath -PathType Leaf)) {
            Add-ValidationError "Referenced image does not exist: $imageSource"
        }
        elseif ((Get-Item -LiteralPath $absoluteImagePath).Length -eq 0) {
            Add-ValidationError "Referenced image is empty: $imageSource"
        }
    }

    $figureMatches = [regex]::Matches(
        $html,
        '<figure\b[^>]*>(.*?)</figure>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    $methodFigureCount = 0
    $resultFigureCount = 0
    foreach ($figureMatch in $figureMatches) {
        if ($figureMatch.Value -match '(?i)^<figure\b[^>]*\bdata-figure-role\s*=\s*["'']method["'']') {
            $methodFigureCount++
        }
        elseif ($figureMatch.Value -match '(?i)^<figure\b[^>]*\bdata-figure-role\s*=\s*["'']result["'']') {
            $resultFigureCount++
        }
        else {
            Add-ValidationError 'Every figure must declare data-figure-role="method" or "result" so it stays attached to the claim it explains.'
        }
        $figureHtml = $figureMatch.Groups[1].Value
        $captionMatches = [regex]::Matches(
            $figureHtml,
            '<figcaption\b[^>]*>(.*?)</figcaption>',
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
        )
        if ($captionMatches.Count -eq 0) {
            Add-ValidationError 'A figure is missing figcaption.'
            continue
        }
        if ($captionMatches.Count -ne 1) {
            Add-ValidationError 'A figure must contain exactly one figcaption.'
            continue
        }
        $captionMatch = $captionMatches[0]
        if ($captionMatch.Value -notmatch '(?i)<figcaption\b[^>]*\bdata-caption-kind\s*=\s*["'']paper-object["'']') {
            Add-ValidationError 'A figure caption must declare data-caption-kind="paper-object".'
        }
        $captionHtml = $captionMatch.Groups[1].Value
        $paperObjectLabel = $null
        $readingGuide = $null
        $paperObjectLabelMatches = [regex]::Matches(
            $captionHtml,
            '<(?<tag>strong|a)\b[^>]*\bdata-caption-field\s*=\s*["'']paper-object-label["''][^>]*>(.*?)</\k<tag>>',
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
        )
        if ($paperObjectLabelMatches.Count -ne 1) {
            Add-ValidationError 'A figure caption must contain exactly one data-caption-field="paper-object-label" source label.'
        }
        else {
            $paperObjectLabel = Get-VisibleHtmlText $paperObjectLabelMatches[0].Groups[1].Value
            if ($paperObjectLabel -notmatch '(?i)^(?:Figure|Table|Algorithm)\s+(?:(?:[A-Z]\.)?\d+(?:\.\d+)*(?:[A-Z])?|[A-Z]\d+(?:\.\d+)*(?:[A-Z])?|[IVXLCDM]+)(?:\s*\([A-Z0-9]+(?:\s*[\-–]\s*[A-Z0-9]+)?\))?$') {
                Add-ValidationError 'The paper-object label must contain only Figure/Table/Algorithm and the original identifier (for example, Figure 4 or Figure A.2).'
            }
        }

        $readingGuideMatches = [regex]::Matches(
            $captionHtml,
            '<(?<tag>span|div|p)\b(?=[^>]*\bclass\s*=\s*["''][^"'']*\breading-guide\b[^"'']*["''])(?=[^>]*\bdata-caption-field\s*=\s*["'']reading-guide["''])[^>]*>(.*?)</\k<tag>>',
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
        )
        if ($readingGuideMatches.Count -ne 1) {
            Add-ValidationError 'A figure caption must contain exactly one marked reading guide.'
        }
        else {
            $readingGuide = Get-VisibleHtmlText $readingGuideMatches[0].Groups[1].Value
            if ($readingGuide -notmatch '^導讀\s*[：:]\s*\S') {
                Add-ValidationError 'A figure reading guide must start with 導讀： and contain self-authored guidance.'
            }
            elseif ($readingGuide.Length -lt 18) {
                Add-ValidationWarning "Figure reading guide is very short and may not explain what to inspect or why it matters: $readingGuide"
            }
        }

        $captionVisibleText = Get-VisibleHtmlText $captionHtml
        if ($captionVisibleText -match '(?i)(?<![A-Za-z])pp?\.\s*\d+|\bpages?\s+\d+|第\s*\d+\s*頁|頁碼|論文標示|(?:(?:裁切|擷取|截取)\s*自\s*(?:原)?論文)|(?:(?:取自|源自|來自)\s*(?:原)?論文)|(?:(?:由|從)\s*(?:原)?論文.{0,12}(?:裁切|擷取|截取))') {
            Add-ValidationError 'A figure caption must not include page mapping, source prose, or crop/extraction provenance.'
        }
        if ($null -ne $paperObjectLabel -and $null -ne $readingGuide) {
            $expectedCaptionText = "$paperObjectLabel $readingGuide".Trim()
            if ($captionVisibleText -cne $expectedCaptionText) {
                Add-ValidationError 'A figure caption may contain only the paper-object label followed directly by its reading guide.'
            }
        }
    }

    if ($figureMatches.Count -eq 0) {
        Add-ValidationError 'The article has no explanatory figures. Extract at least one method and one result figure, or record a paper-specific omission in the validator contract.'
    }
    else {
        if ($methodFigureCount -eq 0) {
            Add-ValidationError 'The article needs at least one figure marked data-figure-role="method".'
        }
        if ($resultFigureCount -eq 0) {
            Add-ValidationError 'The article needs at least one figure marked data-figure-role="result".'
        }
    }
}

Write-Host ''
Write-Host "Paper package: $resolvedPaperDirectory"

if ($validationWarnings.Count -gt 0) {
    Write-Host "Warnings ($($validationWarnings.Count)):" -ForegroundColor Yellow
    foreach ($validationWarning in $validationWarnings) {
        Write-Host "  - $validationWarning" -ForegroundColor Yellow
    }
}

if ($validationErrors.Count -gt 0) {
    Write-Host "Errors ($($validationErrors.Count)):" -ForegroundColor Red
    foreach ($validationError in $validationErrors) {
        Write-Host "  - $validationError" -ForegroundColor Red
    }
    Write-Host ''
    Write-Host 'Validation FAILED.' -ForegroundColor Red
    exit 1
}

Write-Host 'Validation PASSED.' -ForegroundColor Green
exit 0
