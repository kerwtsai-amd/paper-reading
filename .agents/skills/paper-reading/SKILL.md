---
name: paper-reading
description: Organize, download, deeply read, and summarize academic papers in this Paper Reading workspace as evidence-traceable Traditional Chinese HTML. Use for paper discovery, classification, PDF intake or reading, figure/table extraction, technical analysis, or summary.html work when Confluence delivery is not requested; use paper-reading-confluence for Confluence pages.
metadata:
  short-description: Evidence-traceable Traditional Chinese paper reading and HTML summaries
---

# Paper Reading

Organize each paper into a portable, verifiable research folder suitable for a research-group presentation. Explicit instructions in the current user request take precedence over this skill.

If the user requests creating, updating, or migrating a Confluence paper page, use the `paper-reading-confluence` skill in this project instead. The HTML template and `summary.html` contract below do not apply to that delivery mode.

## Fixed Project Contract

1. Treat the nearest ancestor directory containing both `AGENTS.md` and `html template/summary-template.html` as the Paper Reading root; in this project, it is the working directory. Do not create categories or paper files outside that root.
2. Before doing any substantive paper work, read [references/paper-reading-standard.md](references/paper-reading-standard.md).
3. Before generating HTML, read `html template/summary-template.html` from the root and create the paper's `summary.html` from a complete copy. Preserve the template version marker, CSS, MathJax, fixed section IDs, evidence labels, and responsive structure.
4. The project has no default Topic or Subtopic. Every paper must use exactly two category levels, with the formal paper title as the third-level folder. The only valid target structure is:

   ```text
   <Topic>/<Subtopic>/<Formal Paper Title>/
   ├── <Formal Paper Title>.pdf
   ├── summary.html
   └── assets/images/
   ```

   Any named category path in documentation illustrates the hierarchy only. It is not a default category and must not cause directories to be created from example text alone.

5. Inventory an existing paper folder before filling gaps. Do not create duplicate copies such as `(1)` or `copy`, and do not overwrite existing PDFs, summaries, or images unconditionally.

## Required Workflow

### 1. Identify and Classify

