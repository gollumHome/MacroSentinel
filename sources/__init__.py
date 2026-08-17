"""数据源包 — 新增数据源只需在此注册"""
from sources.finviz import get_finviz_headlines
from sources.financial_juice import get_financial_juice_rss

# 数据源注册表：新增数据源追加到这里即可
DATA_SOURCES = [
    get_finviz_headlines,
    get_financial_juice_rss,
]
