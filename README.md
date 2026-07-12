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

1. 启动 LM Studio Local Server。
2. 加载支持 tool use 的模型。
3. 设置环境变量，PowerShell 示例：

```powershell
$env:MINI_AGENT_MODEL="qwen2.5-7b-instruct"
$env:LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1"
```

4. 运行：

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

```powershell
python -m pytest
```

当前测试结果：

```text
67 passed
```

## Notes

- 本项目默认使用本地 SQLite，数据文件不会提交到仓库。
- LM Studio 中的模型名需要与 `MINI_AGENT_MODEL` 保持一致。
- 写库操作采用“预览 -> 确认 -> 保存”流程。
