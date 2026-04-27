# Codex Handoff Notes

## 專案目標
- 使用 Python + Playwright 登入或沿用 YouTube session。
- 進入 YouTube history 頁面，捲動載入觀看紀錄。
- 擷取影片 `video_id`、標題、URL，並嘗試攔截 `timedtext` 字幕 API。
- 合併寫入 `data/output/history_dataset.json`，以 `video_id` 去重。

## 目前架構
- `main.py`: CLI 入口，支援 `--mode extract-cookie|scrape`、`--browser chrome|firefox`、`--profile`。
- `src/scraper.py`: Playwright response 攔截、歷史頁捲動、DOM 影片連結擷取。
- `src/data_handler.py`: JSON 讀寫與基本容錯。
- `src/auth.py`: storage state 讀寫 helper，目前主流程多半直接在 `main.py` 處理。
- `src/utils.py`: 目前幾乎是空檔。
- 輸出改為每日檔案：`data/output/daily/YYYY-MM-DD.json`。去重只針對當天檔案，不跨天去重。

## 已確認
- `python -m py_compile main.py src/auth.py src/scraper.py src/data_handler.py src/utils.py` 通過。
- `.gitignore` 已排除 `.env`、`data/`、SQLite、Playwright profile 等敏感或大型資料。
- `data/output/history_dataset.json` 已存在，大小約 6 KB。
- `data/session/playwright_profile` 已存在且包含瀏覽器 session/profile 資料。

## 已知風險
- VS Code 內中文與 emoji 顯示正常；PowerShell/終端輸出可能因編碼設定呈現 mojibake，不代表檔案損壞。
- Git 在目前使用者下回報 dubious ownership，需要設定 safe.directory 後才能正常查 status。
- `extract-cookie` 需要互動式登入，headless 模式不適合第一次建立 session。
- YouTube DOM selector 與 timedtext API 可能會變動，實際 scrape 需要定期驗證。
- `page.on("response", asyncio.ensure_future(...))` 的背景 task 沒有集中 await；若頁面很快關閉，可能漏收部分字幕 response。
- 字幕取得先不放在 history scrape 主流程；目前只保留被動攔截，實際字幕建議改成針對輸出的 JSON 做後處理。

## 建議下一步
1. 先設定 git safe directory，確認工作樹狀態。
2. 把 README、workspace rule、程式內中文訊息修復成可讀 UTF-8。
3. 實測 `python main.py --mode scrape --browser firefox` 或既有 session 對應 browser。
4. 若字幕很重要，補強 timedtext 擷取策略，必要時改用 `yt-dlp` 或 YouTube transcript API 作為後處理。
