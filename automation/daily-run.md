# 每日論文閱讀執行契約

此檔案是本機 Codex project cron 的執行契約。初次啟用排程前，`automation/daily-reading.json` 應至少有一個啟用主題、GitHub `origin` 與 Pages 應可用，且 Teams 目的地應在被 `.gitignore` 排除的 `automation/daily-reading.local.json` 設定完成。排程建立後，每次執行都要先 reconciliation；即使主題後來停用或本日沒有新論文，也不可略過 pending publication。

## 1. 啟動與必要 reconciliation

1. 從專案根目錄開始，讀取 `AGENTS.md`、`.agents/skills/paper-reading/SKILL.md`、該 Skill 要求的 `references/paper-reading-standard.md`、`automation/daily-reading.json`、`automation/daily-reading.local.json` 與本檔。
2. **每次啟動都必須先 reconciliation，之後才能 discovery。** 掃描被 Git 忽略的 `automation/state/publications/*.json`，依 `createdAt`、完整 commit SHA 排序，逐筆處理所有 `overallStatus != "completed"` 的紀錄。此步驟不受 `topics` 是否為空、今日是否已有候選論文或工作樹是否有使用者變更影響。
3. publication record 的固定路徑為 `automation/state/publications/<full-commit-sha>--<destination-key>.json`。`destination-key` 是對 canonical `{destinationType, destinationId}` 做 SHA-256 所得的小寫十六進位值；record identity、Teams `idempotencyMarker`（`paper-reading/<full-commit-sha>/<destination-key>`）與通知本文在第一次寫入後不得改變。目的地原值可留在這個 Git-ignored record 供復原，但不得出現在檔名、log、commit 或網站。
4. record 至少保存：schema version、完整 commit SHA、remote、branch、建立時間、目的地與 destination key、固定通知本文/連結及其雜湊、`push.status`、`pages.status`、Pages workflow/deployment ID、`teams.status`、Teams message ID、各次查證結果與 `overallStatus`。狀態寫入一律先寫同目錄暫存檔再原子 replace，避免中斷後留下半份 JSON。
5. 對每筆 pending record 依序執行：
   - `push.status` 尚未確認時，先查 remote branch 是否已包含該完整 SHA；已存在就標記 `confirmed`。只有確認 remote 不存在且本機 commit 仍可用時才能 push 一次，之後再查 remote；逾時或結果不確定不得盲目再次 push。
   - 查詢**該 commit SHA 對應**的 Pages workflow 與 deployment，而非只看最新一次 run。若仍 queued/in progress 就等待；若 API/CLI 結果不確定就重新查狀態，不觸發另一個 build、不重新 push。只有 workflow/deployment 成功且首頁及 record 中的摘要 URL 可開啟，才把 `pages.status` 標成 `succeeded`。明確失敗則保存 run/deployment ID 與 failure observation，維持 pending 並停止進入 discovery。
   - Pages 已成功但 `teams.status` 尚未確定為 `sent` 時，先在 record 指定的固定目的地讀取/搜尋完全相同的 `idempotencyMarker`。找到就保存既有 message ID 並標成 `sent`；確認不存在後才能傳送 record 中凍結的本文一次。若傳送逾時或回應不確定，標成 `attemptUncertain`，下次先查訊息，不可直接重送；收到明確成功回應後立刻落盤 message ID 與 `sentAt`。
   - 只有 push、Pages 與 Teams 三者皆確認成功，才把 `overallStatus` 原子更新為 `completed`。completed record 永不重送通知。
6. 所有 pending record 都完成後，才做本日 discovery 的前置檢查。若任何 record 因部署失敗、權限、網路或無法確認的狀態仍 pending，保留紀錄並停止本次執行；不得先建立下一個 publication commit。
7. 此時若沒有啟用主題、缺少 `origin`、GitHub 或 Teams 尚未登入、或缺少 local 設定，安全結束並指出缺少項目；不得自行發明主題或收件人。即使因此不進行 discovery，前面的 reconciliation 仍已執行。
8. 執行 `git status --porcelain`。若有非本次排程建立的變更，不得覆蓋、stash、reset、clean 或提交它們；安全結束並回報。Git-ignored publication records 不算工作樹污染。
9. 以 fast-forward-only 方式同步預設分支。遇到分歧、衝突或無法同步時停止；不得 force push。

