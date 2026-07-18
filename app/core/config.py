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
    upstream_timeout: float = 3600.0

    # MinIO 对象存储
    minio_endpoint: Optional[str] = None
    minio_endpoint_cn: Optional[str] = None
    """MinIO 服务地址，例如 "play.min.io" 或 "127.0.0.1:9000"。"""
    minio_access_key: Optional[str] = None
    """MinIO Access Key（AK）。"""
    minio_secret_key: Optional[str] = None
    """MinIO Secret Key（SK）。"""
    minio_bucket: Optional[str] = None
    """默认使用的桶名。"""
    minio_secure: bool = True
    """是否使用 HTTPS（True 走 443，False 走 HTTP 9000）。"""

@lru_cache
def get_settings() -> Settings:
    """获取全局配置（缓存单例）。"""
    return Settings()
