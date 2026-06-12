import json
import uuid
from typing import Any

from ag_ui.core import RunAgentInput


def get_value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def latest_user_text(input_data: RunAgentInput) -> str:
    for message in reversed(input_data.messages or []):
        if get_value(message, "role") != "user":
            continue

        text = message_text(message)
        if text:
            return text

    return ""


def message_text(message: Any) -> str:
    content = get_value(message, "content", "")
    if isinstance(content, str):
        return content

    text_parts: list[str] = []
    for part in content or []:
        part_type = get_value(part, "type")
        if part_type in {"text", "input_text", "output_text"}:
            text = get_value(part, "text")
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def create_response_input(input_data: RunAgentInput) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for message in input_data.messages or []:
        role = get_value(message, "role")
        if role not in {"user", "assistant", "system", "developer"}:
            continue

        text = message_text(message)
        if not text:
            continue

        messages.append(
            {
                "type": "message",
                "role": role,
                "content": text,
            }
        )

    if messages:
        return messages

    return [
        {
            "type": "message",
            "role": "user",
            "content": latest_user_text(input_data),
        }
    ]


def thread_id(input_data: RunAgentInput) -> str:
    return get_value(input_data, "thread_id") or f"thread_{uuid.uuid4().hex}"


def run_id(input_data: RunAgentInput) -> str:
    return get_value(input_data, "run_id") or f"run_{uuid.uuid4().hex}"


def stringify(value: Any) -> str:
    if isinstance(value, str):
        return value

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", exclude_none=True)

    return json.dumps(value, ensure_ascii=False)
