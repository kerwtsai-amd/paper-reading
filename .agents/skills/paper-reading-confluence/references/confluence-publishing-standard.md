# Confluence Summary and Publishing Standard for Paper Reading

This standard defines only Confluence delivery and medium-specific differences. Inherit research depth, evidence discipline, classification, PDF intake, figure extraction, and stopping conditions from [`paper-reading-standard.md`](../../paper-reading/references/paper-reading-standard.md), and inherit the shared narrative method from [`reader-first-exposition.md`](../../paper-reading/references/reader-first-exposition.md). The user's explicit instructions for the current task still take highest priority. All reader-facing paper-summary content must be written in Traditional Chinese; these operating instructions are in English.

## Deliverable and Source Draft

- The official deliverable is one Confluence page. Local `confluence-summary.md` is that page's reviewable source draft.
- Generate the complete page body from `confluence-summary.md` every time it is rebuilt so remote content cannot diverge from the local source.
- Copy `confluence-summary.md` from [`confluence-summary-template.md`](../assets/confluence-summary-template.md). Do not paste complete HTML directly from an existing `summary.html`. Existing HTML may serve as a content source, but CSS, JavaScript, MathJax, DOM markers, and operational records must not enter Confluence.
- Generate publishing storage XHTML with `prepare_confluence.py`. Do not edit generated XHTML manually; edit the Markdown source and rebuild it.
- For a Prepare-only request, the durable outputs are the local source draft and attachments; generated storage XHTML is a temporary build artifact reproducible from that source. Make no Atlassian connection at all. Resolve a space, parent, or page and perform remote writes only when the user explicitly requests Publish.
- When migrating an existing summary, reverify the formal paper metadata from first-party sources and use the full formal title as the Confluence page title. Use the current two-level physical Topic/Subtopic path as the delivery classification. If legacy summary text conflicts with the physical path, report the conflict and reassess it, but do not move the existing folder without user approval.

## Fixed Sections

The Confluence page title is the only page title. Its body must use these 16 H2 headings, in this order. Keep the heading text itself in Traditional Chinese:

1. **論文基本資料**: formal title, authors, venue/journal/arXiv record, year, version, canonical link, Topic/Subtopic, classification rationale, PDF attachment, and the single `共 N 頁`.
2. **一句話總結**: one to three sentences stating the central problem, method, and result; every number must be traceable.
3. **Executive Summary**: the compact causal order problem, root cause or gap, key insight, method, principal evidence, limitations, and takeaways.
4. **背景與動機**: only the domain prerequisites used later, workflow roles, existing bottlenecks, and author observations, ending with a bridge to the exact problem.
5. **問題定義**: observable symptom, root mechanism, why the nearest existing approach is insufficient, derived requirements, objective, inputs and outputs, assumptions, constraints, terminology, and notation.
6. **核心方法**: an end-to-end walkthrough followed by architecture, algorithms, data flow, component responsibilities, state changes, interactions, and design intuition, with every design choice tied to a requirement.
7. **公式與理論**: necessary formulas, variables, units or system meaning, assumptions, purpose, qualitative sensitivity, execution role, and sources.
8. **圖片與圖表導讀**: necessary attached images placed with the concepts or claims they resolve, original object numbers, original reading guides that say what to inspect and why it matters, and source locations.
9. **實驗設計**: claim-aligned hardware, software, models, datasets, baselines, workloads, metrics, controls, and fairness.
10. **實驗結果**: claim-test pairs containing the setup, metric, observation, supported conclusion, and caveat, plus what the figures support and do not support.
11. **Ablation 與敏感度分析**: each design contribution, parameter sensitivity, and interactions; explicitly note when unavailable.
12. **優點、限制與風險**: system assumptions, scope of applicability, generalization, deployment constraints, and external validity.
13. **與相關工作的比較**: the closest alternatives compared by mechanism, assumptions, scenarios, deployment costs, and failure modes, not merely a list of names.
14. **個人分析與可延伸方向**: reusable design ideas, conclusions still requiring verification, and research or engineering extensions.
15. **組會討論問題**: three to five technical questions that invite evidence-based or design discussion.
16. **術語表與重點索引**: abbreviations, definitions, and section/page/object indexes for important conclusions.

