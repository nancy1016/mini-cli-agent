
# mini-cli-agent

一个本地运行的 CLI AI Agent Demo，基于 **Python + LM Studio + OpenAI-compatible API** 实现。

项目用于演示一个最小可用 Agent 的核心流程：

```text
用户输入
↓
本地大模型判断是否需要调用工具
↓
Python 执行真实工具函数
↓
工具结果回传给模型
↓
模型生成最终回答
````

当前版本支持：

* CLI 命令行交互
* LM Studio 本地模型调用
* OpenAI-compatible API 接入
* Tool Calling / Function Calling
* Markdown Skill 动态加载
* JSON 会话历史保存与加载
* `workspace/` 目录下的安全文件读取

---

## Features

### 本地模型调用

项目通过 LM Studio 启动本地模型服务，并使用 OpenAI Python SDK 访问本地接口：

```text
http://localhost:1234/v1
```

默认模型配置在 `config.py` 中：

```text
MODEL = os.getenv("MINI_AGENT_MODEL", "qwen/qwen3-1.7b")
```

可以通过环境变量覆盖模型名：

```powershell
$env:MINI_AGENT_MODEL="你的模型ID"
python main.py
```

---

### 工具调用

当前内置 3 个工具：

- `get_current_datetime`：获取当前本地日期和时间
- `list_workspace_files`：列出 `workspace/` 目录下的文件
- `read_text_file`：读取 `workspace/` 目录下的文本文件内容

工具定义和执行逻辑位于：

```text
tools.py
```

工具调用流程：

```text
用户提出需求
↓
模型返回 tool_calls
↓
Python 根据 tool_calls 执行真实函数
↓
Python 将工具结果作为 role=tool 消息回传给模型
↓
模型根据工具结果生成最终回答
```

---

### Skill 动态加载

项目支持从 `skills/` 目录加载 Markdown Skill。

当前内置：

```text
skills/
  python_reviewer.md
  translator.md
```

Skill 本质上是一段额外的 system prompt，用于临时改变 Agent 的工作模式。

常用命令：

```text
/load-skill translator
/load-skill python_reviewer
/clear-skill
```

说明：

* `/load-skill translator`：加载翻译助手模式
* `/load-skill python_reviewer`：加载 Python 代码审查模式
* `/clear-skill`：清除当前会话正在使用的 Skill，不会删除 `skills/` 目录下的 `.md` 文件

---

### 会话历史

项目支持将会话保存到：

```text
history/
```

常用命令：

```text
/save
/history-list
/history-load 1
```

说明：

* `/save`：手动保存当前会话
* `/history-list`：列出历史会话
* `/history-load <number>`：加载指定历史会话
* `/exit`：保存并退出

---

### 安全边界

当前版本只提供只读工具，不支持危险操作。

明确不支持：

```text
不执行 shell 命令
不写入文件
不删除文件
不读取 workspace 之外的路径
```

文件读取工具 `read_text_file` 只能读取：

```text
workspace/
```

目录下的文本文件。

---

## Project Structure

```text
mini-cli-agent/
  main.py                 # CLI 主程序入口
  llm.py                  # LM Studio / OpenAI-compatible API 调用封装
  tools.py                # 工具定义、工具 schema、工具执行逻辑
  skills.py               # Skill 列表与加载逻辑
  history.py              # 会话历史保存与加载
  config.py               # 项目配置
  utils.py                # 通用辅助函数

  requirements.txt        # Python 依赖
  README.md               # 项目说明文档
  .gitignore              # Git 忽略规则

  skills/
    python_reviewer.md    # Python 代码审查 Skill
    translator.md         # 翻译 Skill

  workspace/
    README.md             # 测试工作区文件

  history/
    .gitkeep              # 保留 history 目录
```

---

## Requirements

推荐环境：

```text
Python 3.10+
LM Studio
本地聊天模型，例如 qwen/qwen3-1.7b
```

Python 依赖：

```text
openai>=1.40.0
rich>=13.7.0
```

---

## Installation

### 1. 创建虚拟环境

可以使用 conda：

```powershell
conda create -n mini-agent python=3.10 -y
conda activate mini-agent
```

进入项目目录：

```powershell
cd E:\Code\PyCharm\mini-cli-agent
```

安装依赖：

```powershell
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

