import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tool_run import tool  # noqa: E402


class ToolTest(unittest.TestCase):
    def test_stdout_and_stderr_both_land_in_the_log_after_the_command(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "tool.log"

            tool("/bin/sh")(["-c", "echo Copy complete.; echo Encode done! >&2"], log)

            lines = log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines[0].startswith("Command: /bin/sh -c"))
        self.assertIn("Copy complete.", lines)
        self.assertIn("Encode done!", lines)
        self.assertTrue(lines[-1].startswith("End: "))


if __name__ == "__main__":
    unittest.main()
