from __future__ import annotations

import json
from pathlib import Path

from claude_code_manager.cli import (
    TodoItem,
    ensure_hooks_config,
    parse_todo_markdown,
    update_todo_with_pr,
)


def test_parse_todo_markdown_basic():
    md = (
        """
- [x] done 1 [#1](url)
- [ ] top 1
  - [ ] child a
  - [ ] child b
- [ ] top 2
    """
    ).strip()
    items = parse_todo_markdown(md)
    assert [i.title for i in items] == ["top 1", "top 2"]
    assert items[0].children == ["child a", "child b"]


def test_ensure_hooks_config_dedup(tmp_path: Path):
    p = tmp_path / "settings.local.json"
    ensure_hooks_config(p, 3, "DONE")
    # run again to ensure no duplicates
    ensure_hooks_config(p, 3, "DONE")
    data = json.loads(p.read_text())
    stop_entries = data.get("hooks", {}).get("Stop", [])
    # collect inner hook commands
    commands = []
    for entry in stop_entries:
        for h in entry.get("hooks") or []:
            if isinstance(h, dict) and h.get("type") == "command":
                commands.append(h.get("command"))
    # Our command should appear exactly once
    unique = [c for c in commands if c and c.endswith(".claude/hooks/stop-keep-asking.py")]
    assert len(unique) == 1


def test_update_todo_with_pr_trailing_spaces(tmp_path: Path):
    todo = tmp_path / "TODO.md"
    url = "https://github.com/owner/repo/pull/9"
    title1 = "README.md をよりリッチにする。上位の有名なライブラリのREADME.mdポイ感じにする。"
    md = f"- [ ] {title1} \n- [ ] README.md を i18n 化する\n"
    todo.write_text(md, encoding="utf-8")

    # Update the first item which has a trailing space in the line
    ok = update_todo_with_pr(
        todo,
        TodoItem(title=title1, children=[]),
        url,
    )
    assert ok
    text = todo.read_text(encoding="utf-8")
    expected = f"- [x] {title1} [#9](https://github.com/owner/repo/pull/9)"
    assert expected in text
    # The second remains unchecked
    assert "- [ ] README.md を i18n 化する" in text


def test_update_todo_with_pr_multiple_items(tmp_path: Path):
    todo = tmp_path / "TODO.md"
    md = "- [ ] タスクA \n- [ ] タスクB\n"
    todo.write_text(md, encoding="utf-8")

    ok1 = update_todo_with_pr(
        todo,
        TodoItem(title="タスクA", children=[]),
        "https://x/y/pull/12",
    )
    ok2 = update_todo_with_pr(
        todo,
        TodoItem(title="タスクB", children=[]),
        "https://x/y/pull/34",
    )
    assert ok1 and ok2

    text = todo.read_text(encoding="utf-8")
    assert "- [x] タスクA [#12](https://x/y/pull/12)" in text
    assert "- [x] タスクB [#34](https://x/y/pull/34)" in text


def test_update_todo_with_pr_without_number(tmp_path: Path):
    todo = tmp_path / "TODO.md"
    md = "- [ ] Task C\n"
    todo.write_text(md, encoding="utf-8")

    # URL without /pull/<n> should append raw URL in parentheses
    ok = update_todo_with_pr(
        todo,
        TodoItem(title="Task C", children=[]),
        "https://example.com/pr",
    )
    assert ok
    text = todo.read_text(encoding="utf-8")
    assert "- [x] Task C (https://example.com/pr)" in text
