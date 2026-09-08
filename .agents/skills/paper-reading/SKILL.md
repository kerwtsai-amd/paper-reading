---
name: paper-reading
description: Organize, download, deeply read, and summarize academic papers in this Paper Reading workspace as evidence-traceable Traditional Chinese HTML. Use for paper discovery, classification, PDF intake or reading, figure/table extraction, technical analysis, or summary.html work when Confluence delivery is not requested; use paper-reading-confluence for Confluence pages.
metadata:
  short-description: 可追溯證據的繁中論文閱讀與 HTML 摘要流程
---

# Paper Reading

將每篇論文整理成可搬移、可驗證、適合研究組會報告的研究資料夾。使用者在當次任務中的明確指示優先於本 Skill。

若使用者要求建立、更新或遷移 Confluence 論文頁面，改用同專案的 `paper-reading-confluence` Skill；以下 HTML 模板與 `summary.html` 契約不適用於該交付模式。

## 固定專案契約

1. 將最近且同時包含 `AGENTS.md` 與 `html template/summary-template.html` 的祖先目錄視為 Paper Reading root；在目前專案中就是工作目錄。不要向 root 之外建立分類或論文檔案。
2. 開始任何實際論文工作前，讀取 [references/paper-reading-standard.md](references/paper-reading-standard.md)。
3. 產生 HTML 前，必須讀取 root 的 `html template/summary-template.html`，從完整副本建立論文資料夾內的 `summary.html`。保留模板版本標記、CSS、MathJax、固定章節 ID、證據標籤與響應式結構。
4. 專案沒有預設 Topic 或 Subtopic。每篇論文固定使用兩層分類，第三層才是正式論文標題資料夾；唯一目標結構為：

   ```text
   <Topic>/<Subtopic>/<Formal Paper Title>/
   ├── <Formal Paper Title>.pdf
   ├── summary.html
   └── assets/images/
   ```

   文件中的任何具名分類路徑都只用來說明層級，不是預設分類，也不能單憑範例文字建立目錄。

5. 既有論文資料夾必須先盤點再補齊；不得建立 `(1)`、`copy` 等重複副本，也不得無條件覆寫既有 PDF、摘要或圖片。

## 必須完成的工作流

### 1. 辨識與分類

- 先檢查 root 的現有目錄與候選論文資料夾。
- 以使用者提供的關鍵字、論文連結、檔名或 PDF 為起點，查詢標題與 Abstract；優先使用作者頁、arXiv、DOI、正式會議／期刊或出版社等第一方來源。
- 至少交叉核對正式完整標題、作者、venue／arXiv、年份、canonical landing page 與 PDF URL。不要只根據搜尋結果片段命名。
- 依主要技術貢獻逐篇選擇一個 Topic 與一個 Subtopic，而不是只看關鍵字。只有使用者在當次任務明確指定分類時才直接沿用；否則完成 title／Abstract 與主要貢獻判讀後再決定。分類不存在時才在 root 下建立，並在摘要標成「分析：分類理由」。
- 論文資料夾與 PDF 原則上使用正式完整標題。只替換 Windows 禁止字元 `< > : " / \\ | ? *`，移除尾端空格／句點，並避免 `CON`、`PRN`、`AUX`、`NUL`、`COM1`–`COM9`、`LPT1`–`LPT9` 等保留名稱。若經實測完整路徑會使必要工具失敗，可改用可追溯的安全 PDF 檔名；只在最後交付回報中簡短說明例外，不得把路徑長度、字元替換、工具錯誤或命名推理寫進 `summary.html`。

### 2. 取得並驗證 PDF

- 從可信的 canonical PDF 來源下載到論文資料夾，預設命名為 `<Formal Paper Title>.pdf`；只有上述經驗證的路徑／工具相容性問題可使用安全短名。
- 若同名 PDF 已存在，先確認它可開啟且確為目標論文；正確時沿用，不正確或版本不同時保留原檔並向使用者說明，不得靜默覆寫。
- 驗證檔案非 HTML 錯誤頁、具有有效 PDF signature、頁數可讀，並在內部工作筆記記錄 PDF 頁碼與論文印刷頁碼的差異（若確實存在）。這些 intake／QA 結果不是摘要內容。

### 3. 迭代研究 loop

以證據覆蓋率而非固定重複次數作為停止條件。每輪都更新內部 evidence ledger：`主張／數據 → 原文章節 → PDF 頁碼 → 論文頁碼 → Figure/Table/Equation`。

1. **定位輪**：讀 title、Abstract、Introduction、contributions、全文結構與 Conclusion，確認研究問題及分類。
2. **方法輪**：精讀背景、問題定義、系統架構、演算法、偽程式碼與公式；追蹤每個元件、資料流、假設與複雜度。
3. **證據輪**：精讀 evaluation setup、baselines、workloads、硬軟體、指標、主結果、ablation 與 sensitivity；核對 caption、座標軸、單位及比較條件。
4. **批判輪**：區分作者主張、實驗直接支持的事實、自己的分析與推測；尋找缺失 baseline、不公平比較、外部效度、部署限制與未驗證假設。
5. **完整性輪**：回查所有重要數字、公式、圖表與摘要結論。若任一關鍵敘述無來源、16 章節未覆蓋或核心圖仍缺失，就繼續針對缺口閱讀；若原文確實未提供，明確寫「論文未提供」。

