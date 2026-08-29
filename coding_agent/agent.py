from __future__ import annotations

import json
from typing import Any, Callable

from .model_client import ModelClientProtocol, ModelReply, ToolCall
from .prompts import SYSTEM_PROMPT
from .tools import TOOL_DEFINITIONS, WorkspaceTools


LogFunction = Callable[[str], None]


class CodingAgent:
    def __init__(
        self,
        client: ModelClientProtocol,
        tools: WorkspaceTools,
        *,
        max_steps: int = 20,
        log: LogFunction = print,
    ) -> None:
        self.client = client
        self.tools = tools
        self.max_steps = max_steps
        self.log = log

    def run(self, task: str) -> str:
        if not task.strip():
            raise ValueError("任务不能为空")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task.strip()},
        ]

        for step in range(1, self.max_steps + 1):
            self.log(f"\n[第 {step}/{self.max_steps} 轮] 正在请求模型...")
            reply = self.client.complete(messages, TOOL_DEFINITIONS)
            messages.append(self._assistant_message(reply))

            if not reply.tool_calls:
                if reply.content.strip():
                    self.log("[完成] 模型已返回最终结果。")
                    return reply.content.strip()
                raise RuntimeError("模型既没有返回文本，也没有调用工具")

            for call in reply.tool_calls:
                self.log(f"[工具] {call.name}({self._short_arguments(call)})")
                result = self.tools.execute(call.name, call.arguments)
                self.log(f"[结果] {self._short_result(result)}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        raise RuntimeError(f"达到最大执行轮数 {self.max_steps}，Agent 已停止以防止无限循环。")

    @staticmethod
    def _assistant_message(reply: ModelReply) -> dict[str, Any]:
        message: dict[str, Any] = {"role": "assistant", "content": reply.content or None}
        if reply.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.raw_arguments},
                }
                for call in reply.tool_calls
            ]
        return message

    @staticmethod
    def _short_arguments(call: ToolCall) -> str:
        shown = json.dumps(call.arguments, ensure_ascii=False)
        return shown if len(shown) <= 180 else shown[:177] + "..."

    @staticmethod
    def _short_result(result: str) -> str:
        compact = result.replace("\n", " ")
        return compact if len(compact) <= 240 else compact[:237] + "..."
