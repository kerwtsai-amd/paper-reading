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

## Required `summary.html` Sections

Every section below must be present in this order. Preserve each exact Traditional Chinese section title shown in code formatting:

1. **`論文基本資料` (Paper Metadata):** Formal title, authors, conference, journal, or arXiv record, year, canonical link, classification, classification rationale, a neutrally worded local PDF link, and the plain total page count `共 N 頁`. Do not include file or tool-validation information.
2. **`一句話總結` (One-Sentence Summary):** State the central problem, method, and result in one to three sentences. Do not include promotional numbers without sources.
3. **`Executive Summary`:** Quickly summarize the research problem, key insight, method, primary evidence, limitations, and takeaways.
4. **`背景與動機` (Background and Motivation):** Explain the domain and systems context required to understand the paper, the topic's role in the broader workflow, existing bottlenecks, and the authors' observations. Explain prefill's role in model inference only when the paper actually concerns prefill.
5. **`問題定義` (Problem Definition):** Cover objectives, inputs and outputs, assumptions, constraints, important terminology, and notation. Distinguish definitions stated by the authors from formalization introduced by the summarizer.
6. **`核心方法` (Core Method):** Explain the architecture, algorithm, execution flow, component responsibilities, interactions, and design intuition step by step. When restructuring pseudocode, preserve its semantics without copying long passages.
7. **`公式與理論` (Equations and Theory):** Include only equations needed to understand or validate the method. Explain each variable, unit or system meaning, assumption, and purpose.
8. **`圖片與圖表導讀` (Figure and Table Reading Guide):** Include necessary crops. Each caption's source label must show only `Figure/Table/Algorithm + the original identifier`, followed by a self-authored reading guide and reading focus. Put page numbers in body source markers or the key-evidence index, not in captions.
9. **`實驗設計` (Experimental Design):** Hardware, software, models, datasets, baselines, workloads, metrics, variable control, and fairness.
10. **`實驗結果` (Experimental Results):** Organize metrics according to the paper's actual evaluation goals. For model-inference work, these may include latency, throughput, Time to First Token (TTFT), memory, and cost. Explain what the figures and tables can and cannot support.
11. **`Ablation 與敏感度分析` (Ablation and Sensitivity Analysis):** Contribution of each design choice, parameter sensitivity, and interactions. Explicitly note when the paper does not provide these results.
12. **`優點、限制與風險` (Strengths, Limitations, and Risks):** Strengths, system assumptions, applicable scope, scalability, generalizability, deployment constraints, author-stated limitations, and additional analysis.
13. **`與相關工作的比較` (Comparison with Related Work):** Compare technical approaches, applicable scenarios, costs, and tradeoffs rather than merely listing names.
14. **`個人分析與可延伸方向` (Independent Analysis and Extensions):** Reusable design ideas, conclusions still requiring validation, research or engineering extensions, and broader significance. Mark content as `分析` or `推測` as appropriate.
15. **`組會討論問題` (Research-Group Discussion Questions):** Provide three to five technically substantive questions that prompt discussion of evidence or design.
16. **`術語表與重點索引` (Glossary and Key-Evidence Index):** Abbreviations, terminology, definitions, and the pages, sections, Figures, Tables, or Equations supporting key conclusions.

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

- Start from a complete copy of the canonical template. Do not arbitrarily remove CSS, MathJax, the table of contents, fixed section IDs, or evidence-callout classes.
- Write all reader-facing prose in Traditional Chinese (`zh-Hant`). On first use, format technical terms as `中文（English, ABBR）`. Avoid vague descriptions, paragraph-by-paragraph translation, and long verbatim excerpts.
- Use `\( ... \)` for inline equations and `\[ ... \]` for display equations. Put code and pseudocode in `<pre><code>` so MathJax does not process them.
- Place a source chip next to every key result. Prefer the format `§4.2 · PDF p.7（論文標示 p.5）· Fig. 3`.
- Include a table of contents, correct heading hierarchy, source index, image descriptions, tables, code styling, clear focus states, desktop and narrow-screen layouts, and print styles.
- A pinned-version MathJax CDN is allowed. Do not add external fonts, trackers, frameworks, or complex build dependencies.
- Do not leave `{{PLACEHOLDER}}`, sample data, fabricated citations, or template instructions in the finished output.
- After writing, inspect all reader-visible content and remove filename explanations, file-validation details, page-offset status, path, tool, download, or cropping procedures, and other operational logs.

## Research-Loop Stopping Conditions

End full-text research only when all of the following are true:

- Formal metadata and classification have been verified.
- The central problem, method flow, important equations, experimental design, main results, ablations or missing ablations, limitations, and related work all have sources.
- Every important number is traceable, and workloads or conditions have not been conflated as directly comparable.
- Figures required to understand the core method and main results have been extracted and inspected.
- All 16 sections have sufficient content or explicitly state `論文未提供`.
- `作者主張`, `實驗事實`, `分析`, and `推測` content is clearly separated.
- Every unresolved issue is recorded as a limitation or in the delivery report rather than filled with assumed knowledge.

## Manual Acceptance Before Delivery

- The PDF and `summary.html` both open successfully.
- The table of contents and internal anchors work, there is exactly one `h1`, and sections appear in the correct order.
- MathJax renders without obvious parse errors.
- Images exist, are non-empty, use correct paths, remain legible, and have complete caption sources.
- Key data and conclusions are traceable.
- There is no page-level horizontal overflow at 1440 px, 1024 px, or 390 px; individual tables can scroll horizontally.
- A4 print preview does not crop figures or tables or leave orphaned headings.
- The summary covers the method, experiments, limitations, and independent analysis without omitting the most important contribution.
