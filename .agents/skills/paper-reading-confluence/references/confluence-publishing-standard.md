# Paper Reading 的 Confluence 摘要與發佈標準

本標準只定義 Confluence 交付與媒介差異。研究深度、證據紀律、分類、PDF intake、圖片擷取與停止條件沿用 [`paper-reading-standard.md`](../../paper-reading/references/paper-reading-standard.md)。使用者當次明確指示仍具最高優先權。

## 成果與來源稿

- 正式成果是單一 Confluence page；本地 `confluence-summary.md` 是該頁的可審核來源稿。
- 每次重建 page body 都從 `confluence-summary.md` 完整產生，避免遠端內容與本地來源分叉。
- `confluence-summary.md` 必須從 [`confluence-summary-template.md`](../assets/confluence-summary-template.md) 複製，不得從既有 `summary.html` 直接貼上完整 HTML。既有 HTML 可作內容來源，但 CSS、JavaScript、MathJax、DOM markers 與作業紀錄不得進入 Confluence。
- 發佈用 storage XHTML 由 `prepare_confluence.py` 產生。不要手動修改產出的 XHTML；應修改 Markdown 來源後重建。
- 使用者要求 prepare-only 時，耐久成果是本地來源稿與附件；產出的 storage XHTML 是可由來源稿重建的暫存 build artifact。完全不連線 Atlassian，只有明確要求 Publish 才解析 space／parent／page 並執行遠端寫入。
- 遷移既有摘要時，正式論文 metadata 以第一方來源重新核對；Confluence page title 使用正式完整標題。Topic／Subtopic 則以目前兩層實體路徑為交付基準。若舊摘要文字與實體路徑不一致，先回報矛盾並重新判讀，但未經使用者同意不搬動既有資料夾。

## 固定章節

Confluence page title 充當唯一頁面標題，body 依下列順序使用 16 個二級標題：

1. **論文基本資料**：正式標題、作者、venue／期刊／arXiv、年份、版本、canonical link、Topic／Subtopic、分類理由、PDF attachment 與唯一的 `共 N 頁`。
2. **一句話總結**：一至三句交代核心問題、方法與結果；數字必須可追溯。
3. **Executive Summary**：研究問題、洞察、方法、主要證據、限制與 takeaways。
4. **背景與動機**：必要領域背景、流程角色、既有瓶頸與作者觀察。
5. **問題定義**：目標、輸入輸出、假設、限制、術語與符號。
6. **核心方法**：架構、演算法、資料流、元件責任、互動與設計直覺。
7. **公式與理論**：必要公式、變數、單位／系統意義、假設、用途與來源。
8. **圖片與圖表導讀**：必要附件圖片、原物件編號、自撰導讀與來源定位。
9. **實驗設計**：硬軟體、模型、資料集、baseline、工作負載、指標與公平性。
10. **實驗結果**：各評估目標的結果、條件與圖表可支持／不可支持的結論。
11. **Ablation 與敏感度分析**：各設計貢獻、參數敏感度與互動；沒有時明確註記。
12. **優點、限制與風險**：系統假設、適用範圍、泛化、部署限制與外部效度。
13. **與相關工作的比較**：技術路線、場景、成本與取捨，不只列名稱。
14. **個人分析與可延伸方向**：可借鑑設計、待驗證結論與研究／工程延伸。
15. **組會討論問題**：3–5 個可引發證據或設計討論的技術問題。
16. **術語表與重點索引**：縮寫、定義，以及重要結論的章節／頁碼／物件索引。

資訊缺失時保留章節並寫「論文未提供」，不得刪節或虛構。

## 來源稿硬性格式

- 頁首「優先閱讀」恰好列三個有效章節編號。
- body 只使用固定的 16 個 H2，不加 H1 或 H3–H6；子主題用粗體段落或列表，避免把主張藏進未驗證的次標題。
- `最後更新` 使用不晚於今天的有效 `YYYY-MM-DD`；`年份` 使用四位西元年。
- `分類` 必須精確等於實體資料夾的 `<Topic> / <Subtopic>`，不能只在分類理由提到正確字串。
- `正式標題` 預設須和 Windows-safe folder title 同一身份；只有已人工核對的既有 legacy folder 才能以 `--allow-legacy-folder-title` 例外沿用，且不得因此改寫正式 metadata。
- `分類理由` 的 `CLASSIFICATION_SOURCE` 也要同時含原文定位與 PDF 頁碼，例如 `Abstract · PDF p.1`。
- 第 02–14 章除圖片 block 外，每個正文句、列表項或資料列中的主張都要在同一句使用 evidence label；只有純來源行與單獨成句的「論文未提供」例外，不得把該片語和其他未標示主張串在一起。第 15 章是討論問題而免標。第 16 章的術語與重點索引一律在同一句使用 evidence label，且同一列表項／段落必須含原文章節與 `PDF p.N`，不能用另一個項目的來源湊整章覆蓋率。術語可寫成 `` **[作者主張]** `TERM`：指……（來源：§… · PDF p.N）``；沒有 evidence／source 的「純定義」也不例外，以免把結果主張藏進定義句。
- 來源稿不可手寫 HTML/storage tags；inline code 內討論標籤字面值不算手寫 markup。一般 Markdown link 只允許 `https://` 或頁內 anchor；destination 若含括號必須 percent-encode。PDF 與圖片必須使用 attachment block。讀者內容不得含 Windows、UNC、POSIX 絕對本機路徑或 `file://`；code 中的 `/api/...` 類介面路徑不視為本機檔案。

