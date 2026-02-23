"""
main.py

專案執行入口。
提供兩種模式：
1. 提取模式 (extract-cookie)：手動登入 YouTube 並存下 state.json。
2. 爬取模式 (scrape)：載入已存檔的 state.json，自動獲取觀看紀錄。
"""
import os
import sys
import json
import sqlite3
import shutil
import asyncio
import argparse

# 強制將 Windows 終端機輸出設為 UTF-8，避免 emoji 報錯 (cp950)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from src.scraper import handle_response, scroll_to_load_more, extract_history_items
from src.data_handler import save_to_json, load_existing_json

# 載入 .env 變數
load_dotenv()

async def _extract_firefox_cookie(session_dir: str):
    """提取 Firefox 本機 Cookie"""
    # Firefox 較難繞過自動化偵測，這裡改採直接讀取本機 Firefox 的 cookies.sqlite
    print("啟動 Firefox Cookie 提取模式... 準備讀取您的本機 Firefox 登入狀態。")
    print("⚠️ 執行前，請確保您已經「完全關閉」了 Firefox 視窗！")
    input("👉 確認已關閉後，按下 Enter 鍵繼續...")
    
    appdata = os.getenv('APPDATA')
    if not appdata:
        print("❌ 找不到 APPDATA 環境變數。")
        return
        
    firefox_profiles_dir = os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles')
    if not os.path.exists(firefox_profiles_dir):
        print(f"❌ 找不到 Firefox 使用者資料夾：{firefox_profiles_dir}")
        return
        
    # 尋找有 youtube cookies 的目錄
    target_db = None
    for p in os.listdir(firefox_profiles_dir):
        if p.endswith('.default-release') or p.endswith('.default'):
            db_path = os.path.join(firefox_profiles_dir, p, 'cookies.sqlite')
            if os.path.exists(db_path):
                target_db = db_path
                break
                
    if not target_db:
        print("❌ 找不到 Firefox 的 Cookie 資料庫 (cookies.sqlite)。")
        return
        
    # 為了避免鎖定問題，複製一份暫時的 db 來讀取
    temp_db = "temp_cookies.sqlite"
    try:
        shutil.copy2(target_db, temp_db)
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT name, value, host, path, expiry, isSecure, isHttpOnly FROM moz_cookies WHERE host LIKE '%youtube.com%'")
        rows = cur.fetchall()
        
        if not rows:
            print("❌ 在您的 Firefox 中找不到任何 YouTube 的 Cookie。請先透過一般的 Firefox 開啟 YouTube 並登入一次。")
            return
            
        import time
        current_time = int(time.time())
        
        pw_cookies = []
        for r in rows:
            # 確保 expires 是一個合理的 UNIX timestamp (秒)，過大的值 Playwright 不收
            expiry = r[4]
            if not expiry or expiry < 0 or expiry > current_time + 10 * 365 * 86400:
                expiry = -1
            else:
                expiry = int(expiry)
                
            pw_cookies.append({
                "name": r[0],
                "value": r[1],
                "domain": r[2],
                "path": r[3],
                "expires": expiry,
                "httpOnly": bool(r[6]),
                "secure": bool(r[5]),
                "sameSite": "Lax"
            })
            
        state_data = {
            "cookies": pw_cookies,
            "origins": []
        }
        
        # 手動創建一個 profile 目錄與 Default/state.json 來讓後續的 scrape 模式能讀到
        os.makedirs(os.path.join(session_dir, "Default"), exist_ok=True)
        with open(os.path.join(session_dir, "Default", "state.json"), "w", encoding="utf-8") as f:
            json.dump(state_data, f)
            
        print(f"✅ 成功從本機 Firefox 提取 {len(rows)} 筆 YouTube Cookies 至：{session_dir}")
        
    except Exception as e:
        print(f"❌ 提取 Firefox Cookie 時發生錯誤：{e}")
    finally:
        if 'conn' in locals():
            conn.close()
        if os.path.exists(temp_db):
            os.remove(temp_db)

