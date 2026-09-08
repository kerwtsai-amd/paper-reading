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
    if ($pdfFiles.Count -eq 1 -and $matchingPdf.Count -eq 0) {
        if ($canonicalNameHasPathRisk) {
            Add-ValidationWarning "A traceable safe PDF filename is being used because the canonical path is $($expectedPdfPath.Length) characters. Keep this explanation in the completion report, not summary.html. Found: $($pdfFiles[0].Name)"
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
    if ($html -notmatch 'data-template-version\s*=\s*["''][^"'']+["'']') {
        Add-ValidationError 'Missing data-template-version marker.'
    }
    if ($html -notmatch 'paper-summary-template') {
        Add-ValidationError 'Missing paper-summary-template meta marker.'
    }
    if ($html -notmatch 'mathjax@3\.2\.2/es5/tex-chtml\.js') {
        Add-ValidationError 'MathJax 3.2.2 loader is missing or changed.'
    }
    if ($html -notmatch 'inlineMath' -or $html -notmatch 'displayMath') {
        Add-ValidationError 'MathJax inline/display delimiter configuration is missing.'
    }

    $remainingPlaceholders = [regex]::Matches($html, '\{\{[A-Z0-9_]+\}\}') | ForEach-Object { $_.Value } | Sort-Object -Unique
    if ($remainingPlaceholders.Count -gt 0) {
        Add-ValidationError "Unresolved template placeholders: $($remainingPlaceholders -join ', ')"
    }

    $requiredSectionIds = @(
        'paper-info',
        'one-sentence-summary',
        'executive-summary',
        'background-motivation',
        'problem-definition',
        'core-method',
        'formulas-theory',
        'figures-guide',
        'experimental-setup',
        'experimental-results',
        'ablation-sensitivity',
        'strengths-limitations-risks',
        'related-work',
        'personal-analysis',
        'discussion-questions',
        'glossary-index'
    )

    foreach ($sectionId in $requiredSectionIds) {
        $escapedSectionId = [regex]::Escape($sectionId)
        $sectionPattern = '<section\b[^>]*\bid\s*=\s*["'']{0}["''][^>]*>(.*?)</section>' -f $escapedSectionId
        $sectionMatch = [regex]::Match(
            $html,
            $sectionPattern,
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
        )

        if (-not $sectionMatch.Success) {
            Add-ValidationError "Missing required section id: $sectionId"
            continue
        }

        $sectionText = Get-VisibleHtmlText -Fragment $sectionMatch.Groups[1].Value
        if ([string]::IsNullOrWhiteSpace($sectionText)) {
            Add-ValidationError "Section is empty: $sectionId"
        }

        $tocPattern = 'href\s*=\s*["'']#{0}["'']' -f $escapedSectionId
        if ($html -notmatch $tocPattern) {
            Add-ValidationError "Table of contents does not link to: $sectionId"
        }
    }

    $paperInfoMatch = [regex]::Match(
        $html,
        '<section\b[^>]*\bid\s*=\s*["'']paper-info["''][^>]*>(.*?)</section>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    if ($paperInfoMatch.Success) {
        $paperInfoHtml = $paperInfoMatch.Groups[1].Value
        $paperInfoText = Get-VisibleHtmlText -Fragment $paperInfoHtml
        $pageCountFields = [regex]::Matches(
            $paperInfoHtml,
            '<(?:td|dd|span)\b[^>]*\bdata-summary-field\s*=\s*["'']pdf-page-count["''][^>]*>(.*?)</(?:td|dd|span)>',
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
        )

        if ($pageCountFields.Count -ne 1) {
            Add-ValidationError "Paper-info must contain exactly one data-summary-field='pdf-page-count'; found $($pageCountFields.Count)."
        }
        else {
            $pageCountValue = Get-VisibleHtmlText -Fragment $pageCountFields[0].Groups[1].Value
            if ($pageCountValue -notmatch '^共\s*[1-9]\d*\s*頁$') {
                Add-ValidationError "Page-count field must contain only '共 N 頁'; found: $pageCountValue"
            }
        }

        $paperInfoOperationalPatterns = @(
            '(?:檔名|路徑|工具|處理|下載|頁碼對照)(?:說明|備註|紀錄|資訊|驗證)?[：:]',
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
                Add-ValidationError "Paper-info contains operational/QA prose that must stay out of summary.html (matched: $paperInfoOperationalPattern)"
            }
        }
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

    if ($html -match '(?i)\b(?:src|href)\s*=\s*["'']file://') {
        Add-ValidationError 'file:// URLs are not portable and are forbidden.'
    }
    if ($html -match '(?i)\b(?:src|href)\s*=\s*["''][A-Z]:[\\/]') {
        Add-ValidationError 'Absolute Windows paths are not portable and are forbidden.'
    }
    if ($html -match '(?i)\b(?:src|href)\s*=\s*["''][^"'']*(?:\.\.[\\/])') {
        Add-ValidationError 'Parent-directory references (../) are forbidden in summary resources.'
    }
    if ($html -match '(?i)<link\b[^>]*rel\s*=\s*["'']stylesheet["'']') {
        Add-ValidationError 'External or linked stylesheets are forbidden; CSS must remain embedded.'
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
    foreach ($figureMatch in $figureMatches) {
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

    $discussionSection = [regex]::Match(
        $html,
        '<section\b[^>]*\bid\s*=\s*["'']discussion-questions["''][^>]*>(.*?)</section>',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    if ($discussionSection.Success) {
        $questionCount = [regex]::Matches($discussionSection.Groups[1].Value, '<li\b', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase).Count
        if ($questionCount -lt 3 -or $questionCount -gt 5) {
            Add-ValidationWarning "Discussion section should normally contain 3-5 list items; found $questionCount."
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
