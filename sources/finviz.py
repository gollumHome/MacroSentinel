"""Finviz 新闻数据源（通过 Jina Reader API 解析）"""
import re
import logging

import httpx

from models import NewsItem
from http_client import fetch_with_retry

logger = logging.getLogger(__name__)

# Finviz 已将 /news.ashx 重定向到 /news
FINVIZ_URL = "https://finviz.com/news"

# 需要过滤掉的站内导航/非新闻链接关键词
NOISE_KEYWORDS = [
    "finviz.com/news", "finviz.com/screener", "finviz.com/map",
    "finviz.com/crypto", "finviz.com/elite", "finviz.com/login",
    "finviz.com/register", "finviz.com/help", "finviz.com/forex",
    "finviz.com/futures",
    "do not sell", "privacy", "cookie", "terms of service",
    "login", "register", "elite", "screener",
    "market news", "market pulse", "stocks news", "crypto news",
    "blog news",
]


def _is_valid_news(title: str, url: str) -> bool:
    """判断是否为有效的新闻条目（排除导航和噪音）"""
    title_lower = title.lower().strip()
    url_lower = url.lower()

    # 标题太短
    if len(title) < 15:
        return False

    # 链接指向 finviz 站内页面（非外部新闻源）
    if "finviz.com" in url_lower:
        return False

    # 标题命中噪音关键词
    for keyword in NOISE_KEYWORDS:
        if keyword in title_lower:
            return False

    return True


async def get_finviz_headlines(client: httpx.AsyncClient) -> list[NewsItem]:
    """通过 Jina Reader 解析 Finviz 新闻页面，提取标题和链接

    Jina Reader 返回 Markdown 格式内容，新闻链接格式为：
    [标题](url)
    """
    response = await fetch_with_retry(client, FINVIZ_URL, use_jina=True)
    if not response:
        return []

    try:
        content = response.text
        # Jina Reader 返回 Markdown，解析 [title](url) 格式的链接
        link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
        matches = link_pattern.findall(content)

        results = []
        seen_titles = set()

        for title, url in matches:
            title = title.strip()

            if title in seen_titles:
                continue

            if not _is_valid_news(title, url):
                continue

            seen_titles.add(title)
            results.append(NewsItem(title=title, url=url, source="Finviz"))

            if len(results) >= 15:
                break

        logger.info(f"Finviz 解析到 {len(results)} 条有效新闻")
        return results

    except Exception as e:
        logger.error(f"解析 Finviz 内容出错: {e}")
        return []
