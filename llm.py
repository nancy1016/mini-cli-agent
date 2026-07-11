"""
LM Studio 调用封装。

本版本直接使用 Python 标准库调用 LM Studio 的 OpenAI-compatible API。
这样可以避开 OpenAI SDK 与部分 LM Studio tools 请求的兼容性问题。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from config import (
    MODEL,
    SYSTEM_PROMPT,
    MAX_TOOL_ROUNDS,
    LM_STUDIO_BASE_URL,
    LM_STUDIO_API_KEY,
)
from tools import TOOL_SCHEMAS, run_tool_call


def _post_chat_completion(payload: dict) -> dict:
    """
    向 LM Studio Local Server 发送 chat/completions 请求。

    使用标准库 urllib，避免 SDK 对 tools/function calling 请求做额外转换。
    """
    url = LM_STUDIO_BASE_URL.rstrip("/") + "/chat/completions"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LM_STUDIO_API_KEY}",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"LM Studio HTTP 请求失败，状态码 {e.code}，返回内容：{error_body}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 LM Studio Local Server：{e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LM Studio 返回了无法解析的 JSON：{e}") from e


def build_messages(base_messages: list[dict], active_skill_content: str = "") -> list[dict]:
    """
    构造发给 LLM 的 messages。

    base_messages 不保存 system prompt；
    每次请求时动态注入 system prompt 和 active skill。
    """
    system_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    if active_skill_content:
        system_messages.append(
            {
                "role": "system",
                "content": f"当前已加载 Skill：\n\n{active_skill_content}",
            }
        )

    return system_messages + base_messages


def remove_system_messages(messages: list[dict]) -> list[dict]:
    """
    保存历史时去掉动态注入的 system messages。
    """
    return [m for m in messages if m.get("role") != "system"]


def normalize_assistant_message(message: dict) -> dict:
    """
    把 LM Studio 返回的 assistant message 转成普通 dict。
    重点是保留 tool_calls，后续发回 LM Studio 时需要它。
    """
    result = {
        "role": "assistant",
        "content": message.get("content") or "",
    }

    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        result["tool_calls"] = []

        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            result["tool_calls"].append(
                {
                    "id": tool_call.get("id"),
                    "type": tool_call.get("type", "function"),
                    "function": {
                        "name": function.get("name"),
                        "arguments": function.get("arguments") or "{}",
                    },
                }
            )

    return result


def chat_once_with_tools(messages: list[dict]) -> dict:
    """
    单次调用 LM Studio，允许模型返回 tool_calls。
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOL_SCHEMAS,
        "tool_choice": "auto",
        "temperature": 0.3,
    }
    result = _post_chat_completion(payload)

    message = result["choices"][0]["message"]
    return normalize_assistant_message(message)


def chat_once_without_tools(messages: list[dict]) -> dict:
    """
    不带工具的最终回答。
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.3,
    }
    result = _post_chat_completion(payload)

    message = result["choices"][0]["message"]

    return {
        "role": "assistant",
        "content": message.get("content") or "",
    }


def run_agent_turn(
    base_messages: list[dict],
    active_skill_content: str = "",
    debug: bool = False,
) -> list[dict]:
    """
    执行一个 Agent turn。

    输入 base_messages，返回更新后的 base_messages。
    """
    messages = build_messages(base_messages, active_skill_content)

    for round_idx in range(1, MAX_TOOL_ROUNDS + 1):
        assistant_msg = chat_once_with_tools(messages)
        messages.append(assistant_msg)

        tool_calls = assistant_msg.get("tool_calls") or []

        if not tool_calls:
            content = assistant_msg.get("content", "")
            print("\nAgent:")
            print(content)
            return remove_system_messages(messages)

        if debug:
            print(f"\n[DEBUG] Tool round {round_idx}")
            print(f"[DEBUG] tool_calls={tool_calls}")

        for call in tool_calls:
            tool_result = run_tool_call(call)

            tool_result_msg = {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": tool_result.get("content", ""),
            }

            if debug:
                print(f"[DEBUG] Tool result:")
                print(tool_result_msg["content"])

            messages.append(tool_result_msg)

        # 工具结果已经放进 messages 后，再让模型给最终回答。
        # 这里不再传 tools，避免模型一直重复调用工具。
        final_msg = chat_once_without_tools(messages)
        messages.append(final_msg)

        print("\nAgent:")
        print(final_msg.get("content", ""))

        return remove_system_messages(messages)

    error_msg = f"ERROR: 工具调用超过最大轮数 {MAX_TOOL_ROUNDS}，已停止。"

    messages.append(
        {
            "role": "assistant",
            "content": error_msg,
        }
    )

    print(f"\nAgent:\n{error_msg}")
    return remove_system_messages(messages)
