"""Central configuration for memory_engine."""
import os
from pathlib import Path

from dotenv import load_dotenv

# 强制加载 .env 文件
load_dotenv(override=True)


class Settings:
    """Application settings loaded from environment variables."""

    # DeepSeek API（实际使用智谱 AI，兼容 OpenAI 接口）
    deepseek_api_key: str = os.environ.get("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.environ.get("DEEPSEEK_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    deepseek_model: str = os.environ.get("DEEPSEEK_MODEL", "glm-4.5-air")

    # Database
    database_path: Path = Path(os.environ.get("DATABASE_PATH", "./storage/memory.db"))

    # Chroma
    chroma_persist_dir: Path = Path(os.environ.get("CHROMA_PERSIST_DIR", "./storage/chroma"))
    embedding_model: str = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # App
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")
    streamlit_port: int = int(os.environ.get("STREAMLIT_PORT", "8501"))

    def ensure_dirs(self) -> None:
        """Create storage directories if they do not exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()