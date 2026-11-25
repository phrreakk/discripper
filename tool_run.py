"""Run an external tool (makemkvcon, HandBrakeCLI) with its output going to a log.

``tool(program)`` returns ``run(args, log)``: the adapter Disc and Encoder take.
It runs ``program`` with ``args`` and writes the command, start and end times,
and everything the tool prints (stdout and stderr) to the file ``log``.
"""

import shlex
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

Run = Callable[[list[str], Path], None]


def tool(program: str) -> Run:
    def run(args: list[str], log: Path) -> None:
        command = [program, *args]
        with open(log, "w", encoding="utf-8") as file:
            print(f"Command: {shlex.join(command)}", file=file)
            print(f"Start: {datetime.now()}", file=file, flush=True)
            subprocess.run(command, stdout=file, stderr=subprocess.STDOUT, check=False)
            print(f"End: {datetime.now()}", file=file)
    return run
