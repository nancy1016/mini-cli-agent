# JobHuntLedger-Agent V2-01B-1：后端规则 Agent 与安全确认闭环

## 本轮目标

在 V2-01A Web 骨架上增加确定性规则 Agent，使自然语言输入能够查询求职数据，或生成投递、面试、状态更新预览。所有写入必须在用户通过独立确认接口提交服务器生成的 `preview_id` 后发生。

本阶段不实现前端 Agent 操作台，不接入 LM Studio，也不修改 V1 `jobhunt` 核心业务。

## 后端架构

处理链路为：

```text
自然语言 → IntentRouter → ToolRegistry → V1 Web Adapter → V1 Service/Repository
                                ↓
                     查询结果或 Pending Preview
                                ↓
                    preview_id → Confirm → 写入
```

- `IntentRouter`：按固定优先级区分查询、预览和 unknown。
- `ToolRegistry`：只注册明确允许的查询、预览和确认工具，不直接写 SQL。
- `AgentController`：编排路由和工具，维护应用实例内的 Pending Preview。
- `v1_adapter`：继续作为 Web 层复用 V1 能力的唯一边界。

## 支持意图

- `query_applications`
- `query_interviews`
- `query_missing_info`
- `query_application_status`
- `preview_application`
- `preview_interview`
- `preview_status_update`
- `unknown`

## API

### POST `/api/v1/agent/chat`

请求：

```json
{"text": "这周有哪些面试？"}
```

查询直接返回 `data`；写入类意图只返回结构化 `preview` 和 `preview_id`，不会写数据库。

### POST `/api/v1/agent/confirm`

请求：

```json
{"preview_id": "服务器生成的 UUID"}
```

后端从内存 Pending Store 取回原始预览并调用对应确认工具。不存在返回 404，过期或重复确认返回 409，业务数据问题返回 400。

## preview_id 安全机制

- 前端不能把完整 preview 作为写库依据回传。
- Pending Preview 默认有效期为 15 分钟。
- 同一个 ID 只能成功确认一次。
- 确认检查和写入在 Controller 锁内完成，避免并发重复提交。
- 服务重启后未确认的 preview 失效，这是本地单用户 MVP 的可接受边界。
- 同公司存在多条投递时返回候选项，不自动选择第一条。
- 面试没有匹配投递时不自动创建投递。

## 为什么不依赖 LM Studio

V2-01B-1 优先冻结稳定、安全、可测试的 Agent 业务链路。模型 Provider、意图泛化和回答润色将在 V2-01B-3 接入；本阶段响应中的 `model.used` 固定为 `false`。

## 为什么不实现前端

前端需要依赖稳定的 Chat/Confirm 响应契约。V2-01B-1 先通过 API 测试验证查询、预览和确认边界，V2-01B-2 再实现 Agent 对话操作台和预览卡片。

## 测试

```powershell
conda run -n mini-agent python -m pytest backend/tests/test_intent_router.py -q
conda run -n mini-agent python -m pytest backend/tests/test_agent_controller.py -q
conda run -n mini-agent python -m pytest backend/tests/test_agent_api.py -q
conda run -n mini-agent python -m pytest -q
```

所有 Agent 测试使用 `tmp_path` 下的临时 SQLite，不调用真实模型，不读写正式 `data/jobhunt.db`。

## 后续计划

- V2-01B-2：React Agent 对话操作台、消息气泡、预览卡片和确认交互。
- V2-01B-3：LM Studio Provider、`qwen2.5-7b-instruct` 状态检查、意图辅助和回答增强。