- Inspect the root's existing directories and candidate paper folders first.
- Start from the user's keywords, paper link, filename, or PDF and look up the title and abstract. Prefer first-party sources such as author pages, arXiv, DOI records, official conference or journal pages, and publisher pages.
- Cross-check at least the complete formal title, authors, venue or arXiv record, year, canonical landing page, and PDF URL. Do not name a paper from search-result snippets alone.
- Choose one Topic and one Subtopic for each paper based on its primary technical contribution rather than keywords alone. Reuse a category directly only when the user explicitly specifies it in the current request; otherwise decide after reviewing the title, abstract, and primary contribution. Create category directories under the root only when they do not exist, and mark the classification rationale with the `分析` label in the summary.
- In general, use the complete formal title for both the paper folder and PDF. Replace only the Windows-forbidden characters `< > : " / \\ | ? *`, remove trailing spaces or periods, and avoid reserved names such as `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, and `LPT1`–`LPT9`. If testing shows that the full path breaks a required tool, use a traceable safe PDF filename. Mention that exception briefly only in the final delivery report; do not put path length, character substitutions, tool errors, or naming rationale in `summary.html`.

### 2. Acquire and Validate the PDF

- Download the paper from a trustworthy canonical PDF source into its paper folder. Name it `<Formal Paper Title>.pdf` by default; use a safe short name only for a verified path or tool-compatibility problem described above.
- If a PDF with the same name already exists, confirm that it opens and is the intended paper. Reuse it when correct. If it is wrong or a different version, preserve the original and tell the user; never overwrite it silently.
- Verify that the file is not an HTML error page, has a valid PDF signature, and has a readable page count. When PDF page numbers differ from the paper's printed page numbers, record the mapping in internal working notes. These intake and QA results are not summary content.

### 3. Run the Iterative Research Loop

Use evidence coverage, not a fixed number of passes, as the stopping condition. Update the internal evidence ledger during every pass: `claim/data → source section → PDF page → printed paper page → Figure/Table/Equation`.

1. **Orientation pass:** Read the title, abstract, introduction, contributions, document structure, and conclusion to confirm the research question and classification.
2. **Method pass:** Closely read the background, problem definition, system architecture, algorithms, pseudocode, and equations. Trace every component, data flow, assumption, and complexity claim.
3. **Evidence pass:** Closely read the evaluation setup, baselines, workloads, hardware, software, metrics, main results, ablations, and sensitivity analyses. Verify captions, axes, units, and comparison conditions.
4. **Critical pass:** Separate author claims, facts directly supported by experiments, your own analysis, and speculation. Look for missing baselines, unfair comparisons, external-validity issues, deployment constraints, and untested assumptions.
5. **Completeness pass:** Recheck every important number, equation, figure, table, and summary conclusion. Continue targeted reading whenever a key statement lacks a source, any of the 16 sections is uncovered, or a core figure is missing. If the paper genuinely omits the information, write `論文未提供`.

Do not substitute the abstract for full-text reading, and do not invent information absent from the paper merely because it seems plausible from background knowledge.

### 4. Extract Required Figures and Tables

- Extract only the architecture diagrams, flowcharts, algorithm diagrams, result plots, or key tables required to explain the method and validate the conclusions. Prefer high-resolution PNG files under `assets/images/`.
- Use traceable filenames such as `fig-03-p07-overview.png` or `table-02-p10-results.png`. Crops must be clear and retain complete legends, axes, and required annotations while excluding full-page context and irrelevant margins.
- HTML may reference images only through forward-slash relative paths under `assets/images/...`. Give every image descriptive `alt` text and a self-authored reading guide. The source label in `figcaption` must contain only the original paper object identifier, such as `Figure 4`, `Table 2`, or `Algorithm 1`. Do not append `原論文`, punctuation, PDF or printed page numbers, `裁切自原論文`, `擷取自原論文`, or any other source or production note. Put figure and table page numbers in body evidence markers, the key-evidence index, or the internal evidence ledger, not in the caption.
- Preserve the template's caption markers: `data-caption-kind="paper-object"`, `data-caption-field="paper-object-label"`, and `data-caption-field="reading-guide"`. Follow the source label immediately with a non-empty, self-authored reading guide beginning with `導讀：`; do not insert a third visible text segment.

### 5. Write the Summary from the Canonical Template

- Copy the root's `html template/summary-template.html` to the target `summary.html`, then replace every `{{...}}` placeholder. HTML-escape titles, authors, and URLs.
- Write all reader-facing prose in `summary.html` in Traditional Chinese (`zh-Hant`). On first use, retain the English full name and abbreviation for technical terms. The instruction language being English does not change the required output language. Reorganize the content as a research report rather than translating paragraph by paragraph or copying long passages.
- Preserve all 16 fixed sections. When information is missing, write `論文未提供`; do not omit the section or fabricate content.
- Use `\( ... \)` and `\[ ... \]` for important equations, and explain each variable, unit or system meaning, relationship to the method, and source in the paper.
- Apply the template's four textual evidence labels to important statements: `作者主張`, `實驗事實`, `分析`, and `推測`. Do not communicate this distinction by color alone.
- Place a source marker next to every important number. Include at least the source section and PDF page, plus the Figure, Table, or Equation when applicable. If the PDF and printed page numbers differ, show both.

#### Reader-Visible Content Boundary (Required)

- `summary.html` is a paper research report, not a task log, file-creation record, validation report, or model working note. Retain only content that helps a reader understand, cite, evaluate, or discuss the paper.
- If total page count is shown, use exactly one `data-summary-field="pdf-page-count"` element whose complete visible value is only `共 N 頁`. When the PDF and printed page-number systems match, do not append process confirmations such as `PDF 頁碼與印刷頁碼一致`, `無 offset`, or `無頁碼偏移`. When the two systems differ, show the actual page numbers together only in the relevant source markers.
- Do not put any of the following in visible body text, tables, captions, callouts, or footers: search or cross-check procedures; PDF signature, version, byte count, or hash; download or parsing logs; Windows forbidden-character substitutions; folder or PDF naming rationale; absolute paths or path lengths; Poppler, OCR, browser, or other tool errors; crop or rendering commands; QA results; or negative confirmations that something was checked and no difference was found.
- Do not relabel the operational information above as `分析` or `推測` and leave it in the report. Keep it in internal working state. Mention an exception briefly in the final response only when it materially affects delivery; never put it in the HTML.
- A local PDF link may target the actual safe filename, but its visible text must use `開啟本地 PDF` or another neutral Traditional Chinese description without explaining the filename choice. A figure caption displays only `Figure/Table/Algorithm + the original identifier`. Show page numbers only in body source markers or the key-evidence index, and show both PDF and printed page numbers only when they differ.

### 6. Validate Before Delivery

- Run:

  ```powershell
  pwsh -NoProfile -File ".agents/skills/paper-reading/scripts/validate-summary.ps1" -PaperDirectory "<paper-folder>"
  ```

- Then perform visual QA in a browser at desktop and narrow-screen widths. Check table-of-contents navigation, long titles, horizontal scrolling for tables, images, MathJax, keyboard focus, and A4 print preview.
- Find and remove any reader-visible text that exposes intake work, filename handling, path workarounds, tool usage, or QA procedures. The page-count field must match `共 N 頁`.
- Fix validation failures and rerun the checks until every actionable issue passes. If an external resource is unavailable or the paper itself omits information, retain an explicit marker and report it at delivery.

## Completion Report

At delivery, list the folders and files created or updated, the classification and its technical rationale, the three summary sections most worth reading first, and anything that could not be extracted or confirmed or still requires user input.