When information is missing, preserve the section and write `論文未提供`. Do not omit the section or fabricate content.

## Mandatory Source-draft Format

- The top-of-page `優先閱讀` field must list exactly three valid section numbers.
- The body may contain only the fixed 16 H2 headings—no H1 and no H3–H6. Use bold paragraphs or lists for subtopics so claims cannot hide in unvalidated subheadings.
- `最後更新` must be a valid `YYYY-MM-DD` no later than today; `年份` must be a four-digit Gregorian year.
- `分類` must exactly equal the physical folder's `<Topic> / <Subtopic>`. Mentioning the correct string only in the classification rationale is insufficient.
- By default, `正式標題` must identify the same title as the Windows-safe folder title. Use `--allow-legacy-folder-title` only for an existing legacy folder that has been manually verified, and never rewrite formal metadata to justify that exception.
- To display a literal `|` inside a Markdown table cell, write `\|` in the source draft. The renderer restores it in storage XHTML. An unescaped `|` is a field delimiter; do not rewrite the formal title to evade this syntax.
- `CLASSIFICATION_SOURCE` for `分類理由` must include both the source-text location and PDF page, for example `Abstract · PDF p.1`.
- In Sections 02–14, excluding image blocks, every claim in a prose sentence, list item, or data row must include an evidence label in the same sentence. The only exceptions are a source-only line and a standalone `論文未提供`; never join that phrase to other unlabeled claims. Section 15 contains discussion questions and is exempt. In Section 16, every glossary term and key-index entry must use an evidence label in the same sentence, and the same list item or paragraph must contain both a source section and `PDF p.N`. A source attached to another item cannot satisfy coverage for the whole section. A term may be written as `` **[作者主張]** `TERM`：指……（來源：§… · PDF p.N）``. A “definition-only” sentence without evidence or a source is not exempt; this prevents result claims from being hidden inside definitions.
- In Section 04, add external background only when the target reader needs it to understand a later design or result. Label the connection as `分析`, identify the canonical external source explicitly, and also cite the paper section and `PDF p.N` that make the prerequisite relevant. Do not imply that an external explanation or number came from the paper, and do not use external material to fill missing paper evidence.
- Before conversion, apply the reader-first review gates: every prerequisite is reused, every major component answers a named problem or requirement, and every principal empirical conclusion maps to a claim-test pair with conditions and a caveat.
- Do not hand-write HTML or storage tags in the source draft. Discussing a tag literal inside inline code does not count as hand-written markup. Ordinary Markdown links may target only `https://` URLs or same-page anchors; percent-encode parentheses in destinations. PDFs and images must use attachment blocks. Reader content must not contain absolute Windows, UNC, or POSIX local paths or `file://` URLs. Interface paths such as `/api/...` inside code are not treated as local filesystem paths.

## Native Confluence Rendering Mapping

| HTML summary semantics | Confluence rendering |
| --- | --- |
| Page `<h1>` | Confluence page title; do not repeat H1 in the body |
| Hand-built table of contents | `toc` storage macro, inserted automatically by the converter |
| Hero/properties | Native Markdown table or paragraph |
| Evidence chip | Visible text `**[作者主張]**`, `**[實驗事實]**`, `**[分析]**`, or `**[推測]**` |
| Source chip | `（來源：§4.2 · PDF p.7 · Figure 3）` immediately adjacent to the claim |
| HTML table | Markdown pipe table converted to a Confluence table |
| `<pre><code>` / MathJax | Inline code or fenced code block; explain the formula separately in prose |
| `<img>` / local PDF link | Page attachment reference; absolute local paths and `file://` are prohibited |
| CSS / JS / responsive / print | Do not migrate; use native Confluence layout and perform visual QA on the live page |

The four evidence labels carry semantic information. Do not omit them or replace them with a color-only status macro. Every claim containing an important number must carry an evidence label in the same sentence. Its source must include both a nonempty source section or appendix location and a positive-integer `PDF p.N`. Include the printed page number only when it differs from the PDF page, for example `PDF p.7（論文標示 p.5）`.

## PDF attachment block

