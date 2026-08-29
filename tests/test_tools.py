from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from coding_agent.tools import WorkspaceTools


class WorkspaceToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.tools = WorkspaceTools(self.root, confirm_command=lambda _command: True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_write_read_list_and_replace(self) -> None:
        result = self.tools.write_file("src/hello.py", "name = 'old'\n")
        self.assertIn("OK", result)
        self.assertIn("src/hello.py", self.tools.list_files())
        self.assertIn("1 | name = 'old'", self.tools.read_file("src/hello.py"))

        result = self.tools.replace_in_file("src/hello.py", "old", "new", False)
        self.assertIn("替换 1 处", result)
        self.assertEqual((self.root / "src/hello.py").read_text(encoding="utf-8"), "name = 'new'\n")

    def test_path_traversal_is_rejected(self) -> None:
        result = self.tools.execute("read_file", {"path": "../outside.txt"})
        self.assertIn("拒绝访问工作区之外", result)

    def test_sensitive_files_are_hidden_and_rejected(self) -> None:
        (self.root / ".env").write_text("MODEL_API_KEY=secret", encoding="utf-8")
        (self.root / ".env.example").write_text("MODEL_API_KEY=placeholder", encoding="utf-8")

        listing = self.tools.list_files()
        self.assertNotIn("\n.env\n", f"\n{listing}\n")
        self.assertIn(".env.example", listing)
        result = self.tools.execute("read_file", {"path": ".env"})
        self.assertIn("拒绝通过 Agent 文件工具访问敏感凭据文件", result)

    def test_ambiguous_replacement_is_rejected(self) -> None:
        (self.root / "twice.txt").write_text("same same", encoding="utf-8")
        result = self.tools.execute(
            "replace_in_file",
            {"path": "twice.txt", "old_text": "same", "new_text": "new"},
        )
        self.assertIn("出现 2 次", result)
        self.assertEqual((self.root / "twice.txt").read_text(encoding="utf-8"), "same same")

    def test_command_requires_approval(self) -> None:
        denied_tools = WorkspaceTools(self.root, confirm_command=lambda _command: False)
        result = denied_tools.run_command("echo should-not-run")
        self.assertTrue(result.startswith("DENIED:"))

    def test_command_runs_and_removes_secrets_from_environment(self) -> None:
        previous = os.environ.get("MODEL_API_KEY")
        os.environ["MODEL_API_KEY"] = "must-not-leak"
        try:
            command = (
                f'"{sys.executable}" -c "import os; '
                "print(os.getenv('MODEL_API_KEY', 'clean'))\""
            )
            result = self.tools.run_command(command)
        finally:
            if previous is None:
                os.environ.pop("MODEL_API_KEY", None)
            else:
                os.environ["MODEL_API_KEY"] = previous

        self.assertIn("exit_code: 0", result)
        self.assertIn("clean", result)
        self.assertNotIn("must-not-leak", result)


if __name__ == "__main__":
    unittest.main()
