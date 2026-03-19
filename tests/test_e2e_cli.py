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
