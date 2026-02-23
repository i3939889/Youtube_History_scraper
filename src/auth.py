"""
auth.py

負責 YouTube 的登入與 Cookie 處理。
提供保存當前登入狀態至本地檔案，以及從本地檔案載入狀態的功能。
"""
import os
import logging
from typing import Optional
from playwright.async_api import BrowserContext

# 設定基本的 logging 格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def save_cookie(context: BrowserContext, path: str) -> None:
    """
    將目前的 BrowserContext 狀態（包含 Cookies、Local Storage 等）保存到指定的 JSON 檔案中。
    
    為什麼需要這個：
    YouTube 登入流程可能會有圖形驗證碼或雙重驗證。如果我們能手動登入一次並把狀態存下來，
    之後的自動化程式就可以直接掛載這個狀態，達到「免互動登入」的效果。
    
    :param context: Playwright 的 BrowserContext 物件
    :param path: 狀態檔要存放的目的地路徑
    """
    try:
        # 確保目標資料夾存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Playwright 內建方法，直接把整個 context 的 state 拿出來存
        await context.storage_state(path=path)
        logger.info(f"成功保存登入狀態至：{path}")
    except Exception as e:
        logger.error(f"保存登入狀態時發生錯誤：{e}")
        raise

async def load_cookie_context(browser, path: str) -> Optional[BrowserContext]:
    """
    嘗試從指定的 JSON 檔案中讀取先前的登入狀態，並實例化一個新的 BrowserContext。
    
    為什麼需要這個：
    讓自動化程式能夠利用之前存好的 Session 狀態，繞過繁瑣的登入步驟。
    
    :param browser: Playwright 的 Browser 實例
    :param path: 先前保存的狀態檔路徑
    :return: 帶有登入狀態的 BrowserContext；如果檔案不存在，則回傳 None
    """
    if not os.path.exists(path):
        logger.warning(f"找不到指定的狀態檔案：{path}，將無法以登入狀態啟動。")
        return None
        
    try:
        context = await browser.new_context(storage_state=path)
        logger.info(f"成功從 {path} 載入登入狀態。")
        return context
    except Exception as e:
        logger.error(f"載入登入狀態時發生錯誤：{e}")
        raise
