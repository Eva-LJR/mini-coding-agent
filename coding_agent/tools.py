from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Callable


ConfirmCommand = Callable[[str], bool]


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "递归列出工作区内指定目录的文件。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "相对工作区的目录，默认为 ."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取工作区内的 UTF-8 文本文件，返回带行号的内容。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "相对工作区的文件路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "在工作区内创建或完整写入 UTF-8 文本文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对工作区的文件路径"},
                    "content": {"type": "string", "description": "完整文件内容"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "精确替换文件中的一段文本，适合局部修改。old_text 必须至少出现一次。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "replace_all": {"type": "boolean", "description": "是否替换全部匹配，默认 false"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "在工作区根目录运行一条终端命令，返回退出码、标准输出和错误输出。",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "要运行的单条命令"}},
                "required": ["command"],
            },
        },
    },
]


class WorkspaceTools:
    MAX_FILE_BYTES = 1_000_000
    MAX_OUTPUT_CHARS = 12_000
    MAX_LISTED_FILES = 500
    SKIPPED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__"}

    def __init__(
        self,
        root: Path,
        *,
        command_timeout: int = 60,
        confirm_command: ConfirmCommand | None = None,
    ) -> None:
        self.root = root.resolve()
        self.command_timeout = command_timeout
        self.confirm_command = confirm_command or (lambda _command: False)

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        if "__parse_error__" in arguments:
            return f"ERROR: 工具参数不是有效 JSON：{arguments['__parse_error__']}"
        try:
            if name == "list_files":
                return self.list_files(arguments.get("path", "."))
            if name == "read_file":
                return self.read_file(self._required(arguments, "path"))
            if name == "write_file":
                return self.write_file(
                    self._required(arguments, "path"), self._required(arguments, "content")
                )
            if name == "replace_in_file":
                return self.replace_in_file(
                    self._required(arguments, "path"),
                    self._required(arguments, "old_text"),
                    self._required(arguments, "new_text"),
                    bool(arguments.get("replace_all", False)),
                )
            if name == "run_command":
                return self.run_command(self._required(arguments, "command"))
            return f"ERROR: 未知工具：{name}"
        except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as exc:
            return f"ERROR: {type(exc).__name__}: {exc}"

    @staticmethod
    def _required(arguments: dict[str, Any], key: str) -> str:
        value = arguments.get(key)
        if not isinstance(value, str):
            raise ValueError(f"参数 {key} 必须是字符串")
        return value

    def _resolve(self, relative_path: str) -> Path:
        if not relative_path or "\x00" in relative_path:
            raise ValueError("路径为空或包含非法字符")
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("拒绝访问工作区之外的路径") from exc
        return candidate

    def list_files(self, relative_path: str = ".") -> str:
        target = self._resolve(relative_path)
        if not target.is_dir():
            raise ValueError(f"目录不存在：{relative_path}")

        files: list[str] = []
        for path in sorted(target.rglob("*")):
            if any(part in self.SKIPPED_DIRS for part in path.relative_to(self.root).parts):
                continue
            if path.is_file():
                files.append(path.relative_to(self.root).as_posix())
                if len(files) >= self.MAX_LISTED_FILES:
                    files.append(f"... 已达到 {self.MAX_LISTED_FILES} 个文件的显示上限")
                    break
        return "\n".join(files) if files else "(目录中没有文件)"

    def read_file(self, relative_path: str) -> str:
        target = self._resolve(relative_path)
        if not target.is_file():
            raise ValueError(f"文件不存在：{relative_path}")
        if target.stat().st_size > self.MAX_FILE_BYTES:
            raise ValueError("文件过大，拒绝一次性读取")
        content = target.read_text(encoding="utf-8")
        return "\n".join(f"{number:4d} | {line}" for number, line in enumerate(content.splitlines(), 1))

    def write_file(self, relative_path: str, content: str) -> str:
        if len(content.encode("utf-8")) > self.MAX_FILE_BYTES:
            raise ValueError("写入内容过大")
        target = self._resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: 已写入 {target.relative_to(self.root).as_posix()}（{len(content)} 字符）"

    def replace_in_file(self, relative_path: str, old: str, new: str, replace_all: bool) -> str:
        if old == "":
            raise ValueError("old_text 不能为空")
        target = self._resolve(relative_path)
        if not target.is_file():
            raise ValueError(f"文件不存在：{relative_path}")
        content = target.read_text(encoding="utf-8")
        occurrences = content.count(old)
        if occurrences == 0:
            raise ValueError("未找到要替换的 old_text，文件未修改")
        if not replace_all and occurrences > 1:
            raise ValueError(f"old_text 出现 {occurrences} 次，请提供更精确的文本或设置 replace_all")
        updated = content.replace(old, new, -1 if replace_all else 1)
        if len(updated.encode("utf-8")) > self.MAX_FILE_BYTES:
            raise ValueError("修改后的文件过大")
        target.write_text(updated, encoding="utf-8")
        changed = occurrences if replace_all else 1
        return f"OK: 已修改 {target.relative_to(self.root).as_posix()}（替换 {changed} 处）"

    def run_command(self, command: str) -> str:
        if not command.strip():
            raise ValueError("命令不能为空")
        if not self.confirm_command(command):
            return "DENIED: 用户未批准执行该命令。请解释用途或选择其他方法。"

        safe_env = {
            key: value
            for key, value in os.environ.items()
            if not any(marker in key.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
        }
        try:
            completed = subprocess.run(
                command,
                cwd=self.root,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.command_timeout,
                env=safe_env,
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: 命令运行超过 {self.command_timeout} 秒，已终止。"

        output = (
            f"exit_code: {completed.returncode}\n"
            f"stdout:\n{completed.stdout or '(empty)'}\n"
            f"stderr:\n{completed.stderr or '(empty)'}"
        )
        if len(output) > self.MAX_OUTPUT_CHARS:
            output = "... 前部输出已截断 ...\n" + output[-self.MAX_OUTPUT_CHARS :]
        return output
