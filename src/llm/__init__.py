"""
LLM サービス層

ENABLE_LLM フラグで制御される AI 機能を提供します。

Phase1-2: スタブ実装
Phase3-4: サンドボックス統合とセキュリティ強化

関連:
- docs/security/SECURITY_MODEL.md
- docs/plan/cdp-webui-modernization.md
"""

from .service_gateway import (
    LLMServiceGateway,
    LLMServiceGatewayStub,
    LLMServiceError,
    get_llm_gateway,
    reset_llm_gateway,
)

__all__ = [
    "LLMServiceGateway",
    "LLMServiceGatewayStub",
    "LLMServiceError",
    "get_llm_gateway",
    "reset_llm_gateway",
]

__version__ = "1.0.0-alpha"
