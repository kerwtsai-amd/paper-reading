---
name: paper-reading-confluence
description: Organize, deeply read, and publish academic papers as reader-first, evidence-traceable Traditional Chinese Confluence pages in this Paper Reading workspace. Use when a paper task requests Confluence delivery, migration from summary.html to Confluence, or creation or maintenance of a Confluence paper-reading page; use paper-reading alone for HTML-only delivery.
metadata:
  short-description: Reader-first, evidence-traceable Traditional Chinese paper reading and Confluence publishing
---

# Paper Reading for Confluence

Organize each paper into a verifiable research folder and deliver a Traditional Chinese Confluence summary suitable for a research group meeting. Keep the existing `paper-reading` Skill; apply this Skill's output contract only when the user requests Confluence delivery.

## Fixed Project Contract

1. Treat the nearest ancestor directory that contains `AGENTS.md`, `.agents/skills/paper-reading/`, and this Skill as the Paper Reading root. Do not create classification or paper files outside that root.
2. Before beginning any substantive paper work, read:
   - [Shared paper-reading content standard](../paper-reading/references/paper-reading-standard.md) for classification, full-text reading, evidence discipline, figure extraction, and research depth.
   - [Shared reader-first exposition guide](../paper-reading/references/reader-first-exposition.md) for prerequisite selection, causal organization, end-to-end method explanation, and claim-test evaluation.
   - [Confluence summary and publishing standard](references/confluence-publishing-standard.md) for this Skill's output format, attachments, and remote-safety rules.
   Apply the reader-first guide's content and narrative rules in full. From the shared standard, inherit only: “Researcher Role and Evidence Discipline”; “Reader-First Exposition”; the classification and formal-title rules from “Directory and Filename Standard”; “Boundary Between Reader Content and Operational Records”; “Method and Experiment Reading Checks”; the figure-selection and extraction-fidelity rules from “Figure and Table Standard”; and “Research-Loop Stopping Conditions.” Its fixed `summary.html` sections, HTML/CSS/MathJax rules, HTML image embedding and caption format, HTML validator, and browser acceptance checks do not apply. Use this Skill's fixed sections, attachment, storage, and Confluence read-back rules instead. If the standards conflict, this Skill's Confluence rendering and publishing rules take precedence.
3. Continue to place each paper at `<Topic>/<Subtopic>/<Formal Paper Title>/`. In Confluence mode, use this local structure:

   ```text
   <Topic>/<Subtopic>/<Formal Paper Title>/
   ├── <PDF basename>.pdf
   ├── confluence-summary.md
   ├── assets/images/
   └── .confluence-page.json    # Exists only after a successful Publish; never reader-visible
   ```

   `confluence-summary.md` is the reviewable, reproducible source draft; the Confluence page is the official deliverable. Do not create or overwrite `summary.html` unless the user also requests HTML.
4. Audit an existing paper folder before filling any gaps. Do not create duplicate copies such as `(1)` or `copy`, and do not unconditionally overwrite an existing PDF, summary, image, or remote page.
5. Determine Topic and Subtopic for each paper from its primary technical contribution. Reuse a classification directly only when the user explicitly specifies it; create the corresponding two directory levels only when they do not already exist.

## Required Workflow

Choose the execution scope from the user's request:

- **Prepare-only:** When the user says “prepare first,” “generate a draft only,” “do not publish,” or equivalent, complete only steps 1–4. Do not run `atl check`, look up any space or page, or send any Atlassian network request. The durable outputs are `confluence-summary.md` and its local attachments. Storage XHTML is a reproducible temporary build artifact: report only where this run produced it and the local validation result, without promising that the temporary path will persist. Mark space, parent, and URL as not yet created.
- **Publish:** When the user explicitly requests creating or updating a Confluence page, complete steps 1–6. If the space or page choice is missing and would materially change the destination, finish whatever local preparation is safe, then obtain that choice from the user.

### 1. Identify, Classify, and Intake the PDF

- Cross-check the complete title, authors, venue or arXiv record, year, canonical landing page, and PDF URL against first-party sources such as author pages, arXiv, DOI records, official conference or journal pages, and publisher pages.
- Create or reuse the paper folder under the shared standard, then obtain and validate the PDF. Keep PDF intake details, hashes, tools, and path handling only in internal working state; do not place them on the Confluence page.
- By default, name a newly downloaded PDF after the formal paper title. If the paper folder already contains a legacy-basename or arXiv-ID PDF whose content and version have been validated, preserve it exactly and make `paper-attachment.file` reference it exactly. Do not create a duplicate PDF merely to match an example filename. If an existing file is incorrect or its purpose is unclear, preserve it and explain the issue to the user.
- When migrating existing HTML, use the verified formal paper title as the Confluence page title. Do not automatically move an existing physical folder because its summary text differs. In Section 01, derive Topic and Subtopic from the current physical path. If a legacy summary conflicts with that path, reassess the classification and report the discrepancy at completion; move the folder only with user approval.

### 2. Read the Full Paper with an Evidence Ledger

