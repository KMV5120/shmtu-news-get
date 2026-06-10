"""
PushPlus 微信推送模块

使用 PushPlus API 向微信发送消息。
首次使用：
  1. 微信关注公众号 "pushplus 推送加"
  2. 访问 www.pushplus.plus 获取 token
  3. 填入 config.py 的 PUSHPLUS_TOKEN
"""

import time

import requests

from config import PUSHPLUS_TOKEN, REQUEST_TIMEOUT

PUSHPLUS_SEND_URL = "http://www.pushplus.plus/send"


def send_daily_report(all_items: list[dict], new_count: int = 0) -> bool:
    """
    发送每日概览（展示所有文章，标注新增）

    Args:
        all_items: 本次所有抓取的条目
        new_count: 新增条目数量
    """
    if not all_items:
        print("[推送] 无内容，跳过")
        return True

    today = time.strftime("%Y-%m-%d")
    title = f"📋 数字平台日报 — {today}"

    grouped = _group_by_section(all_items)
    content = _build_markdown(today, grouped, len(all_items), new_count)

    return _push(title, content)


def send_test_message() -> bool:
    title = "🧪 数字平台监控 — 测试消息"
    content = f"### 测试成功！\n\n- 发送时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n- 推送通道：PushPlus 微信\n\n如果你收到这条消息，说明配置正确。"
    return _push(title, content)


def send_error_alert(error_message: str) -> bool:
    title = "⚠️ 数字平台监控 — 运行异常"
    content = f"## 脚本运行出错\n\n```\n{error_message}\n```\n\n请检查脚本状态。"
    return _push(title, content)


def _group_by_section(items: list[dict]) -> dict[str, list[dict]]:
    grouped = {}
    for item in items:
        section = item.get("section", "其他")
        grouped.setdefault(section, []).append(item)
    return grouped


def _build_markdown(date: str, grouped: dict[str, list[dict]],
                    total: int, new_count: int) -> str:
    lines = [
        f"# 📋 数字平台日报 {date}",
        "",
    ]
    if new_count > 0:
        lines.append(f"🔴 新增 {new_count} 条 | 📊 共 {total} 条")
    else:
        lines.append(f"📊 共 {total} 条")
    lines.append("")

    for section, items in grouped.items():
        lines.append(f"## {section}（{len(items)} 条）")
        lines.append("")
        for item in items:
            title = item.get("title", "无标题")
            date_str = item.get("date", "")
            summary = item.get("summary", "")

            if summary and len(summary) > 5:
                # 有有效摘要：标题加粗 + 摘要缩进
                lines.append(f"**{title}** — {date_str}")
                lines.append(f"> {summary}")
                lines.append("")
            else:
                # 无摘要：仅显示标题
                lines.append(f"- {title} — {date_str}")
        lines.append("")

    lines.append("---")
    lines.append(f"*由数字平台监控脚本自动推送 · {date}*")

    return "\n".join(lines)


def _push(title: str, content: str, template: str = "markdown") -> bool:
    if PUSHPLUS_TOKEN in ("你的PushPlusToken", ""):
        print("[推送] ⚠️ 未配置 PushPlus Token")
        return False

    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": template,
    }

    try:
        resp = requests.post(PUSHPLUS_SEND_URL, json=payload, timeout=REQUEST_TIMEOUT)
        data = resp.json()
    except requests.RequestException as e:
        print(f"[推送] 网络错误: {e}")
        return False
    except ValueError:
        print(f"[推送] 响应解析失败: {resp.text[:200]}")
        return False

    if data.get("code") == 200:
        print(f"[推送] ✅ 发送成功！")
        return True
    else:
        print(f"[推送] ❌ 发送失败: {data}")
        return False
