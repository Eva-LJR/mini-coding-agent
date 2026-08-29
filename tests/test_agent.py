from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from coding_agent.agent import CodingAgent
from coding_agent.model_client import ModelReply, ToolCall
from coding_agent.tools import WorkspaceTools


class FakeClient:
    def __init__(self) -> None:
        self.call_count = 0
        self.seen_messages: list[list[dict[str, Any]]] = []

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelReply:
        self.call_count += 1
        self.seen_messages.append(list(messages))
        self.assert_tools(tools)
        if self.call_count == 1:
            arguments = {"path": "answer.txt", "content": "done\n"}
            return ModelReply(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="write_file",
                        arguments=arguments,
                        raw_arguments=json.dumps(arguments),
                    )
                ],
            )
        return ModelReply(content="任务已完成并写入文件。", tool_calls=[])

    @staticmethod
    def assert_tools(tools: list[dict[str, Any]]) -> None:
        names = {item["function"]["name"] for item in tools}
        if "write_file" not in names:
            raise AssertionError("write_file tool was not supplied")


class CodingAgentTests(unittest.TestCase):
    def test_agent_executes_tool_and_returns_final_answer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = FakeClient()
            logs: list[str] = []
            agent = CodingAgent(
                client,
                WorkspaceTools(root),
                max_steps=3,
                log=logs.append,
            )

            answer = agent.run("创建答案文件")

            self.assertEqual(answer, "任务已完成并写入文件。")
            self.assertEqual((root / "answer.txt").read_text(encoding="utf-8"), "done\n")
            second_request = client.seen_messages[1]
            tool_messages = [item for item in second_request if item["role"] == "tool"]
            self.assertEqual(len(tool_messages), 1)
            self.assertEqual(tool_messages[0]["tool_call_id"], "call_1")
            self.assertTrue(any("write_file" in line for line in logs))


if __name__ == "__main__":
    unittest.main()