不要用 Abstract 代替全文閱讀，也不要因背景知識看似合理而補造論文沒有的資訊。

### 4. 擷取必要圖片

- 只擷取解釋方法與驗證結論所必需的架構圖、流程圖、演算法圖、結果圖或關鍵表格；優先以高解析度 PNG 儲存於 `assets/images/`。
- 檔名使用 `fig-03-p07-overview.png`、`table-02-p10-results.png` 這類可追溯格式。裁切需清晰、完整保留圖例／座標／必要標註，避免整頁截圖與無關邊界。
- HTML 只能以 `assets/images/...` 正斜線相對路徑引用。每張圖都要有描述性 `alt` 與自行撰寫的導讀。`figcaption` 的來源標籤只能直接寫成原論文物件編號本身，例如 `Figure 4`、`Table 2` 或 `Algorithm 1`；不得加上「原論文」、句點、PDF／印刷頁碼、`裁切自原論文`、`擷取自原論文` 或其他來源／產製說明。圖表頁碼放在正文來源標記、重點索引或內部 evidence ledger，不放在圖說。
- 必須沿用模板的 caption markers：`data-caption-kind="paper-object"`、`data-caption-field="paper-object-label"` 與 `data-caption-field="reading-guide"`。來源標籤後直接接以「導讀：」開頭的非空導讀，不插入第三段可見文字。

### 5. 用固定模板撰寫摘要

- 複製 root 的 `html template/summary-template.html` 為目標 `summary.html`，再替換所有 `{{...}}` placeholder。對標題、作者與 URL 做 HTML escaping。
- 正文使用繁體中文；專有名詞第一次出現時保留英文全名與縮寫。以研究報告方式重組內容，不逐段翻譯或大段抄錄。
- 保留 16 個固定章節。資訊缺失時寫「論文未提供」，不可刪節或虛構。
- 重要公式使用 `\( ... \)` 與 `\[ ... \]`，並解釋變數、單位／系統意義、與方法的關係及原文來源。
- 對關鍵敘述使用模板的四種文字標籤：`作者主張`、`實驗事實`、`分析`、`推測`。資訊不能只靠顏色區分。
- 所有重要數字緊鄰來源標記，至少包含原文章節與 PDF 頁碼；有 Figure、Table 或 Equation 時一併列出。若 PDF 頁碼與印刷頁碼不同，兩者都列。

#### 讀者可見內容邊界（強制）

- `summary.html` 是論文研究報告，不是任務日誌、建檔紀錄、驗證報告或模型工作筆記。只保留有助於理解、引用、評估或討論論文的內容。
- 若呈現總頁數，必須使用唯一的 `data-summary-field="pdf-page-count"` 欄位，且其完整可見值只能是 `共 N 頁`。頁碼系統相同時，不得附加「PDF 頁碼與印刷頁碼一致」、「無 offset／無頁碼偏移」等確認過程；兩套頁碼不同時，只在相關來源標記中直接並列實際頁碼。
- 禁止在可見正文、表格、caption、callout 或 footer 寫入：搜尋／交叉核對過程、PDF signature／版本／bytes／hash、下載或解析紀錄、Windows 禁止字元替換、資料夾或 PDF 命名理由、絕對路徑與長度、Poppler／OCR／瀏覽器或其他工具錯誤、裁圖／渲染命令、QA 結果，以及「已檢查但沒有差異」的負面確認。
- 不得把上述操作資訊改標為「分析」或「推測」後留在正文。它們應保留在內部工作狀態；只有 materially 影響交付的例外，才在最後回覆中簡短說明，不寫入 HTML。
- 本地 PDF 連結可以指向實際安全檔名，但可見文字使用「開啟本地 PDF」或其他中性描述，不解釋檔名選擇。圖說只顯示 `Figure／Table／Algorithm + 原編號`；頁碼只在正文來源標記或重點索引中呈現，且僅在兩套頁碼不同時並列 PDF 與印刷頁碼。

### 6. 驗證後才交付

- 執行：

  ```powershell
  pwsh -NoProfile -File ".agents/skills/paper-reading/scripts/validate-summary.ps1" -PaperDirectory "<paper-folder>"
  ```

- 再以瀏覽器做視覺 QA：桌面與窄螢幕、目錄跳轉、長標題、表格橫向捲動、圖片、MathJax、鍵盤 focus 與 A4 列印預覽。
- 搜尋並移除任何暴露 intake、檔名處理、路徑 workaround、工具使用或 QA 過程的讀者可見文字；頁數欄必須符合 `共 N 頁`。
- 驗證失敗就修正並重跑，直到所有可修項目通過。外部資源不可用或論文本身缺資料時，保留明確標記並在交付回報。

## 完成回報

交付時列出：建立／更新的資料夾與檔案、分類與技術理由、最值得優先閱讀的三個摘要部分，以及任何無法擷取、無法確認或仍需使用者補充的內容。
