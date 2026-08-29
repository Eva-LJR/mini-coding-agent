from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str


@dataclass(frozen=True)
class ModelReply:
    content: str
    tool_calls: list[ToolCall]


class ModelClientProtocol(Protocol):
    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelReply:
        ...


class OpenAICompatibleClient:
    """Thin adapter around an OpenAI-compatible Chat Completions endpoint."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelReply:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        message = response.choices[0].message
        parsed_calls: list[ToolCall] = []

        for call in message.tool_calls or []:
            raw = call.function.arguments or "{}"
            try:
                arguments = json.loads(raw)
                if not isinstance(arguments, dict):
                    raise ValueError("工具参数必须是 JSON 对象")
            except (json.JSONDecodeError, ValueError) as exc:
                arguments = {"__parse_error__": str(exc)}
            parsed_calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=arguments,
                    raw_arguments=raw,
                )
            )

        return ModelReply(content=message.content or "", tool_calls=parsed_calls)