## Confluence 原生呈現對應

| HTML 摘要語意 | Confluence 呈現 |
| --- | --- |
| 頁面 `<h1>` | Confluence page title；body 不再重複 H1 |
| 手工目錄 | `toc` storage macro，由轉換腳本自動加入 |
| hero／properties | 原生 Markdown table／段落 |
| evidence chip | 可見文字 `**[作者主張]**`、`**[實驗事實]**`、`**[分析]**`、`**[推測]**` |
| source chip | 緊鄰主張的 `（來源：§4.2 · PDF p.7 · Figure 3）` |
| HTML table | Markdown pipe table，轉為 Confluence table |
| `<pre><code>`／MathJax | inline code 或 fenced code block；正文另解釋公式 |
| `<img>`／本地 PDF link | page attachment reference；禁止本地絕對路徑與 `file://` |
| CSS／JS／responsive／print | 不移植；使用 Confluence 原生版面並在實際頁面做視覺 QA |

四種 evidence label 是語意資訊，不得省略或改成只靠顏色的 status macro。每句含重要數值的主張都要在同一句帶 evidence label；來源必須同時含非空的原文章節／附錄定位與正整數 `PDF p.N`。只有 PDF 與印刷頁碼不同時才並列，例如 `PDF p.7（論文標示 p.5）`。

## PDF attachment block

在第 1 章使用一個 fenced JSON block。`file` 只能是論文資料夾根層的 PDF basename；`label` 是讀者看見的中性連結文字。不可放絕對路徑。

````markdown
```paper-attachment
{"file":"Formal Paper Title.pdf","label":"開啟論文 PDF"}
```
````

允許可選的 `description`，但不得用來記錄下載、驗證或命名過程。每份摘要必須恰有一個 PDF attachment block。

## Image attachment block

一般 Markdown image 語法不會被目前的 Atlassian CLI 轉成 Confluence attachment image，故每張圖使用 fenced JSON block：

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

規則：

- `file` 必須是 `assets/images/` 下的 PNG、JPG 或 JPEG 相對路徑，且檔案存在、非空、signature 正確。不得使用 `..`、反斜線、URL 或絕對路徑。
- `label` 只能是 `Figure N`、`Table N` 或 `Algorithm N` 形式的原物件編號；panel 可寫 `Figure 3(a)` 或 `Figure 3 (a)`。不可加入「原論文」、句點、頁碼或擷取說明。
- `evidence` 必須是 `作者主張`、`實驗事實`、`分析` 或 `推測`，用來標示自撰導讀的證據類型；renderer 會顯示成粗體 label。
- `alt` 描述圖片本身；`guide` 是非空的自撰導讀，不要自行加「導讀：」前綴，轉換器會加入。
- `source` 至少包含原文章節、`PDF p.N` 與原物件編號。頁碼是證據定位，不混入 `label`。
- `width` 可省略；若提供，必須是 200–1600 的整數。不要用寬度掩蓋解析度不足。
- 同一 attachment filename 在同一頁只能代表同一張圖；更新圖檔會建立附件新版本。
- 轉換器會將 `assets/images/` 的 PNG/JPEG 視為待審核 manifest，預設要求每張都被一個 `paper-image` 引用。若資料夾含確定不屬於此頁的保留素材，可在人工核對後使用 `--allow-unreferenced-images`；不得為了讓驗證通過而隨意刪除既有檔案。
- 若論文有圖但摘要判斷無需擷取，不放 block，改寫 `**[分析]** 本摘要未擷取圖表：<理由>（來源：<原文章節> · PDF p.N）`。只有原文確實沒有相應資訊時才寫「論文未提供」。

## 公式、表格與引用

