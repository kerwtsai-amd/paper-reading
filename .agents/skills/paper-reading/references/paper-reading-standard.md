# Paper Reading Content and Quality Standard

Read this standard whenever organizing, reading, or summarizing a paper. It supplements the execution contract in `SKILL.md`; explicit instructions in the current user request still take precedence.

## Researcher Role and Evidence Discipline

Work from the perspective of a senior researcher with expertise in deep learning, model systems, GPU performance optimization, and distributed systems. Adapt the technical context to the paper's field rather than assuming every paper concerns model inference. The result should reach the depth of a graduate-level paper-reading presentation to fellow researchers, enabling someone who has not read the paper to understand the problem, its importance, limitations of prior approaches, the proposed mechanism, useful intuition, experimental evidence, limitations, and possible extensions.

Maintain an evidence ledger before writing the summary. Every important number, comparison, limitation, equation, and design-causality claim must trace back to the source section, PDF page, and any applicable Figure, Table, Equation, or Algorithm. Strictly distinguish the following reader-visible Traditional Chinese labels:

- **`作者主張` (author claim):** An explanation or conclusion explicitly stated by the authors, which is not necessarily fully proven.
- **`實驗事實` (experimental fact):** An observation directly supported by the paper's figures, tables, data, or experimental design.
- **`分析` (analysis):** Commentary, synthesis, or reasonable interpretation based on evidence in the paper.
- **`推測` (speculation):** A mechanism, risk, or extension hypothesis not directly validated by the paper.

Do not fabricate information or present analysis or speculation as an author-established fact. When information is missing, write `論文未提供` and explain how that absence affects verifiability.

## Reader-First Exposition

Before drafting, read and apply [reader-first-exposition.md](reader-first-exposition.md). The report must teach only the minimum prerequisites needed by its target reader, then carry one causal thread from system context and observed failure through root cause, prior-art gap, derived requirements, end-to-end method, evidence, and limitations. Every prerequisite must be used later; every major method component must answer a named problem or requirement; and every principal empirical conclusion must map to the experiment that tests it.

Keep provenance explicit when adding context beyond the paper. Cite canonical external sources for necessary prerequisites, identify them as external background, and label the summarizer's connection to the paper as `分析`. External material may improve explanation but must never fill a missing experiment, ablation, or deployment detail in the paper.

## Directory and Filename Standard

```text
<Paper Reading root>/
├── html template/
│   └── summary-template.html
└── <Topic>/
    └── <Subtopic>/
        └── <Formal Paper Title>/
            ├── <Formal Paper Title>.pdf
            ├── summary.html
            └── assets/
                └── images/
```

- In general, use the verified complete formal title for both the PDF and folder, applying only the character substitutions required for Windows safety. If testing shows that the full PDF path breaks a required tool, use a traceable safe filename. Mention a naming exception briefly only in the delivery report; never put it in the summary body.
- The project has no default Topic or Subtopic. Determine the two category levels for each paper from its primary technical contribution. Reuse a category only when the user explicitly specifies it in the current request. Named category examples in documentation illustrate hierarchy only; they are not defaults for the project or current batch and must not trigger directory creation.
- When a candidate folder already exists, compare the formal title, PDF metadata, and content before filling any gaps. Do not create a duplicate copy.
- Do not move an existing paper to a new category unless the user explicitly requests it. If the classification assessment changes, explain the evidence and recommendation first.

## Boundary Between Reader Content and Operational Records

`summary.html` presents only the paper's bibliographic metadata, research content, evidence, and analysis. Search, download, file organization, PDF validation, page-number mapping, tool workarounds, and validation results are internal operational records, not paper-summary content.

- **Academic metadata allowed in the report:** Formal title, authors, venue, journal, or arXiv record, year and version, DOI or canonical URL, classification and its rationale, and the plain total page count.
- **Evidence locations allowed in the report:** Source section, PDF page, and Figure, Table, or Equation. Show PDF and printed page numbers together in an individual source marker only when they differ.
- **Information restricted to internal state or the final delivery report:** How metadata was cross-checked; PDF signature, version, byte count, or hash; download or parsing method; operating-system character substitutions; filename rationale; absolute path or path length; Poppler, OCR, browser, or conversion errors; cropping and rendering steps; and QA results.
- If total page count is shown, include exactly one `data-summary-field="pdf-page-count"` element whose entire visible value is exactly `共 N 頁`. When the page-number systems match, do not write confirmations such as `一致`, `無 offset`, or `無頁碼偏移`. When they differ, write `PDF p.N（論文標示 p.M）` in the relevant source marker without additional process explanation.
- Keep the evidence ledger, page-number mapping, hashes, and tool diagnostics in working state only. Do not disguise production details with the `分析` or `推測` labels. If an exception affects the user's access to the result, mention it concisely in the completion report only.

