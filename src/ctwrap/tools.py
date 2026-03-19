from __future__ import annotations

import re
import shutil
import subprocess

from ctwrap.errors import ToolError


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise ToolError(f"Required tool not found: {name}")
    return path


def detect_clang_tidy_version(path: str) -> str | None:
    try:
        proc = subprocess.run(
            [path, "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    output = proc.stdout.strip() or proc.stderr.strip()
    match = re.search(r"version\s+([0-9]+(?:\.[0-9]+)*)", output)
    if not match:
        return output or None
    return match.group(1)


def parse_major_version(version: str | None) -> int | None:
    if not version:
        return None
    match = re.match(r"(\d+)", version)
    if not match:
        return None
    return int(match.group(1))