- Complete orientation, method, evidence, critique, completeness, and exposition passes in that order. In the exposition pass, define the target reader's minimum prerequisites and construct the causal thread from context through problem, requirements, mechanism, evidence, and boundaries. Stop based on evidence coverage, not a fixed number of passes.
- Maintain an internal `claim/data → source section → PDF page → printed paper page → Figure/Table/Equation/Algorithm` ledger.
- Strictly distinguish `作者主張`, `實驗事實`, `分析`, and `推測`. Write `論文未提供` for information that cannot be verified; never invent it from background knowledge.
- Extract only figures and tables needed to understand the method or validate conclusions. Save them under `assets/images/` with traceable PNG/JPEG filenames, and inspect every image for clarity and completeness.

### 3. Create the Source Draft from the Fixed Template

- Copy the [Confluence summary template](assets/confluence-summary-template.md) to `confluence-summary.md` inside the paper folder, then fill every `{{...}}` placeholder. Do not invent an ad hoc format.
- Apply the reader-first guide across the fixed sections: keep Section 04 to prerequisites used later, derive requirements in Section 05, start Section 06 with an end-to-end walkthrough, and organize Sections 09–10 as claim-test pairs. Keep external prerequisites visibly distinct from claims made by the paper.
- When a metadata field or another Markdown table cell must display a literal `|`, write `\|` in the source draft. The converter restores it in storage XHTML; an unescaped `|` remains a field delimiter. Do not rewrite the formal paper title to evade table syntax.
- Write all reader-facing paper content in Traditional Chinese. Preserve the 16 fixed H2 sections and their order; add no H1 or H3–H6 headings, and express subtopics as bold paragraphs or lists. In Sections 02–14, except for image blocks, every claim in a prose sentence, list item, or data row—quantitative or qualitative—must carry an evidence label in the same sentence, with a source that includes both the source section or appendix and `PDF p.N`. Section 15 contains discussion questions and is exempt from evidence labels. Every term and key-index entry in Section 16 must also carry an evidence label in the same sentence, with the source section and `PDF p.N` in the same list item or paragraph. A term may be written as `` **[作者主張]** `TERM`：指……（來源：§… · PDF p.N）``. Only when an entire item is missing may `論文未提供` appear as a standalone sentence; do not combine it with other unlabeled claims. Follow the shared standard's page-number format.
- Mark evidence types explicitly with `**[作者主張]**`, `**[實驗事實]**`, `**[分析]**`, and `**[推測]**`; do not rely only on color or a Confluence status.
- Do not use Markdown image syntax because the current Atlassian CLI does not convert it to a Confluence attachment image. Use `paper-image` and `paper-attachment` fenced JSON blocks as defined by the Confluence standard. Each `paper-image` must also specify an `evidence` type. If the paper contains figures but the summary does not need an extraction, explain this with `**[分析]** 本摘要未擷取圖表：...（來源：...）`; do not falsely claim that the paper does not provide figures.
- In the current source format, preserve LaTeX and formula text only as inline code or fenced code blocks, then explain variables and sources in the prose. Do not hand-write or later inject an equation or storage macro. If a formula app becomes necessary, first extend and validate a formal directive instead of bypassing the renderer.

### 4. Validate Locally and Generate Storage XHTML

- First resolve the installed `slai-atlassian` Skill path. Here, `ATL` means that Skill's `scripts/atlassian.py`. Do not write a separate REST client, and do not request a token in the conversation.
- Run:

  ```powershell
  python ".agents/skills/paper-reading-confluence/scripts/prepare_confluence.py" `
    --source "<paper-folder>/confluence-summary.md" `
    --paper-directory "<paper-folder>" `
    --atlassian-cli "<slai-atlassian-skill>/scripts/atlassian.py" `
    --output "<temporary-path>/confluence-summary.storage.xhtml"
  ```

- If validation fails, correct the source draft or attachments and rerun it. Storage XHTML is a temporary publishing artifact, not another summary source; do not treat it as a manually maintained document.
- By default, the formal title must correspond to the paper-folder basename. Add `--allow-legacy-folder-title` only during a migration after verifying that the existing folder contains the same paper and that the preserve-existing-files rule prevents moving it. Report the reused legacy folder at completion; never use this flag to conceal selection of the wrong paper.
- By default, the converter rejects unreferenced PNG/JPEG files under `assets/images/` so a migration cannot silently omit figures. Add `--allow-unreferenced-images` only after manually confirming that those files do not belong on this page. Existing output is not overwritten by default. Generated output carries a generator marker, and `--overwrite-output` accepts only an existing `.storage.xhtml` file with the same marker. Never use it to overwrite a source draft, attachment, or unrelated XHTML.
- The attachment `bytes` and `sha256` returned by the command are only for local-to-remote version decisions. Never put them on the Confluence page or in the reader summary.
- The validator uses a PDF parser to compare Section 01's `共 N 頁` with the attachment's actual page count. Do not rely only on a count displayed by a download page.

### 5. Resolve the Confluence Target and Publish Safely

