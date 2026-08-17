"""LRU 去重缓存"""
from collections import OrderedDict
from config import SEEN_MAX_SIZE


class SeenCache:
    """基于 OrderedDict 的 LRU 去重缓存，自动淘汰最早条目"""

    def __init__(self, max_size: int = SEEN_MAX_SIZE):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size

    def contains(self, item: str) -> bool:
        if item in self._cache:
            self._cache.move_to_end(item)
            return True
        return False

    def add(self, item: str):
        if item in self._cache:
            self._cache.move_to_end(item)
        else:
            self._cache[item] = True
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def __len__(self) -> int:
        return len(self._cache)
