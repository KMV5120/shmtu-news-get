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
import traceback
from datetime import datetime

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

        # 推送
        new_items = find_new_items(all_items)
        print(f"[差异] {len(new_items)} 条新增")

        send_daily_report(all_items, len(new_items))
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
