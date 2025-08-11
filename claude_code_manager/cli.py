from __future__ import annotations

import json
import os
import random
import re
import shutil
import stat
import string
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import typer

from . import __version__

# i18n loader and translator
I18N_CACHE: dict[str, dict[str, str]] = {}


def load_i18n_toml(path: Path) -> dict[str, dict[str, str]]:
    try:
        import tomllib

        if not path.exists():
            return {}
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        blocks = data.get("i18n") if isinstance(data.get("i18n"), dict) else data
        result: dict[str, dict[str, str]] = {}
        for lang, mapping in (blocks or {}).items():
            if isinstance(mapping, dict):
                # Ensure values are strings
                result[lang] = {str(k): str(v) for k, v in mapping.items()}
        return result
    except Exception:
        return {}


def set_i18n(path: Path) -> None:
    global I18N_CACHE
    I18N_CACHE = load_i18n_toml(path)


def tr(key: str, lang: str, **kwargs) -> str:
    # Lookup order: selected lang -> en -> key
    base = I18N_CACHE.get(lang) or {}
    s = base.get(key) or (I18N_CACHE.get("en") or {}).get(key) or key
    try:
        return s.format(**kwargs)
    except Exception:
        return s


APP = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Manage claude-code runs from a TODO list",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def echo(msg: str, err: bool = False):
    stream = sys.stderr if err else sys.stdout
    # Colorize errors in red when enabled
    if err:
        try:
            if COLOR_ENABLED:
                msg = f"\x1b[31m{msg}\x1b[0m"
        except NameError:
            # COLOR_ENABLED not initialized yet
            pass
    print(msg, file=stream, flush=True)


# --- simple color helpers ---
COLOR_ENABLED = True  # will be set based on CLI option and TTY
DEBUG_ENABLED = False  # set from CLI


def _ansi(code: str, s: str) -> str:
    return f"\x1b[{code}m{s}\x1b[0m" if COLOR_ENABLED else s


def color_info(s: str) -> str:
    return _ansi("36", s)  # cyan


def color_success(s: str) -> str:
    return _ansi("32", s)  # green


def color_warn(s: str) -> str:
    return _ansi("33", s)  # yellow


def color_header(s: str) -> str:
    return _ansi("1;36", s)  # bold cyan


def color_debug(s: str) -> str:
    return _ansi("35", s)  # magenta


def debug_log(msg: str) -> None:
    if DEBUG_ENABLED:
        try:
            sys.stderr.write(color_debug(f"[debug] {msg}\n"))
            sys.stderr.flush()
        except Exception:
            pass


class LiveRows:
    """Simple multi-row live renderer for TTY. Each row can have 1 or 2 lines."""

    def __init__(self, rows: int, lines_per_row: int = 2):
        self.rows = int(rows)
        self.lines_per_row = 1 if int(lines_per_row) == 1 else 2
        self.lines: list[tuple[str, str, bool]] = [("", "", False) for _ in range(self.rows)]
        self._lock = threading.Lock()
        self._initialized = False

    def _draw(self):
        total_lines = self.rows * self.lines_per_row
        try:
            if not self._initialized:
                # Allocate lines once
                for _ in range(total_lines):
                    sys.stderr.write("\n")
                # Move back to top of block
                if total_lines:
                    sys.stderr.write(f"\x1b[{total_lines}A")
                self._initialized = True
            else:
                # Move back to top of block to redraw
                if total_lines:
                    sys.stderr.write(f"\x1b[{total_lines}A")

            # Redraw all rows
            for i in range(self.rows):
                l1, l2, _ = self.lines[i]
                sys.stderr.write("\r\x1b[2K" + (l1 or ""))
                if self.lines_per_row == 2:
                    sys.stderr.write("\n\x1b[2K" + (l2 or ""))
                else:
                    sys.stderr.write("\n")

            # Leave cursor at bottom of block
            sys.stderr.flush()
        except Exception:
            pass

    def update(self, index: int, line1: str, line2: str, final: bool = False) -> None:
        if index < 0 or index >= self.rows:
            return
        with self._lock:
            self.lines[index] = (line1, line2, final)
            self._draw()

    def finish(self) -> None:
        # Ensure cursor is just after the block
        try:
            if not self._initialized:
                return
            sys.stderr.write("\n")
            sys.stderr.flush()
        except Exception:
            pass


