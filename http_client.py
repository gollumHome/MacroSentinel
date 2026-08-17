"""异步 HTTP 客户端工厂 + 带重试的请求工具"""
import asyncio
import logging

import httpx
from groq import AsyncGroq

from config import PROXY_ENABLED, PROXY_URL, GROQ_API_KEY, MAX_RETRIES, RETRY_BACKOFF, JINA_ENABLED, JINA_BASE_URL

logger = logging.getLogger(__name__)


def _get_proxy() -> str | None:
    """根据配置返回代理地址，关闭时返回 None"""
    return PROXY_URL if PROXY_ENABLED else None


def build_http_client() -> httpx.AsyncClient:
    """构建公共异步 HTTP 客户端（连接池复用，支持重定向）"""
    return httpx.AsyncClient(
        proxy=_get_proxy(),
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )


def build_groq_client() -> AsyncGroq:
    """构建 Groq 异步客户端"""
    return AsyncGroq(
        api_key=GROQ_API_KEY,
        http_client=httpx.AsyncClient(proxy=_get_proxy()),
    )


def wrap_jina_url(url: str) -> str:
    """如果启用 Jina Reader，将目标 URL 包装为 Jina 解析地址"""
    if JINA_ENABLED:
        return f"{JINA_BASE_URL}{url}"
    return url


async def fetch_with_retry(
    client: httpx.AsyncClient, url: str, max_retries: int = MAX_RETRIES, use_jina: bool = False
) -> httpx.Response | None:
    """带指数退避的异步 HTTP GET 请求

    Args:
        client: httpx 异步客户端
        url: 目标 URL
        max_retries: 最大重试次数
        use_jina: 是否通过 Jina Reader API 解析（适用于反爬页面）
    """
    actual_url = wrap_jina_url(url) if use_jina else url

    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.get(actual_url)
            resp.raise_for_status()
            return resp
        except httpx.TimeoutException:
            wait = RETRY_BACKOFF ** attempt
            logger.warning(f"请求超时 (第{attempt}次): {url}，{wait}s 后重试...")
        except httpx.ConnectError as e:
            wait = RETRY_BACKOFF ** attempt
            logger.warning(f"连接失败 (第{attempt}次): {url} - {e}，{wait}s 后重试...")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误: {url} - {e}")
            return None
        except Exception as e:
            logger.error(f"未知请求错误: {url} - {e}")
            return None

        if attempt < max_retries:
            await asyncio.sleep(wait)

    logger.error(f"请求最终失败 (已重试{max_retries}次): {url}")
    return None
