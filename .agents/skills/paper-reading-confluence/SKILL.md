---
name: paper-reading-confluence
description: Organize, deeply read, and publish academic papers as evidence-traceable Traditional Chinese Confluence pages in this Paper Reading workspace. Use when a paper task requests Confluence delivery, migration from summary.html to Confluence, or creation or maintenance of a Confluence paper-reading page; use paper-reading alone for HTML-only delivery.
metadata:
  short-description: 可追溯證據的繁中論文閱讀與 Confluence 發佈流程
---

# Paper Reading for Confluence

將每篇論文整理成可驗證的研究資料夾，並以 Confluence page 交付適合研究組會使用的繁體中文摘要。保留既有 `paper-reading` Skill；只有使用者要求 Confluence 時才使用本 Skill 的輸出契約。

## 固定專案契約

1. 將最近且同時包含 `AGENTS.md`、`.agents/skills/paper-reading/` 與本 Skill 的祖先目錄視為 Paper Reading root。不要向 root 之外建立分類或論文檔案。
2. 開始任何實際論文工作前，讀取：
   - [共用論文內容標準](../paper-reading/references/paper-reading-standard.md)，用於分類、全文閱讀、證據紀律、圖片擷取與研究深度。
   - [Confluence 摘要與發佈標準](references/confluence-publishing-standard.md)，用於本 Skill 的輸出格式、附件與遠端安全規則。
   共用標準中只沿用「研究者角色與證據紀律」、「目錄與檔名標準」的分類／正式標題原則、「讀者內容與作業紀錄的邊界」、「方法與實驗閱讀檢查」、「圖片與表格標準」的選圖／擷取忠實度，以及「研究 loop 停止條件」。其中的 `summary.html` 固定章節、HTML/CSS/MathJax、HTML 圖片嵌入與 caption 格式、HTML validator／瀏覽器驗收不適用；改採本 Skill 的固定章節、attachment、storage 與 Confluence read-back 規則。若兩份標準衝突，以本 Skill 的 Confluence 規則為準。
3. 每篇論文仍固定放在 `<Topic>/<Subtopic>/<Formal Paper Title>/`。Confluence 模式的本地資料結構為：

   ```text
   <Topic>/<Subtopic>/<Formal Paper Title>/
   ├── <PDF basename>.pdf
   ├── confluence-summary.md
   ├── assets/images/
   └── .confluence-page.json    # Publish 成功後才有；不進讀者頁面
   ```

   `confluence-summary.md` 是可審核、可重建的來源稿；Confluence page 是正式交付。除非使用者同時要求 HTML，不要建立或覆寫 `summary.html`。
4. 既有論文資料夾必須先盤點再補齊。不得建立 `(1)`、`copy` 等重複副本，也不得無條件覆寫既有 PDF、摘要、圖片或遠端頁面。
5. Topic 與 Subtopic 依主要技術貢獻逐篇判斷。只有使用者明確指定分類時才直接沿用；不存在時才建立對應的兩層目錄。

## 必須完成的工作流

先依使用者要求選擇執行範圍：

- **Prepare-only**：使用者說「先準備」、「先產生草稿」、「不要發佈」或同義指示時，只完成步驟 1–4；不執行 `atl check`、不查 space/page，也不發出任何 Atlassian 網路請求。耐久成果是 `confluence-summary.md` 與本地附件；storage XHTML 是可重建的暫存 build artifact，只回報此次產出位置與本地驗證結果，不承諾該暫存路徑長期存在。space／parent／URL 標成尚未建立即可。
- **Publish**：使用者明確要求建立或更新 Confluence page 時，完成步驟 1–6。若缺少會實質改變目的地的 space 或 page 選擇，先完成可安全完成的本地準備，再向使用者取得該選擇。

### 1. 辨識、分類與 PDF intake

- 以作者頁、arXiv、DOI、正式會議／期刊或出版社等第一方來源交叉核對完整標題、作者、venue／arXiv、年份、canonical landing page 與 PDF URL。
- 依共用標準建立或沿用論文資料夾，取得並驗證 PDF。PDF intake、hash、工具與路徑處理只留在內部工作狀態，不寫入 Confluence page。
- 新下載 PDF 預設使用正式論文標題；若論文資料夾已有經內容與版本驗證的舊 basename／arXiv ID PDF，原樣沿用並讓 `paper-attachment.file` 精確引用它，不得為符合範例檔名另建重複 PDF。不正確或用途不明時保留原檔並向使用者說明。
- 遷移既有 HTML 時，Confluence page title 使用核對後的正式論文標題；既有實體資料夾不因摘要文字不同而自動搬動。第 01 章 Topic／Subtopic 以目前實體路徑為準；若舊摘要與路徑不一致，先重新判讀分類並在完成回報指出差異，只有使用者同意時才搬動資料夾。

