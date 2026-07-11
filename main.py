"""
Mini CLI Agent 主程序。

运行：
    python main.py
"""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.panel import Panel

from config import MODEL
from history import (
    new_session_id,
    save_session,
    load_session,
    format_session_list,
)
from llm import run_agent_turn
from skills import list_skills, load_skill
from tools import (
    jobhunt_check_missing_info,
    jobhunt_list_applications,
    jobhunt_list_interviews,
    jobhunt_save_application,
    jobhunt_save_interview,
    jobhunt_update_status,
    tool_names,
)


console = Console()

PREVIEW_ACTIONS = {
    "preview_application",
    "preview_interview",
    "preview_status_update",
}

CONFIRM_KEYWORDS = (
    "确认保存",
    "请你保存",
    "请保存",
    "保存",
    "确认更新",
    "确认",
    "是的",
    "好的",
    "可以",
)

EXPLICIT_SAVE_CONFIRM_KEYWORDS = (
    "确认保存",
    "请你保存",
    "请保存",
    "保存",
    "确认更新",
)


def print_help() -> None:
    console.print(
        """
[bold]可用命令[/bold]

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

[bold]示例输入[/bold]

workspace 里有哪些文件？
帮我总结 README.md
现在几点？
""".strip()
    )


def handle_command(
    user_input: str,
    state: dict,
) -> None:
    """
    处理 slash command。
    直接修改 state。
    """
    parts = user_input.split()
    command = parts[0].lower()

    if command == "/help":
        print_help()

    elif command == "/tools":
        console.print("[bold]工具列表[/bold]")
        for name in tool_names():
            console.print(f"- {name}")

    elif command == "/skills":
        skills = list_skills()
        if not skills:
            console.print("暂无可用 skill。")
        else:
            console.print("[bold]可用 Skills[/bold]")
            for name in skills:
                marker = " [green](active)[/green]" if name == state.get("active_skill_name") else ""
                console.print(f"- {name}{marker}")

    elif command == "/load-skill":
        if len(parts) < 2:
            console.print("[red]用法：/load-skill <name>[/red]")
            return

        name = parts[1]
        try:
            content = load_skill(name)
            state["active_skill_name"] = name.replace(".md", "")
            state["active_skill_content"] = content
            console.print(f"[green]已加载 skill：{state['active_skill_name']}[/green]")
        except Exception as e:
            console.print(f"[red]加载 skill 失败：{e}[/red]")

    elif command == "/clear-skill":
        state["active_skill_name"] = None
        state["active_skill_content"] = ""
        console.print("[green]已清除当前 skill。[/green]")

    elif command == "/history-list":
        console.print(format_session_list())

    elif command == "/history-load":
        if len(parts) < 2:
            console.print("[red]用法：/history-load <number>[/red]")
            return

        try:
            index = int(parts[1])
            data = load_session(index)
            state["session_id"] = data.get("session_id") or new_session_id()
            state["base_messages"] = data.get("messages", [])
            state["pending_preview"] = None

            skill_name = data.get("active_skill_name")
            state["active_skill_name"] = None
            state["active_skill_content"] = ""

            if skill_name:
                try:
                    state["active_skill_content"] = load_skill(skill_name)
                    state["active_skill_name"] = skill_name
                except Exception:
                    console.print(
                        f"[yellow]历史会话记录了 skill={skill_name}，但当前 skills 目录中无法加载它。[/yellow]"
                    )

            console.print(
                f"[green]已加载历史会话：{state['session_id']}，消息数：{len(state['base_messages'])}[/green]"
            )

        except Exception as e:
            console.print(f"[red]加载历史失败：{e}[/red]")

    elif command == "/save":
        path = save_session(
            state["session_id"],
            MODEL,
            state["base_messages"],
            state.get("active_skill_name"),
        )
        console.print(f"[green]已保存：{path}[/green]")

    elif command == "/debug":
        state["debug"] = not state.get("debug", False)
        console.print(f"[green]debug={state['debug']}[/green]")

    elif command in ["/exit", "/quit"]:
        path = save_session(
            state["session_id"],
            MODEL,
            state["base_messages"],
            state.get("active_skill_name"),
        )
        console.print(f"[green]已保存：{path}[/green]")
        console.print("Bye.")
        sys.exit(0)

    else:
        console.print(f"[red]未知命令：{command}。输入 /help 查看帮助。[/red]")


