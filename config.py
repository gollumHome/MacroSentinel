"""全局配置，从环境变量加载"""
import os
from dotenv import load_dotenv

load_dotenv()

# Groq / LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# 代理
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "true").lower() in ("true", "1", "yes")
PROXY_URL = os.getenv("PROXY_URL", "http://127.0.0.1:58309")

# Jina Reader API（用于解析反爬页面）
# 设为 true 时通过 https://r.jina.ai/ 前缀请求目标页面
JINA_ENABLED = os.getenv("JINA_ENABLED", "true").lower() in ("true", "1", "yes")
JINA_BASE_URL = "https://r.jina.ai/"

# 轮询
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

# Web 服务端口（Koyeb 默认 8000）
PORT = int(os.getenv("PORT", "8000"))

# LLM 输入限制
MAX_NEWS_BATCH = int(os.getenv("MAX_NEWS_BATCH", "20"))

# 重试
MAX_RETRIES = 3
RETRY_BACKOFF = 2

# 去重缓存
SEEN_MAX_SIZE = 500

# 企业微信
WECOM_WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "")
WECOM_ENABLED = bool(WECOM_WEBHOOK_URL)
