from __future__ import annotations

from pathlib import Path

import typer

from ctwrap.compilation import load_compile_database
from ctwrap.config import load_settings
from ctwrap.config.schema import Settings
from ctwrap.doctor import run_doctor
from ctwrap.errors import ToolError
from ctwrap.report.render import render_agent_report_json, render_report_json, render_text_summary
from ctwrap.scan import build_final_command, run_scan
from ctwrap.tools import detect_clang_tidy_version, require_tool

app = typer.Typer(help="Agent-friendly clang-tidy wrapper")


def _merge_settings(
    config: Path | None,
    compile_db: Path | None,
    paths: list[Path] | None,
    checks: str | None,
    header_filter: str | None,
    timeout_sec: int | None,
) -> Settings:
    settings = load_settings(config)
    if compile_db is not None:
        settings.compile_db.path = compile_db
    if paths:
        settings.scan.paths = paths
    if checks is not None:
        settings.scan.checks = checks
    if header_filter is not None:
        settings.scan.header_filter = header_filter
    if timeout_sec is not None:
        settings.scan.timeout_sec = timeout_sec
    return settings


@app.command()
def doctor(
    config: Path | None = typer.Option(None, "--config"),
    compile_db: Path | None = typer.Option(None, "--compile-db"),
) -> None:
    settings = _merge_settings(config, compile_db, None, None, None, None)
    for level, message in run_doctor(settings):
        typer.echo(f"{level}: {message}")


@app.command("print-cmd")
def print_cmd(
    source: Path,
    config: Path | None = typer.Option(None, "--config"),
    compile_db: Path | None = typer.Option(None, "--compile-db"),
) -> None:
    settings = _merge_settings(config, compile_db, None, None, None, None)
    if settings.compile_db.path is None:
        raise typer.BadParameter("--compile-db is required")
    try:
        clang_tidy_path = require_tool("clang-tidy")
    except ToolError:
        clang_tidy_path = "clang-tidy"
    db = load_compile_database(settings.compile_db.path, settings.compile_db.strip_flags)
    entry = db.select_for_file(source)
    final_cmd = build_final_command(source.resolve(), entry, settings, clang_tidy_path)
    typer.echo("original:")
    typer.echo(" ".join(entry.original_arguments))
    typer.echo("filtered:")
    removed = [arg for arg in entry.original_arguments if arg not in entry.arguments]
    typer.echo(" ".join(removed) if removed else "(none)")
    typer.echo("final:")
    typer.echo(" ".join(final_cmd))


@app.command()
def scan(
    paths: list[Path] = typer.Argument(None),
    config: Path | None = typer.Option(None, "--config"),
    compile_db: Path | None = typer.Option(None, "--compile-db"),
    checks: str | None = typer.Option(None, "--checks"),
    header_filter: str | None = typer.Option(None, "--header-filter"),
    timeout_sec: int | None = typer.Option(None, "--timeout-sec"),
    json_out: Path | None = typer.Option(None, "--json"),
    agent_json_out: Path | None = typer.Option(None, "--agent-json"),
    text_out: Path | None = typer.Option(None, "--text"),
) -> None:
    settings = _merge_settings(config, compile_db, paths, checks, header_filter, timeout_sec)
    if settings.compile_db.path is None:
        raise typer.BadParameter("--compile-db is required in v1")

    clang_tidy_path = require_tool("clang-tidy")
    version = detect_clang_tidy_version(clang_tidy_path)
    db = load_compile_database(settings.compile_db.path, settings.compile_db.strip_flags)
    report = run_scan(settings, db, clang_tidy_path, version)

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
