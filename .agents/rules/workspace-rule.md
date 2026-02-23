---
trigger: always_on
---

# YouTube History Scraper - Workspace Rules

## 1. 專案目標與範圍 (Project Goals & Scope)
- **核心目標**: 自動化登入 YouTube 並抓取使用者的觀看紀錄，提取影片 URL 及對應的字幕檔。
- **產出格式**: 將抓取到的資料（包含 URL、字幕檔、觀看時間）存入 JSON 檔案中，以提供給其他程式進行後續處理。
- **輸入方式**: 支援使用「帳號密碼」模擬登入，或直接載入「Cookie」進行身分驗證。

## 2. 執行環境與基礎建設 (Environment & Infrastructure)
- **開發環境**: Windows 或 macOS 本地開發。
- **測試與生產環境**: 遠端 Ubuntu 24.04 伺服器，採 SSH 連線部署與執行。
- **自動化工具**: 建議使用 Playwright 作為瀏覽器自動化方案，因其對非同步與網路請求攔截支援良好。
- **組態管理**: 使用 `python-dotenv` 讀取 `.env` 檔來管理敏感資訊 (如：登入帳密、Cookie 路徑等)。
- **資料儲存**: JSON（內建模組）。

## 3. 開發規範 (Development Standards)
專案應嚴格遵循以下核心原則：

### 3.1. 簡潔原則與不重工 (KISS & DRY)
- 保持邏輯單純，避免過度設計。
- 提取重複的邏輯進入共用的輔助函式（Helper functions）。

### 3.2. 現代語法與型別安全 (Modern Syntax & Type Safety)
- 全面使用 Python Type Hints（例如 `List`, `Dict`, `Optional` 等），確保變數和回傳值型別清晰。
- 善用 Python 最新穩定版語法（如 Dataclasses, Match-Case 等）。

### 3.3. 穩健的錯誤處理 (Error Handling)
- 絕對不可靜默吞噬任何異常（Never swallow errors silently）。發生預期外狀況時必須記錄並提供具意義的錯誤訊息。
- 針對網路請求、元素截取以及檔案讀寫，須有明確的例外處理 (Targeted exception handling)。

### 3.4. 註解與文件規範 (Documentation Standards)
- **語言規定**: 所有程式碼註解、說明文件與 Docstrings 均須使用 **繁體中文（台灣）**。
- **Docstrings 原則**: 所有的 Public functions 和 Classes 必須具備簡短的說明，解釋其輸入、輸出及副作用。
- **說明動機**: 註解應解釋「為什麼（Why）」做此決策，而非翻譯程式碼在做「什麼（What）」。

## 4. Git Commit 規範 (Git Commit Standards)
依循 **Conventional Commits** 規範：
- `feat: ` 新增功能
- `fix: ` 修復 Bug
- `docs: ` 文件更動
- `refactor: ` 重構（不新增功能且不修 Bug 的程式碼變動）
- `chore: ` 建置程序或輔助工具變動
**格式**: `<type>(<scope>): <subject>`

## 5. 目錄結構建議 (Suggested Directory Structure)
```text
.
├── src/                 # 核心原始碼
│   ├── scraper.py       # 網頁爬取與交互邏輯
│   ├── auth.py          # 負責登入與 Cookie 處理
│   ├── data_handler.py  # 負責 JSON 資料的讀寫處理
│   └── utils.py         # 共用輔助函式
├── data/                # 輸出與憑證存放目錄 (應加入 .gitignore)
│   ├── output/          # 產出的 JSON 檔存放處
│   └── session/         # 登入後的 Cookie 存放處
├── doc.agent/           # 專案相關文件
│   ├── goal.txt
│   └── workspace-rule.md
├── requirements.txt     # 套件依賴清單
├── .env.example         # 環境變數範例檔
└── main.py              # 專案執行入口
```
