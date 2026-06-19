"""
Mini CLI Agent 主程序。

运行：
    python main.py
"""

from __future__ import annotations

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
from tools import tool_names


console = Console()


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


def main() -> None:
    state = {
        "session_id": new_session_id(),
        "base_messages": [],
        "active_skill_name": None,
        "active_skill_content": "",
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
