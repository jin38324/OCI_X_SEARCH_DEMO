import uuid
from collections.abc import AsyncIterator
from typing import Any, cast

from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,

    ReasoningMessageStartEvent,
    ReasoningStartEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    ReasoningEndEvent,



    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder
from openai import AsyncOpenAI

from .handdler import create_response_input, get_value, run_id, stringify, thread_id


def _extract_tool_call_id(item_id: str) -> str:
    return item_id.split("_")[-1]


class ResponseStreamState:
    def __init__(self) -> None:
        self.item_to_tool_call: dict[str, str] = {}


async def response_events(
    input_data: RunAgentInput,
    client: AsyncOpenAI,
    model: str,
    instructions: str,
    tools: list[dict[str, Any]],
) -> AsyncIterator[BaseEvent]:
    current_thread_id = thread_id(input_data)
    current_run_id = run_id(input_data)
    state = ResponseStreamState()

    yield RunStartedEvent(
        type=EventType.RUN_STARTED,
        thread_id=current_thread_id,
        run_id=current_run_id,
        input=input_data,
    )

    # try:
    stream = await client.responses.create(
        model=model,
        input=cast(Any, create_response_input(input_data)),
        instructions=instructions,
        tools=cast(Any, tools),
        # include=["web_search_call.action.sources"],
        parallel_tool_calls=True,
        stream=True,
    )

    async for response_event in stream:
        try:
            agui_event = map_response_event(response_event, state)
            if isinstance(agui_event, list):
                for event in agui_event:
                    yield event
            elif agui_event:
                yield agui_event
        except Exception as exc:
            print(f"Error mapping response event: {exc}")
            print(response_event)
            break       


    yield RunFinishedEvent(
        type=EventType.RUN_FINISHED,
        thread_id=current_thread_id,
        run_id=current_run_id,
    )
    # except Exception as exc:
    #     yield RunErrorEvent(
    #         type=EventType.RUN_ERROR,
    #         message=str(exc),
    #         code="response_run_error",
    #     )


async def encoded_response_events(
    input_data: RunAgentInput,
    client: AsyncOpenAI,
    model: str,
    instructions: str,
    tools: list[dict[str, Any]],
    accept: str | None,
) -> AsyncIterator[str]:
    encoder = EventEncoder(accept=accept)
    async for event in response_events(input_data, client, model, instructions, tools):
        yield encoder.encode(event)


def map_response_event(response_event: Any, state: ResponseStreamState) -> BaseEvent | list[BaseEvent] | None:
    event_type = get_value(response_event, "type")
    
    item = get_value(response_event, "item",{})
    item_type = get_value(item, "type","")
    message_id = get_value(item, "id","")
    if not message_id:
        message_id = get_value(response_event, "item_id","")

    # 开始事件
    if event_type == "response.output_item.added":
        # 创建推理事件
        if item_type == "reasoning":
            return ReasoningStartEvent(message_id=message_id)
        # assistant message开始
        elif item_type == "message":
            return TextMessageStartEvent(message_id=message_id)
        # 创建工具调用事件
        elif item_type in {"custom_tool_call"}:
            tool_call_id = get_value(item, "call_id")
            tool_call_name = get_value(item, "name")
            state.item_to_tool_call[message_id] = tool_call_id
            print(f"Tool call started: {tool_call_name} with ID: {tool_call_id}")
            return ToolCallStartEvent(
                tool_call_id=tool_call_id,
                tool_call_name = tool_call_name
            )
        elif item_type in {"web_search_call"}:
            tool_call_id = _extract_tool_call_id(message_id)
            tool_call_name = item_type
            return ToolCallStartEvent(
                tool_call_id=tool_call_id,
                tool_call_name = tool_call_name
            )
        elif item_type in {"code_interpreter_call"}:
            tool_call_id = _extract_tool_call_id(message_id)
            tool_call_name = item_type
            return ToolCallStartEvent(
                tool_call_id=tool_call_id,
                tool_call_name = tool_call_name
            )

    # 推理消息开始
    elif event_type == "response.reasoning_summary_part.added":
        return ReasoningMessageStartEvent(role="reasoning", message_id=message_id)

    # 推理消息内容
    elif event_type == "response.reasoning_summary_text.delta":
        delta = get_value(response_event, "delta", "")
        return ReasoningMessageContentEvent(message_id=message_id, delta=delta)

    # 推理消息结束
    elif event_type == "response.reasoning_summary_part.done":
        return ReasoningMessageEndEvent(message_id=message_id)

    # assistant message内容
    elif event_type == "response.output_text.delta":
        message_id = str(get_value(response_event, "item_id"))
        delta = get_value(response_event, "delta", "")
        return TextMessageContentEvent(message_id=message_id, delta=delta)

    # 结束事件
    elif event_type == "response.output_item.done":
        # 推理结束
        if item_type == "reasoning":
            return ReasoningEndEvent(message_id=message_id)

        # assistant message结束
        elif item_type == "message":
            return TextMessageEndEvent(message_id=message_id)

        # 工具调用结束
        elif item_type in {"custom_tool_call"}:
            tool_call_id = get_value(item, "call_id")
            return [
                ToolCallArgsEvent(            
                    tool_call_id=tool_call_id, 
                    delta=get_value(item, "input")
                ),              
                ToolCallEndEvent(tool_call_id=tool_call_id),                
                ToolCallResultEvent(
                    message_id=message_id,
                    tool_call_id=tool_call_id,
                    content="X search completed.",
                ),  
                
            ]
        elif item_type in {"web_search_call"}:
            tool_call_id = _extract_tool_call_id(message_id)
            action = get_value(item, "action")
            if hasattr(action, "query"):
                input = {"query": get_value(action, "query")}
            else:
                input = action
            return [
                ToolCallArgsEvent(            
                    tool_call_id=tool_call_id, 
                    delta=stringify(input)
                ),  
                ToolCallEndEvent(tool_call_id=tool_call_id),
                ToolCallResultEvent(
                    message_id=message_id,
                    tool_call_id=tool_call_id,
                    content=stringify(get_value(item, "action"))
                ),
            ]

        elif item_type in {"code_interpreter_call"}:            
            tool_call_id = _extract_tool_call_id(message_id)
            code = get_value(item, "code")
            outputs = get_value(item, "outputs")
            return [
                ToolCallArgsEvent(            
                    tool_call_id=tool_call_id, 
                    delta=stringify({"code": code})
                ),                   
                ToolCallEndEvent(tool_call_id=tool_call_id),
                ToolCallResultEvent(
                    message_id=message_id,
                    tool_call_id=tool_call_id,
                    content=str(outputs)
                ),
            ]

    # elif event_type == "response.completed":
    #     return _annotations_event(response_event)

    elif event_type in {"error", "response.failed", "response.incomplete"}:
        return RunErrorEvent(
            message=get_value(response_event, "message") or stringify(response_event),
            code=event_type,
        )

    else:
        return None

