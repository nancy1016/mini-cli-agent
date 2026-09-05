"""V2-01B-1 规则 Agent 对话与确认 API。"""

from fastapi import APIRouter, HTTPException, Request

from backend.app.schemas.agent import AgentChatRequest, AgentConfirmRequest, AgentResponse
from backend.app.services.agent_controller import (
    AgentBusinessError,
    PreviewConflictError,
    PreviewNotFoundError,
)


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentResponse)
def agent_chat(payload: AgentChatRequest, request: Request) -> dict[str, object]:
    controller = request.app.state.agent_controller
    return controller.handle_agent_message(
        payload.text,
        db_path=request.app.state.database_path,
    )


@router.post("/confirm", response_model=AgentResponse)
def agent_confirm(payload: AgentConfirmRequest, request: Request) -> dict[str, object]:
    controller = request.app.state.agent_controller
    try:
        return controller.confirm_agent_preview(
            payload.preview_id,
            db_path=request.app.state.database_path,
        )
    except PreviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PreviewConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AgentBusinessError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
