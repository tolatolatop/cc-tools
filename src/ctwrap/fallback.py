from __future__ import annotations

from pathlib import Path

from ctwrap.config.schema import Settings


def build_fallback_flags(settings: Settings, source: Path) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    confidence_reasons: list[str] = []

    compiler = settings.fallback.compiler
    language = settings.fallback.language
    std = settings.fallback.std

    if compiler:
        flags.append(f"-x{language}")
    if std:
        flags.append(f"-std={std}")
    else:
        confidence_reasons.append("missing_std")

    for include in settings.fallback.includes:
        flags.extend(["-I", str(include)])
    if not settings.fallback.includes:
        confidence_reasons.append("missing_includes")

    for define in settings.fallback.defines:
        flags.extend(["-D", define])

    for undefine in settings.fallback.undefines:
        flags.extend(["-U", undefine])

    flags.extend(settings.fallback.extra_args_before)

    if settings.toolchain.target:
        flags.append(f"--target={settings.toolchain.target}")
    else:
        confidence_reasons.append("missing_target")

    if settings.toolchain.sysroot:
        flags.append(f"--sysroot={settings.toolchain.sysroot}")
    else:
        confidence_reasons.append("missing_sysroot")

    if settings.toolchain.gcc_toolchain:
        flags.append(f"--gcc-toolchain={settings.toolchain.gcc_toolchain}")

    for include in settings.toolchain.extra_system_includes:
        flags.extend(["-isystem", str(include)])

    flags.extend(settings.fallback.extra_args)
    flags.append(str(source))
    return flags, confidence_reasons


def classify_confidence(reasons: list[str]) -> tuple[str, str]:
    if not reasons:
        return "high", "strict"
    if reasons == ["missing_sysroot"] or reasons == ["missing_target"]:
        return "medium", "advisory"
    return "low", "advisory"
