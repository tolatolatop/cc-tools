import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(shutil.which("clang-tidy") is None, reason="clang-tidy is required")


def test_e2e_scan_and_agent_report(tmp_path: Path) -> None:
    source = tmp_path / "test.cpp"
    source.write_text(
        "#include <cstddef>\n"
        "int *p = NULL;\n"
        "int main() { return p == NULL; }\n"
    )
    compile_db = tmp_path / "compile_commands.json"
    compile_db.write_text(
        json.dumps(
            [
                {
                    "directory": str(tmp_path),
                    "file": "test.cpp",
                    "arguments": ["clang++", "-std=c++17", "-c", "test.cpp"],
                }
            ]
        )
    )
    report_json = tmp_path / "report.json"
    agent_json = tmp_path / "agent-report.json"
    text_out = tmp_path / "report.txt"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ctwrap",
            "scan",
            str(source),
            "--compile-db",
            str(compile_db),
            "--checks=-*,modernize-use-nullptr",
            "--json",
            str(report_json),
            "--agent-json",
            str(agent_json),
            "--text",
            str(text_out),
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1, proc.stderr
    report = json.loads(report_json.read_text())
    agent_report = json.loads(agent_json.read_text())
    text_summary = text_out.read_text()

    assert report["summary"]["findings_total"] == 2
    assert report["summary"]["warnings"] == 2
    assert report["summary"]["exit_code"] == 1
    assert report["findings"][0]["rule_id"] == "modernize-use-nullptr"
    assert agent_report["agent_schema_version"] == 1
    assert len(agent_report["actionable_findings"]) == 2
    assert "findings: 2" in text_summary


def test_e2e_print_cmd(tmp_path: Path) -> None:
    source = tmp_path / "test.cpp"
    source.write_text("int main() { return 0; }\n")
    compile_db = tmp_path / "compile_commands.json"
    compile_db.write_text(
        json.dumps(
            [
                {
                    "directory": str(tmp_path),
                    "file": "test.cpp",
                    "arguments": ["clang++", "-std=c++17", "-c", "test.cpp"],
                }
            ]
        )
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ctwrap",
            "print-cmd",
            str(source),
            "--compile-db",
            str(compile_db),
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "original:" in proc.stdout
    assert "final:" in proc.stdout
    assert "clang-tidy" in proc.stdout


def test_e2e_fallback_scan(tmp_path: Path) -> None:
    source = tmp_path / "null_deref.c"
    source.write_text(
        "int test(int cond) {\n"
        "  int *p = 0;\n"
        "  if (cond)\n"
        "    return *p;\n"
        "  return 0;\n"
        "}\n"
    )
    report_json = tmp_path / "report.json"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ctwrap",
            "scan",
            str(source),
            "--mode",
            "fallback",
            "--std=gnu11",
            "--json",
            str(report_json),
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 3, proc.stderr
    report = json.loads(report_json.read_text())
    assert report["run_meta"]["mode"] == "fallback"
    assert report["summary"]["findings_total"] >= 1
    assert report["findings"][0]["context_kind"] == "fallback"
    assert report["findings"][0]["result_trust"] == "advisory"


def test_e2e_kernel_auto_db_scan(tmp_path: Path) -> None:
    kernel_root = tmp_path / "kernel"
    build_dir = kernel_root / "build"
    source_dir = kernel_root / "src"
    (kernel_root / "arch" / "x86").mkdir(parents=True)
    (kernel_root / "scripts").mkdir(parents=True)
    build_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    (kernel_root / "Kconfig").write_text("config DUMMY\n\tbool \"dummy\"\n")
    (kernel_root / "Makefile").write_text("obj-y += src/\n")
    source = source_dir / "null_deref.c"
    source.write_text(
        "int test(int cond) {\n"
        "  int *p = 0;\n"
        "  if (cond)\n"
        "    return *p;\n"
        "  return 0;\n"
        "}\n"
    )
    compile_db = build_dir / "compile_commands.json"
    compile_db.write_text(
        json.dumps(
            [
                {
                    "directory": str(kernel_root),
                    "file": "src/null_deref.c",
                    "arguments": ["clang", "-std=gnu11", "-Wall", "-Wextra", "-c", "src/null_deref.c"],
                }
            ]
        )
    )
    report_json = tmp_path / "report.json"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ctwrap",
            "scan",
            str(source),
            "--mode",
            "kernel-auto-db",
            "--kernel-src",
            str(kernel_root),
            "--kernel-build",
            str(build_dir),
            "--json",
            str(report_json),
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1, proc.stderr
    report = json.loads(report_json.read_text())
    assert report["run_meta"]["mode"] == "kernel-auto-db"
    assert report["run_meta"]["project_kind"] == "linux-kernel"
    assert report["summary"]["findings_total"] >= 1
    assert report["findings"][0]["context_kind"] == "kernel-auto-db"


def test_print_cmd_injects_toolchain_flags(tmp_path: Path) -> None:
    source = tmp_path / "test.c"
    source.write_text("int main(void) { return 0; }\n")
    compile_db = tmp_path / "compile_commands.json"
    compile_db.write_text(
        json.dumps(
            [
                {
                    "directory": str(tmp_path),
                    "file": "test.c",
                    "arguments": ["clang", "-std=c11", "-c", "test.c"],
                }
            ]
        )
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ctwrap",
            "print-cmd",
            str(source),
            "--compile-db",
            str(compile_db),
            "--target",
            "aarch64-linux-gnu",
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "--extra-arg-before=--target=aarch64-linux-gnu" in proc.stdout
