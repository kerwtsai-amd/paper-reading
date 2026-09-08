# Paper Reading

這個 repository 用來把論文探索、深度閱讀與繁體中文 HTML 摘要整理成可瀏覽的研究網站。每篇論文仍依專案規則放在 `<Topic>/<Subtopic>/<Formal Paper Title>/`，摘要由 `html template/summary-template.html` 產生並通過 paper-reading Skill 的驗證。

## 自動化架構

整體流程刻意分成三段，讓論文處理、網站部署與通知各自有清楚的責任邊界：

1. **本機 Codex project cron**：每天在此 project 的實際 checkout 執行，讀取 `automation/daily-reading.json`，依啟用主題搜尋候選論文、品質篩選及去重；再依 `.agents/skills/paper-reading/SKILL.md` 完整閱讀，建立分類、摘要與必要圖表，驗證後才 commit 並 push。
2. **GitHub Actions / Pages**：push 到預設分支後，由 repository 內的 Pages workflow 建置可公開瀏覽的靜態網站並部署。這一段只處理已提交的網站來源，不負責搜尋或閱讀論文。
3. **本機 Teams 通知**：Codex cron 在 push 後等待 GitHub Pages deployment 成功，再透過本機 `m365-teams` Skill 把本次新增摘要的 Pages 連結送到指定 chat/channel。Teams 登入資訊只留在本機，不交給 GitHub Actions。

```text
每日 Codex cron（本機）
  └─ 搜尋 → 深讀 → 驗證 → commit/push
                         └─ GitHub Actions → Pages deploy
                                                   └─ 成功後由本機 m365-teams 通知
```

每次排程一啟動，都會先恢復先前已 commit/push、但 Pages 或 Teams 尚未確認完成的工作，全部 reconciliation 完成後才搜尋新論文。若當天找不到符合條件且未讀過的論文，仍會完成這項復原檢查，但不建立空白 commit 或新的 publication record，也不發送新的「成功新增」通知；先前 pending commit 若確認尚未通知，則只會補送一次。

## 每日閱讀設定

設定檔是 [`automation/daily-reading.json`](automation/daily-reading.json)。目前 `topics` 為空，因此不會臆測或啟用任何研究主題；加入至少一個 `enabled: true` 的主題後，自動閱讀才會選稿。

完整的安全檢查、選稿、驗證、精準 stage、Pages readiness、crash recovery 與 Teams 防重複通知規則，集中在 [`automation/daily-run.md`](automation/daily-run.md)。Teams 目的地請從 [`automation/daily-reading.local.example.json`](automation/daily-reading.local.example.json) 建立本機的 `automation/daily-reading.local.json`；實際檔案已被 Git 忽略。

每次 publication commit 會在 push 前建立 `automation/state/publications/<commit-sha>--<destination-key>.json`，並在 push、deploy、通知確認後原子更新。這個 Git-ignored record 使用完整 SHA 與目的地雜湊作為固定身份，通知中也帶有 deterministic marker；遇到逾時時，下一次排程會先查 remote、該 SHA 的 Pages deployment 及 Teams 既有訊息，而不是盲目重推、重建或重送。只有三段都確認成功才標成 completed，且 completed record 不再通知。

每個 `topics` 項目支援：

| 欄位 | 用途 |
| --- | --- |
| `id` | 穩定、唯一的機器識別碼；建議用小寫英數與連字號。 |
| `name` | 顯示在執行紀錄中的主題名稱。 |
| `enabled` | 是否納入當日搜尋。 |
| `queries` | 一或多組搜尋詞；同主題的候選結果會合併後去重。 |
| `excludeTerms` | 標題或 abstract 命中時排除的詞。 |

可加入的主題物件格式如下（尖括號內容需自行替換）：

```json
{
  "id": "<topic-id>",
  "name": "<主題名稱>",
  "enabled": true,
  "queries": ["<查詢詞一>", "<查詢詞二>"],
  "excludeTerms": ["<排除詞>"]
}
```

全域選稿規則：

- `selection.dailyMaxPapers`：整次執行最多完成幾篇，預設為 `1`；是所有主題合計，不是每個主題各一篇。
- `selection.lookback.days`：候選論文回溯天數，預設為 `7`；以 `submittedOrPublished` 日期判定。
- `quality`：要求 canonical landing page、可取得全文、完整作者與 abstract，並優先採第一方來源。`preferPeerReviewed` 是排序偏好，不會硬性排除新近 preprint。
- `deduplication`：依 DOI、arXiv ID、正規化標題依序比對；同時掃描既有摘要並略過已處理論文。

主題適合直接提交到版本控制，但 token、cookie、Teams chat/channel ID、私人 webhook 或其他憑證不屬於此設定檔。通知目的地與登入狀態應由本機 automation/Skill 的安全儲存提供。

## 啟用每日流程

在 git remote、GitHub Pages workflow 與 Pages URL 都設定完成後，再於 Codex 建立 project cron。建議排程使用 `Asia/Taipei` 每天早上執行，prompt 至少應要求：

- 先讀取本 repository 的 `AGENTS.md`、paper-reading Skill 與 `automation/daily-reading.json`。
- `topics` 為空或沒有啟用項目時安全結束，不自行發明主題。
- 先搜尋、交叉核對來源、依品質與去重規則選出不超過 `dailyMaxPapers` 的論文。
- 每篇都完成全文深讀、分類、模板摘要、圖片/表格擷取與驗證；不得只依 abstract 產生摘要。
- 只提交本次產生且通過驗證的網站內容；同步遠端變更後再 push，遇到衝突或失敗不要強推。
- push 後確認對應 GitHub Pages deployment 成功，才以本機 `m365-teams` 傳送可開啟的摘要 URL；deployment 失敗時不要傳送失效連結。
- 每次都先 reconciliation 所有 Git-ignored pending publication records；結果不確定時先查 deployment 或 Teams marker，確認完成後才進入本日 discovery。

排程本身與 Teams 目標屬於本機 Codex 設定，不由 repository 內檔案自動建立。這也避免把公司帳號資訊寫進 git history。

## 安全與發佈邊界

- **不發佈 PDF**：`.gitignore` 排除所有 `*.pdf`。論文 PDF 僅供本機閱讀；GitHub Pages artifact 也不可另行複製 PDF。摘要可連到 canonical publisher/arXiv 頁面，但不應假設本地 PDF 連結在網站上可用。
- **不提交秘密**：不要 commit access token、cookie、webhook、Teams 對話識別碼或含秘密的 `.env` / local override；如果秘密曾經進入 commit，僅刪除目前檔案並不足夠，還必須撤銷並輪替該憑證。
- **Public Pages 不是存取控制**：公開 GitHub Pages 上的 HTML、圖片與 metadata 都應視為任何人可讀。不要放入 AMD 機密、受 NDA 約束的內容、個資或不可公開的研究筆記；robots 設定、難猜 URL 或未列在首頁都不是權限機制。
- **尊重授權**：摘要與必要引用應維持轉述及來源追溯；圖片/表格是否能公開仍須依原論文授權與合理使用情境判斷。