@APP.callback()
def _version_callback(
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    if version:
        echo(__version__)
        raise typer.Exit()


@dataclass
class Config:
    cooldown: int = 0
    git_branch_prefix: str = "todo/"
    git_commit_message_prefix: str = "feat: "
    git_base_branch: str = "main"
    github_pr_title_prefix: str = "feat: "
    github_pr_body_template: str = "Implementing TODO item: {todo_item}"
    config_path: str = ".claude-manager.toml"
    input_path: str = "TODO.md"
    claude_args: str = ""
    hooks_config: str = ".claude/settings.local.json"
    max_keep_asking: int = 3
    task_done_message: str = "CLAUDE_MANAGER_DONE"
    show_claude_output: bool = False
    doctor: bool = False
    worktree_parallel: bool = False
    worktree_parallel_max_semaphore: int = 1
    lang: str = "en"
    i18n_path: str = ".claude-manager.i18n.toml"
    # Headless mode (always used)
    headless_prompt_template: str = (
        "Implement the following TODO item in this repository.\n\n"
        "Title: {title}\n"
        "Subtasks:\n{children_bullets}\n\n"
        "Please apply necessary changes. When finished, output the token: {done_token}\n"
    )
    headless_output_format: str = "stream-json"
    # Reporting
    pr_urls: list[str] | None = None  # filled during run
    color: bool = True


TODO_TOP_PATTERN = re.compile(r"^- \[ \] (?P<title>.+)$")
TODO_DONE_PATTERN = re.compile(r"^- \[x\] .+")
TODO_CHILD_PATTERN = re.compile(r"^\s{2,}- \[ \] (?P<title>.+)$")


@dataclass
class TodoItem:
    title: str
    children: list[str]


def parse_todo_markdown(md: str) -> list[TodoItem]:
    """Parse top-level unchecked items and attach child unchecked titles.
    Expects GitHub Flavored Markdown checklist structure.
    """
    items: list[TodoItem] = []
    current: TodoItem | None = None
    for line in md.splitlines():
        if TODO_DONE_PATTERN.match(line):
            continue
        m = TODO_TOP_PATTERN.match(line)
        if m:
            if current:
                items.append(current)
            current = TodoItem(title=m.group("title").strip(), children=[])
            continue
        m2 = TODO_CHILD_PATTERN.match(line)
        if m2 and current is not None:
            current.children.append(m2.group("title").strip())
    if current:
        items.append(current)
    return items


STOP_HOOK_REL_SCRIPT = ".claude/hooks/stop-keep-asking.py"
STOP_HOOK_COMMAND = f"$CLAUDE_PROJECT_DIR/{STOP_HOOK_REL_SCRIPT}"


def _write_stop_hook_script(script_path: Path, max_keep_asking: int, done_message: str) -> None:
    script_path.parent.mkdir(parents=True, exist_ok=True)
    template = """#!/usr/bin/env python3
import json, sys, os, io
from pathlib import Path

STATE_FILE = (
    Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    / ".claude"
    / "manager_state.json"
)

MAX_ASK = __MAX_ASK__
DONE_TOKEN = __DONE_TOKEN__


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(s):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def transcript_has_done(path: str, token: str) -> bool:
    if not path:
        return False
    try:
        p = os.path.expanduser(path)
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if token in line:
                    return True
    except Exception:
        return False
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        # invalid input, do nothing
        sys.exit(0)

    sid = data.get("session_id") or ""
    transcript_path = data.get("transcript_path") or ""

    # If DONE token already present, allow stop
    if transcript_has_done(transcript_path, DONE_TOKEN):
        print(json.dumps({"continue": True, "suppressOutput": True}, ensure_ascii=False))
        return

    # Count per-session asks
    state = load_state()
    key = f"{sid}:asks"
    cnt = int(state.get(key, 0))
    if cnt < MAX_ASK:
        state[key] = cnt + 1
        save_state(state)
        print(json.dumps({
            "decision": "block",
            "reason": f"続けて。実装が終了し終わっていたら、{DONE_TOKEN}と返して。",
            "suppressOutput": True
        }, ensure_ascii=False))
        return

    # Max reached: allow stop
    print(json.dumps({"continue": True, "suppressOutput": True}, ensure_ascii=False))

if __name__ == "__main__":
    main()
"""
    content = template.replace("__MAX_ASK__", str(int(max_keep_asking))).replace(
        "__DONE_TOKEN__", json.dumps(done_message, ensure_ascii=False)
    )
    script_path.write_text(content, encoding="utf-8")
    # Make executable
    st = os.stat(script_path)
    os.chmod(script_path, st.st_mode | stat.S_IEXEC)


def ensure_hooks_config(path: Path, max_keep_asking: int, done_message: str) -> None:
    """Create or update hooks config ensuring our Stop hook command exists once."""
    path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Ensure our stop hook script exists (embed current settings)
    script_path = path.parent / "hooks" / Path(STOP_HOOK_REL_SCRIPT).name
    _write_stop_hook_script(script_path, max_keep_asking, done_message)

    # 2) Load existing settings JSON
    data: dict
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}

    hooks = data.get("hooks") or {}

    stop_arr = hooks.get("Stop") or []
    # Normalize: each item is an object possibly with matcher and hooks
    if isinstance(stop_arr, dict):
        stop_arr = [stop_arr]

    # Clean up existing Stop entries:
    # - remove our command from any existing entry
    # - drop entries that end up empty or have no valid hooks list
    # - deduplicate hooks within an entry
    cleaned_stop_arr: list[dict] = []
    for entry in stop_arr if isinstance(stop_arr, list) else []:
        hooks_list = entry.get("hooks") or []
        if not isinstance(hooks_list, list):
            hooks_list = []
        filtered_hooks: list[dict] = []
        seen: set[tuple] = set()
        for h in hooks_list:
            if not isinstance(h, dict):
                continue
            if h.get("type") == "command" and h.get("command") == STOP_HOOK_COMMAND:
                # remove our command from legacy entries; we'll add a single canonical entry later
                continue
            key = (h.get("type"), h.get("command"))
            if key in seen:
                continue
            seen.add(key)
            filtered_hooks.append(h)
        if filtered_hooks:
            cleaned_stop_arr.append({**entry, "hooks": filtered_hooks})
        # if no hooks remain, drop the entry (avoids accumulating empty objects)

    stop_entry = {
        # No matcher for Stop per reference
        "hooks": [
            {
                "type": "command",
                "command": STOP_HOOK_COMMAND,
            }
        ]
    }

    # Append our canonical stop entry exactly once at the end
    cleaned_stop_arr.append(stop_entry)
    hooks["Stop"] = cleaned_stop_arr

    data["hooks"] = hooks
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _args_list(args: str) -> list[str]:
    return [x for x in args.split() if x]


