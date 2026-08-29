from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str | None
    model: str
    workspace: Path
    max_steps: int = 20
    command_timeout: int = 60
    auto_approve_commands: bool = False

    @classmethod
    def from_env(
        cls,
        workspace: str | Path,
        *,
        model: str | None = None,
        base_url: str | None = None,
        max_steps: int = 20,
        command_timeout: int = 60,
        auto_approve_commands: bool = False,
    ) -> "Settings":
        load_dotenv()
        api_key = os.getenv("MODEL_API_KEY", "").strip()
        chosen_model = (model or os.getenv("MODEL_NAME", "")).strip()
        chosen_base_url = (base_url or os.getenv("MODEL_BASE_URL", "")).strip() or None

        if not api_key:
            raise ValueError("缺少 MODEL_API_KEY，请复制 .env.example 为 .env 后填写。")
        if not chosen_model:
            raise ValueError("缺少 MODEL_NAME，请在 .env 中填写要调用的模型名称。")
        if max_steps < 1:
            raise ValueError("max_steps 必须大于 0。")

        root = Path(workspace).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"工作区不存在或不是目录：{root}")

        return cls(
            api_key=api_key,
            base_url=chosen_base_url,
            model=chosen_model,
            workspace=root,
            max_steps=max_steps,
            command_timeout=command_timeout,
            auto_approve_commands=auto_approve_commands,
        )
