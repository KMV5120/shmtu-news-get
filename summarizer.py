"""
DeepSeek API 文章概括模块

将抓取到的文章正文发送给 DeepSeek，生成摘要。
"""

import requests

from config import DEEPSEEK_API_KEY

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def summarize_articles(articles: list[dict]) -> list[dict]:
    """
    按栏目分批发送给 DeepSeek，为每篇文章生成摘要。

    Args:
        articles: [{"title": "...", "text": "...", "section": "...", "date": "..."}, ...]

    Returns:
        同结构，summary 字段被填充
    """
    if not articles:
        return articles

    grouped = {}
    for a in articles:
        grouped.setdefault(a["section"], []).append(a)

    all_summaries = {}

    for section, items in grouped.items():
        print(f"[AI概括] 「{section}」{len(items)} 篇...")

        prompt = f"""你是上海海事大学信息简报助手。以下是「{section}」栏目的文章列表。
请为每篇文章写中文摘要，提炼关键信息，长度根据原文内容自适应（短则一两句，长则一小段）。

格式要求：以"标题：xxx\n摘要：xxx"格式输出，文章之间用"---"分隔。

"""
        for i, item in enumerate(items):
            text = item.get("text", "")
            if not text or len(text) < 30:
                prompt += f"\n文章{i+1}：{item['title']}\n内容：（仅有标题，请根据标题推测内容摘要）\n"
            else:
                prompt += f"\n文章{i+1}：{item['title']}\n内容：{text[:500]}\n"

        try:
            resp = requests.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-v4-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": min(2000, len(items) * 80 + 200),
                },
                timeout=60,
            )
            data = resp.json()
            ai_text = data["choices"][0]["message"]["content"]
            summaries = _parse_summaries(ai_text, items)
            all_summaries.update(summaries)

        except Exception as e:
            print(f"    AI 概括失败: {e}")
            for item in items:
                all_summaries[item["title"]] = ""

    result = []
    for a in articles:
        result.append({
            **a,
            "summary": all_summaries.get(a["title"], ""),
        })

    return result


def _parse_summaries(ai_text: str, items: list[dict]) -> dict:
    summaries = {}
    blocks = ai_text.split("---")

    for block in blocks:
        lines = block.strip().split("\n")
        title_from_ai = ""
        summary = ""

        for line in lines:
            line = line.strip()
            if line.startswith("标题：") or line.startswith("标题:"):
                title_from_ai = line.replace("标题：", "").replace("标题:", "").strip()
            elif line.startswith("摘要：") or line.startswith("摘要:"):
                summary = line.replace("摘要：", "").replace("摘要:", "").strip()

        if summary:
            best = _fuzzy_match(title_from_ai, [it["title"] for it in items])
            summaries[best] = summary

    if not summaries:
        for item in items:
            summaries[item["title"]] = ""

    return summaries


def _fuzzy_match(target: str, candidates: list[str]) -> str:
    if not target:
        return candidates[0] if candidates else ""
    best, best_score = candidates[0], 0
    for c in candidates:
        score = len(set(target) & set(c))
        if score > best_score:
            best_score = score
            best = c
    return best
