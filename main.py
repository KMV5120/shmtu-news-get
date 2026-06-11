"""
上海海事大学数字平台信息监控 — 主入口

用法：
  python main.py              # 正常模式：抓取并推送日报
  python main.py --discover   # 探索模式：分析页面结构
  python main.py --test       # 测试模式：发送微信测试消息
  python main.py --setup      # 安装模式：创建 Windows 定时任务

流程：
  1. requests 完成 CAS 登录 → 获取 service ticket URL
  2. Playwright 直接打开 ticket URL → 获得认证门户页面
  3. 等待页面渲染 → 遍历栏目抓取内容
  4. 与本地记录比对 → PushPlus 微信推送
"""

import sys
import os
import traceback
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import SECTIONS, USERNAME, PASSWORD, PUSHPLUS_TOKEN, USER_AGENT, CHROMIUM_EXECUTABLE
from auth import login_and_get_portal_url
from scraper import PortalScraper, run_discover
from summarizer import summarize_articles
from storage import find_new_items, cleanup_old_items
from notifier import send_daily_report, send_test_message, send_error_alert


def _detect_proxy():
    import urllib.request
    proxies = urllib.request.getproxies()
    if not proxies:
        return None
    for key in ("http", "https"):
        url = proxies.get(key, "")
        if url:
            if url.startswith("https://"):
                url = url.replace("https://", "http://", 1)
            return url
    return None


def _create_browser_context(playwright):
    """创建 Playwright browser + context"""
    proxy = _detect_proxy()
    args = ["--disable-blink-features=AutomationControlled"]
    if proxy:
        args.append(f"--proxy-server={proxy}")
    browser = playwright.chromium.launch(
        headless=True,
        args=args,
        executable_path=CHROMIUM_EXECUTABLE,  # 为 None 时用 Playwright 自带的 Chromium
    )
    context = browser.new_context(user_agent=USER_AGENT)
    return browser, context


def check_config() -> bool:
    issues = []
    if USERNAME in ("你的学号或工号", ""):
        issues.append("USERNAME 未设置")
    if PASSWORD in ("你的统一认证密码", ""):
        issues.append("PASSWORD 未设置")
    if PUSHPLUS_TOKEN in ("你的PushPlusToken", ""):
        issues.append("PUSHPLUS_TOKEN 未设置")
    if issues:
        print("⚠️  配置问题：")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        return False
    return True


def _print_new_items_console(new_items: list[dict]):
    """在终端醒目显示新增条目"""
    if not new_items:
        return

    width = 60
    print(f"\n{'=' * width}")
    print(f"  {'🔴 新增内容 — ' + str(len(new_items)) + ' 条':^{width-4}}")
    print(f"{'=' * width}")

    # 按栏目分组
    grouped = {}
    for item in new_items:
        section = item.get("section", "其他")
        grouped.setdefault(section, []).append(item)

    for section, items in grouped.items():
        print(f"\n  ┌─ {section}（{len(items)} 条）")
        for i, item in enumerate(items):
            prefix = "  ├" if i < len(items) - 1 else "  └"
            title = item.get("title", "无标题")[:50]
            summary = item.get("summary", "")
            print(f"  {prefix}─ {title}")
            if summary:
                s = summary.replace('\n', ' ')[:80]
                print(f"  │  > {s}...")
    print(f"\n{'=' * width}\n")


