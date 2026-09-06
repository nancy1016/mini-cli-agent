# JobHuntLedger-Agent V2-01B-2：前端 Agent 对话操作台

## 本轮目标

将 V2-01A 的 Agent 助手占位页升级为自然语言操作台，对接 V2-01B-1 提供的 Chat/Confirm API。查询操作直接展示结果，新增投递、新增面试和状态更新先展示预览，用户确认后才请求后端写入。

## 页面结构

- 页面标题和写入安全说明
- 可点击填入输入框的示例指令
- 用户、Agent 和错误消息区域
- 查询结果简洁列表
- 投递、面试、状态更新三类预览卡片
- 多行输入框与发送按钮
- 请求 Loading 和错误状态

支持 Enter 发送、Shift+Enter 换行。存在待确认预览时，输入区会被禁用，用户需要先确认或取消当前操作。

当前标签页内的聊天记录使用浏览器 `sessionStorage` 临时保存。切换页面再返回时会恢复消息；后端返回的待确认预览也可恢复展示，但确认请求仍只提交 `preview_id`，不会提交或信任前端保存的完整预览字段。

## API

- `POST /api/v1/agent/chat`：发送自然语言并取得查询结果或预览。
- `POST /api/v1/agent/confirm`：使用服务器生成的 `preview_id` 确认操作。

前端复用 `api/client.ts` 的统一 API 地址和错误处理，并新增通用 JSON POST 方法。

## 安全确认机制

- 前端只展示后端返回的结构化预览。
- 确认请求只提交 `preview_id`，不回传完整 Preview 作为写库依据。
- 请求期间禁用确认按钮，避免重复点击。
- 确认失败时保留预览并显示后端错误。
- 取消不会调用 Confirm API，并提示“本次未写入数据库”。
- 状态查询出现多条候选记录时按普通 Agent 回复展示，并提示使用投递日期、来源、岗位、当前状态或重复记录处理来进一步区分；写入类歧义仍由后端阻止确认。

## 为什么本轮不做 LM Studio

本轮只完成前端与确定性规则 Agent 的交互闭环。LM Studio Provider、模型状态和 Qwen2.5 回答增强将在 V2-01B-3 实现。

## 为什么不做普通 CRUD

本页面以自然语言为主入口，由 Agent 识别查询或写入意图。写入通过预览和确认完成，不增加独立的投递或面试表单。

## 启动方式

后端从项目根目录启动：

```powershell
conda run -n mini-agent python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

前端从 `frontend` 目录启动：

```powershell
npm.cmd run dev
```

浏览器访问 `http://127.0.0.1:5173/agent`。

## 测试命令

```powershell
cd frontend
npm.cmd run build
cd ..

conda run --no-capture-output -n mini-agent python -m pytest -q
```

## 已知边界

- 消息只在当前浏览器标签页的 `sessionStorage` 中临时保留；关闭标签页后不保证保留，不提供跨设备或多会话同步。
- 同一时间只展示一个待确认 Preview。
- 取消操作不会通知后端删除 Pending Preview，服务器端记录会按有效期失效。
- 当前没有前端单元测试和浏览器自动化测试。
- 当前回复来自规则 Agent，尚未由本地模型润色。

## 后续 V2-01B-3

- LM Studio Provider 与模型健康检查
- `qwen2.5-7b-instruct` 回答增强
- Unknown 意图辅助识别
- Agent 页面与设置页展示模型状态
- 模型不可用时继续使用规则 Agent
