"""
门户内容抓取 + 文章摘要

1. 点击栏目标签 → 文章列表出现在右侧
2. 读取 .titleBox 获取文章标题和日期
3. 点击文章标题 → 新标签页打开正文 → 提取 150 字摘要 → 关闭标签页
"""

import re
import hashlib
import time

from datetime import datetime, timedelta
from config import SECTIONS, MAX_ITEMS_PER_SECTION

CUTOFF_DATE = datetime.now() - timedelta(days=90)  # 3 个月前

DATE_PATTERN = re.compile(
    r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)"
    r"|(\d{1,2}[-/月]\d{1,2}[日]?)"
)


def extract_date(text: str) -> str:
    m = DATE_PATTERN.search(text)
    return m.group(0).strip() if m else "未知"


def is_recent(date_str: str) -> bool:
    """检查日期是否在 3 个月内"""
    if not date_str or date_str == "未知":
        return True  # 无法解析的保留
    try:
        # 尝试多种日期格式
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%m月%d日"]:
            try:
                d = datetime.strptime(date_str.replace('日', ''), fmt.replace('日', ''))
                if d.year == 1900:
                    d = d.replace(year=datetime.now().year)
                return d >= CUTOFF_DATE
            except ValueError:
                continue
        return True  # 无法解析的保留
    except Exception:
        return True


def make_item_id(title: str, link: str) -> str:
    return hashlib.md5(f"{title}|{link}".encode()).hexdigest()


def _get_article_list(page) -> list[dict]:
    """从当前页面 .titleBox 提取文章标题和日期"""
    return page.evaluate("""() => {
        const results = [], seen = new Set();
        document.querySelectorAll('.titleBox').forEach(tb => {
            const row = tb.parentElement;
            if (!row || row.children.length < 2) return;
            const spans = tb.querySelectorAll('span');
            let title = '';
            spans.forEach(s => {
                if (s.textContent.trim().length > title.length)
                    title = s.textContent.trim();
            });
            if (title.length < 4 || seen.has(title)) return;
            seen.add(title);
            const metaDiv = row.children[1];
            const metaText = metaDiv ? metaDiv.textContent.trim() : '';
            let date = '';
            const dm = metaText.match(
                /(\\d{4}[-/]\\d{1,2}[-/]\\d{1,2}|\\d{1,2}[-/月]\\d{1,2}[日]?)/
            );
            if (dm) date = dm[0];
            results.push({title, date: date || '未知'});
        });
        return results;
    }""")


