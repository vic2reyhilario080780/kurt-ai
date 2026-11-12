"""Check public command parsing without model requests or account mutations."""

from functools import wraps
import unittest
from unittest.mock import patch

from typer.main import get_command
from typer.testing import CliRunner

from kurt.main import app


class CommandParsingTests(unittest.TestCase):
    def test_every_registered_command_has_working_help(self):
        runner = CliRunner()

        def check(command, path):
            with self.subTest(command=" ".join(path) or "kurt"):
                result = runner.invoke(app, [*path, "--help"])
                self.assertEqual(result.exit_code, 0, result.output)
            for name, child in getattr(command, "commands", {}).items():
                check(child, [*path, name])

        check(get_command(app), [])

    def test_documented_prompt_shortcuts_reach_chat_with_options(self):
        info = next(c for c in app.registered_commands if c.callback.__name__ == "chat")
        calls = []

        @wraps(info.callback)
        def capture(**kwargs):
            calls.append(kwargs)

        cases = [
            (["translate this"], "translate this", None, None),
            (["--skill", "seo", "audit this site"], "audit this site", "seo", None),
            (["--model=gpt4o", "explain this"], "explain this", None, "gpt4o"),
            (["explain this", "-s", "seo", "-m", "gpt4o"], "explain this", "seo", "gpt4o"),
            (["--", "-a literal prompt"], "-a literal prompt", None, None),
            (["chat", "hello"], "hello", None, None),
        ]
        with patch.object(info, "callback", capture):
            for args, prompt, skill, model in cases:
                with self.subTest(args=args):
                    result = CliRunner().invoke(app, args)
                    self.assertEqual(result.exit_code, 0, result.output)
                    self.assertEqual(calls[-1]["prompt"], prompt)
                    self.assertEqual(calls[-1]["skill"], skill)
                    self.assertEqual(calls[-1]["model"], model)

    def test_existing_commands_and_invalid_options_keep_their_behavior(self):
        for args in (["--version"], ["version"], ["library", "stats"]):
            with self.subTest(args=args):
                result = CliRunner().invoke(app, args)
                self.assertEqual(result.exit_code, 0, result.output)
        for args in (["--unknown", "hello"], ["--skill"], ["library", "unknown"]):
            with self.subTest(args=args):
                self.assertEqual(CliRunner().invoke(app, args).exit_code, 2)


if __name__ == "__main__":
    unittest.main()
