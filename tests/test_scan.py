from pathlib import Path

from ctwrap.scan import parse_findings


def test_parse_findings() -> None:
    output = (
        "/tmp/a.c:3:7: warning: use of old-style cast [cppcoreguidelines-pro-type-cstyle-cast]\n"
    )
    findings = parse_findings(output, ["clang-tidy", "/tmp/a.c"])
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].rule_id == "cppcoreguidelines-pro-type-cstyle-cast"
