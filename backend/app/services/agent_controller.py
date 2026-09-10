"""规则 Agent 主流程与服务器端安全确认状态。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Callable
from uuid import uuid4

from backend.app.core.config import resolve_database_path
from backend.app.services.agent_response_enhancer import enhance_agent_response
from backend.app.services.intent_router import route_intent
from backend.app.services.llm_provider import LLMProvider
from backend.app.services.tool_registry import ToolRegistry


DbPath = str | Path
Clock = Callable[[], datetime]
QUERY_INTENTS = {
    "query_applications",
    "query_interviews",
    "query_missing_info",
    "query_application_status",
}
PREVIEW_TYPES = {
    "preview_application": "application",
    "preview_interview": "interview",
    "preview_status_update": "status_update",
}


class AgentControllerError(Exception):
    """AgentController 可映射为 HTTP 业务错误的基类。"""


class PreviewNotFoundError(AgentControllerError):
    pass


class PreviewConflictError(AgentControllerError):
    pass


class AgentBusinessError(AgentControllerError):
    pass


@dataclass
class PendingPreview:
    action: str
    preview: dict[str, object]
    database_path: Path
    expires_at: datetime
    consumed: bool = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _base_response(intent: str, ok: bool, message: str) -> dict[str, object]:
    return {
        "ok": ok,
        "intent": intent,
        "message": message,
        "data": None,
        "preview": None,
        "requires_confirmation": False,
        "model": {
            "used": False,
            "provider": None,
            "name": None,
            "fallback_reason": None,
        },
    }


class AgentController:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        preview_ttl: timedelta = timedelta(minutes=15),
        clock: Clock = _utc_now,
        model_provider: LLMProvider | None = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.preview_ttl = preview_ttl
        self.clock = clock
        self.model_provider = model_provider
        self._pending: dict[str, PendingPreview] = {}
        self._lock = Lock()

    def handle_agent_message(
        self,
        text: str,
        db_path: DbPath | None = None,
        base_date: date | None = None,
    ) -> dict[str, object]:
        routed = route_intent(text)
        intent = str(routed["intent"])
        if intent == "unknown":
            return _base_response(
                intent,
                False,
                "我暂时无法确认你想查询还是修改记录，请换一种更明确的说法。",
            )

        arguments = routed.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            result = self.registry.run_chat_tool(
                intent,
                text=text,
                arguments=arguments,
                db_path=db_path,
                base_date=base_date,
            )
        except ValueError as exc:
            response = _base_response(intent, False, str(exc))
            return response

        if not isinstance(result, dict):
            return _base_response(intent, False, "Agent 工具返回了无法处理的数据。")
        if intent in QUERY_INTENTS:
            response = self._query_response(intent, result)
            if response["ok"]:
                enhanced = enhance_agent_response(
                    user_text=text,
                    intent=intent,
                    rule_message=str(response["message"]),
                    data=result,
                    model_provider=self.model_provider,
                )
                response["message"] = enhanced["message"]
                response["model"] = enhanced["model"]
            return response
        return self._preview_response(intent, result, db_path=db_path)

    def _query_response(self, intent: str, result: dict[str, object]) -> dict[str, object]:
        response = _base_response(intent, True, "查询完成。")
        response["data"] = result

        if intent == "query_applications":
            rows = result.get("applications", [])
            response["message"] = f"目前共有 {len(rows) if isinstance(rows, list) else 0} 条投递记录。"
        elif intent == "query_interviews":
            rows = result.get("interviews", [])
            response["message"] = f"该时间范围内共有 {len(rows) if isinstance(rows, list) else 0} 场面试。"
        elif intent == "query_missing_info":
            rows = result.get("items", [])
            response["message"] = f"共有 {len(rows) if isinstance(rows, list) else 0} 条记录需要补充信息。"
        elif intent == "query_application_status":
            status = result.get("status")
            if status == "found":
                application = result.get("application")
                if isinstance(application, dict):
                    response["message"] = (
                        f"{application.get('company')} {application.get('position')}"
                        f"目前状态为：{application.get('status')}。"
                    )
            elif status == "ambiguous":
                response["ok"] = False
                response["message"] = "同一公司存在多条投递记录，请补充岗位后再查询。"
            elif status == "needs_company":
                response["ok"] = False
                response["message"] = "请补充需要查询的公司名称。"
            else:
                response["ok"] = False
                response["message"] = "没有找到该公司的投递记录。"
        return response

    def _preview_response(
        self,
        intent: str,
        result: dict[str, object],
        db_path: DbPath | None,
    ) -> dict[str, object]:
        if result.get("requires_clarification"):
            response = _base_response(intent, False, "同一公司存在多条投递记录，请补充岗位后重试。")
            response["data"] = {"candidates": result.get("candidates", [])}
            return response
        if intent == "preview_interview" and result.get("needs_application_creation"):
            return _base_response(
                intent,
                False,
                "面试未匹配到投递记录，请先创建投递或补充准确的公司信息。",
            )
        if intent == "preview_status_update" and result.get("needs_application_match"):
            parsed = result.get("parsed")
            if isinstance(parsed, dict) and parsed.get("company") == "待补充":
                return _base_response(intent, False, "请补充公司名称后再更新状态。")
            return _base_response(intent, False, "未找到对应公司的投递记录，无法预览状态更新。")

        missing = result.get("missing")
        if not isinstance(missing, dict):
            missing = None
        required = missing.get("required", []) if missing else []
        if required:
            response = _base_response(intent, False, "必要信息不完整，请补充后重新发送。")
            response["data"] = {"parsed": result.get("parsed"), "missing": missing}
            return response

        preview_id = uuid4().hex
        with self._lock:
            self._pending[preview_id] = PendingPreview(
                action=intent,
                preview=result,
                database_path=resolve_database_path(db_path).resolve(),
                expires_at=self.clock() + self.preview_ttl,
            )

        fields = dict(result.get("parsed", {})) if isinstance(result.get("parsed"), dict) else {}
        warnings: list[str] = []
        if missing and missing.get("recommended"):
            warnings.append("存在建议补充的字段，可确认后再补充完善。")
        if intent == "preview_interview":
            fields["matched_application"] = result.get("matched_application")
        elif intent == "preview_status_update":
            matched = result.get("matched_application")
            if isinstance(matched, dict):
                fields = {
                    "company": matched.get("company"),
                    "position": matched.get("position"),
                    "old_status": matched.get("status"),
                    "new_status": result.get("new_status"),
                }

        messages = {
            "preview_application": "已识别为新增投递，请确认以下信息。",
            "preview_interview": "已识别为新增面试，请确认以下信息。",
            "preview_status_update": "已识别为状态更新，请确认以下信息。",
        }
        response = _base_response(intent, True, messages[intent])
        response["preview"] = {
            "preview_id": preview_id,
            "type": PREVIEW_TYPES[intent],
            "fields": fields,
            "missing": missing,
            "warnings": warnings,
        }
        response["requires_confirmation"] = True
        return response

    def confirm_agent_preview(
        self,
        preview_id: str,
        db_path: DbPath | None = None,
    ) -> dict[str, object]:
        with self._lock:
            pending = self._pending.get(preview_id)
            if pending is None:
                raise PreviewNotFoundError("preview_id 不存在")
            if pending.consumed:
                raise PreviewConflictError("该预览已经确认，不能重复操作")
            if self.clock() >= pending.expires_at:
                raise PreviewConflictError("该预览已经过期，请重新发送原始指令")
            if resolve_database_path(db_path).resolve() != pending.database_path:
                raise PreviewConflictError("该预览与当前数据库不匹配，请重新发送原始指令")

            try:
                result = self.registry.run_confirm_tool(
                    pending.action,
                    preview=pending.preview,
                    db_path=db_path,
                )
            except ValueError as exc:
                raise AgentBusinessError(str(exc)) from exc
            pending.consumed = True

        messages = {
            "preview_application": ("confirm_application", "投递记录已保存。"),
            "preview_interview": ("confirm_interview", "面试记录已保存。"),
            "preview_status_update": ("confirm_status_update", "投递状态已更新。"),
        }
        intent, message = messages[pending.action]
        response = _base_response(intent, True, message)
        response["data"] = result if isinstance(result, dict) else {"result": result}
        return response


_DEFAULT_CONTROLLER = AgentController()


def handle_agent_message(
    text: str,
    db_path: DbPath | None = None,
    base_date: date | None = None,
) -> dict[str, object]:
    return _DEFAULT_CONTROLLER.handle_agent_message(text, db_path=db_path, base_date=base_date)


def confirm_agent_preview(
    preview_id: str,
    db_path: DbPath | None = None,
) -> dict[str, object]:
    return _DEFAULT_CONTROLLER.confirm_agent_preview(preview_id, db_path=db_path)
