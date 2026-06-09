"""配置管理：通过环境变量加载。"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。所有字段均可通过环境变量或 .env 文件覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 服务
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "INFO"

    # 鉴权
    downstream_api_key: Optional[str] = None
    """下游调用本服务时使用的 API Key（new-api 配置）。留空则不校验。"""

    # 上游厂商默认 key（备用，优先使用请求头中的 key）
    seedance_api_key: Optional[str] = None

    # webhook
    webhook_base_url: Optional[str] = None

    # 上游请求超时
    upstream_timeout: float = 60.0


@lru_cache
def get_settings() -> Settings:
    """获取全局配置（缓存单例）。"""
    return Settings()
