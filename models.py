"""数据模型"""
from dataclasses import dataclass


@dataclass
class NewsItem:
    """一条新闻，包含标题和原始链接"""
    title: str
    url: str
    source: str  # 来源标识

    @property
    def key(self) -> str:
        """用于去重的唯一键"""
        return self.title
