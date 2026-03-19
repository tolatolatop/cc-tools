from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ctwrap.compilation import CompileDatabase
from ctwrap.config.schema import Settings
from ctwrap.fallback import build_fallback_flags, classify_confidence
from ctwrap.report.model import Finding, Report, RunMeta, Summary


_DIAG_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+):\s+(?P<severity>warning|error|note):\s+"
    r"(?P<message>.+?)\s+\[(?P<rule>[^\]]+)\]$"
)


def build_toolchain_extra_args(settings: Settings) -> list[str]:
    args: list[str] = []
    if settings.toolchain.target:
        args.append(f"--target={settings.toolchain.target}")
    if settings.toolchain.sysroot:
        args.append(f"--sysroot={settings.toolchain.sysroot}")
    if settings.toolchain.gcc_toolchain:
        args.append(f"--gcc-toolchain={settings.toolchain.gcc_toolchain}")
    for include in settings.toolchain.extra_system_includes:
        args.append(f"-isystem{include}")
    return args


def build_final_command(source: Path, compile_command, settings: Settings, clang_tidy_path: str) -> list[str]:
    cmd = [clang_tidy_path, str(source)]
    if settings.scan.checks:
        cmd.append(f"--checks={settings.scan.checks}")
    if settings.scan.header_filter:
        cmd.append(f"--header-filter={settings.scan.header_filter}")
    for flag in build_toolchain_extra_args(settings):
        cmd.append(f"--extra-arg-before={flag}")
    for flag in settings.compile_db.add_flags_before:
        cmd.append(f"--extra-arg-before={flag}")
    for flag in settings.compile_db.add_flags_after:
        cmd.append(f"--extra-arg={flag}")
    cmd.append("--")
    cmd.extend(compile_command.arguments[1:] if compile_command.arguments else [])
    return cmd


def build_fallback_command(source: Path, settings: Settings, clang_tidy_path: str) -> tuple[list[str], list[str]]:
    cmd = [clang_tidy_path, str(source)]
    if settings.scan.checks:
        cmd.append(f"--checks={settings.scan.checks}")
    if settings.scan.header_filter:
        cmd.append(f"--header-filter={settings.scan.header_filter}")
    cmd.append("--")
    flags, confidence_reasons = build_fallback_flags(settings, source)
    cmd.extend(flags[:-1])
    return cmd, confidence_reasons


def run_scan(settings: Settings, compile_db: CompileDatabase, clang_tidy_path: str, version: str | None) -> Report:
    grouped = compile_db.group_by_file()
    requested = [path.resolve() for path in settings.scan.paths] if settings.scan.paths else sorted(grouped.keys())
    findings: list[Finding] = []
    errors: list[str] = []
    next_actions: list[str] = []
    summary = Summary(files_total=len(requested))
    run_meta = RunMeta(
        mode=settings.scan.mode,
        compile_db_path=compile_db.path,
        clang_tidy_path=clang_tidy_path,
        clang_tidy_version=version,
    )

    for source in requested:
        try:
            compile_command = compile_db.select_for_file(source)
            cmd = build_final_command(source, compile_command, settings, clang_tidy_path)
            proc = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                cwd=str(compile_command.directory),
                timeout=settings.scan.timeout_sec,
            )
            file_findings = parse_findings(proc.stdout + proc.stderr, cmd)
            findings.extend(file_findings)
            summary.files_scanned += 1
            if proc.returncode not in (0, 1):
                errors.append(f"{source}: clang-tidy exited with status {proc.returncode}")
                summary.files_failed += 1
        except Exception as exc:
            errors.append(f"{source}: {exc}")
            summary.files_failed += 1

    summary.findings_total = len(findings)
    summary.errors = sum(1 for item in findings if item.severity == "error")
    summary.warnings = sum(1 for item in findings if item.severity == "warning")
    summary.notes = sum(1 for item in findings if item.severity == "note")
    if summary.files_failed:
        next_actions.append("Use ctwrap print-cmd on failed files and verify their compile database entries.")
    if not summary.files_failed and summary.findings_total == 0:
        next_actions.append("No findings were reported for the selected checks.")

    if summary.files_failed:
        summary.exit_code = 2
    elif summary.findings_total:
        summary.exit_code = 1
    else:
        summary.exit_code = 0

    return Report(
        run_meta=run_meta,
        summary=summary,
        findings=findings,
        errors=errors,
        next_actions=next_actions,
    )


def run_fallback_scan(settings: Settings, clang_tidy_path: str, version: str | None) -> Report:
    requested = [path.resolve() for path in settings.scan.paths]
    findings: list[Finding] = []
    errors: list[str] = []
    next_actions: list[str] = []
    summary = Summary(files_total=len(requested))
    run_meta = RunMeta(
        mode="fallback",
        compile_db_path=None,
        clang_tidy_path=clang_tidy_path,
        clang_tidy_version=version,
        project_kind="generic-c-cpp",
        fallback_reason="compile database unavailable or disabled",
    )

    for source in requested:
        try:
            cmd, confidence_reasons = build_fallback_command(source, settings, clang_tidy_path)
            proc = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=settings.scan.timeout_sec,
            )
            confidence, result_trust = classify_confidence(confidence_reasons)
            file_findings = parse_findings(
                proc.stdout + proc.stderr,
                cmd,
                confidence=confidence,
                confidence_reasons=confidence_reasons,
                context_kind="fallback",
                result_trust=result_trust,
                build_origin="fallback",
            )
            findings.extend(file_findings)
            summary.files_scanned += 1
            if proc.returncode not in (0, 1):
                errors.append(f"{source}: clang-tidy exited with status {proc.returncode}")
                summary.files_failed += 1
        except Exception as exc:
            errors.append(f"{source}: {exc}")
            summary.files_failed += 1

    summary.findings_total = len(findings)
    summary.errors = sum(1 for item in findings if item.severity == "error")
    summary.warnings = sum(1 for item in findings if item.severity == "warning")
    summary.notes = sum(1 for item in findings if item.severity == "note")
    if summary.files_failed:
        next_actions.append("Provide explicit includes/defines/target or use a compile database for higher confidence.")
        summary.exit_code = 2
    elif findings and any(item.confidence == "low" for item in findings):
        next_actions.append("Fallback scan is advisory. Provide --target/--sysroot/includes or a compile database.")
        summary.exit_code = 3
    elif summary.findings_total:
        next_actions.append("Fallback scan found issues. Validate results with a compile database when possible.")
        summary.exit_code = 1
    else:
        next_actions.append("Fallback scan completed. Add compile database support to improve confidence.")
        summary.exit_code = 0

    return Report(
        run_meta=run_meta,
        summary=summary,
        findings=findings,
        errors=errors,
        next_actions=next_actions,
    )


def parse_findings(
    output: str,
    command: list[str],
    *,
    confidence: str = "high",
    confidence_reasons: list[str] | None = None,
    context_kind: str = "compile_db",
    result_trust: str = "strict",
    build_origin: str | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    confidence_reasons = confidence_reasons or []
    for line in output.splitlines():
        match = _DIAG_RE.match(line.strip())
        if not match:
            continue
        findings.append(
            Finding(
                rule_id=match.group("rule"),
                severity=match.group("severity"),
                message=match.group("message"),
                file=Path(match.group("file")),
                line=int(match.group("line")),
                column=int(match.group("column")),
                confidence=confidence,
                confidence_reasons=confidence_reasons,
                context_kind=context_kind,
                result_trust=result_trust,
                repro_command=command,
                build_origin=build_origin,
            )
        )
    return findings
