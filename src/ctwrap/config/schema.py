from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class OutputSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    json_path: Path | None = Field(default=None, alias="json")
    agent_json_path: Path | None = Field(default=None, alias="agent_json")
    text_path: Path | None = Field(default=None, alias="text")


class CompileDbSettings(BaseModel):
    path: Path | None = None
    strip_flags: list[str] = Field(default_factory=list)
    add_flags_before: list[str] = Field(default_factory=list)
    add_flags_after: list[str] = Field(default_factory=list)


class ScanSettings(BaseModel):
    mode: Literal["db"] = "db"
    jobs: int = 1
    checks: str = "-*,bugprone-*,clang-analyzer-*"
    header_filter: str | None = None
    timeout_sec: int = 60
    paths: list[Path] = Field(default_factory=list)


class Settings(BaseModel):
    compile_db: CompileDbSettings = Field(default_factory=CompileDbSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    scan: ScanSettings = Field(default_factory=ScanSettings)