### 2. 以 evidence ledger 深讀全文

- 依序完成定位、方法、證據、批判與完整性輪；停止條件採證據覆蓋率，不採固定輪數。
- 內部維護 `主張／數據 → 原文章節 → PDF 頁碼 → 論文頁碼 → Figure/Table/Equation/Algorithm` ledger。
- 嚴格區分 `作者主張`、`實驗事實`、`分析`、`推測`。不能確認的內容寫「論文未提供」，不得用背景知識補造。
- 只擷取理解方法與驗證結論所需的圖表，存為 `assets/images/` 下可追溯的 PNG/JPEG 檔名，並逐張檢查清晰度與完整性。

### 3. 從固定模板建立來源稿

- 複製 [Confluence 摘要模板](assets/confluence-summary-template.md) 為論文資料夾內的 `confluence-summary.md`，再填滿所有 `{{...}}` placeholder；不得臨時另造版型。
- 正文使用繁體中文並保留 16 個固定 H2 章節及順序，不加 H1 或 H3–H6；子主題改用粗體段落或列表。第 02–14 章（圖片 block 除外）的每個正文、列表或資料列主張，不論數值或定性，都必須在同一句放 evidence label；來源同時含原文章節／附錄與 `PDF p.N`。第 15 章是討論問題而免標。第 16 章的術語與重點索引也一律在同一句使用 evidence label，並在同一列表項／段落附原文章節與 `PDF p.N`；術語可寫成 `` **[作者主張]** `TERM`：指……（來源：§… · PDF p.N）``。只有整個缺漏項目時才單獨寫「論文未提供」，不能把它混在其他未標示主張中。頁碼格式遵循共用標準。
- 以 `**[作者主張]**`、`**[實驗事實]**`、`**[分析]**`、`**[推測]**` 顯式標示證據類型，不只靠顏色或 Confluence status。
- 不要使用 Markdown 圖片語法；它不會由目前的 Atlassian CLI 轉成附件圖片。圖片與 PDF 依 Confluence 標準使用 `paper-image` 與 `paper-attachment` fenced JSON blocks。每個 `paper-image` 必須另填 `evidence` 類型；若論文有圖但判斷摘要無需擷取，以 `**[分析]** 本摘要未擷取圖表：...（來源：...）` 說明，不得謊稱論文未提供。
- 目前來源稿一律以行內 code 或 fenced code block 保存 LaTeX／公式文字，並在正文解釋變數與來源。不要手寫或事後注入 equation/storage macro；若未來需要公式 app，應先擴充並驗證正式 directive，而不是繞過 renderer。

### 4. 本地驗證並產生 storage XHTML

- 先解析已安裝的 `slai-atlassian` Skill 路徑；`ATL` 代表該 Skill 的 `scripts/atlassian.py`，不得自行另寫 REST client，也不得在對話中索取 token。
- 執行：

  ```powershell
  python ".agents/skills/paper-reading-confluence/scripts/prepare_confluence.py" `
    --source "<paper-folder>/confluence-summary.md" `
    --paper-directory "<paper-folder>" `
    --atlassian-cli "<slai-atlassian-skill>/scripts/atlassian.py" `
    --output "<temporary-path>/confluence-summary.storage.xhtml"
  ```

- 驗證失敗就修正來源稿或附件後重跑。storage XHTML 是發佈用暫存物，不是另一份摘要來源，不要把它當成需要長期維護的人工文件。
- 正式標題預設須對應論文資料夾 basename。只有遷移時已核對「現有資料夾確為同一篇論文」且依保留原檔規則不能搬動，才可在命令加 `--allow-legacy-folder-title`；必須在完成回報註明沿用 legacy folder，不能用此旗標掩蓋選錯論文。
- 轉換器預設拒絕 `assets/images/` 中未被引用的 PNG/JPEG，避免遷移時漏圖；只有人工確認那些檔案不屬於本頁後，才可加 `--allow-unreferenced-images`。輸出已存在時預設不覆寫；產物會帶 generator marker，`--overwrite-output` 只接受帶相同 marker 的既有 `.storage.xhtml`，絕不能用來覆寫來源稿、附件或其他 XHTML。
- 命令回傳的附件 `bytes`／`sha256` 只供本地與遠端版本判定，不能寫入 Confluence page 或讀者摘要。
- 驗證器會用 PDF parser 將第 01 章的 `共 N 頁` 與實際附件頁數比對；不可只填下載頁面顯示的頁數。

### 5. 解析 Confluence 目標並安全發佈

