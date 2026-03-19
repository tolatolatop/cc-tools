from __future__ import annotations

import shlex
from collections import defaultdict
from pathlib import Path

import orjson
from pydantic import BaseModel

from ctwrap.errors import CompileDbError


class CompileCommand(BaseModel):
    directory: Path
    file: Path
    arguments: list[str]
    original_arguments: list[str]


class CompileDatabase(BaseModel):
    path: Path
    entries: list[CompileCommand]

    def group_by_file(self) -> dict[Path, list[CompileCommand]]:
        grouped: dict[Path, list[CompileCommand]] = defaultdict(list)
        for entry in self.entries:
            grouped[entry.file].append(entry)
        return dict(grouped)

    def select_for_file(self, source: Path) -> CompileCommand:
        normalized = source.resolve()
        candidates = self.group_by_file().get(normalized, [])
        if not candidates:
            raise CompileDbError(f"No compile database entry for {source}")
        candidates.sort(key=lambda item: (len(str(item.directory)), len(item.arguments)), reverse=True)
        return candidates[0]


def _entry_args(entry: dict) -> list[str]:
    if "arguments" in entry and entry["arguments"]:
        return [str(part) for part in entry["arguments"]]
    if "command" in entry and entry["command"]:
        return shlex.split(str(entry["command"]))
    raise CompileDbError("Compile database entry must contain 'arguments' or 'command'")


def load_compile_database(path: Path, strip_flags: list[str] | None = None) -> CompileDatabase:
    strip_flags = strip_flags or []
    try:
        raw = orjson.loads(path.read_bytes())
    except FileNotFoundError as exc:
        raise CompileDbError(f"Compile database not found: {path}") from exc
    except orjson.JSONDecodeError as exc:
        raise CompileDbError(f"Invalid compile database JSON: {path}") from exc

    entries: list[CompileCommand] = []
    for item in raw:
        directory = Path(item["directory"]).resolve()
        file_path = Path(item["file"])
        if not file_path.is_absolute():
            file_path = (directory / file_path).resolve()
        args = [arg for arg in _entry_args(item) if arg not in strip_flags]
        entries.append(
            CompileCommand(
                directory=directory,
                file=file_path.resolve(),
                arguments=args,
                original_arguments=_entry_args(item),
            )
        )
    return CompileDatabase(path=path.resolve(), entries=entries)