Use one fenced JSON block in Section 1. `file` may contain only the PDF basename at the paper-folder root. `label` is neutral reader-visible link text. Do not include an absolute path.

````markdown
```paper-attachment
{"file":"Formal Paper Title.pdf","label":"開啟論文 PDF"}
```
````

An optional `description` is allowed, but it must not record download, validation, or naming operations. Each summary must contain exactly one PDF attachment block.

## Image attachment block

Because the current Atlassian CLI does not convert ordinary Markdown image syntax to a Confluence attachment image, use one fenced JSON block for each image:

````markdown
```paper-image
{
  "file": "assets/images/fig-03-p07-overview.png",
  "label": "Figure 3",
  "evidence": "分析",
  "alt": "系統架構與請求資料流",
  "guide": "先沿實線追蹤正常路徑，再比較虛線表示的 fallback；兩條路徑共享相同的快取索引。",
  "source": "§3.2 · PDF p.7 · Figure 3",
  "width": 1000
}
```
````

Rules:

- `file` must be a relative PNG, JPG, or JPEG path under `assets/images/`. The file must exist, be nonempty, and have a valid signature. Do not use `..`, backslashes, URLs, or absolute paths.
- `label` may contain only the original object number in the form `Figure N`, `Table N`, or `Algorithm N`. A panel may be written as `Figure 3(a)` or `Figure 3 (a)`. Do not add `原論文`, punctuation, a page number, or extraction notes.
- `evidence` must be one of `作者主張`, `實驗事實`, `分析`, or `推測` to identify the evidence type of the original reading guide; the renderer displays it as a bold label.
- `alt` describes the image itself. `guide` is a nonempty, original reading guide. Do not add the `導讀：` prefix yourself; the converter adds it.
- `source` must include at least the source section, `PDF p.N`, and original object number. The page number is an evidence location and must not be mixed into `label`.
- `width` is optional; when supplied, it must be an integer from 200 through 1600. Do not use width to hide inadequate resolution.
- Within one page, a given attachment filename may represent only one image. Updating the image file creates a new attachment version.
- The converter treats PNG/JPEG files under `assets/images/` as a manifest requiring review and, by default, requires each one to be referenced by a `paper-image` block. If the folder contains retained material confirmed not to belong on this page, use `--allow-unreferenced-images` only after manual review. Never delete an existing file casually just to make validation pass.
- If the paper has figures but the summary does not require an extraction, omit the block and write `**[分析]** 本摘要未擷取圖表：<理由>（來源：<原文章節> · PDF p.N）` instead. Write `論文未提供` only when the source paper truly lacks the corresponding information.

## Equations, Tables, and Quotations

- Present equations as copyable LaTeX or clear plain text. Put inline equations in backticks and multiline equations in fenced code blocks. The current renderer provides no equation directive, so never hand-write, inject, or later convert them into a particular formula macro.
- After every important equation, explain its variables, units or system meaning, assumptions, relationship to the method, and source in the paper. Do not present an equation only as an image.
- Prefer restructuring data that can be represented structurally as a Markdown table. Use an image attachment only when a heatmap, complex header, or visual arrangement is itself important.
- Do not derive undisclosed absolute values from percentages, and do not combine best cases from different workloads into one representative number.
- Use only short excerpts and faithful paraphrases, retain the canonical link, and do not copy long passages from the paper.

## Page and Attachment Safety in Publish Mode

