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
    jobhunt_preview_interview,
    jobhunt_preview_status_update,
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

STATUS_UPDATE_KEYWORDS = (
    "一面通过",
    "二面通过",
    "三面通过",
    "HR面通过",
    "通过了",
    "挂了",
    "没过",
    "未通过",
    "被拒",
    "拒了",
    "offer",
    "拿到 offer",
    "已放弃",
    "放弃",
)

INTERVIEW_STAGE_KEYWORDS = (
    "一面",
    "二面",
    "三面",
    "HR面",
    "群面",
)

INTERVIEW_TIME_KEYWORDS = (
    "今天",
    "明天",
    "后天",
    "下周",
    "周一",
    "周二",
    "周三",
    "周四",
    "周五",
    "周六",
    "周日",
    "上午",
    "下午",
    "晚上",
    "几点",
    "点",
)

INTERVIEW_SIGNAL_KEYWORDS = (
    "面试",
    "通知",
    "电话",
    "腾讯会议",
    "飞书会议",
    "线下",
)

APPLICATION_STATUS_QUERY_KEYWORDS = (
    "面试状态",
    "到哪一步",
    "当前状态",
    "投递状态",
    "进展怎么样",
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
    compact_text = text.replace(" ", "")

    if any(keyword in text for keyword in ("哪些信息没填完整", "没填完整", "缺失信息", "待补充")):
        return "jobhunt_check_missing_info", {}
    if any(
        keyword in text
        for keyword in ("未来一个月", "未来30天", "一个月内", "近一个月", "最近", "近期")
    ) and "面试" in text:
        return "jobhunt_list_interviews", {"range": "next_thirty_days"}
    if "未来一周" in text and "面试" in text:
        return "unsupported_interview_range", {}
    if (
        any(keyword in compact_text for keyword in ("未来三天", "未来3天", "近三天", "近3天"))
        and "面试" in text
    ):
        return "jobhunt_list_interviews", {"range": "next_three_days"}
    if "本周" in text and "面试" in text:
        return "jobhunt_list_interviews", {"range": "this_week"}
    if "今天" in text and "面试" in text:
        return "jobhunt_list_interviews", {"range": "today"}
    if "明天" in text and "面试" in text:
        return "jobhunt_list_interviews", {"range": "tomorrow"}
    if any(keyword in text for keyword in ("我现在投了哪些公司", "投递记录", "已投递", "求职台账")):
        return "jobhunt_list_applications", {}

    return None


def is_status_update_input(user_input: str) -> bool:
    text = user_input.strip()
    return any(keyword in text for keyword in STATUS_UPDATE_KEYWORDS)


def is_interview_input(user_input: str) -> bool:
    text = user_input.strip()
    if is_status_update_input(text):
        return False

    has_stage = any(keyword in text for keyword in INTERVIEW_STAGE_KEYWORDS)
    has_time = any(keyword in text for keyword in INTERVIEW_TIME_KEYWORDS)
    return has_stage and has_time


def is_application_status_query(user_input: str) -> bool:
    text = user_input.strip()
    return any(keyword in text for keyword in APPLICATION_STATUS_QUERY_KEYWORDS)


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


def _find_application_for_interview(
    interview: dict,
    applications: list[dict],
) -> dict | None:
    for application in applications:
        if _application_matches_interview(application, interview):
            return application
    return None


def _format_interview(item: dict, applications: list[dict] | None = None) -> str:
    application = _find_application_for_interview(item, applications or [])
    progress = "待补充"
    if application and not _is_blank_display_value(application.get("status")):
        progress = str(application.get("status"))

    return (
        f"- {item.get('company', '-')}"
        f" | {item.get('position', '-')}"
        f" | 时间：{item.get('interview_time', '-')}"
        f" | 进度：{progress}"
    )


def _is_blank_display_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in {"", "待补充"}
    return False


def _same_id(left: object, right: object) -> bool:
    return left is not None and right is not None and str(left) == str(right)


def _application_matches_interview(application: dict, interview: dict) -> bool:
    if _same_id(application.get("id"), interview.get("application_id")):
        return True

    app_company = application.get("company")
    interview_company = interview.get("company")
    if not app_company or app_company != interview_company:
        return False

    interview_position = interview.get("position")
    if _is_blank_display_value(interview_position):
        return True

    return application.get("position") == interview_position


def _filter_applications_for_interviews(
    interviews: list[dict],
    applications: list[dict],
) -> list[dict]:
    filtered = []
    seen = set()

    for application in applications:
        if not any(
            _application_matches_interview(application, interview)
            for interview in interviews
        ):
            continue

        key = application.get("id")
        if key is None:
            key = (application.get("company"), application.get("position"))
        if key in seen:
            continue
        seen.add(key)
        filtered.append(application)

    return filtered


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

    if "interviews" in data:
        interviews = data.get("interviews") or []
        if not interviews:
            return "该范围内没有面试记录。"
        applications = data.get("applications") or []
        return "面试记录：\n" + "\n".join(
            _format_interview(item, applications) for item in interviews
        )

    if "applications" in data:
        applications = data.get("applications") or []
        if not applications:
            return "当前还没有投递记录。"
        return "当前投递记录：\n" + "\n".join(
            _format_application(item) for item in applications
        )

    if "missing_info" in data:
        return "缺失信息检查结果：\n" + json.dumps(
            data["missing_info"],
            ensure_ascii=False,
            indent=2,
        )

    return json.dumps(data, ensure_ascii=False, indent=2)


def format_status_update_preview(preview: dict) -> str:
    matched = preview.get("matched_application") or {}
    parsed = preview.get("parsed") or {}

    if preview.get("needs_application_match"):
        return (
            "状态更新预览失败：没有匹配到对应投递记录。\n"
            f"- 公司：{parsed.get('company', '-')}\n"
            f"- 新状态：{preview.get('new_status', '-')}\n"
            "请先确认该公司是否已有投递记录。"
        )

    return (
        "状态更新预览：\n"
        f"- 公司：{matched.get('company', parsed.get('company', '-'))}\n"
        f"- 岗位：{matched.get('position', parsed.get('position', '-'))}\n"
        f"- 当前状态：{matched.get('status', '-')}\n"
        f"- 新状态：{preview.get('new_status', parsed.get('status', '-'))}\n"
        "确认无误后请输入“确认更新”。"
    )


def format_interview_preview(preview: dict) -> str:
    parsed = preview.get("parsed") or {}
    matched = preview.get("matched_application")
    match_text = "已匹配" if matched else "未匹配"
    extra = (
        "\n未找到匹配投递记录，确认保存时会同时创建投递记录。"
        if preview.get("needs_application_creation")
        else ""
    )

    return (
        "面试记录预览：\n"
        f"- 公司：{parsed.get('company', '-')}\n"
        f"- 岗位：{parsed.get('position', '-')}\n"
        f"- 阶段：{parsed.get('stage', '-')}\n"
        f"- 时间：{parsed.get('interview_time', '-')}\n"
        f"- 方式：{parsed.get('interview_method', '-')}\n"
        f"- 匹配投递：{match_text}"
        f"{extra}\n\n"
        "确认无误后请输入“确认保存”。"
    )


def format_application_status_matches(user_input: str, applications: list[dict]) -> str:
    matches = [
        application
        for application in applications
        if application.get("company") and application["company"] in user_input
    ]

    if not matches:
        return "未找到该公司的投递记录。"

    return "当前状态：\n" + "\n".join(_format_application(item) for item in matches)


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
            if result.get("ok") is True:
                applications_result = _tool_result_dict(jobhunt_list_applications())
                if applications_result.get("ok") is True:
                    result.setdefault("data", {})["applications"] = (
                        applications_result.get("data") or {}
                    ).get("applications", [])
        elif name == "jobhunt_check_missing_info":
            result = _tool_result_dict(jobhunt_check_missing_info())
        elif name == "unsupported_interview_range":
            result = {
                "ok": False,
                "error": "V1 当前支持：今天、明天、未来三天、未来30天、本周。暂不支持未来一周范围查询。",
            }
        else:
            result = {"ok": False, "error": f"不支持的固定查询：{name}"}
    except Exception as e:
        result = {"ok": False, "error": f"查询失败：{e}"}

    message = format_jobhunt_result(result)
    console.print(f"\nAgent:\n{message}")
    save_direct_turn(state, user_input, message)
    return True


def handle_application_status_query(user_input: str, state: dict) -> bool:
    if not is_application_status_query(user_input):
        return False

    try:
        result = _tool_result_dict(jobhunt_list_applications())
        if result.get("ok") is True:
            applications = (result.get("data") or {}).get("applications") or []
            message = format_application_status_matches(user_input, applications)
        else:
            message = format_jobhunt_result(result)
    except Exception as e:
        message = f"查询失败：{e}"

    console.print(f"\nAgent:\n{message}")
    save_direct_turn(state, user_input, message)
    return True


def handle_status_update_preview(user_input: str, state: dict) -> bool:
    if not is_status_update_input(user_input):
        return False

    try:
        result = _tool_result_dict(jobhunt_preview_status_update(text=user_input))
    except Exception as e:
        result = {"ok": False, "error": f"状态更新预览失败：{e}"}

    if result.get("ok") is not True:
        message = format_jobhunt_result(result)
        console.print(f"\nAgent:\n{message}")
        save_direct_turn(state, user_input, message)
        return True

    preview = result.get("data")
    if not isinstance(preview, dict) or preview.get("action") != "preview_status_update":
        message = "状态更新预览失败：工具返回了无法识别的预览结果。"
        console.print(f"\nAgent:\n{message}")
        save_direct_turn(state, user_input, message)
        return True

    message = format_status_update_preview(preview)
    if preview.get("needs_application_match"):
        state["pending_preview"] = None
    else:
        state["pending_preview"] = preview

    console.print(f"\nAgent:\n{message}")
    save_direct_turn(state, user_input, message)
    return True


def handle_interview_preview_fallback(user_input: str, state: dict) -> bool:
    if not is_interview_input(user_input):
        return False

    try:
        result = _tool_result_dict(jobhunt_preview_interview(text=user_input))
    except Exception as e:
        result = {"ok": False, "error": f"面试预览失败：{e}"}

    if result.get("ok") is not True:
        message = format_jobhunt_result(result)
        console.print(f"\nAgent:\n{message}")
        save_direct_turn(state, user_input, message)
        return True

    preview = result.get("data")
    if not isinstance(preview, dict) or preview.get("action") != "preview_interview":
        message = "面试预览失败：工具返回了无法识别的预览结果。"
        console.print(f"\nAgent:\n{message}")
        save_direct_turn(state, user_input, message)
        return True

    state["pending_preview"] = preview
    message = format_interview_preview(preview)
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

        if handle_application_status_query(user_input, state):
            continue

        if handle_status_update_preview(user_input, state):
            continue

        if handle_interview_preview_fallback(user_input, state):
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