class PortalScraper:
    def __init__(self, context):
        self._context = context
        self._page = context.new_page()

    def navigate(self, url: str):
        self._page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(5)
        print(f"[浏览器] 就绪: {self._page.title()}")

    def _click_section(self, name: str) -> bool:
        return self._page.evaluate(f"""
            () => {{
                const btns = document.querySelectorAll('button');
                for (const b of btns) {{
                    const d = b.querySelector('div');
                    if (d && d.textContent.trim() === '{name}') {{
                        b.click(); return true;
                    }}
                }}
                return false;
            }}
        """)

    def scrape_all(self) -> list[dict]:
        page = self._page
        all_items = []

        for section in SECTIONS:
            name = section["name"]
            print(f"\n[抓取] 「{name}」...")

            try:
                # 点击栏目
                if not self._click_section(name):
                    print(f"    ⚠️ 未找到按钮")
                    continue
                time.sleep(3)

                # 获取文章列表，过滤 3 个月前的
                articles = _get_article_list(page)
                before = len(articles)
                articles = [a for a in articles if is_recent(a.get("date", ""))]
                skipped = before - len(articles)
                articles = articles[:MAX_ITEMS_PER_SECTION]
                print(f"    共 {len(articles)} 篇" + (f"（过滤 {skipped} 篇旧文）" if skipped else ""))

                # 逐篇提取摘要
                for i, art in enumerate(articles):
                    title = art["title"]
                    date = art.get("date", "未知")
                    print(f"    [{i+1}/{len(articles)}] {title[:45]}...")

                    text = self._try_extract_fulltext(title)

                    all_items.append({
                        "title": title,
                        "link": "",
                        "date": date,
                        "section": name,
                        "text": text,       # 全文，供 AI 概括
                        "summary": "",      # 稍后由 summarizer 填充
                        "id": make_item_id(title, ""),
                    })

            except Exception as e:
                print(f"    ❌ {e}")

        return all_items

    def _try_extract_fulltext(self, title: str) -> str:
        """点击文章标题 → 新标签页 → 提取全文 → 关闭标签页"""
        page = self._page
        popups = []
        listener = lambda p: popups.append(p)
        self._context.on("page", listener)

        try:
            # 逐层点击 DOM 链（titleBox → 父级 → 祖父级 → ...）
            # 直到触发新标签页
            chain = page.evaluate(f"""
                () => {{
                    for (const tb of document.querySelectorAll('.titleBox')) {{
                        if (!tb.textContent.includes({repr(title)})) continue;
                        const chain = [];
                        let node = tb;
                        for (let i = 0; i < 5 && node; i++) {{
                            const r = node.getBoundingClientRect();
                            chain.push({{x: r.x + r.width/2, y: r.y + r.height/2}});
                            node = node.parentElement;
                        }}
                        return chain;
                    }}
                    return [];
                }}
            """)
            for pt in (chain or []):
                page.mouse.click(pt["x"], pt["y"])
                # 短暂等待看是否触发 popup
                for _ in range(10):
                    if popups:
                        break
                    time.sleep(0.1)
                if popups:
                    break

            # 等待 popup（最多 8 秒）
            for _ in range(80):
                if popups:
                    break
                time.sleep(0.1)

            if not popups:
                return ""

            popup = popups[0]
            popup.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(1.5)

            text = popup.evaluate("""() => {
                const sels = ['.article-content','.news-content','.content',
                    '.detail-content','article','.TRS_Editor','#vsb_content',
                    '.rich-text','.text-content','[class*=\"article\"]'];
                for (const sel of sels) {
                    const el = document.querySelector(sel);
                    if (el && el.textContent.trim().length > 50)
                        return el.textContent.trim();
                }
                return document.body.innerText.trim();
            }""")

            popup.close()

            if not text:
                return ""

            text = re.sub(r'\s+', ' ', text.strip())

            # 强力去噪：移除页面导航/页头/页脚垃圾
            noise = [
                r'信息发布\s*个人信息\s*退出',
                r'当前位置[：:][^。]{0,50}',
                r'发布日期[：:]\s*\d{4}[^ ]{0,30}',
                r'部门[：:]\s*[^\s]{0,30}',
                r'浏览次数[：:]\s*\d+',
                r'打印\s*关闭',
                r'上海海事大学\S*?\s*(?:登录|首页|邮箱|处长)',
                r'处长信箱\s*登录',
                r'<[^>]+>',           # HTML 标签
                r'&[a-z]+;',           # HTML 实体
            ]
            for pat in noise:
                text = re.sub(pat, '', text)
            # 再次压缩多余空白
            text = re.sub(r'\s{2,}', ' ', text).strip()

            return text if len(text) > 20 else ""

        except Exception:
            if popups:
                try: popups[0].close()
                except Exception: pass
            return ""

        finally:
            self._context.remove_listener("page", listener)

    def close(self):
        self._page.close()


def run_discover(context, portal_url: str):
    scraper = PortalScraper(context)
    try:
        scraper.navigate(portal_url)
        page = scraper._page
        print(f"\n{'=' * 60}")
        print(f"  栏目探索")
        print(f"{'=' * 60}")

        total = 0
        for section in SECTIONS:
            name = section["name"]
            print(f"[探索] 「{name}」...")
            if not scraper._click_section(name):
                print(f"    ⚠️ 未找到")
                continue
            time.sleep(2)
            articles = _get_article_list(page)
            count = min(len(articles), MAX_ITEMS_PER_SECTION)
            total += count
            print(f"    ✅ {count} 篇")
            for a in articles[:3]:
                print(f"       [{a.get('date','?')}] {a['title'][:60]}")

        print(f"\n[完成] 共 {total} 篇")
    finally:
        scraper.close()
