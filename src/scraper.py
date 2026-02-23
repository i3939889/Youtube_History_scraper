"""
scraper.py

核心爬蟲模組，負責：
1. 自動捲動 YouTube 歷史紀錄頁面以載入更多影片。
2. 解析影片的 URL、標題與觀看時間。
3. （預留）攔截影片的 `timedtext` (字幕) API 請求。
"""
import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import Page, Response

logger = logging.getLogger(__name__)

# --- 字幕攔截相關 ---

async def handle_response(response: Response, subtitle_store: Dict[str, Any]):
    """
    Playwright 網路請求攔截器 (Interceptor)。
    當頁面背景發送 API 請求時，會經過這裡。我們找出字幕 API 並把內容存下來。
    YouTube 的字幕 API 通常網址包含 'timedtext'。
    """
    if "timedtext" in response.url and response.request.method == "GET":
        try:
            # 確保請求成功 (HTTP 200)
            if response.status == 200:
                # 嘗試將回傳的資料解析為 JSON (YouTube 現代預設格式通常為 JSON3)
                json_data = await response.json()
                
                # 從 url 中提取 video id，以便將字幕與特定影片綁定
                # URL 範例：.../api/timedtext?v=VIDEO_ID&...
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(response.url)
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
                
                if video_id:
                    # 將字幕存進外部傳入的字典中
                    subtitle_store[video_id] = json_data
                    logger.info(f"成功攔截並儲存影片 {video_id} 的字幕資料。")
                    
        except Exception as e:
            logger.warning(f"解析字幕 API 發生錯誤：{e}")


# --- 網頁操作與解析相關 ---

async def scroll_to_load_more(page: Page, max_scrolls: int = 5):
    """
    向下捲動頁面以觸發 YouTube 的無限載入 (Infinite Scroll)。
    
    為什麼需要：
    YouTube 首屏只會顯示十幾支影片，必須捲到底部才會 AJAX 載入舊的歷史紀錄。
    
    :param page: Playwright Page 實例
    :param max_scrolls: 最大捲動次數
    """
    logger.info(f"開始向下捲動頁面，預計執行 {max_scrolls} 次。")
    for i in range(max_scrolls):
        # 捲動到頁面最底部
        await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight);")
        # 等待一小段時間讓新內容載入並渲染
        await page.wait_for_timeout(2000)
        logger.info(f"已完成第 {i + 1}/{max_scrolls} 次捲動。")


async def extract_history_items(page: Page) -> List[Dict[str, str]]:
    """
    從已經載入的觀看紀錄 DOM 樹中，提取所有影片的資訊。
    
    :param page: Playwright Page 實例
    :return: 包含影片 URL、標題等的字典列表
    """
    logger.info("開始解析觀看紀錄項目...")
    
    # YouTube 歷史紀錄現在不僅包含常規影片，也包含 Shorts
    # 我們抓取所有帶有 id="video-title" 的 a 標籤
    video_elements = await page.locator("a#video-title").all()
    
    results = []
    
    for el in video_elements:
        href = await el.get_attribute("href")
        if not href:
            continue
            
        # 嘗試取得 title 屬性，如果沒有則取得內部文字
        title = await el.get_attribute("title")
        if not title:
            title = await el.text_content()
            
        if title and href:
            # 處理相對路徑
            if href.startswith('/'):
                full_url = f"https://www.youtube.com{href}"
            else:
                full_url = href
                
            results.append({
                "title": title.strip(),
                "url": full_url
            })
            
    logger.info(f"共提取到 {len(results)} 部影片的資訊。")
    return results
