from __future__ import annotations

from pathlib import Path

import typer

from ctwrap.compilation import load_compile_database
from ctwrap.config import load_settings
from ctwrap.config.schema import Settings
from ctwrap.doctor import run_doctor
from ctwrap.errors import CompileDbError, ToolError
from ctwrap.kernel import is_kernel_tree, resolve_kernel_compile_db
from ctwrap.report.render import render_agent_report_json, render_report_json, render_text_summary
from ctwrap.scan import build_fallback_command, build_final_command, run_fallback_scan, run_scan
from ctwrap.tools import detect_clang_tidy_version, require_tool

app = typer.Typer(help="Agent-friendly clang-tidy wrapper")


def _merge_settings(
    config: Path | None,
    compile_db: Path | None,
    paths: list[Path] | None,
    mode: str | None,
    checks: str | None,
    header_filter: str | None,
    timeout_sec: int | None,
    target: str | None,
    sysroot: Path | None,
    gcc_toolchain: Path | None,
    includes: list[Path] | None,
    defines: list[str] | None,
    std: str | None,
    kernel_src: Path | None,
    kernel_build: Path | None,
    allow_fallback: bool,
) -> Settings:
    settings = load_settings(config)
    if compile_db is not None:
        settings.compile_db.path = compile_db
    if paths:
        settings.scan.paths = paths
    if mode is not None:
        settings.scan.mode = mode
    if checks is not None:
        settings.scan.checks = checks
    if header_filter is not None:
        settings.scan.header_filter = header_filter
    if timeout_sec is not None:
        settings.scan.timeout_sec = timeout_sec
    if target is not None:
        settings.toolchain.target = target
    if sysroot is not None:
        settings.toolchain.sysroot = sysroot
    if gcc_toolchain is not None:
        settings.toolchain.gcc_toolchain = gcc_toolchain
    if includes:
        settings.fallback.includes = includes
    if defines:
        settings.fallback.defines = defines
    if std is not None:
        settings.fallback.std = std
    if kernel_src is not None:
        settings.kernel.source_dir = kernel_src
    if kernel_build is not None:
        settings.kernel.build_dir = kernel_build
    if allow_fallback:
        settings.kernel.allow_fallback = True
    return settings


def _resolve_mode(settings: Settings) -> tuple[str, Path | None, str | None]:
    configured_mode = settings.scan.mode
    if configured_mode == "db":
        return "db", settings.compile_db.path, None
    if configured_mode == "fallback":
        return "fallback", None, None
    if configured_mode == "kernel-auto-db":
        kernel_src = settings.kernel.source_dir or Path.cwd()
        kernel_build = settings.kernel.build_dir
        try:
            compile_db = resolve_kernel_compile_db(kernel_src, kernel_build, settings.kernel.gen_script)
            return "kernel-auto-db", compile_db, None
        except CompileDbError as exc:
            if settings.kernel.allow_fallback:
                return "fallback", None, str(exc)
            raise

    if settings.compile_db.path:
        return "db", settings.compile_db.path, None

    kernel_src = settings.kernel.source_dir or Path.cwd()
    if is_kernel_tree(kernel_src):
        try:
            compile_db = resolve_kernel_compile_db(kernel_src, settings.kernel.build_dir, settings.kernel.gen_script)
            return "kernel-auto-db", compile_db, None
        except CompileDbError as exc:
            if settings.kernel.allow_fallback:
                return "fallback", None, str(exc)
            raise
    return "fallback", None, "auto mode could not find a compile database"


@app.command()
def doctor(
    config: Path | None = typer.Option(None, "--config"),
    compile_db: Path | None = typer.Option(None, "--compile-db"),
    mode: str | None = typer.Option(None, "--mode"),
    target: str | None = typer.Option(None, "--target"),
    sysroot: Path | None = typer.Option(None, "--sysroot"),
    gcc_toolchain: Path | None = typer.Option(None, "--gcc-toolchain"),
    include: list[Path] | None = typer.Option(None, "-I", "--include"),
    define: list[str] | None = typer.Option(None, "-D", "--define"),
    std: str | None = typer.Option(None, "--std"),
    kernel_src: Path | None = typer.Option(None, "--kernel-src"),
    kernel_build: Path | None = typer.Option(None, "--kernel-build"),
    allow_fallback: bool = typer.Option(False, "--allow-fallback"),
) -> None:
    settings = _merge_settings(
        config, compile_db, None, mode, None, None, None, target, sysroot, gcc_toolchain, include, define, std, kernel_src, kernel_build, allow_fallback
    )
    for level, message in run_doctor(settings):
        typer.echo(f"{level}: {message}")