验证依赖：

```powershell
python -c "import openai; import rich; print('ok')"
```

如果输出：

```text
ok
```

说明依赖安装成功。

---

## LM Studio Setup

### 1. 启动本地模型

打开 LM Studio，加载一个本地聊天模型。

当前项目默认使用：

```text
qwen/qwen3-1.7b
```

如果使用其他模型，需要修改 `config.py` 中的：

```text
MODEL = os.getenv("MINI_AGENT_MODEL", "qwen/qwen3-1.7b")
```

---

### 2. 启动 Local Server

在 LM Studio 中进入 Developer / Local Server 页面，启动本地服务。

默认 API 地址：

```text
http://localhost:1234/v1
```

---

### 3. 验证 API

在 PowerShell 中执行：

```powershell
Invoke-RestMethod http://localhost:1234/v1/models | ConvertTo-Json -Depth 5
```

如果能看到已加载模型，例如：

```json
{
  "data": [
    {
      "id": "qwen/qwen3-1.7b",
      "object": "model"
    }
  ],
  "object": "list"
}
```

说明 LM Studio Server 已经可以被项目访问。

---

## Usage

在项目根目录执行：

```powershell
python main.py
```

启动后会看到类似：

```text
Mini CLI Agent
model=qwen/qwen3-1.7b
输入 /help 查看命令，输入 /exit 退出。
```

输入：

```text
/help
```

查看可用命令。

---

## Commands

```text
/help                     显示帮助
/tools                    查看工具列表
/skills                   查看可用 skills
/load-skill <name>        加载 skill，例如 /load-skill python_reviewer
/clear-skill              清除当前 skill
/history-list             查看历史会话
/history-load <number>    加载历史会话，例如 /history-load 1
/save                     手动保存当前会话
/debug                    开关 debug 模式
/exit                     保存并退出
```

---

## Examples

### 普通聊天

```text
你好，请用中文简单介绍一下你自己
```

---

### 获取当前时间

```text
请使用工具获取当前时间，然后告诉我现在几点。
```

---

### 列出 workspace 文件

```text
请使用工具列出 workspace 里的文件。
```

---

### 读取并总结文件

```text
请使用工具读取 workspace 里的 README.md，然后总结它。
```

---

### 测试路径安全边界

```text
请使用工具读取 ../config.py
```

预期结果：Agent 应提示不能访问 `workspace/` 之外的路径。

---

### 加载翻译 Skill

```text
/load-skill translator
```

然后输入：

```text
请把这句话翻译成英文：这个项目是一个本地 CLI Agent Demo。
```

---

### 加载 Python Reviewer Skill

```text
/load-skill python_reviewer
```

然后输入：

```text
请帮我审查下面这段 Python 代码：print('hello')
```

---

## Architecture

```text
用户
↓
main.py：CLI 输入层 / 命令分发层
↓
llm.py：Agent 编排与模型调用层
↓
LM Studio Local Server
↓
本地模型 qwen/qwen3-1.7b
↓
模型返回 content 或 tool_calls
↓
tools.py：工具注册与执行层
↓
工具结果 role=tool 回传给模型
↓
模型生成最终回答
↓
main.py 输出到终端
↓
history.py 保存会话历史
```

---

## Tool Calling Flow

以这个问题为例：

```text
请使用工具获取当前时间，然后告诉我现在几点。
```

实际流程：

```text
用户输入一次问题
↓
Python Agent 第一次请求模型
↓
模型返回 tool_calls：get_current_datetime({})
↓
Python 执行 get_current_datetime()
↓
工具返回当前时间
↓
Python Agent 第二次请求模型，并附带工具结果
↓
模型根据工具结果生成最终回答
↓
终端打印回答
```

因此，一次用户问题可能对应：

```text
模型请求：2 次
工具执行：1 次
```

---

## Current Limitations

当前版本是第一版 Demo，主要用于理解 Agent 的基础机制。

当前不支持：

```text
shell 执行
文件写入
联网搜索
上下文自动压缩
长期记忆数据库
MCP
```