- 第一次 Atlassian 動作先執行 `python <ATL> check`，並遵循 `slai-atlassian` Skill。缺少認證時只回報 CLI 的 next step；絕不請使用者把 secret 貼進對話。
- 需要明確的 space key；parent page 可選。若使用者未指定且無法從單一現有專案慣例無歧義推得，先列出候選並請使用者選擇，不得猜測。
- 頁面標題預設採正式論文標題；使用者可指定前綴或其他標題。建立前以 `conf-pages --space <KEY> --title "<TITLE>"` 查重。
- 先讀論文資料夾內可選的 `.confluence-page.json`。它是非讀者可見的遠端 identity sidecar，至少保存 `site`、`spaceKey`、`pageId`、`title`、`parentId`、最後確認的 page `version`，以及每個附件的 `filename`、本地 `bytes`／`sha256`、遠端 attachment `id`／`version`。只有成功 read-back 後才建立或原子更新；若 sidecar 與目前 site／遠端 identity 不符，停止並重新解析，不能盲信或靜默改寫。
- 發出任何 write 前，先向使用者說明精確 space、parent、title、建立或更新、以及會上傳的附件。目標若由搜尋推得，先使用 `--dry-run`。
- 新頁面可直接以最終 storage XHTML 建立，再上傳它所引用的 PDF 與圖片；attachment reference 可先存在，附件上傳完成後即解析：

  ```powershell
  python <ATL> conf-create --space <KEY> --title "<TITLE>" --parent <PARENT_ID> `
    --format storage --body-file "<temporary-path>/confluence-summary.storage.xhtml"
  python <ATL> conf-attach <PAGE_ID> --file "<paper.pdf>" --file "<image.png>"
  ```

  未指定 parent 時省略 `--parent`。同檔名附件重傳會建立新版本，因此只能上傳已驗證且確屬該頁的檔案。
- 若站台在首次實際 Publish 明確拒絕 body 內尚未存在的 attachment references，先確認沒有殘留的同名頁，再建立不含 attachment reference 的最小 placeholder page、上傳附件，最後用同一份已驗證 storage XHTML 更新該新頁；不得在不確定回應後直接走 fallback，避免重複頁。
- create 或 attachment 回應不確定時，先用 exact title 或 pageId + filename 讀回確認，不得直接重送造成重複頁或不必要的附件版本。
- 若同標題頁已存在，先讀取頁面、確認是同一論文並比較目前版本。完整替換 page body 前必須取得使用者明確確認；確認後使用 `conf-update <PAGE_ID> --format storage --body-file <storage-file> --message "Regenerated from confluence-summary.md"`。不要用 create 迴避衝突，也不要把摘要 append 成第二份內容。
- 判定附件是否變更時，同名或同大小不算內容等價。只有 `.confluence-page.json` 的本地 SHA-256 仍等於目前附件，且遠端 attachment id／version 仍等於 sidecar 記錄時，才能安全略過；本地 hash 改變才上傳新版本。sidecar 缺失、遠端版本漂移或 identity 不一致時，先回報並取得是否重傳的明確決定，不得猜測。成功上傳並讀回後才更新 sidecar。

### 6. 讀回驗證後才交付

- 以 `conf-page <PAGE_ID> --format storage` 與預設 Markdown read-back 驗證 title、space、parent、version、16 章節、來源標記、TOC、附件 reference 與可讀內容。
- 以 `raw GET /wiki/api/v2/pages/<PAGE_ID>/attachments --query limit=250` 核對每個引用檔名、media type、file size 與版本；若回應有 next/cursor，依回傳值逐頁讀到沒有下一頁，先累積完整清單再與所有 references／sidecar 比對。不得只查第一頁，也不得只因上傳命令回傳成功就假設附件完整。
- 開啟回傳 URL 做視覺 QA：目錄、標題階層、表格、code／公式、圖片、caption、長標題與窄視窗。無法直接檢查時明確回報未完成的 QA，不得聲稱通過。
- 搜尋並移除任何暴露 intake、下載、檔名處理、工具使用、認證或 QA 過程的讀者可見文字。

## 讀者可見內容邊界

Confluence page 是論文研究報告，不是任務日誌。只保留學術 metadata、分類理由、研究內容、來源定位與分析。不得寫入絕對本地路徑、PDF signature／hash、下載／解析／裁圖命令、Windows 命名處理、token／認證狀態、API request、CLI output 或「驗證通過」等產製資訊。

附件連結使用中性可見文字，例如「開啟論文 PDF」。圖說只顯示 `Figure／Table／Algorithm + 原編號`、自撰「導讀」與必要來源定位；不得把裁切或上傳過程當成圖說。

## 完成回報

交付時列出：本地建立／更新的檔案、分類與技術理由、最值得優先閱讀的三個章節，以及任何尚未完成的驗證。Prepare-only 只稱「本地待上傳附件已驗證」並明確寫「尚未發佈」；Publish 模式才列 Confluence page title／space／parent／URL 與「遠端附件已 read-back 核對」。首次 Publish 也要如實標示已完成的實站 storage/API 相容性 QA。不要在回報中暴露 credential、附件 hash 或不必要的內部 API 細節。