def _load_tool_json(content: str) -> dict | None:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def update_pending_preview_from_messages(state: dict) -> None:
    """
    从最近的工具结果中记录待确认预览。
    只记录 JobHunt preview 工具返回的 ok=true/data/action。
    """
    for message in reversed(state.get("base_messages", [])):
        if message.get("role") != "tool":
            continue

        data = _load_tool_json(message.get("content", ""))
        if not data or data.get("ok") is not True:
            continue

        preview = data.get("data")
        if isinstance(preview, dict) and preview.get("action") in PREVIEW_ACTIONS:
            state["pending_preview"] = preview
            return


def is_confirm_input(user_input: str) -> bool:
    compact = user_input.strip().replace("，", "").replace("。", "")
    return any(keyword in compact for keyword in CONFIRM_KEYWORDS)


def is_explicit_save_confirm_input(user_input: str) -> bool:
    compact = user_input.strip().replace("，", "").replace("。", "")
    return any(keyword in compact for keyword in EXPLICIT_SAVE_CONFIRM_KEYWORDS)


def detect_fixed_query(user_input: str) -> tuple[str, dict] | None:
    text = user_input.strip()

    if any(keyword in text for keyword in ("哪些信息没填完整", "缺失信息", "待补充")):
        return "jobhunt_check_missing_info", {}
    if "今天" in text and "面试" in text:
        return "jobhunt_list_interviews", {"range": "today"}
    if "明天" in text and "面试" in text:
        return "jobhunt_list_interviews", {"range": "tomorrow"}
    if any(keyword in text for keyword in ("未来三天有哪些面试", "近三天有哪些面试")):
        return "jobhunt_list_interviews", {"range": "next_three_days"}
    if "本周" in text and "面试" in text:
        return "jobhunt_list_interviews", {"range": "this_week"}
    if any(keyword in text for keyword in ("我现在投了哪些公司", "投递记录", "已投递", "求职台账")):
        return "jobhunt_list_applications", {}

    return None


def _tool_result_dict(result_text: str) -> dict:
    data = json.loads(result_text)
    if not isinstance(data, dict):
        raise ValueError("工具返回结果不是 JSON 对象")
    return data


def _format_application(item: dict) -> str:
    return (
        f"- {item.get('company', '-')}"
        f" | {item.get('position', '-')}"
        f" | 状态：{item.get('status', '-')}"
    )


def _format_interview(item: dict) -> str:
    return (
        f"- {item.get('company', '-')}"
        f" | {item.get('position', '-')}"
        f" | {item.get('stage', '-')}"
        f" | {item.get('interview_time', '-')}"
    )


def format_jobhunt_result(result: dict) -> str:
    """
    将 JobHunt 工具统一 JSON 包装结果转成简洁中文。
    """
    if result.get("ok") is not True:
        return f"操作失败：{result.get('error', '未知错误')}"

    data = result.get("data") or {}
    if not isinstance(data, dict):
        return str(data)

    if data.get("saved") and "application" in data and "interview" not in data:
        application = data["application"]
        return f"已保存投递：{application.get('company')}，{application.get('position')}。"

    if data.get("saved") and "interview" in data:
        interview = data["interview"]
        status = data.get("updated_status")
        suffix = f"；投递状态已更新为：{status}" if status else ""
        return (
            f"已保存面试：{interview.get('company')}，"
            f"{interview.get('stage')}，{interview.get('interview_time')}{suffix}。"
        )

    if data.get("updated") and "application" in data:
        application = data["application"]
        return f"已更新状态：{application.get('company')} -> {application.get('status')}。"

    if "applications" in data:
        applications = data.get("applications") or []
        if not applications:
            return "当前还没有投递记录。"
        return "当前投递记录：\n" + "\n".join(
            _format_application(item) for item in applications
        )

    if "interviews" in data:
        interviews = data.get("interviews") or []
        if not interviews:
            return "该范围内没有面试记录。"
        return "面试记录：\n" + "\n".join(_format_interview(item) for item in interviews)

    if "missing_info" in data:
        return "缺失信息检查结果：\n" + json.dumps(
            data["missing_info"],
            ensure_ascii=False,
            indent=2,
        )

    return json.dumps(data, ensure_ascii=False, indent=2)


