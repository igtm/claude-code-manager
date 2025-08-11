from __future__ import annotations

import json
from pathlib import Path

from claude_code_manager.cli import ensure_hooks_config, parse_todo_markdown


def test_parse_todo_markdown_basic():
    md = """
- [x] done 1 [#1](url)
- [ ] top 1
  - [ ] child a
  - [ ] child b
- [ ] top 2
    """.strip()
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
    unique = [
        c for c in commands if c and c.endswith(".claude/hooks/stop-keep-asking.py")
    ]
    assert len(unique) == 1
