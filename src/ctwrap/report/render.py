from __future__ import annotations

from pathlib import Path

import orjson

from .model import AgentFinding, AgentReport, Finding, Report


def render_report_json(report: Report) -> bytes:
    return orjson.dumps(report.model_dump(mode="json"), option=orjson.OPT_INDENT_2)


def build_agent_report(report: Report) -> AgentReport:
    trust_summary = {"high": 0, "medium": 0, "low": 0}
    agent_findings: list[AgentFinding] = []
    for finding in report.findings:
        trust_summary[finding.confidence] = trust_summary.get(finding.confidence, 0) + 1
        agent_findings.append(
            AgentFinding(
                rule_id=finding.rule_id,
                severity=finding.severity,
                file=Path(finding.file),
                line=finding.line,
                message=finding.message,
                confidence=finding.confidence,
                context_kind=finding.context_kind,
                result_trust=finding.result_trust,
            )
        )

    summary = (
        f"Scanned {report.summary.files_scanned}/{report.summary.files_total} files, "
        f"found {report.summary.findings_total} findings."
    )
    return AgentReport(
        scan_mode=report.run_meta.mode,
        summary=summary,
        trust_summary=trust_summary,
        actionable_findings=agent_findings,
        next_actions=report.next_actions,
    )


def render_agent_report_json(report: Report) -> bytes:
    agent_report = build_agent_report(report)
    return orjson.dumps(agent_report.model_dump(mode="json"), option=orjson.OPT_INDENT_2)


def render_text_summary(report: Report) -> str:
    lines = [
        f"mode: {report.run_meta.mode}",
        f"files: {report.summary.files_scanned}/{report.summary.files_total}",
        f"findings: {report.summary.findings_total}",
        f"errors: {report.summary.errors}",
        f"warnings: {report.summary.warnings}",
        f"notes: {report.summary.notes}",
        f"exit_code: {report.summary.exit_code}",
    ]
    if report.errors:
        lines.append("run errors:")
        lines.extend(f"  - {item}" for item in report.errors)
    return "\n".join(lines) + "\n"