def save_direct_turn(state: dict, user_input: str, assistant_text: str) -> None:
    state["base_messages"].append({"role": "user", "content": user_input})
    state["base_messages"].append({"role": "assistant", "content": assistant_text})
    save_session(
        state["session_id"],
        MODEL,
        state["base_messages"],
        state.get("active_skill_name"),
    )


def handle_pending_confirmation(user_input: str, state: dict) -> bool:
    preview = state.get("pending_preview")
    if not preview:
        if not is_explicit_save_confirm_input(user_input):
            return False
        message = "当前没有待确认的预览，请先输入投递/面试/状态信息。"
        console.print(f"\nAgent:\n{message}")
        save_direct_turn(state, user_input, message)
        return True

    if not is_confirm_input(user_input):
        return False

    action = preview.get("action")
    try:
        if action == "preview_application":
            result = _tool_result_dict(
                jobhunt_save_application(preview=preview, confirmed=True)
            )
        elif action == "preview_interview":
            result = _tool_result_dict(
                jobhunt_save_interview(
                    preview=preview,
                    confirmed=True,
                    create_application_if_missing=bool(
                        preview.get("needs_application_creation")
                    ),
                )
            )
        elif action == "preview_status_update":
            result = _tool_result_dict(
                jobhunt_update_status(preview=preview, confirmed=True)
            )
        else:
            result = {"ok": False, "error": f"不支持的待确认预览类型：{action}"}
    except Exception as e:
        result = {"ok": False, "error": f"确认操作失败：{e}"}

    message = format_jobhunt_result(result)
    if result.get("ok") is True:
        state["pending_preview"] = None

    console.print(f"\nAgent:\n{message}")
    save_direct_turn(state, user_input, message)
    return True


def handle_fixed_query(user_input: str, state: dict) -> bool:
    query = detect_fixed_query(user_input)
    if query is None:
        return False

    name, arguments = query
    try:
        if name == "jobhunt_list_applications":
            result = _tool_result_dict(jobhunt_list_applications())
        elif name == "jobhunt_list_interviews":
            result = _tool_result_dict(jobhunt_list_interviews(**arguments))
        elif name == "jobhunt_check_missing_info":
            result = _tool_result_dict(jobhunt_check_missing_info())
        else:
            result = {"ok": False, "error": f"不支持的固定查询：{name}"}
    except Exception as e:
        result = {"ok": False, "error": f"查询失败：{e}"}

    message = format_jobhunt_result(result)
    console.print(f"\nAgent:\n{message}")
    save_direct_turn(state, user_input, message)
    return True


def main() -> None:
    state = {
        "session_id": new_session_id(),
        "base_messages": [],
        "active_skill_name": None,
        "active_skill_content": "",
        "pending_preview": None,
        "debug": False,
    }

    console.print(
        Panel.fit(
            f"[bold]Mini CLI Agent[/bold]\nmodel={MODEL}\n输入 /help 查看命令，输入 /exit 退出。",
            title="Started",
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except KeyboardInterrupt:
            console.print("\n[yellow]收到 Ctrl+C，正在保存并退出。[/yellow]")
            save_session(
                state["session_id"],
                MODEL,
                state["base_messages"],
                state.get("active_skill_name"),
            )
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            handle_command(user_input, state)
            continue

        if handle_pending_confirmation(user_input, state):
            continue

        if handle_fixed_query(user_input, state):
            continue

        state["base_messages"].append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        try:
            state["base_messages"] = run_agent_turn(
                state["base_messages"],
                state.get("active_skill_content", ""),
                debug=state.get("debug", False),
            )
            update_pending_preview_from_messages(state)

            save_session(
                state["session_id"],
                MODEL,
                state["base_messages"],
                state.get("active_skill_name"),
            )

        except Exception as e:
            console.print(f"[red]Agent 执行失败：{e}[/red]")
            console.print("[yellow]请确认 LM Studio Local Server 已启动，并且模型已加载。[/yellow]")


if __name__ == "__main__":
    main()
