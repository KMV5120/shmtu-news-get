"""
上海海事大学数字平台监控系统 — 配置文件

所有敏感信息请填入 config.json，本文件只读 JSON。
"""

import json
import os
from pathlib import Path


def _load_json():
    json_path = Path(__file__).parent / "config.json"
    if not json_path.exists():
        raise FileNotFoundError(
            f"配置文件 {json_path} 不存在！\n"
            "请复制 config.json.example 为 config.json 并填入你的信息。"
        )
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


_cfg = _load_json()

# ============================================================
# 认证信息（从 config.json 读取，环境变量优先）
# ============================================================
USERNAME = os.getenv("SHMTU_USERNAME", _cfg.get("username", ""))
PASSWORD = os.getenv("SHMTU_PASSWORD", _cfg.get("password", ""))
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", _cfg.get("pushplus_token", ""))
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", _cfg.get("deepseek_api_key", ""))

# ============================================================
# CAS 认证 URL
# ============================================================
CAS_LOGIN_URL = "https://cas.shmtu.edu.cn/cas/login"
CAS_CAPTCHA_URL = "https://cas.shmtu.edu.cn/cas/captcha"
PORTAL_SERVICE = "https://my.shmtu.edu.cn/sopcb/"

# ============================================================
# 监控栏目配置
# ============================================================
SECTIONS = [
    {"name": "部门通知公告"},
    {"name": "部门动态"},
    {"name": "学术与活动"},
    {"name": "教务公告"},
    {"name": "全校文件下载"},
    {"name": "学院要闻"},
    {"name": "学院新闻"},
    {"name": "通知公告"},
    {"name": "讲座活动"},
    {"name": "图片要闻"},
    {"name": "新闻动态"},
    {"name": "学术活动"},
    {"name": "科创竞赛"},
    {"name": "学生天地"},
]

# ============================================================
# 文件路径
# ============================================================
SESSION_FILE = "session.pkl"
SEEN_ITEMS_FILE = "seen_items.json"

# ============================================================
# 推送选项
# ============================================================
MAX_ITEMS_PER_SECTION = 10

# ============================================================
# 请求配置
# ============================================================
REQUEST_TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ============================================================
# 浏览器配置（可指定系统 Edge 路径，省去 Playwright Chromium 下载）
# ============================================================
CHROMIUM_EXECUTABLE = os.getenv("CHROMIUM_EXECUTABLE", _cfg.get("chromium_executable", "")) or None
