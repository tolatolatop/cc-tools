from pathlib import Path

from ctwrap.compilation.database import load_compile_database


def test_load_compile_database_from_command(tmp_path: Path) -> None:
    db_path = tmp_path / "compile_commands.json"
    source = tmp_path / "a.c"
    source.write_text("int main(void) { return 0; }\n")
    db_path.write_text(
        '[{"directory": "%s", "file": "a.c", "command": "clang -Iinclude -c a.c"}]' % tmp_path
    )

    db = load_compile_database(db_path)
    entry = db.select_for_file(source)

    assert entry.file == source.resolve()
    assert entry.arguments[0] == "clang"
    assert "-Iinclude" in entry.arguments
