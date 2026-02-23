# AI Chat Notes: 動態網頁爬取與架構選擇

這份筆記摘要了開發過程中關於 YouTube 這種高度動態更新 (AJAX / SPA) 網頁的爬取原理，以及工具選擇的討論。

## 1. 關於 `scroll_to_load_more` 與 DOM 更新機制
當腳本執行向下捲動 (`scroll_to_load_more`) 時，YouTube 會在背景觸發網路請求載入新資料，並透過底層的 JavaScript/TypeScript（如其自家的 Polymer 框架）動態改變並更新 DOM 樹，把一批批新的影片卡片自動插入到畫面上。

## 2. 為什麼 Selenium 在這部分非常難以控制？
* **StaleElementReferenceException (過期元素例外)**：Selenium 屬於早期的「同步」架構設計。當它抓取了畫面上的元素存入變數後，只要網頁的腳本稍微改變或更新了那個 DOM 節點，Selenium 手上的元素參照就會瞬間「失效」。在動態網頁中跌代這些元素非常容易造成腳本崩潰。
* **缺乏智慧等待機制**：Selenium 先天無法感知網頁背景裡面的網路請求是否已經處理完畢，開發者只能被迫使用寫死的 `sleep`，或是寫又長又脆弱的 `WebDriverWait` 條件去偵測，實作成本與出錯率都極高。

## 3. 為什麼 Playwright 處理起來非常輕鬆？
* **Auto-waiting (自動等待)**：Playwright 的設計核心是「事件驅動」與「非同步」。在執行 `locator.all()` 抓取元素時，它會自動確保元素已經掛載到 DOM 上、處於可見狀態，並且不再閃爍變動 (Stable) 才行動，不會因為抓到一半的半成品而報錯。
* **快照式的整批抓取策略**：在我們的腳本中，是選擇先捲動 N 次並等待數秒，讓 YouTube 把新影片的 DOM 都長好以後，再「一次性地」把當前畫面上所有的影片卡片給摘取下來。這樣就不必面對邊執行邊長資料的不可控狀態。
* **網路攔截能力優勢**：由於 Playwright 透過更底層的協定可以雙向溝通，它允許我們編寫 `page.on("response", ...)` 來輕鬆攔截字幕 API (timedtext) 等網頁在背後偷偷發送的請求與 JSON 回應，這在傳統的 Selenium 實作中是極難達成的。

---

## 4. 專案完成進度 (Task Tracker)
以下為截至目前的開發目標達成狀況。這份清單可幫助您在轉換（例如轉入 macOS/Ubuntu）時，清楚知道所有開發功能均已實作與測試完畢。

- [x] 專案結構與基礎建設初始配置
- [x] 準備 `requirements.txt` 與 `.env.example`
- [x] 建立 `auth.py` (儲存與載入 Playwright Cookie state.json) 
  *(註：後因繞過防護策略全面改寫整入 `main.py` 與 SQLite 無頭提取方案)*
- [x] 提供 `main.py` 的命令列介面 (支援 extract-cookie, scrape 以及 --profile)
- [x] 實作 `scraper.py`：攔截 YouTube 字幕 API 請求
- [x] 實作 `scraper.py`：解析 YouTube 觀看紀錄 DOM 並向下捲動
- [x] 實作 `scraper.py`：整合 URL、觀看時間與攔截到的字幕內容
- [x] 實作 `data_handler.py`：儲存整合好之資料為 JSON 格式並具備防重 (Deduplication) 機制
- [x] 新增 `Firefox` 本機 Cookie SQLite 解密與提取支援 (準備供 Ubuntu 遠端無頭使用)
- [x] SSH 佈署與 Ubuntu 24.04 遠端測試 (本方案的 state.json 支援異地伺服器無縫運作)
