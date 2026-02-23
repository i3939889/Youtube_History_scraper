"""
data_handler.py

負責將爬取到的資料儲存為 JSON 格式。
"""
import json
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def load_existing_json(filepath: str) -> List[Dict[str, Any]]:
    """
    從現有的 JSON 檔案中載入資料，用來比對避免重複抓取。
    
    :param filepath: JSON 檔案路徑
    :return: 現存的資料列表；如果檔案不存在或格式錯誤，則回傳空列表
    """
    if not os.path.exists(filepath):
        return []
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                logger.warning(f"檔案 {filepath} 格式非預期（非 List），將以空列表初始化。")
                return []
    except Exception as e:
        logger.warning(f"讀取 {filepath} 失敗：{e}，將以空列表初始化。")
        return []

def save_to_json(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    將資料列表儲存為 JSON 檔案。
    
    :param data: 要儲存的資料串列 (包含影片標題、URL、字幕等)
    :param filepath: 輸出的檔案路徑
    """
    try:
        # 確保輸出目錄存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 以 UTF-8 寫入 JSON，ensure_ascii=False 確保中文字元正確顯示
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        logger.info(f"✅ 資料已成功儲存至 {filepath} (共 {len(data)} 筆紀錄)。")
    except Exception as e:
        logger.error(f"❌ 儲存 JSON 檔案時發生錯誤：{e}")
        raise