@app.command("print-cmd")
def print_cmd(
    source: Path,
    config: Path | None = typer.Option(None, "--config"),
    compile_db: Path | None = typer.Option(None, "--compile-db"),
    mode: str | None = typer.Option(None, "--mode"),
    target: str | None = typer.Option(None, "--target"),
    sysroot: Path | None = typer.Option(None, "--sysroot"),
    gcc_toolchain: Path | None = typer.Option(None, "--gcc-toolchain"),
    include: list[Path] | None = typer.Option(None, "-I", "--include"),
    define: list[str] | None = typer.Option(None, "-D", "--define"),
    std: str | None = typer.Option(None, "--std"),
    kernel_src: Path | None = typer.Option(None, "--kernel-src"),
    kernel_build: Path | None = typer.Option(None, "--kernel-build"),
    allow_fallback: bool = typer.Option(False, "--allow-fallback"),
) -> None:
    settings = _merge_settings(
        config, compile_db, None, mode, None, None, None, target, sysroot, gcc_toolchain, include, define, std, kernel_src, kernel_build, allow_fallback
    )
    try:
        clang_tidy_path = require_tool("clang-tidy")
    except ToolError:
        clang_tidy_path = "clang-tidy"
    mode_name, compile_db_path, _ = _resolve_mode(settings)
    if mode_name in ("db", "kernel-auto-db"):
        if compile_db_path is None:
            raise typer.BadParameter("--compile-db is required")
        db = load_compile_database(compile_db_path, settings.compile_db.strip_flags)
        entry = db.select_for_file(source)
        final_cmd = build_final_command(source.resolve(), entry, settings, clang_tidy_path)
        typer.echo("original:")
        typer.echo(" ".join(entry.original_arguments))
        typer.echo("filtered:")
        removed = [arg for arg in entry.original_arguments if arg not in entry.arguments]
        typer.echo(" ".join(removed) if removed else "(none)")
        typer.echo("final:")
        typer.echo(" ".join(final_cmd))
    else:
        final_cmd, confidence_reasons = build_fallback_command(source.resolve(), settings, clang_tidy_path)
        typer.echo("original:")
        typer.echo("(fallback mode has no compile database entry)")
        typer.echo("filtered:")
        typer.echo("(none)")
        typer.echo("final:")
        typer.echo(" ".join(final_cmd))
        typer.echo("confidence_reasons:")
        typer.echo(", ".join(confidence_reasons) if confidence_reasons else "(none)")


@app.command()
def scan(
    paths: list[Path] = typer.Argument(None),
    config: Path | None = typer.Option(None, "--config"),
    compile_db: Path | None = typer.Option(None, "--compile-db"),
    mode: str | None = typer.Option(None, "--mode"),
    checks: str | None = typer.Option(None, "--checks"),
    header_filter: str | None = typer.Option(None, "--header-filter"),
    timeout_sec: int | None = typer.Option(None, "--timeout-sec"),
    target: str | None = typer.Option(None, "--target"),
    sysroot: Path | None = typer.Option(None, "--sysroot"),
    gcc_toolchain: Path | None = typer.Option(None, "--gcc-toolchain"),
    include: list[Path] | None = typer.Option(None, "-I", "--include"),
    define: list[str] | None = typer.Option(None, "-D", "--define"),
    std: str | None = typer.Option(None, "--std"),
    kernel_src: Path | None = typer.Option(None, "--kernel-src"),
    kernel_build: Path | None = typer.Option(None, "--kernel-build"),
    allow_fallback: bool = typer.Option(False, "--allow-fallback"),
    json_out: Path | None = typer.Option(None, "--json"),
    agent_json_out: Path | None = typer.Option(None, "--agent-json"),
    text_out: Path | None = typer.Option(None, "--text"),
) -> None:
    settings = _merge_settings(
        config, compile_db, paths, mode, checks, header_filter, timeout_sec, target, sysroot, gcc_toolchain, include, define, std, kernel_src, kernel_build, allow_fallback
    )
    clang_tidy_path = require_tool("clang-tidy")
    version = detect_clang_tidy_version(clang_tidy_path)
    mode_name, compile_db_path, fallback_reason = _resolve_mode(settings)
    settings.scan.mode = mode_name
    if mode_name in ("db", "kernel-auto-db"):
        if compile_db_path is None:
            raise typer.BadParameter("--compile-db is required")
        db = load_compile_database(compile_db_path, settings.compile_db.strip_flags)
        report = run_scan(settings, db, clang_tidy_path, version)
        report.run_meta.mode = mode_name
        report.run_meta.project_kind = "linux-kernel" if mode_name == "kernel-auto-db" else "generic-c-cpp"
        report.run_meta.compile_db_path = compile_db_path
        if mode_name == "kernel-auto-db":
            for finding in report.findings:
                finding.context_kind = "kernel-auto-db"
                finding.build_origin = "kernel-auto-db"
    else:
        if not settings.scan.paths:
            raise typer.BadParameter("fallback mode requires at least one source path")
        report = run_fallback_scan(settings, clang_tidy_path, version)
        report.run_meta.fallback_reason = fallback_reason

    report_bytes = render_report_json(report)
    agent_bytes = render_agent_report_json(report)
    text_summary = render_text_summary(report)

    if json_out:
        json_out.write_bytes(report_bytes)
    else:
        typer.echo(report_bytes.decode())

    if agent_json_out:
        agent_json_out.write_bytes(agent_bytes)

    if text_out:
        text_out.write_text(text_summary)

    raise typer.Exit(report.summary.exit_code)


if __name__ == "__main__":
    app()