## Required `summary.html` Editorial Roles

The HTML template fixes semantic roles and their order, not generic reader-facing chapter names. Every role below must occur exactly once as `data-section-role`; each `<h2>` must be a paper-specific question or claim that tells the reader what that chapter resolves.

1. **Header `thesis`:** Compact bibliographic context plus one non-repeated lede containing the problem, mechanism, strongest evidence, and principal boundary.
2. **`prerequisites`:** Only the minimum domain or systems concepts used later. Prefer a small example, data-flow sketch, or comparison table when it lowers cognitive load. Explicitly reconnect every concept to a later design choice or result.
3. **`problem`:** Observable symptom → root mechanism → why the nearest approach is insufficient → derived requirements or success criteria. Integrate the closest related-work comparison here rather than postponing it to a detached survey chapter.
4. **`insight`:** A concrete analogy, miniature calculation, or one packet/request/token/tensor/cache-block walkthrough that makes the central mechanism intuitive. Map the objects to formal notation and state where the simplification stops being exact.
5. **`method`:** The complete end-to-end flow followed by component mechanics in execution order. Tie every component to a named requirement. Put equations, algorithms, and method figures at their first explanatory use; there is no separate formula warehouse or figure gallery.
6. **`evidence`:** Claim-test units that keep setup, controls, metric, observation, supported conclusion, and caveat together. Include main results, ablations, sensitivity analysis, and fairness checks beside the result figure or table they interpret.
7. **`critique`:** Strengths, assumptions, applicable scope, scalability, deployment constraints, author-stated limitations, external-validity risks, and conclusions the evidence cannot support.
8. **`extensions`:** Reusable design ideas, independent analysis, concrete follow-up experiments, broader significance, and three to five substantive research-group questions. Mark analysis and speculation explicitly.
9. **`reference`:** Formal metadata, neutral local-PDF link context where needed, exactly one plain page-count field `共 N 頁`, glossary, and key-evidence index. Keep this appendix lower in visual prominence than the article.

The article must read as continuous exposition, not a collection of form fields. Do not repeat the same summary in the header, first chapter, and conclusion. Do not use generic headings such as `背景與動機`, `核心方法`, `公式與理論`, `圖片與圖表導讀`, or `實驗結果` as the universal top-level scheme.

## Method and Experiment Reading Checks

### Method

- Is the research problem and objective precise? Start from the paper's own success criteria. For systems optimization, distinguish latency, throughput, TTFT, memory, energy, cost, and multi-objective tradeoffs as applicable.
- At which layer or component of the studied system does the method operate? For model inference, further distinguish prefill, decode, scheduling, memory, communication, kernels, model architecture, and cross-layer coordination.
- How does every state, tensor, cache, worker, and communication step change during execution?
- Which workload, hardware topology, model structure, precision, or sequence-length assumptions does the design depend on?
- Do the equations genuinely derive the design, or do they provide only approximate intuition? Are compute and communication costs complete?

### Experiments

- Record hardware, software, versions, and key settings that can affect results. For accelerator or model-systems research, also record GPU model and count, CPU, memory, interconnect, driver, CUDA or ROCm version, framework, and precision. Explicitly mark anything the paper does not provide.
- Record the studied system, datasets, and workloads. For model inference, also record models, parameter counts, context length, input and output length distributions, batch size or concurrency, and request-arrival pattern.
- Do the baselines use the same hardware, precision, model quality, batch size or concurrency, and level of software optimization? If not, state the comparison limitation.
- Distinguish absolute values, relative gains, means, percentiles, and best cases. Do not combine maximum gains from different conditions into one representative number.
- Check error bars, repetition count, warmup, statistical method, cost model, and measurement boundary. Do not fill in details the paper omits.
- Are figure axes truncated, logarithmic, mixed-unit, or restricted to favorable ranges?
- Do ablations, profiles, or microbenchmarks support the authors' causal explanations?

## Figure and Table Standard

