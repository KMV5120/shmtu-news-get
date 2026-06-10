"""
本地 JSON 存储模块 — 记录已抓取的条目，实现差异检测
"""

import json
import time
from pathlib import Path
from typing import Optional

from config import SEEN_ITEMS_FILE


def load_seen_items() -> dict[str, str]:
    """
    加载已见条目记录

    Returns:
        {"<item_id>": "<首次发现日期>"}
    """
    path = Path(SEEN_ITEMS_FILE)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", {})
    except (json.JSONDecodeError, KeyError):
        print("[存储] seen_items.json 损坏，将重新创建")
        return {}


def save_seen_items(items: dict[str, str]):
    """保存已见条目记录"""
    path = Path(SEEN_ITEMS_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"items": items, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")},
                  f, ensure_ascii=False, indent=2)


def find_new_items(current_items: list[dict]) -> list[dict]:
    """
    比对当前抓取结果与已见记录，找出新增条目

    Args:
        current_items: 当前抓取的条目列表，每个条目需含 "id" 键

    Returns:
        新增条目列表
    """
    seen = load_seen_items()
    new_items = []

    for item in current_items:
        item_id = item.get("id", "")
        if not item_id:
            continue
        if item_id not in seen:
            new_items.append(item)
            seen[item_id] = time.strftime("%Y-%m-%d")

    if new_items:
        save_seen_items(seen)

    return new_items


def mark_as_seen(item_id: str):
    """手动标记单个条目为已见"""
    seen = load_seen_items()
    seen[item_id] = time.strftime("%Y-%m-%d")
    save_seen_items(seen)


def cleanup_old_items(days: int = 30):
    """清理 N 天前的记录，防止文件膨胀"""
    seen = load_seen_items()
    cutoff = time.time() - days * 86400

    cleaned = {}
    for item_id, date_str in seen.items():
        try:
            item_time = time.mktime(time.strptime(date_str, "%Y-%m-%d"))
            if item_time >= cutoff:
                cleaned[item_id] = date_str
        except ValueError:
            cleaned[item_id] = date_str  # 无法解析日期的保留

    removed = len(seen) - len(cleaned)
    if removed > 0:
        save_seen_items(cleaned)
        print(f"[存储] 清理了 {removed} 条 {days} 天前的记录")

    return cleaned


def get_stats() -> dict:
    """获取存储统计"""
    seen = load_seen_items()
    sections = {}
    # 这里无法直接获取 section，只能统计总数
    return {
        "total_items": len(seen),
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
