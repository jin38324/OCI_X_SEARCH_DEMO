import json
import os
from pathlib import Path
from collections.abc import AsyncIterator
from typing import Any

from ag_ui.core import RunAgentInput
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from utils.agui_impl import encoded_response_events
from utils.prompt import INSTRUCTIONS


load_dotenv()

AGENT_MODEL_ID = os.getenv("AGENT_MODEL_ID", "xai.grok-4.3")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


client = AsyncOpenAI(
    # 调用端点
    base_url=_required_env("OCI_GENAI_BASE_URL"),
    # API密钥
    api_key=_required_env("OCI_GENAI_KEY")
)


class Agent:
    def __init__(
        self,
        *,
        name: str,
        client: AsyncOpenAI,
        model: str,
        instructions: str,
        tools: list[dict[str, Any]],
    ) -> None:
        self.name = name
        self.client = client
        self.model = model
        self.instructions = instructions
        self.tools = tools

    async def run(
        self,
        input_data: RunAgentInput,
        *,
        accept: str | None = None,
    ) -> AsyncIterator[str]:
        async for event in encoded_response_events(
            input_data=input_data,
            client=self.client,
            model=self.model,
            instructions=self.instructions,
            tools=self.tools,
            accept=accept,
        ):
            yield event


doc_agent = Agent(
    name=AGENT_NAME,
    client=client,
    model=AGENT_MODEL_ID,
    instructions=INSTRUCTIONS,
    tools=[
        {"type": "x_search"},
        # {"type": "web_search"},
        {"type": "code_interpreter"},
    ],
)

app = FastAPI(title=AGENT_NAME)


@app.post("/")
async def run_agent(input_data: RunAgentInput, request: Request) -> StreamingResponse:
    return StreamingResponse(
        doc_agent.run(
            input_data,
            accept=request.headers.get("accept"),
        ),
        media_type="text/event-stream",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
