# Paper Reading 專案規則

## 專案根目錄

- 本檔案所在目錄就是 **Paper Reading 專案根目錄**。處理本專案時，以此目錄解析所有分類、論文、模板與驗證腳本路徑；不要把父目錄或暫存目錄當成專案根目錄。
- 保留既有內容。除非使用者明確要求，不得覆蓋、移動或刪除與目前論文無關的檔案。

## 必用 Skill 與模板

- 任何涉及論文查找、下載、分類、PDF 閱讀、圖片／表格擷取或技術分析的任務，都必須依交付目的地先讀取對應 Skill：
  - 本地 HTML 或未指定 Confluence 時，使用 [`.agents/skills/paper-reading/SKILL.md`](.agents/skills/paper-reading/SKILL.md)。
  - 建立、更新或遷移 Confluence 論文頁面時，使用 [`.agents/skills/paper-reading-confluence/SKILL.md`](.agents/skills/paper-reading-confluence/SKILL.md)；其 Confluence 輸出契約優先於 HTML 專屬規則。
- HTML 摘要必須從 [`html template/summary-template.html`](html%20template/summary-template.html) 複製後填寫，不得改用 Markdown 取代使用者要求的 HTML。Confluence 摘要則必須從 [`.agents/skills/paper-reading-confluence/assets/confluence-summary-template.md`](.agents/skills/paper-reading-confluence/assets/confluence-summary-template.md) 建立 `confluence-summary.md`，再依該 Skill 驗證，並在使用者要求 Publish 時發佈；除非使用者同時要求，不必另外建立 `summary.html`。
- 使用者在當次任務中的明確指示優先於本檔案與 Skill；若有衝突，保留使用者意圖並說明差異。

## 分類結構

- 專案不設定預設 Topic 或 Subtopic。每篇論文固定放在兩層分類之下，第三層才是論文資料夾：`<Topic>/<Subtopic>/<Formal Paper Title>/`。
- Topic 與 Subtopic 應依每篇論文的主要技術貢獻逐篇判斷；若使用者在當次任務明確指定分類，才沿用該分類。分類不存在時才建立對應的兩層目錄。
- 任何具名的分類路徑都只能在使用者明確指定時採用；文件中的分類範例只用來說明層級，不代表本專案、目前批次或任何論文的預設分類，也不能單憑範例建立目錄。
