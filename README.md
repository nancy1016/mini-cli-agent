# JobHuntLedger-Agent

## Overview

JobHuntLedger-Agent is a local job-hunting ledger Agent built with Python, SQLite, and LM Studio. It supports natural-language application, interview, and status updates, then saves confirmed records to a local SQLite database.

The project uses LM Studio as the local model entry point and keeps job-hunting data on the user's machine.

## Features

- 自然语言记录投递
- 预览后确认保存
- 自然语言记录面试
- 面试日期查询
- 投递状态更新
- 缺失信息检查
- SQLite 本地持久化
- LM Studio 本地模型调用
- pytest 自动化测试

## Tech Stack

- Python
- SQLite
- pytest
- LM Studio OpenAI-compatible API
- Function calling / tool calling

## Project Structure

- `main.py`：CLI 入口
- `llm.py`：LM Studio 调用封装
- `tools.py`：Agent 工具定义与分发
- `jobhunt/parser.py`：文本解析
- `jobhunt/service.py`：业务流程编排
- `jobhunt/repository.py`：SQLite 数据访问
- `jobhunt/reminders.py`：面试时间查询
- `jobhunt/missing.py`：缺失信息检查
- `tests/`：自动化测试

## Setup

1. 使用 Python 3.12 创建并激活项目虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2. 启动 LM Studio Local Server。
3. 加载支持 tool use 的模型。
4. 设置环境变量，PowerShell 示例：

```powershell
$env:MINI_AGENT_MODEL="qwen2.5-7b-instruct"
$env:LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1"
```

5. 运行：

```powershell
python main.py
```

## Usage Example

```text
/load-skill jobhunt_ledger
今天在官网投递了西安某科技公司的测试开发岗，地点西安。
确认保存
我现在投了哪些公司？
明天下午三点，西安某科技公司测试开发岗一面，电话通知的。
明天有哪些面试？
```

## Tests

安装开发和测试依赖：

```powershell
python -m pip install -r requirements-dev.txt
```

默认回归测试不需要启动 LM Studio，也不会读写正式求职数据库：

```powershell
python -m pytest
```

V1 冻结时的测试结果（Python 3.12）：

```text
109 passed, 7 skipped
```

默认跳过的 7 项是需要真实 LM Studio、已加载模型和工具调用能力的可选冒烟测试。配置模型后可显式运行：

```powershell
$env:RUN_LMSTUDIO_E2E="1"
$env:MINI_AGENT_MODEL="qwen2.5-7b-instruct"
$env:LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1"
python -m pytest tests/test_lmstudio_jobhunt_smoke.py -q
```

较长的双公司完整流程还需要设置：

```powershell
$env:RUN_LMSTUDIO_FULL_E2E="1"
```

## V2 Web MVP

V2-01A 增加了 FastAPI + React Web 主体骨架，并继续只读复用现有 SQLite 数据。安装新增后端依赖后，在项目根目录启动 API：

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

前端需要单独安装依赖并启动：

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`，API 文档位于 `http://127.0.0.1:8000/docs`。完整范围与启动说明见 `docs/v2-01a-web-mvp.md`。

## Notes

- 本项目默认使用本地 SQLite，数据文件不会提交到仓库。
- 默认测试使用 pytest 提供的临时目录和临时数据库，不会污染 `data/jobhunt.db`。
- LM Studio 中的模型名需要与 `MINI_AGENT_MODEL` 保持一致。
- 写库操作采用“预览 -> 确认 -> 保存”流程。