- Crop only the content required to understand the architecture, flow, algorithm, key results, and key ablations.
- Prefer PNG. Keep text, lines, axes, legends, and necessary footnotes legible, and inspect every crop after creating it.
- HTML image paths must use `assets/images/<filename>`. Do not use absolute paths, `file://`, remote hotlinks, or `../` paths that escape the paper folder.
- Each `figcaption` must contain one direct, independent source label such as `Figure 4`, `Table 2`, or `Algorithm 1`, plus a self-authored reading guide beginning with `導讀：`. Do not append `原論文`, punctuation, PDF or printed page numbers, section references, image-source notes, or production status to the source label. The full caption must not contain redundant production phrases such as `裁切自原論文`, `擷取自原論文`, or `取自原論文`. Put location pages in body source chips, the key-evidence index, or the internal evidence ledger.
- Preserve the template markers `data-caption-kind="paper-object"`, `data-caption-field="paper-object-label"`, and `data-caption-field="reading-guide"`. Each field must appear exactly once, and the caption must not contain additional visible text.
- Prefer restructuring data into an HTML `<table>` when it can be represented structurally. Use an image only when the layout, heatmap, graphical form, or complex header is itself important. Do not infer undisclosed absolute values from percentages.

## HTML and Writing Quality

- Start from a complete copy of the canonical template. Preserve its CSS, MathJax, table of contents, semantic role markers, evidence labels, and responsive structure.
- Write all reader-facing prose in Traditional Chinese (`zh-Hant`). On first use, format technical terms as `中文（English, ABBR）`. Avoid vague descriptions, paragraph-by-paragraph translation, and long verbatim excerpts.
- Use `\( ... \)` for inline equations and `\[ ... \]` for display equations. Put code and pseudocode in `<pre><code>` so MathJax does not process them.
- Place a source chip next to every key result. Prefer the format `§4.2 · PDF p.7（論文標示 p.5）· Fig. 3`.
- Include a table of contents, correct heading hierarchy, source index, image descriptions, tables, code styling, clear focus states, desktop and narrow-screen layouts, and print styles.
- Use a single editorial reading column. Do not add a permanent sidebar TOC, dashboard properties grid, detached figure gallery, or card wall. Prefer compact inline evidence markers; normally keep large statement callouts to six or fewer.
- Use Open Sans for Latin glyphs and Noto Sans TC for CJK glyphs throughout the page. Preserve the canonical `"Open Sans", "Noto Sans TC", sans-serif` value for all three template variables `--sans`, `--serif`, and `--mono`; the repeated value is intentional, including for headings and code.
- The only permitted font resources are preconnects to `https://fonts.googleapis.com` and `https://fonts.gstatic.com` (the latter with `crossorigin`) plus the exact Google Fonts stylesheet `https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700;800&family=Open+Sans:wght@400;500;600;700;800&display=swap`. A pinned-version MathJax CDN is also allowed. Do not add another stylesheet, font, preconnect, tracker, framework, or complex build dependency.
- Do not leave `{{PLACEHOLDER}}`, sample data, fabricated citations, or template instructions in the finished output.
- After writing, inspect all reader-visible content and remove filename explanations, file-validation details, page-offset status, path, tool, download, or cropping procedures, and other operational logs.
- Inspect the explanatory spine: prerequisites must be reused, the problem must derive the requirements, components must answer those requirements, and conclusions must point to the experiments that test them.

## Research-Loop Stopping Conditions

End full-text research only when all of the following are true:

- Formal metadata and classification have been verified.
- The central problem, method flow, important equations, experimental design, main results, ablations or missing ablations, limitations, and related work all have sources.
- Every important number is traceable, and workloads or conditions have not been conflated as directly comparable.
- Figures required to understand the core method and main results have been extracted and inspected.
- Every required semantic role has meaningful content or explicitly states `論文未提供`.
- `作者主張`, `實驗事實`, `分析`, and `推測` content is clearly separated.
- Every unresolved issue is recorded as a limitation or in the delivery report rather than filled with assumed knowledge.
- Every prerequisite introduced for the reader is used later, every major component is tied to a problem or requirement, and every principal empirical conclusion has a claim-test mapping.

## Manual Acceptance Before Delivery

- The PDF and `summary.html` both open successfully.
- The table of contents and internal anchors work, there is exactly one `h1`, and sections appear in the correct order.
- The first two screenfuls communicate the problem, core insight, and strongest evidence without repeating the same summary in multiple boxes.
- MathJax renders without obvious parse errors.
- Latin and CJK samples resolve respectively to Open Sans and Noto Sans TC, and no unexpected stylesheet or font connection is requested.
- Images exist, are non-empty, use correct paths, remain legible, and have complete caption sources.
- Key data and conclusions are traceable.
- There is no page-level horizontal overflow at 1440 px, 1024 px, or 390 px; individual tables can scroll horizontally.
- A4 print preview does not crop figures or tables or leave orphaned headings.
- The summary covers the method, experiments, limitations, and independent analysis without omitting the most important contribution.
