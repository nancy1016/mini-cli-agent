# JobHuntLedger-Agent V2-01B-3A：LM Studio Provider 与模型状态

## 本轮目标

为 Web Agent 增加独立的 LM Studio Provider 健康检查能力，并在 Agent 助手和系统设置页面展示服务及模型状态。规则 Agent 仍独立负责查询、预览和确认，LM Studio 不可用不会阻断这些基础能力。

## Provider 架构

- `LLMProvider` 定义最小 `health_check()` 契约。
- `LMStudioProvider` 实现 LM Studio OpenAI-compatible `/models` 检查。
- Provider 构造时不联网，只有调用健康检查时才发送请求。
- 健康检查使用完整的 `{base_url}/models` URL，并设置 `trust_env=False`，避免本机 `127.0.0.1` 请求误走系统代理。
- `/v1/models` 是本地只读探测，不发送 Authorization Header；配置中的 API Key 仍不返回前端，并保留给后续真正需要鉴权的模型调用。
- FastAPI 通过 `app.state.model_provider` 注入 Provider，测试可注入 Stub。
- 本阶段不修改 `AgentController`，也不让模型参与业务数据处理。

## 配置项

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `LM_STUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | OpenAI-compatible API 根地址 |
| `MINI_AGENT_MODEL` | `qwen2.5-7b-instruct` | 需要精确匹配的模型 ID |
| `LM_STUDIO_API_KEY` | `lm-studio` | Bearer 请求凭据，不通过 API 返回 |
| `LM_STUDIO_HEALTH_TIMEOUT_SECONDS` | `2` | 健康检查超时秒数 |

Base URL 包含 `/v1`，因为 LM Studio 暴露的模型接口是 `/v1/models`。配置模型使用 LM Studio 当前加载模型的 API Model Identifier `qwen2.5-7b-instruct`，Provider 不做模糊匹配或自动模型切换。

旧 CLI 根目录 `config.py` 仍保留自己的默认模型 `qwen/qwen3-1.7b`。V2-01B-3A 不修改或统一旧 CLI 配置；需要同时运行时，应通过环境变量明确模型。

## Model Health API

```text
GET /api/v1/model/health
```

响应包含 Provider、Base URL、配置模型、已加载模型、服务可连接状态、模型可用状态和错误说明，不包含 API Key。LM Studio 不可用时仍返回 HTTP 200，并在响应体中使用 `ok=false` 表示业务状态。

该接口不连接数据库、不调用 AgentController，也不调用 `/chat/completions`。

## 前端展示

- Agent 助手顶部显示规则 Agent、LM Studio 和当前模型的紧凑状态条。
- 模型状态检查失败不会禁用输入、Preview 或 Confirm，也不会清空 `sessionStorage` 会话。
- 系统设置页展示完整只读状态并提供刷新按钮。
- 页面不提供模型切换、地址编辑、API Key 展示或配置保存。

## 为什么不调用 chat/completions

本阶段先建立可测试的 Provider 边界和故障降级能力。如果同时接入模型回答，会引入 Prompt、输出校验、超时降级和回答一致性等额外问题，扩大本阶段范围。

因此本阶段也不做回答润色和 unknown 意图辅助。模型不会参与意图识别、Preview、Confirm 或数据库写入。

## 自动化测试隔离

- Provider 单元测试使用 `httpx.MockTransport`。
- Model Health API 测试通过 `create_app(model_provider=StubProvider)` 注入 Stub。
- 默认测试不依赖 LM Studio 是否启动，不访问真实模型，也不访问正式数据库。
- 既有真实 LM Studio CLI 冒烟测试仍由 `RUN_LMSTUDIO_E2E=1` 显式开启，默认跳过。

## 启动与可选人工验收

从项目根目录启动后端：

```powershell
conda run -n mini-agent python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

在用户明确允许真实只读检查后，可访问：

```text
http://127.0.0.1:8000/api/v1/model/health
```

该检查只会请求 LM Studio 的 `GET /v1/models`，不会调用模型生成，也不会写数据库。

## 测试命令

```powershell
conda run --no-capture-output -n mini-agent python -m pytest backend/tests/test_lmstudio_provider.py backend/tests/test_model_health_api.py -q
conda run --no-capture-output -n mini-agent python -m pytest -q

cd frontend
npm.cmd run build
```

## 后续 V2-01B-3B

- 在规则 Agent 结果确定后进行可降级的回答润色。
- 为 unknown 意图增加受约束的模型辅助识别。
- 明确模型输出 Schema、超时策略和安全边界。
- 模型继续不得绕过 Preview/Confirm 或直接写数据库。