## 2. 探索與選稿

1. 依每個啟用主題的 `queries` 搜尋設定回溯期間內的新論文，優先作者頁、arXiv、OpenReview、正式會議／期刊及出版社等第一方來源。
2. 交叉核對正式標題、完整作者、abstract、日期、venue、canonical landing page 與全文 URL；依設定的必要條件與偏好排序。
3. 以 DOI、arXiv ID、正規化標題及既有 `summary.html` 去重。查詢主題只是 discovery filter，不是資料夾 Topic/Subtopic；分類必須逐篇依主要技術貢獻判斷。
4. 整次執行最多完成 `selection.dailyMaxPapers` 篇。若沒有新的合格論文，不建立空白 commit、不建立新的 publication record，也不發送新的成功通知；但啟動時仍須完成第 1 節的 reconciliation。若 reconciliation 補送一筆先前確定尚未送達的 pending 通知，那是舊 commit 的唯一通知，不是本日 no-op 通知。

## 3. 深讀與驗證

1. 對選定論文逐篇完整執行 paper-reading Skill：下載並驗證 PDF、建立 evidence ledger、完成定位／方法／證據／批判／完整性閱讀迴圈、擷取必要圖表，並從完整模板建立繁體中文 `summary.html`。
2. 保留固定 16 章、來源標記與主張類型；不得只讀 abstract，也不得把工作日誌或工具錯誤寫進摘要。
3. 執行 Skill 指定的 `validate-summary.ps1`，再做桌面與窄螢幕視覺 QA。任何必要驗證失敗都不得提交。
4. 執行 `python scripts/build_site.py --check`，確認站台能從已追蹤內容建置，且 Pages artifact 不含 PDF、憑證、`.agents` 或內部設定。

## 4. 提交、部署與通知

1. 僅 stage 本次新增或更新的論文摘要、必要圖片與自動化 catalog；不得使用 `git add -A`，不得順帶提交使用者的其他變更。PDF 是本機研究輸入，不加入 Git。
2. 使用 `papers: add YYYY-MM-DD daily reading` 形式的 commit message 建立 commit。取得完整 SHA 後，先依第 1 節的 deterministic 路徑建立 publication record：凍結 remote/branch、目的地、首頁與各摘要 URL、日期、新增篇數、主題、通知本文及 `idempotencyMarker`；初始狀態為 `push.status = "prepared"`、`pages.status = "pending"`、`teams.status = "pending"`、`overallStatus = "pending"`。record 必須在 push **之前**原子落盤。
3. push 到預設分支且不得 force push。push 回報成功後仍要查 remote 是否包含完整 SHA，確認後立即把 `push.status = "confirmed"` 原子落盤；若 push 回應逾時，也先查 remote 再決定，不可直接重送。
4. 其後直接對這筆 record 執行第 1 節相同的 reconciliation：查該 SHA 的 Pages deployment、確認 URL readiness、查 Teams marker、必要時傳送一次，最後標成 completed。不得另走一套沒有狀態紀錄的臨時通知流程。
5. process 在 commit、push、deployment 或傳送後的任何位置中斷都保留 pending record；下一個排程必須先恢復它。`automation/state/` 永遠不得 stage、commit、複製到 Pages artifact 或當作摘要內容。

## 5. 失敗邊界

任何驗證、同步、push、部署或權限問題都必須保留原始檔案與 publication record 的最後已確認狀態，不得 reset、clean、刪除既有內容或強推。未知結果只能記為 unknown/attemptUncertain，不能推定失敗後重做。只有 `notifyOnFailure` 啟用且 Teams 目的地已明確驗證時，才傳送簡短失敗警示；警示也必須使用獨立的 deterministic marker 防重複，且不得宣稱 Pages 已更新。
