from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coding_agent.agent import CodingAgent
from coding_agent.config import Settings
from coding_agent.model_client import OpenAICompatibleClient
from coding_agent.tools import WorkspaceTools


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="一个不依赖 Agent 框架的简易 Coding Agent")
    parser.add_argument("--workspace", default=".", help="Agent 可以操作的工作目录")
    parser.add_argument("--task", help="直接指定任务；省略时会交互输入")
    parser.add_argument("--model", help="覆盖 .env 中的 MODEL_NAME")
    parser.add_argument("--base-url", help="覆盖 .env 中的 MODEL_BASE_URL")
    parser.add_argument("--max-steps", type=int, default=20, help="最大模型调用轮数")
    parser.add_argument("--timeout", type=int, default=60, help="单条命令超时秒数")
    parser.add_argument("-y", "--yes", action="store_true", help="自动批准模型请求的命令（仅在可信工作区使用）")
    return parser.parse_args()


def ask_command(command: str) -> bool:
    print(f"\n模型请求执行命令：\n  {command}")
    answer = input("是否允许？[y/N] ").strip().lower()
    return answer in {"y", "yes"}


def main() -> int:
    args = parse_args()
    try:
        settings = Settings.from_env(
            Path(args.workspace),
            model=args.model,
            base_url=args.base_url,
            max_steps=args.max_steps,
            command_timeout=args.timeout,
            auto_approve_commands=args.yes,
        )
        task = args.task or input("请输入编程任务：\n> ").strip()
        client = OpenAICompatibleClient(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.base_url,
        )
        confirm = (lambda _command: True) if settings.auto_approve_commands else ask_command
        tools = WorkspaceTools(
            settings.workspace,
            command_timeout=settings.command_timeout,
            confirm_command=confirm,
        )
        agent = CodingAgent(client, tools, max_steps=settings.max_steps)
        result = agent.run(task)
        print(f"\n=== Agent 最终回答 ===\n{result}")
        return 0
    except KeyboardInterrupt:
        print("\n已由用户中止。", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\n运行失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
