"""
项目配置。
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 可以通过环境变量覆盖：
MODEL = os.getenv("MINI_AGENT_MODEL", "qwen/qwen3-1.7b")

LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")

WORKSPACE_DIR = BASE_DIR / "workspace"
SKILLS_DIR = BASE_DIR / "skills"
HISTORY_DIR = BASE_DIR / "history"

MAX_TOOL_ROUNDS = 5
MAX_TOOL_RESULT_CHARS = 5000

SYSTEM_PROMPT = """你是一个本地 CLI AI Agent。

除非用户明确要求其他语言，否则你必须始终使用简体中文回答。

你可以根据用户需求调用工具，但必须遵守以下规则：

1. 不要编造工具结果。
2. 如果需要查看本地文件，先使用 list_workspace_files 或 read_text_file 工具。
3. 你只能访问 workspace 目录下的文件。
4. 当工具返回 ERROR 时，要向用户解释错误，不要假装成功。
5. 回答要清晰、务实、可执行。
"""
