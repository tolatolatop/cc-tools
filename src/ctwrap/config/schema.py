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


class ToolchainSettings(BaseModel):
    target: str | None = None
    sysroot: Path | None = None
    gcc_toolchain: Path | None = None
    extra_system_includes: list[Path] = Field(default_factory=list)


class FallbackSettings(BaseModel):
    compiler: str = "clang"
    language: Literal["c", "c++"] = "c"
    std: str | None = None
    includes: list[Path] = Field(default_factory=list)
    defines: list[str] = Field(default_factory=list)
    undefines: list[str] = Field(default_factory=list)
    extra_args_before: list[str] = Field(default_factory=list)
    extra_args: list[str] = Field(default_factory=list)


class KernelSettings(BaseModel):
    source_dir: Path | None = None
    build_dir: Path | None = None
    gen_script: str = "scripts/clang-tools/gen_compile_commands.py"
    allow_fallback: bool = False


class ScanSettings(BaseModel):
    mode: Literal["auto", "db", "fallback", "kernel-auto-db"] = "auto"
    jobs: int = 1
    checks: str = "-*,bugprone-*,clang-analyzer-*"
    header_filter: str | None = None
    timeout_sec: int = 60
    paths: list[Path] = Field(default_factory=list)


class Settings(BaseModel):
    compile_db: CompileDbSettings = Field(default_factory=CompileDbSettings)
    toolchain: ToolchainSettings = Field(default_factory=ToolchainSettings)
    fallback: FallbackSettings = Field(default_factory=FallbackSettings)
    kernel: KernelSettings = Field(default_factory=KernelSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    scan: ScanSettings = Field(default_factory=ScanSettings)
