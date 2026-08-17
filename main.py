"""MacroSentinel 入口 — 主循环调度"""
import signal
import asyncio
import logging

from config import GROQ_API_KEY, PROXY_ENABLED, PROXY_URL, WECOM_ENABLED, CHECK_INTERVAL
from cache import SeenCache
from http_client import build_http_client, build_groq_client
from sources import DATA_SOURCES
from analyzer import analyze_market
from notifier import build_message, send_to_wecom
from models import NewsItem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 优雅退出
shutdown_event = asyncio.Event()


def _signal_handler():
    logger.info("收到中断信号，正在退出...")
    shutdown_event.set()


# ================= 并发抓取 =================


async def fetch_all_news(client) -> list[NewsItem]:
    """并发抓取所有数据源，汇总结果"""
    tasks = [source_fn(client) for source_fn in DATA_SOURCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_news: list[NewsItem] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"数据源 {DATA_SOURCES[i].__name__} 异常: {result}")
        else:
            all_news.extend(result)

    return all_news


# ================= 主循环 =================


async def monitor():
    proxy_status = f"代理: {PROXY_URL}" if PROXY_ENABLED else "代理: 关闭(直连)"
    wecom_status = "企微推送: 开启" if WECOM_ENABLED else "企微推送: 关闭"
    logger.info("🚀 MacroSentinel 已启动 (%s, %s, 间隔: %ds)", proxy_status, wecom_status, CHECK_INTERVAL)

    seen_news = SeenCache()

    async with build_http_client() as http_client:
        groq_client = build_groq_client()

        while not shutdown_event.is_set():
            # 并发抓取
            all_news = await fetch_all_news(http_client)

            # 去重
            current_batch: list[NewsItem] = []
            for item in all_news:
                if not seen_news.contains(item.key):
                    current_batch.append(item)
                    seen_news.add(item.key)

            if current_batch:
                logger.info("检测到 %d 条新资讯，正在分析...", len(current_batch))
                analysis = await analyze_market(groq_client, current_batch)

                if analysis and "IGNORE" not in analysis:
                    message = build_message(analysis, current_batch)

                    # 本地输出
                    print("\n" + "🔥" * 25)
                    print(message)
                    print("🔥" * 25 + "\n")

                    # 企业微信推送
                    await send_to_wecom(http_client, message)
                else:
                    logger.info("分析完成：暂无重磅变动。")
            else:
                logger.debug("扫描中... 暂无新资讯。")

            # 可中断的异步等待
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=CHECK_INTERVAL)
            except asyncio.TimeoutError:
                pass

        await groq_client.close()

    logger.info("MacroSentinel 已安全退出。")


# ================= 入口 =================


def main():
    if not GROQ_API_KEY:
        logger.error("未设置 GROQ_API_KEY 环境变量！请在 .env 文件或系统环境变量中配置。")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.add_signal_handler(signal.SIGINT, _signal_handler)
        loop.add_signal_handler(signal.SIGTERM, _signal_handler)
    except NotImplementedError:
        signal.signal(signal.SIGINT, lambda s, f: _signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: _signal_handler())

    try:
        loop.run_until_complete(monitor())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