- Before the first Atlassian action, run `python <ATL> check` and follow the `slai-atlassian` Skill. If authentication is missing, report only the CLI's next step; never ask the user to paste a secret into the conversation.
- Require an explicit space key; a parent page is optional. If the user did not specify one and no single existing project convention resolves it unambiguously, list the candidates and ask the user to choose. Do not guess.
- Use the formal paper title as the default page title; the user may specify a prefix or another title. Before creation, check for duplicates with `conf-pages --space <KEY> --title "<TITLE>"`.
- First read the optional `.confluence-page.json` in the paper folder. It is a non-reader-visible remote-identity sidecar that stores at least `site`, `spaceKey`, `pageId`, `title`, `parentId`, the last verified page `version`, and, for every attachment, its `filename`, local `bytes` and `sha256`, and remote attachment `id` and `version`. Create or atomically update it only after a successful read-back. If it conflicts with the current site or remote identity, stop and resolve the target again; do not trust it blindly or rewrite it silently.
- Before any write, tell the user the exact space, parent, title, whether the action is a create or update, and which attachments will be uploaded. If search determined the target, run `--dry-run` first.
- A new page may be created directly from the final storage XHTML, then supplied with the referenced PDF and images. Attachment references may exist first and will resolve after upload:

  ```powershell
  python <ATL> conf-create --space <KEY> --title "<TITLE>" --parent <PARENT_ID> `
    --format storage --body-file "<temporary-path>/confluence-summary.storage.xhtml"
  python <ATL> conf-attach <PAGE_ID> --file "<paper.pdf>" --file "<image.png>"
  ```

  Omit `--parent` when no parent is specified. Re-uploading an attachment with the same filename creates a new version, so upload only validated files that definitely belong to that page.
- If the site explicitly rejects attachment references whose attachments do not yet exist during the first real Publish, first confirm that no same-title page was left behind. Then create a minimal placeholder page with no attachment references, upload the attachments, and finally update that new page with the same validated storage XHTML. Never enter this fallback after an uncertain response; that could create a duplicate page.
- If a create or attachment response is uncertain, read back by exact title or by pageId plus filename before retrying. Do not immediately resend and risk a duplicate page or unnecessary attachment version.
- If a same-title page exists, read it, confirm that it represents the same paper, and compare the current version. Obtain explicit user confirmation before fully replacing its body. After confirmation, use `conf-update <PAGE_ID> --format storage --body-file <storage-file> --message "Regenerated from confluence-summary.md"`. Do not use create to evade a conflict, and do not append the summary as a second copy.
- A matching filename or file size does not establish attachment equivalence. It is safe to skip an upload only when the local SHA-256 in `.confluence-page.json` still matches the current attachment and the remote attachment id and version still match the sidecar. Upload a new version only when the local hash changes. If the sidecar is missing, the remote version has drifted, or the identity does not match, report the condition and obtain an explicit retransmission decision instead of guessing. Update the sidecar only after a successful upload and read-back.
- If an image or PDF is removed or renamed in the source draft, preserve the old Confluence attachment by default and omit it from the current sidecar. Never delete it automatically. Only when the user explicitly requests cleanup may you list the exact stale filename and attachment id, recheck the current page references, and follow the Atlassian Skill's deletion procedure.

### 6. Deliver Only After Read-back Verification

- Use `conf-page <PAGE_ID> --format storage` and the default Markdown read-back to verify title, space, parent, version, all 16 sections, source markers, TOC, attachment references, and readable content.
- Use `raw GET /wiki/api/v2/pages/<PAGE_ID>/attachments --query limit=250` to verify the filename, media type, file size, and version of every current reference. If a response contains a next link or cursor, follow it page by page until none remains. Then confirm that the current references form a uniquely matched subset of the complete remote list and correspond one-to-one with the sidecar. Historical attachments that the current page does not reference may remain and be reported as stale; they must not make validation fail and must not be deleted automatically. Do not inspect only the first response page, and do not assume that attachments are complete merely because an upload command succeeded.
- Open the returned URL for visual QA of the TOC, heading hierarchy, tables, code and formulas, images, captions, long titles, and narrow viewports. If direct inspection is unavailable, explicitly report the incomplete QA; do not claim that it passed.
- Find and remove any reader-visible text that exposes intake, download, filename handling, tool usage, authentication, or QA operations.

## Reader-visible Content Boundary

The Confluence page is a paper research report, not a task log. Include only academic metadata, classification rationale, research content, source locations, and analysis. Never include absolute local paths, PDF signatures or hashes, download/parsing/cropping commands, Windows naming workarounds, tokens or authentication state, API requests, CLI output, or production notes such as “validation passed.”

Use neutral reader-visible attachment text such as `開啟論文 PDF`. A figure caption may show only `Figure/Table/Algorithm + original number`, an original `導讀：`, and the necessary source location. Never present cropping or upload operations as a caption.

## Completion Report

At delivery, list the locally created or updated files, the classification and its technical rationale, the three sections most worth reading first, and any incomplete verification. In Prepare-only mode, say only `本地待上傳附件已驗證` and explicitly state `尚未發佈`. Only in Publish mode may the report include the Confluence page title, space, parent, URL, and `遠端附件已 read-back 核對`. For the first Publish, accurately identify the live-site storage/API compatibility QA that was completed. Do not expose credentials, attachment hashes, or unnecessary internal API details in the report.
