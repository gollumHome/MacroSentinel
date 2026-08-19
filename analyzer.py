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

    prompt = f"""你是一名资深美股市场信息分析师，擅长从海量快讯中快速识别真正影响市场的关键事件，并过滤噪音。

【实时资讯】：
{combined_news}

【评估维度】：

一、宏观层面（影响 SPY/QQQ 大盘方向）
- 利率路径：加息/降息预期变化、美联储官员讲话、点阵图
- 关键数据：非农、CPI、PPI、GDP、PMI、初请失业金、零售销售
- 地缘政治：战争升级、制裁、贸易摩擦、关税
- 流动性/信用：套利平仓、美债拍卖异常、银行或债务风险

二、个股层面（可能引发单票 5%+ 波动）
- 财报意外：盈利大幅超/不及预期、指引调整
- 重大事件：并购、拆分、大额回购、高管变动
- 监管动作：FDA 批准/拒绝、反垄断、SEC 调查
- 行业催化：AI 新品、临床数据、大额合同

【评分标准（1-10）】：
- 9-10：可能引发日内趋势反转或恐慌/狂热的重磅事件
- 7-8：显著影响当日情绪或特定板块/个股方向
- 4-6：中等关注度，暂不输出
- 1-3：噪音，忽略

【硬性要求】：
1. 只依据资讯本身分析，不臆造未提供的信息，不虚构数据。
2. 区分"已发生的事实"与"市场预期/传闻"，在逻辑中注明。
3. 过滤重复报道，同一事件多篇报道只输出一条并合并编号。
4. 不提供任何买卖建议、点位或仓位指引，仅做客观信息与影响分析。

【输出格式】：
仅输出评分>=7的事件（无则该区留空）。事件简述后标注对应资讯编号（如 [1][3]）。

📊 宏观信号：
🚨 [评分/10] 事件简述 [编号]
🧠 影响分析：(传导路径 + 受影响的资产/板块 + 事实/预期标注)

💎 个股异动：
🚨 [评分/10] 标的代码 | 事件简述 [编号]
🧠 影响分析：(波动方向与量级判断的依据)

若两个维度均无评分>=7的事件，请只回复 "IGNORE"。
"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            completion = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return completion.choices[0].message.content
        except Exception as e:
            wait = RETRY_BACKOFF ** attempt
            logger.warning(f"Groq API 调用出错 (第{attempt}次): {e}，{wait}s 后重试...")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(wait)

    logger.error("Groq API 调用最终失败")
    return None
