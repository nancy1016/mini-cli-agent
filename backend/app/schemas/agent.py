"""后端规则 Agent 的 HTTP 请求与响应模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    text: str = Field(min_length=1)


class AgentConfirmRequest(BaseModel):
    preview_id: str = Field(min_length=1)


class AgentModelUsage(BaseModel):
    used: bool = False
    provider: str | None = None
    name: str | None = None
    fallback_reason: str | None = None


class PreviewEnvelope(BaseModel):
    preview_id: str
    type: Literal["application", "interview", "status_update"]
    fields: dict[str, Any]
    missing: dict[str, list[str]] | None = None
    warnings: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    ok: bool
    intent: str
    message: str
    data: dict[str, Any] | None = None
    preview: PreviewEnvelope | None = None
    requires_confirmation: bool = False
    model: AgentModelUsage = Field(default_factory=AgentModelUsage)
