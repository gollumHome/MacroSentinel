"""Financial Juice RSS 数据源"""
import logging

import httpx
import feedparser

from models import NewsItem
from http_client import fetch_with_retry

logger = logging.getLogger(__name__)

RSS_URL = "https://www.financialjuice.com/feed.ashx?xy=rss"


async def get_financial_juice_rss(client: httpx.AsyncClient) -> list[NewsItem]:
    """异步解析 Financial Juice 实时 RSS，返回带链接的新闻列表

    RSS 是结构化数据，无需 Jina，直接请求即可。
    """
    response = await fetch_with_retry(client, RSS_URL, use_jina=False)
    if not response:
        return []

    try:
        feed = feedparser.parse(response.content)
        results = []
        for entry in feed.entries[:10]:
            title = entry.title.replace("FinancialJuice: ", "").strip()
            link = entry.get("link", "https://www.financialjuice.com")
            results.append(NewsItem(title=title, url=link, source="FinancialJuice"))

        logger.info(f"Financial Juice 解析到 {len(results)} 条新闻")
        return results
    except Exception as e:
        logger.error(f"解析 Financial Juice RSS 出错: {e}")
        return []
