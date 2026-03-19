from __future__ import annotations

from pathlib import Path

from ctwrap.compilation import load_compile_database
from ctwrap.config.schema import Settings
from ctwrap.tools import detect_clang_tidy_version, parse_major_version, require_tool


def run_doctor(settings: Settings) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    try:
        clang_tidy_path = require_tool("clang-tidy")
        version = detect_clang_tidy_version(clang_tidy_path)
        results.append(("INFO", f"clang-tidy: {clang_tidy_path} ({version or 'unknown version'})"))
        major = parse_major_version(version)
        if major is not None and major < 15:
            results.append(("ERROR", f"clang-tidy version too old: {version} (require >= 15)"))
    except Exception as exc:
        results.append(("ERROR", str(exc)))

    try:
        clang_path = require_tool("clang")
        results.append(("INFO", f"clang: {clang_path}"))
    except Exception as exc:
        results.append(("ERROR", str(exc)))

    if settings.compile_db.path:
        path = Path(settings.compile_db.path)
        if path.exists():
            try:
                db = load_compile_database(path, settings.compile_db.strip_flags)
                results.append(("INFO", f"compile database: ok ({len(db.entries)} entries)"))
            except Exception as exc:
                results.append(("ERROR", str(exc)))
        else:
            results.append(("WARN", f"compile database not found: {path}"))
    else:
        results.append(("WARN", "compile database path not configured"))
    return results
