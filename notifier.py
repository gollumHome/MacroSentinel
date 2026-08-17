"""消息推送模块（企业微信）"""
import re
import asyncio
import logging

import httpx

from config import WECOM_ENABLED, WECOM_WEBHOOK_URL, MAX_RETRIES, RETRY_BACKOFF, MAX_NEWS_BATCH
from models import NewsItem

logger = logging.getLogger(__name__)

# 企业微信 text 单条消息上限
WECOM_MAX_LENGTH = 2000  # 留点余量，官方限制 2048


def _extract_cited_indices(analysis: str) -> set[int]:
    """从 LLM 分析结果中提取被引用的新闻编号"""
    matches = re.findall(r'[【\[](\d+)[】\]]', analysis)
    return {int(m) for m in matches}


def build_message(analysis: str, news_list: list[NewsItem]) -> str:
    """组装最终推送消息：分析结果 + 仅被引用的原始链接"""
    truncated = news_list[:MAX_NEWS_BATCH]

    cited_indices = _extract_cited_indices(analysis)

    if not cited_indices:
        return analysis

    links_section = "\n\n📎 相关原文链接：\n"
    for idx in sorted(cited_indices):
        if 1 <= idx <= len(truncated):
            item = truncated[idx - 1]
            links_section += f"[{idx}] {item.title}\n    🔗 {item.url}\n"

    return f"{analysis}{links_section}"


def _split_message(message: str, max_length: int = WECOM_MAX_LENGTH) -> list[str]:
    """将超长消息按段落拆分为多条，每条不超过 max_length

    优先按空行分段，确保不会把一段分析截断到两条消息里。
    """
    if len(message) <= max_length:
        return [message]

    chunks: list[str] = []
    # 按双换行分段
    paragraphs = message.split("\n\n")

    current_chunk = ""
    for para in paragraphs:
        # 单段就超长，强制按字符截断
        if len(para) > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # 按 max_length 硬切
            for i in range(0, len(para), max_length):
                chunks.append(para[i:i + max_length])
            continue

        # 加上这段会超限，先保存当前 chunk
        if len(current_chunk) + len(para) + 2 > max_length:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # 加上分段标识
    if len(chunks) > 1:
        total = len(chunks)
        chunks = [f"({i+1}/{total}) {chunk}" for i, chunk in enumerate(chunks)]

    return chunks


async def send_to_wecom(http_client: httpx.AsyncClient, message: str):
    """推送消息到企业微信群机器人，超长自动分段发送"""
    if not WECOM_ENABLED:
        return

    chunks = _split_message(message)

    for i, chunk in enumerate(chunks):
        payload = {
            "msgtype": "text",
            "text": {
                "content": chunk,
            },
        }

        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await http_client.post(WECOM_WEBHOOK_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("errcode") == 0:
                    success = True
                    break
                else:
                    logger.warning(f"企业微信返回错误: {data}")
                    break
            except Exception as e:
                wait = RETRY_BACKOFF ** attempt
                logger.warning(f"企业微信推送失败 (第{attempt}次): {e}，{wait}s 后重试...")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(wait)

        if not success:
            logger.error(f"企业微信推送第 {i+1}/{len(chunks)} 段失败")
            return

        # 多段之间间隔 1 秒，避免触发频率限制
        if i < len(chunks) - 1:
            await asyncio.sleep(1)

    logger.info("企业微信推送成功 (%d 段)", len(chunks))