1. Run `atl check` only after entering Publish mode. Never request or store a token in the conversation.
2. Require an explicit space key. An unspecified parent page may default to the space root, but disclose that destination clearly before writing. Do not guess from similarly named spaces or pages.
3. Before creation, check for duplicates by space plus exact title. If the search returns multiple candidates, stop and ask the user to choose.
4. Dry-run any target inferred from search. Before replacing a page body, read the current page and obtain the user's explicit confirmation.
5. Create a new page once with the complete final storage body, then upload its referenced PDF and images. If an attachment fails, preserve the created page rather than deleting it automatically; after correction, retry only the missing attachment.
6. After confirming an existing page, rebuild its complete body with `conf-update <pageId> --format storage --body-file <storage-file>`. Do not publish a complete summary with append, which would create a second set of 16 sections. Reuse unchanged existing attachments and upload only files that are missing or genuinely updated. Append is appropriate only for an appendix or supplement explicitly requested by the user.
7. If an attachment exceeds the site limit, permissions are insufficient, or an API operation partially fails, report the exact remaining work and do not claim complete delivery.
8. If a create response is uncertain or the connection is interrupted, query by space plus exact title before retrying. If an attachment response is uncertain, query by pageId plus filename and version to avoid creating an unintended new version.
9. After successful Publish read-back, atomically write `.confluence-page.json` in the paper folder. Store the site, spaceKey, pageId, title, parentId, page version, and each attachment's filename, local bytes and SHA-256, plus remote id and version. This is an operational sidecar and must not enter the page body. Use it first on later runs to resolve a custom title and remote identity; stop for confirmation if identity has drifted.
10. A matching filename and size do not prove that attachments are identical. Skip an upload only when the sidecar's local hash still matches the current file and the remote id and version still match the sidecar. Create a new attachment version when the local hash changes. If the sidecar is missing or the remote version has drifted, obtain a retransmission decision rather than blindly adding a version.
11. If the source draft removes or renames an attachment, preserve the old remote attachment as historical stale content by default. The current body no longer references it, and the sidecar records only current references. Never delete it automatically merely to make the sets equal. Delete an attachment only when the user explicitly requests cleanup, after listing the exact filename and attachment id and rechecking the page references.

Use the following minimum sidecar schema and never add credentials. `parentId` is `null` when no parent exists. The attachment array must contain exactly the PDF and images referenced by the current page and must exclude unreferenced historical stale attachments:

```json
{
  "schemaVersion": 1,
  "site": "https://example.atlassian.net",
  "spaceKey": "RESEARCH",
  "pageId": "123456",
  "title": "Formal Paper Title",
  "parentId": null,
  "version": 1,
  "attachments": [
    {
      "filename": "paper.pdf",
      "bytes": 123456,
      "sha256": "64 lowercase hex characters",
      "remoteId": "att123",
      "remoteVersion": 1
    }
  ]
}
```

## Post-publish Verification

- `conf-page <id> --format storage`: Confirm that the page is current; title, space, parent, and version are correct; the TOC macro, all 16 sections, and every `ri:attachment` reference are present; and no placeholder or absolute local path remains.
- `conf-page <id>`: Confirm that the Markdown read-back is readable, headings remain in order, tables and code are intact, and important numbers still have sources.
- `/wiki/api/v2/pages/<id>/attachments?limit=250`: Verify the filename, media type, file size, version, and pageId of every currently referenced PDF and image. `raw` does not paginate automatically for its caller. While the response contains `_links.next` or a cursor, follow it and accumulate results until no next page remains. Every current reference must have exactly one match in the complete remote list and agree with the sidecar. Additional unreferenced historical attachments may be reported as stale; do not delete them automatically or fail this read-back because of them.
- Browser: Verify the TOC, images, captions, tables, long title, and narrow viewport. Images must not appear only as broken placeholders, and captions must not contain cropping or upload logs.
- After local conversion: Parse the storage XHTML and recheck that it contains exactly one TOC, no H1, all 16 H2 headings in order, every table, formulas or code blocks, evidence and PDF source markers, the canonical link, image attributes and captions, and each attachment reference exactly once. The artifact carries the `paper-reading-confluence` generator marker. An existing `.storage.xhtml` file is not overwritten by default, and `--overwrite-output` accepts only an old artifact containing that marker.
- If UI access or permissions prevent a check, list it as incomplete verification. Never describe an unchecked item as passed.

## Reader-visible Content Boundary

Keep only information needed to understand, cite, evaluate, or discuss the paper. Do not include search or download procedures, PDF signatures, byte counts or hashes, operational page-number mapping details, Windows character substitutions, filename rationale, absolute paths, CLI or API requests, authentication state, rendering or cropping commands, QA logs, or negative confirmations that a check found no difference.

Do not relabel this operational information as `分析` or `推測` and leave it on the page. If an exception materially affects delivery, mention it briefly only in the final response.
