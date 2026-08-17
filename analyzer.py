"""LLM 市场分析模块"""
import asyncio
import logging

from groq import AsyncGroq

from config import MAX_NEWS_BATCH, MAX_RETRIES, RETRY_BACKOFF, GROQ_MODEL
from models import NewsItem

logger = logging.getLogger(__name__)


async def analyze_market(groq_client: AsyncGroq, news_list: list[NewsItem]) -> str | None:
    """异步调用 LLM 进行市场分析（宏观 + 个股）"""
    if not news_list:
        return None

    truncated = news_list[:MAX_NEWS_BATCH]
    combined_news = "\n".join(
        [f"[{i+1}] [{item.source}] {item.title}" for i, item in enumerate(truncated)]
    )

    prompt = f"""你是一名资深美股全市场分析师，擅长从快讯中捕捉宏观趋势与个股异动。请分析以下最新资讯。

【实时资讯】：
{combined_news}

【分析任务】：
请从两个维度评估：

一、宏观层面（影响 SPY/QQQ 大盘方向）
识别涉及以下主题的消息并评估冲击力(1-10分)：
- 利率路径：加息/降息预期变化、美联储官员讲话
- 关键数据：非农、CPI、PPI、GDP、PMI、初请失业金
- 地缘政治：战争升级、制裁、贸易摩擦
- 流动性事件：日元套利平仓、美债拍卖异常、银行风险

二、个股层面（影响单票 3%+ 波动）
识别涉及以下主题的消息：
- 财报意外：盈利大幅超预期/不及预期、指引调整
- 重大事件：并购、拆分、大额回购、管理层变动
- 监管动作：FDA 批准/拒绝、反垄断诉讼、SEC 调查
- 行业催化：AI 新品发布、药物临床数据、大额合同

【输出格式】：
分区输出，仅输出评分>=7的事件（无则该区留空）。
在事件简述中标注对应的资讯编号（如 [1][3]），以便追溯原文。

📊 宏观信号：
🚨 [评分/10] 事件简述 [对应编号]
🧠 逻辑：(核心传导路径)
📈 操作：(对大盘 ETF 的 T+0 建议)

💎 个股异动：
🚨 [评分/10] 标的 | 事件简述 [对应编号]
🧠 逻辑：(为什么会引发大幅波动)
📈 操作：(方向、入场时机、止损参考)

若两个维度均无评分>=7的事件，请只回复 "IGNORE"。
"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            completion = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
            )
            return completion.choices[0].message.content
        except Exception as e:
            wait = RETRY_BACKOFF ** attempt
            logger.warning(f"Groq API 调用出错 (第{attempt}次): {e}，{wait}s 后重试...")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(wait)

    logger.error("Groq API 调用最终失败")
    return None
