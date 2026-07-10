"""模型→厂商 注册表。

设计目标：
- 一个模型名映射到一个厂商（不做 fallback，因为是聚合而非容灾）
- 不同服务类型（chat/image/video/audio）独立注册
- 模型名通过前缀匹配（最长前缀优先）

新增厂商只需：
1. 在 vendors/ 下实现一个 BaseVendor 子类
2. 在本文件的 _build_registry() 中加一行 register

无需改动路由、core、其他厂商代码。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.core.errors import ModelNotFoundError

from loguru import logger


class ServiceType(str, Enum):
    CHAT = "chat"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    EMBEDDING = "embedding"
    GEMINI_IMAGE= "gemini-image"

@dataclass
class VendorRoute:
    """单条注册项：服务类型 + 模型前缀 → 厂商实例。"""

    service: ServiceType
    model_patterns: list[str]
    vendor: object  # BaseVendor 实例（避免循环导入，运行时鸭子类型）
    enabled: bool = True

    def matches(self, model: str) -> Optional[int]:
        """返回匹配长度（用于最长前缀优先），不匹配返回 None。"""
        if not self.enabled:
            return None
        m = model.lower()
        best = None
        for pat in self.model_patterns:
            p = pat.lower()
            if m.startswith(p) or m == p:
                if best is None or len(p) > best:
                    best = len(p)
        return best


@dataclass
class Registry:
    _routes: list[VendorRoute] = field(default_factory=list)

    def register(
        self,
        service: ServiceType,
        model_patterns: str | list[str],
        vendor: object,
    ) -> None:
        if isinstance(model_patterns, str):
            model_patterns = [model_patterns]
        route = VendorRoute(service=service, model_patterns=model_patterns, vendor=vendor)
        self._routes.append(route)
        logger.info(
            "Registered vendor: service=%s patterns=%s vendor=%s",
            service.value,
            model_patterns,
            type(vendor).__name__,
        )

    def lookup(self, service: ServiceType, model: str) -> object:
        """根据服务类型 + 模型名查找厂商。最长前缀匹配优先。"""
        best_route: Optional[VendorRoute] = None
        best_len = -1
        for route in self._routes:
            if route.service != service:
                continue
            length = route.matches(model)
            if length is not None and length > best_len:
                best_len = length
                best_route = route

        if best_route is None:
            raise ModelNotFoundError(
                f"Model '{model}' is not registered for service '{service.value}'"
            )
        return best_route.vendor

    def all_models(self, service: Optional[ServiceType] = None) -> list[dict]:
        """返回所有注册的模型（用于诊断）。"""
        out: list[dict] = []
        for route in self._routes:
            if service is not None and route.service != service:
                continue
            out.append({
                "service": route.service.value,
                "patterns": route.model_patterns,
                "vendor": type(route.vendor).__name__,
                "enabled": route.enabled,
            })
        return out


# 全局单例
_registry: Optional[Registry] = None


def get_registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def _build_registry() -> Registry:
    """初始化注册表，注册所有厂商。

    新增厂商在这里加一行 register。
    """
    from app.vendors.seedance import SeedanceVideoVendor
    from app.vendors.seedream2gemini import Seedream2GeminiVendor
    from app.vendors.gpt2image import GPTIMAGE

    reg = Registry()

    # ===== 视频生成 =====
    reg.register(
        ServiceType.VIDEO,
        model_patterns=["doubao-seedance", "seedance"],
        vendor=SeedanceVideoVendor(),
    )
    # ===== 图片生成 =====
    reg.register(
        ServiceType.GEMINI_IMAGE,
        model_patterns=["doubao-seedream","seedream"],
        vendor=Seedream2GeminiVendor(),
    )
    reg.register(
        ServiceType.IMAGE,
        model_patterns=["gpt-image-2"],
        vendor=GPTIMAGE(),
    )

    # 在这里继续注册新厂商：
    # reg.register(ServiceType.CHAT, "gpt-4", OpenAIChatVendor())
    # reg.register(ServiceType.IMAGE, "flux-", FluxImageVendor())

    return reg