- 公式以可複製的 LaTeX 或清楚純文字呈現。行內公式放在 backticks；多行公式用 fenced code block。目前 renderer 不提供 equation directive，因此一律不要手寫、注入或事後修改成特定公式 macro。
- 每個關鍵公式後說明變數、單位／系統意義、假設、與方法的關係及原文來源。不要把公式只做成圖片。
- 可結構化數據優先用 Markdown table 重整；只有熱圖、複雜表頭或視覺配置本身重要時才以圖片附件呈現。
- 不得從百分比反推論文未披露的絕對值，不得把不同工作負載的 best case 拼成單一代表數字。
- 引用只做短摘錄與忠實改寫，保留 canonical link；不要大段複製原文。

## Publish 模式的頁面與附件安全

1. 只有進入 Publish 模式才先執行 `atl check`。不可在對話中詢問或保存 token。
2. space key 必須明確；parent page 若未指定可放 space root，但必須在寫入前清楚告知。不可從同名 space 或 page 猜測。
3. 建立前以 space + exact title 查重。若搜尋得到多個候選，停止並請使用者選擇。
4. 由搜尋推得的 target 先 dry-run。任何 body replacement 都先讀取 current page 並取得使用者明確確認。
5. 新頁用完整最終 storage body 一次建立，再上傳被引用的 PDF 與圖片。若其中一個附件失敗，保留已建立頁面，不自動刪除；修正後只重試缺失附件。
6. 既有頁確認後以 `conf-update <pageId> --format storage --body-file <storage-file>` 完整重建 body；不以 append 發佈完整摘要，否則會產生第二套 16 章。沿用未變的既有附件，只上傳缺少或確實更新的檔案；append 只適合使用者明確要求的附錄或增補。
7. 附件超過站台限制、權限不足或 API 部分失敗時，回報精確剩餘項目，不宣稱完整交付。
8. create 回應不確定或連線中斷時，先以 space + exact title 查詢是否已建立，不能直接重送。attachment 回應不確定時，先依 pageId + filename 查附件與版本，避免無意建立新版本。
9. Publish 成功 read-back 後，在論文資料夾原子寫入 `.confluence-page.json`，保存 site／spaceKey／pageId／title／parentId／page version，以及各 attachment 的 filename、本地 bytes／SHA-256、遠端 id／version。這是操作 sidecar，不可放入 page body。後續先以它解析 custom title 與 remote identity；identity 漂移時停止確認。
10. 同名與同大小不能證明附件相同。只有 sidecar 的本地 hash 仍匹配目前檔案，且遠端 id／version 仍匹配 sidecar，才略過上傳；本地 hash 改變時建立新附件版本。缺 sidecar 或遠端 version 漂移時，先取得重傳決定，不能盲目增加版本。

Sidecar 使用下列最小 schema；不得加入 credential。`parentId` 沒有 parent 時為 `null`，附件陣列必須涵蓋 page 引用的 PDF 與每張圖片：

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

## 發佈後驗證

- `conf-page <id> --format storage`：確認頁面是 current、title／space／parent／version 正確、含 TOC macro、16 個章節和所有 `ri:attachment` reference，且無 placeholder 或本地絕對路徑。
- `conf-page <id>`：確認 Markdown read-back 可讀、標題順序正確、表格與 code 未丟失，重要數字仍有來源。
- `/wiki/api/v2/pages/<id>/attachments?limit=250`：逐一核對 PDF／圖片 filename、media type、file size、version 與 pageId。`raw` 不會代替呼叫端自動分頁；只要回應仍有 `_links.next`／cursor，就用該 cursor 續查並累積結果，直到沒有下一頁，再做 reference、附件清單與 sidecar 的一一對應。
- 瀏覽器：確認 TOC、圖片、caption、表格、長標題與窄視窗。圖片不可只顯示 broken placeholder；caption 不可混入裁圖／上傳日誌。
- 本地轉換後：解析 storage XHTML 並再次核對唯一 TOC、無 H1、16 個 H2 的文字與順序、所有表格、公式／code block、evidence 與 PDF 來源標記、canonical link、圖片屬性與 caption，以及每個 attachment reference 恰好一次。產物含 `paper-reading-confluence` generator marker；`.storage.xhtml` 已存在時預設不覆寫，且 `--overwrite-output` 只接受含該 marker 的舊產物。
- 若沒有 UI 或權限完成某項檢查，將它列為未完成驗證；不要把「尚未檢查」寫成「通過」。

## 讀者內容邊界

頁面只保留理解、引用、評估或討論論文所需資訊。禁止寫入搜尋／下載過程、PDF signature／bytes／hash、頁碼 mapping 的操作說明、Windows 字元替換、檔案命名理由、絕對路徑、CLI／API request、認證狀態、渲染／裁圖命令、QA log 或「已檢查但無差異」的負面確認。

這些資訊不得改標成「分析」或「推測」後留在頁面。若例外 materially 影響交付，只在最後回覆簡短說明。
