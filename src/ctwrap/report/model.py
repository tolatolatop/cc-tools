from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    rule_id: str
    severity: Literal["error", "warning", "note", "unknown"]
    message: str
    file: Path
    line: int
    column: int
    confidence: Literal["high", "medium", "low"] = "high"
    context_kind: Literal["compile_db"] = "compile_db"
    result_trust: Literal["strict", "advisory"] = "strict"
    repro_command: list[str] = Field(default_factory=list)
    filtered_flags: list[str] = Field(default_factory=list)


class RunMeta(BaseModel):
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    mode: str
    compile_db_path: Path | None = None
    clang_tidy_path: str
    clang_tidy_version: str | None = None
    parser_mode: str = "text"


class Summary(BaseModel):
    files_total: int = 0
    files_scanned: int = 0
    files_failed: int = 0
    findings_total: int = 0
    errors: int = 0
    warnings: int = 0
    notes: int = 0
    exit_code: int = 0


class Report(BaseModel):
    run_meta: RunMeta
    summary: Summary
    findings: list[Finding] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class AgentFinding(BaseModel):
    rule_id: str
    severity: str
    file: Path
    line: int
    message: str
    confidence: str
    context_kind: str
    result_trust: str


class AgentReport(BaseModel):
    agent_schema_version: int = 1
    run_intent: str = "code_review"
    scan_mode: str
    project_kind: str = "generic-c-cpp"
    summary: str
    trust_summary: dict[str, int]
    actionable_findings: list[AgentFinding] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
