"""JobHuntLedger-Agent V2-01A FastAPI 入口。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import agent, applications, dashboard, health, interviews, missing, model
from backend.app.core.config import API_PREFIX, DATABASE_PATH, PROJECT_NAME
from backend.app.services.agent_controller import AgentController
from backend.app.services.llm_provider import LLMProvider
from backend.app.services.lmstudio_provider import LMStudioProvider


LOCAL_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app(
    database_path: str | Path = DATABASE_PATH,
    model_provider: LLMProvider | None = None,
) -> FastAPI:
    """创建可注入临时数据库路径的应用实例。"""
    application = FastAPI(
        title=PROJECT_NAME,
        version="v2-01b-1",
        description="JobHuntLedger-Agent Web API 与规则 Agent 安全确认闭环",
    )
    application.state.database_path = Path(database_path)
    application.state.model_provider = model_provider or LMStudioProvider()
    application.state.agent_controller = AgentController(model_provider=model_provider)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=LOCAL_FRONTEND_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix=API_PREFIX)
    application.include_router(dashboard.router, prefix=API_PREFIX)
    application.include_router(applications.router, prefix=API_PREFIX)
    application.include_router(interviews.router, prefix=API_PREFIX)
    application.include_router(missing.router, prefix=API_PREFIX)
    application.include_router(agent.router, prefix=API_PREFIX)
    application.include_router(model.router, prefix=API_PREFIX)
    return application


app = create_app(model_provider=LMStudioProvider())