def _save_report_md(all_items: list[dict], new_items: list[dict], timestamp: datetime):
    """保存完整报告到本地 markdown 文件"""
    filename = timestamp.strftime("%y%m%d%H%M.md")
    filepath = Path(__file__).parent / filename

    today = timestamp.strftime("%Y-%m-%d")
    new_ids = {item.get("id") for item in new_items}

    # 按栏目分组
    grouped = {}
    for item in all_items:
        section = item.get("section", "其他")
        grouped.setdefault(section, []).append(item)

    lines = []
    lines.append(f"# 📋 数字平台监控日报 {today}")
    lines.append("")
    lines.append(f"**生成时间**: {timestamp:%Y-%m-%d %H:%M:%S}")
    lines.append(f"**抓取条数**: {len(all_items)} 条  |  **新增**: {len(new_items)} 条")
    lines.append("")

    # ── 置顶：新增内容 ──
    if new_items:
        lines.append("---")
        lines.append("")
        lines.append(f"## 🔴 新增内容（{len(new_items)} 条）")
        lines.append("")

        new_grouped = {}
        for item in new_items:
            s = item.get("section", "其他")
            new_grouped.setdefault(s, []).append(item)

        for section, items in new_grouped.items():
            lines.append(f"### {section}")
            lines.append("")
            for item in items:
                title = item.get("title", "无标题")
                date_str = item.get("date", "")
                link = item.get("link", "")
                summary = item.get("summary", "")
                text = item.get("text", "")

                lines.append(f"#### {title}")
                if date_str:
                    lines.append(f"📅 {date_str}")
                if link:
                    lines.append(f"🔗 {link}")
                lines.append("")
                if summary:
                    lines.append(f"> {summary}")
                    lines.append("")
                elif text:
                    # 无 AI 摘要时显示原文前 200 字
                    preview = text[:200].replace('\n', ' ').strip()
                    lines.append(f"> {preview}...")
                    lines.append("")
                lines.append("")
        lines.append("---")
        lines.append("")

    # ── 全部条目 ──
    lines.append(f"## 📊 全部条目（{len(all_items)} 条）")
    lines.append("")

    for section, items in grouped.items():
        new_in_section = sum(1 for it in items if it.get("id") in new_ids)
        header = f"### {section}（{len(items)} 条"
        if new_in_section:
            header += f"，其中新增 {new_in_section} 条"
        header += "）"
        lines.append(header)
        lines.append("")

        for item in items:
            title = item.get("title", "无标题")
            date_str = item.get("date", "")
            summary = item.get("summary", "")
            is_new = item.get("id") in new_ids

            prefix = "🆕 " if is_new else ""
            if summary and len(summary) > 5:
                lines.append(f"- {prefix}**{title}** — {date_str}")
                lines.append(f"  > {summary}")
            else:
                lines.append(f"- {prefix}{title} — {date_str}")
            lines.append("")

        lines.append("")

    lines.append("---")
    lines.append(f"*由数字平台监控脚本自动生成 · {today}*")
    lines.append("")

    content = "\n".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[文件] 报告已保存到: {filepath.name}")


def run_monitor():
    print(f"\n{'=' * 60}")
    print(f"  数字平台监控 — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"{'=' * 60}\n")

    if not check_config():
        return

    pw = sync_playwright().start()
    browser = None
    scraper = None

    try:
        # 1. CAS 登录获取 ticket URL
        portal_url = login_and_get_portal_url()

        # 2. Playwright 打开门户
        browser, context = _create_browser_context(pw)

        # 3. 抓取
        scraper = PortalScraper(context)
        scraper.navigate(portal_url)
        all_items = scraper.scrape_all()

        print(f"\n[汇总] 共抓取 {len(all_items)} 条")

        # AI 概括
        print("\n[AI] 正在调用 DeepSeek 生成摘要...")
        all_items = summarize_articles(all_items)

        # 差异比对
        new_items = find_new_items(all_items)

        # ── 终端醒目显示新增 ──
        _print_new_items_console(new_items)

        # ── 微信推送 ──
        send_daily_report(all_items, len(new_items))

        # ── 保存本地 Markdown 文件 ──
        now = datetime.now()
        _save_report_md(all_items, new_items, now)

        cleanup_old_items(days=30)

    except Exception as e:
        send_error_alert(str(e))
        traceback.print_exc()

    finally:
        if scraper:
            scraper.close()
        if browser:
            browser.close()
        pw.stop()

    print(f"\n[完成] {datetime.now():%Y-%m-%d %H:%M:%S}\n")


def run_setup():
    import subprocess
    task_name = "SHMTU_Monitor"
    program = f'"{sys.executable}" "{__file__}"'
    print(f"[安装] 创建定时任务「{task_name}」...")
    subprocess.run(f'schtasks /delete /tn "{task_name}" /f',
                   shell=True, capture_output=True)
    r = subprocess.run(
        f'schtasks /create /tn "{task_name}" /tr "{program}" /sc weekly /d SAT /st 18:00 /f',
        shell=True, capture_output=True, text=True)
    print("[安装] ✅ 成功" if r.returncode == 0 else f"[安装] ❌ {r.stderr}")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--discover":
            if not check_config():
                return
            portal_url = login_and_get_portal_url()
            pw = sync_playwright().start()
            browser = None
            try:
                browser, context = _create_browser_context(pw)
                run_discover(context, portal_url)
            finally:
                if browser:
                    browser.close()
                pw.stop()
        elif arg == "--test":
            send_test_message()
        elif arg == "--setup":
            run_setup()
        elif arg == "--help":
            print(__doc__)
        else:
            print(f"未知参数: {arg}")
    else:
        run_monitor()


if __name__ == "__main__":
    main()