async def _extract_chrome_cookie(session_dir: str, headless: bool):
    """提取 Chrome Cookie"""
    print("啟動登入模式... 請在彈出的瀏覽器中手動登入 YouTube。")
    print("⚠️ 這是專屬於爬蟲的獨立瀏覽器，您只需要在這裡登入一次。")
    
    # 確保儲存 profile 的資料夾存在
    os.makedirs(session_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser_launcher = p.chromium
        launch_kwargs = {
            "channel": "chrome",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
        }
            
        # 使用 launch_persistent_context 啟動，所有紀錄（Cookie, LocalStorage 等）會自動存入 session_dir
        context = await browser_launcher.launch_persistent_context(
            user_data_dir=session_dir,
            headless=headless,
            **launch_kwargs
        )
        
        page = await context.new_page()
        await page.goto("https://www.youtube.com")
        
        # 阻塞等待用戶手動登入
        input("👉 登入完成後，按下 Enter 鍵關閉瀏覽器並儲存狀態...")
        
        await context.close()
        print(f"✅ 登入狀態已永久保存至：{session_dir}，後續可直接使用自動爬取模式。")

async def run_extract_cookie_mode(session_dir: str, headless: bool, browser_type: str = "chrome"):
    """
    新建一個獨立的瀏覽器設定檔讓使用者手動登入 YouTube。
    下次程式執行時，只要載入同一個設定檔，就會持續保持登入狀態。
    """
    if browser_type == "firefox":
        await _extract_firefox_cookie(session_dir)
    else:
        await _extract_chrome_cookie(session_dir, headless)

async def run_scrape_mode(session_dir: str, headless: bool, browser_type: str = "chrome"):
    """
    載入專屬的瀏覽器設定檔，以登入狀態啟動爬蟲邏輯。
    """
    print("啟動自動爬取模式...")
    
    async with async_playwright() as p:
        if browser_type == "firefox":
            # Firefox 使用剛剛我們轉換出的 state.json
            browser = await p.firefox.launch(headless=headless)
            state_path = os.path.join(session_dir, "Default", "state.json")
            if not os.path.exists(state_path):
                print("❌ 找不到 Firefox 的狀態檔，請先執行 `--mode extract-cookie --browser firefox`。")
                await browser.close()
                return
            context = await browser.new_context(storage_state=state_path)
        else:
            if not os.path.exists(session_dir) or not os.listdir(session_dir):
                print("❌ 找不到登入狀態，請先執行 `--mode extract-cookie` 進行手動登入。")
                return
                
            browser_launcher = p.chromium
            launch_kwargs = {
                "channel": "chrome",
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars"
                ]
            }
            
            # 直接掛載剛剛存好登入狀態的 profile 資料夾
            context = await browser_launcher.launch_persistent_context(
                user_data_dir=session_dir,
                headless=headless,
                **launch_kwargs
            )

            
        page = await context.new_page()
        
        # 建立一個字典來集中管理攔截下來的字幕資料 (key: video_id, value: json subtitle)
        subtitle_store = {}
        
        # 綁定網路攔截器：當網頁背景發送 response，就會觸發 handle_response
        page.on("response", lambda response: asyncio.ensure_future(
            handle_response(response, subtitle_store)
        ))
        
        print(f"👉 正在前往 YouTube 歷史紀錄頁面...")
        await page.goto("https://www.youtube.com/feed/history")
        
        print("✅ 成功進入歷史紀錄頁面！開始載入舊紀錄並持續攔截字幕...")
        
        # 向下捲動 5 次以獲得更多影片
        await scroll_to_load_more(page, max_scrolls=5)
        
        # 解析 DOM，獲取影片標題跟網址
        history_videos = await extract_history_items(page)
        
        # 準備輸出儲存路徑
        from urllib.parse import urlparse, parse_qs
        output_path = os.path.join(os.getcwd(), "data", "output", "history_dataset.json")
        
        # 載入現存的資料庫以防止重複抓取
        existing_data = load_existing_json(output_path)
        existing_video_ids = {item.get('video_id') for item in existing_data if item.get('video_id')}
        print(f"📦 目前本地資料庫已存有 {len(existing_video_ids)} 筆歷史紀錄。")
        
        # 將攔截到的字幕資料，對應合併到歷史紀錄中
        new_records = []
        for v in history_videos:
            video_url = v.get("url", "")
            parsed_url = urlparse(video_url)
            
            video_id = None
            # 常規影片: https://www.youtube.com/watch?v=VIDEO_ID
            if 'v' in parse_qs(parsed_url.query):
                video_id = parse_qs(parsed_url.query)['v'][0]
            # Shorts: https://www.youtube.com/shorts/VIDEO_ID
            elif '/shorts/' in parsed_url.path:
                video_id = parsed_url.path.split('/shorts/')[-1].split('/')[0]
                
            if not video_id:
                continue
                
            # 💡 防重複機制：因為觀看紀錄是從新到舊排序的，
            # 當我們遇到早就存過的 video_id，可以選擇跳過或是直接當作爬取界線。
            # 這裡我們採取安全的「遇到重複的就跳過不加入」策略
            if video_id in existing_video_ids:
                continue
            
            # 如果攔截的清單裡剛好有這部影片的字幕，就塞進去
            subtitle_data = subtitle_store.get(video_id) if video_id else None
            
            new_records.append({
                "video_id": video_id,
                "title": v.get("title"),
                "url": video_url,
                "subtitle": subtitle_data
            })
            
            # 加入已存在的集合中，防止我們自己這次捲動抓到重複的 DOM 元素
            existing_video_ids.add(video_id)
            
        if new_records:
            # 把新的紀錄插在最前面 (保持時間從新到舊)
            merged_results = new_records + existing_data
            save_to_json(merged_results, output_path)
            print(f"🎉 爬取結束！成功新增 {len(new_records)} 筆紀錄，其中攔截到 {len(subtitle_store)} 筆字幕。目前總收錄：{len(merged_results)} 筆。")
        else:
            print("✨ 爬取結束！沒有發現新的歷史紀錄，無須更新 JSON。")
        await context.close()

def main():
    parser = argparse.ArgumentParser(description="YouTube History Scraper")
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["extract-cookie", "scrape"], 
        default="scrape",
        help="執行模式。'extract-cookie' 用於手動保存登入狀態，'scrape' 用於自動抓取資料。"
    )
    
    parser.add_argument(
        "--browser",
        type=str,
        choices=["chrome", "firefox"],
        default="chrome",
        help="使用的瀏覽器引擎，可選 chrome 或 firefox。"
    )
    
    args = parser.parse_args()
    
    # 用資料夾來放 persistent profile
    session_dir = os.path.join(os.getcwd(), "data", "session", "playwright_profile")
    headless_env = os.getenv("HEADLESS", "False").lower() == "true"
    
    # 如果是登入模式，強制開啟瀏覽器介面
    headless = False if args.mode == "extract-cookie" else headless_env

    # 根據不同模式呼叫對應的非同步函式
    if args.mode == "extract-cookie":
        asyncio.run(run_extract_cookie_mode(session_dir, headless, args.browser))
    else:
        asyncio.run(run_scrape_mode(session_dir, headless, args.browser))

if __name__ == "__main__":
    main()
