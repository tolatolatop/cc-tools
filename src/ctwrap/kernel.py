from __future__ import annotations

import subprocess
from pathlib import Path

from ctwrap.errors import CompileDbError


def is_kernel_tree(root: Path) -> bool:
    return (
        (root / "Kconfig").exists()
        and (root / "Makefile").exists()
        and (root / "arch").exists()
        and (root / "scripts").exists()
    )


def resolve_kernel_compile_db(source_dir: Path, build_dir: Path | None, gen_script: str) -> Path:
    build_root = build_dir or source_dir
    direct = build_root / "compile_commands.json"
    if direct.exists():
        return direct.resolve()
    generated = source_dir / "compile_commands.json"
    if generated.exists():
        return generated.resolve()

    script = source_dir / gen_script
    if script.exists():
        proc = subprocess.run(
            ["python3", str(script)],
            cwd=str(source_dir),
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise CompileDbError(
                f"Kernel compile database generation failed: {proc.stderr.strip() or proc.stdout.strip()}"
            )
        if direct.exists():
            return direct.resolve()
        if generated.exists():
            return generated.resolve()

    raise CompileDbError("Kernel compile database not found and no usable generation script output was produced")
