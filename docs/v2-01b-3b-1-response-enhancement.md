# V2-01B-3B-1：LM Studio 查询回答润色

## 目标

在规则 Agent 已完成意图识别和真实数据查询后，使用 LM Studio 中的
`qwen2.5-7b-instruct` 仅润色查询类回答的 `message`。结构化 `data` 始终来自
原 ToolRegistry，模型不可改写业务数据，也不参与业务判断和写入。

## 调用边界

仅以下成功查询可调用模型：

- `query_applications`
- `query_interviews`
- `query_missing_info`
- `query_application_status`

新增投递、添加面试、更新状态的预览与确认，以及 `unknown` 意图均不调用模型。
现有 `preview_id` 服务端确认机制保持不变。

## 调用与降级

Provider 使用 OpenAI-compatible 的 `POST /v1/chat/completions`，固定非流式调用，
不传递 tools 或 tool_choice，最大输出为 300 tokens。Prompt 仅包含用户问题、已识别意图、
规则回答和真实工具结果，并明确禁止编造数据、修改事实或声称执行写入。
Prompt 同时禁止承诺主动通知、定时提醒或后台推送；没有面试记录时，只能说明当前没有记录，
或提示用户后续可以随时回来查询。若模型仍输出此类承诺，安全检查会放弃模型回答并回退规则回答。

健康检查与生成请求使用独立超时：`LM_STUDIO_HEALTH_TIMEOUT_SECONDS` 默认 2 秒，
`LM_STUDIO_CHAT_TIMEOUT_SECONDS` 默认 30 秒。两者都可以通过同名环境变量覆盖。

模型超时、连接失败、HTTP 错误、返回格式异常、空回答、超长回答或包含未授权操作声明时，
接口自动保留规则回答。响应中的 `model.used` 表示本条消息是否采用模型结果，
`fallback_reason` 使用 `provider_missing`、`timeout`、`connection_error`、`http_error`、
`invalid_response`、`empty_content`、`too_long` 或 `unsafe_content` 区分降级原因，且不包含 API Key。

`query_applications` 传给模型的是独立构造的精简摘要，只保留公司、岗位、状态、投递日期、来源、
地点和招聘类型，并附记录数量。API 返回的原始 `data` 不会因此改变。正常的“投递记录”、
“投递状态”、“已完成投递”或“建议补充”等查询描述不属于危险声明；只有模型明确声称已经替用户
保存、写库、修改、自动投递或主动通知时才触发 `unsafe_content` 回退。

## 前端展示

查询回复显示以下来源标记之一：

- `LM Studio 已润色`
- `模型不可用，已使用规则回答`
- `规则 Agent 回答`

来源信息随现有 sessionStorage 临时会话一起保留，不新增后端会话或数据库表。
Agent 缺失信息列表只在展示层将数据库字段映射为中文标签，不修改 API 数据或数据库字段名。

## 测试约束

自动化测试通过 MockTransport 或桩 Provider 覆盖成功、失败、超时、异常响应、降级和安全边界。
默认测试不访问真实 LM Studio，也不向真实 `/chat/completions` 发送请求。

## 已知风险

聊天生成默认等待 30 秒。本地模型首次加载或机器负载较高时仍可能超时，系统会安全回退到规则回答；
可根据人工验收结果通过 `LM_STUDIO_CHAT_TIMEOUT_SECONDS` 调整，无需修改代码。