def _args_has_flag(args_list: list[str], flag: str) -> bool:
    return any(a == flag or a.startswith(flag + "=") for a in args_list) or any(
        args_list[i] == flag and i + 1 < len(args_list) for i in range(len(args_list))
    )


def _get_flag_value(args_list: list[str], flag: str) -> str | None:
    for i, a in enumerate(args_list):
        if a == flag and i + 1 < len(args_list):
            return args_list[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def run_claude_code(
    args: str,
    show_output: bool,
    env: dict | None = None,
    cwd: Path | None = None,
    *,
    prompt: str,
    output_format: str = "stream-json",
    row_updater: Callable[[int, str, str, bool], None] | None = None,
    row_index: int | None = None,
) -> int:
    # Always run in headless mode using -p
    extra = _args_list(args)
    cmd: list[str] = ["claude", "-p", prompt]

    provided_fmt = _get_flag_value(extra, "--output-format")
    effective_fmt = provided_fmt or output_format

    if not provided_fmt:
        cmd += ["--output-format", output_format]

    # Ensure Claude emits structured info for stream-json
    if effective_fmt == "stream-json" and not _args_has_flag(extra, "--verbose"):
        cmd += ["--verbose"]

    cmd += extra

    debug_log(f"running: {' '.join(cmd)}")
    debug_log(f"cwd={cwd or Path.cwd()}")
    debug_log(f"show_output={show_output}, output_format={effective_fmt}")

    if show_output:
        # Stream output to terminal while also allowing JSON parsing by callers if needed
        p_head = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, **(env or {})},
            cwd=str(cwd) if cwd else None,
        )
        assert p_head.stdout is not None
        try:
            for line in p_head.stdout:
                try:
                    sys.stdout.write(line)
                except Exception:
                    pass
            p_head.wait()
            return int(p_head.returncode or 0)
        finally:
            try:
                p_head.stdout.close()
            except Exception:
                pass
    else:
        # Parse JSONL quietly and live-update a status with counts (no usage)
        counts: dict[str, int] = {"system": 0, "assistant": 0, "user": 0}
        allowed = set(counts.keys())

        spinner = "|/-\\"
        spin_idx = 0
        last_len = 0
        aborted = False
        errored = False

        def _counts_text() -> str:
            return ", ".join(
                [
                    f"assistant: {counts['assistant']}",
                    f"user: {counts['user']}",
                    f"system: {counts['system']}",
                ]
            )

        def _print_status(prefix_char: str | None = None, *, final: bool = False):
            nonlocal last_len
            ch = prefix_char if prefix_char is not None else spinner[spin_idx % len(spinner)]

            if row_updater is not None and row_index is not None and sys.stderr.isatty():
                # Parallel worktree rendering: single line per worktree, no color, no usage
                head = ch
                line = f"{head} worktree {row_index + 1} | {_counts_text()}"
                row_updater(row_index, line, "", final)
                return

            # Fallback: single-line spinner + counts (no usage)
            counts_part_plain = _counts_text()
            line1_plain = f"{ch} running claude...: {counts_part_plain}"
            try:
                import shutil as _shutil

                width = max(20, int(_shutil.get_terminal_size((80, 24)).columns))
            except Exception:
                width = 80
            if len(line1_plain) > width:
                line1_plain = line1_plain[: width - 1]

            if sys.stderr.isatty():
                # Optional colorization for spinner only
                try:
                    if ch == "✓":
                        spinner_col = color_success(ch)
                    elif ch == "❌":
                        spinner_col = color_warn(ch)
                    else:
                        spinner_col = color_info(ch)
                    if line1_plain.startswith(ch):
                        line1_out = spinner_col + line1_plain[len(ch) :]
                    else:
                        line1_out = line1_plain
                except Exception:
                    line1_out = line1_plain
                try:
                    sys.stderr.write("\r\x1b[2K" + line1_out)
                    sys.stderr.flush()
                except Exception:
                    pass
            else:
                pad = max(0, last_len - len(line1_plain))
                try:
                    sys.stderr.write("\r" + line1_plain + (" " * pad))
                    sys.stderr.flush()
                except Exception:
                    pass
                last_len = len(line1_plain)

        # initial status
        _print_status()

        p_head = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, **(env or {})},
            cwd=str(cwd) if cwd else None,
        )
        assert p_head.stdout is not None
        rc = 1
        try:
            for line in p_head.stdout:
                debug_log(f"line: {line.rstrip()}")
                dirty = False
                try:
                    obj = json.loads(line)
                    typ = str(obj.get("type", "")).strip()
                    debug_log(f"parsed type={typ}")
                    if typ in allowed:
                        counts[typ] = counts.get(typ, 0) + 1
                        dirty = True
                    if dirty:
                        spin_idx = (spin_idx + 1) % len(spinner)
                        _print_status()
                except Exception as e:
                    debug_log(f"non-json or parse error: {e}")
                    # ignore non-JSON lines
                    pass
            p_head.wait()
            rc = int(p_head.returncode or 0)
        except KeyboardInterrupt:
            aborted = True
            try:
                p_head.terminate()
            except Exception:
                pass
            try:
                p_head.wait(timeout=2)
            except Exception:
                pass
        except Exception:
            errored = True
        finally:
            try:
                p_head.stdout.close()
            except Exception:
                pass
        # finalize status line with a check/cross and newline
        try:
            marker = "✓" if (not aborted and not errored and rc == 0) else "❌"
            _print_status(prefix_char=marker, final=True)
            if row_updater is None or row_index is None:
                sys.stderr.write("\n")
                sys.stderr.flush()
        except Exception:
            pass
        return rc


def pr_number_from_url(url: str) -> int | None:
    m = re.search(r"/pull/(\d+)", url)
    return int(m.group(1)) if m else None


def update_todo_with_pr(todo_path: Path, item: TodoItem, pr_url: str | None) -> bool:
    if not todo_path.exists():
        return False
    text = todo_path.read_text(encoding="utf-8")
    replacement_suffix = ""
    if pr_url:
        num = pr_number_from_url(pr_url)
        if num is not None:
            replacement_suffix = f" [#{num}]({pr_url})"
        else:
            replacement_suffix = f" ({pr_url})"
    # Be tolerant of trailing spaces after the title in the original TODO line
    pattern = re.compile(rf"^- \[ \] {re.escape(item.title)}\s*$", re.MULTILINE)
    new_text, n = pattern.subn(f"- [x] {item.title}{replacement_suffix}", text, count=1)
    if n:
        todo_path.write_text(new_text, encoding="utf-8")
        return True
    return False
