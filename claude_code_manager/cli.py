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


@APP.callback(invoke_without_command=True)
def _version_callback(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit", is_eager=True
    ),
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

            def _colorize_line_from_plain(line_plain: str) -> str:
                line_colored = line_plain
                try:
                    # Color spinner/check/cross at the start
                    if line_colored.startswith(ch):
                        if ch == "✓":
                            spin_col = color_success(ch)
                        elif ch == "❌":
                            spin_col = color_warn(ch)
                        else:
                            spin_col = color_info(ch)
                        line_colored = spin_col + line_colored[len(ch) :]

                    # Color the role counts
                    a_tok = f"assistant: {counts['assistant']}"
                    u_tok = f"user: {counts['user']}"
                    s_tok = f"system: {counts['system']}"
                    if a_tok in line_colored:
                        line_colored = line_colored.replace(a_tok, color_success(a_tok))
                    if u_tok in line_colored:
                        line_colored = line_colored.replace(u_tok, color_info(u_tok))
                    if s_tok in line_colored:
                        line_colored = line_colored.replace(s_tok, color_warn(s_tok))
                except Exception:
                    pass
                return line_colored

            if row_updater is not None and row_index is not None and sys.stderr.isatty():
                # Parallel worktree rendering: single line per worktree
                line_plain = f"{ch} worktree {row_index + 1} | {_counts_text()}"
                line_out = _colorize_line_from_plain(line_plain) if COLOR_ENABLED else line_plain
                row_updater(row_index, line_out, "", final)
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
                try:
                    line1_out = (
                        _colorize_line_from_plain(line1_plain) if COLOR_ENABLED else line1_plain
                    )
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
        # finalize status line with a check/cross without moving to a new line
        try:
            marker = "✓" if (not aborted and not errored and rc == 0) else "❌"
            _print_status(prefix_char=marker, final=True)
            # Keep same line (no newline) to behave like spinner
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


def git(*args: str, cwd: Path | None = None) -> str:
    kwargs: dict = {"text": True, "cwd": str(cwd) if cwd else None}
    if not DEBUG_ENABLED:
        # Suppress stderr (progress/hints) when not debugging
        kwargs["stderr"] = subprocess.DEVNULL
    return subprocess.check_output(["git", *args], **kwargs).strip()


def git_call(args: list[str], cwd: Path | None = None) -> None:
    # Suppress stdout/stderr from git when not debugging
    kwargs: dict = {"cwd": str(cwd) if cwd else None}
    if not DEBUG_ENABLED:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    subprocess.check_call(["git", *args], **kwargs)


def is_git_ignored(path: Path, cwd: Path | None = None) -> bool:
    """Return True if path is ignored by git according to ignore rules."""
    spath = str(path)
    if cwd:
        try:
            spath = os.path.relpath(path, cwd)
        except Exception:
            spath = str(path)
    res = subprocess.run(
        ["git", "check-ignore", "-q", "--", spath],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return res.returncode == 0


def _warn_if_worktrees_not_ignored(root: Path, *, lang: str) -> None:
    """Warn user to add .worktrees to .gitignore if it's not ignored."""
    wt = root / ".worktrees"
    try:
        if not is_git_ignored(wt, cwd=root):
            if (lang or "").lower().startswith("ja"):
                msg = (
                    "⚠️ .worktrees が .gitignore に含まれていません。"
                    "git worktree 並列モードでは '.worktrees/' を .gitignore に追加してください。"
                )
            else:
                msg = (
                    "⚠️ .worktrees is not in .gitignore. "
                    "For worktree parallel mode, add '.worktrees/' to .gitignore."
                )
            echo(color_warn(msg))
    except Exception:
        # best-effort warning only
        pass


def _list_tracked_changes(cwd: Path | None = None) -> set[str]:
    changed: set[str] = set()
    try:
        out_wt = git("diff", "--name-only", cwd=cwd)
        if out_wt:
            for line in out_wt.splitlines():
                if line.strip():
                    changed.add(line.strip())
    except Exception:
        pass
    try:
        out_index = git("diff", "--cached", "--name-only", cwd=cwd)
        if out_index:
            for line in out_index.splitlines():
                if line.strip():
                    changed.add(line.strip())
    except Exception:
        pass
    return changed


def ensure_branch(
    base: str,
    name: str,
    cwd: Path | None = None,
    prefer_local_todo: bool = True,  # kept for backward-compat; no longer used
    todo_relpath: str = "TODO.md",  # kept for backward-compat; no longer used
    *,
    lang: str = "en",
) -> None:
    git("fetch", "--all", cwd=cwd)

    # Check for any local tracked changes before switching branches
    changed = _list_tracked_changes(cwd=cwd)
    if changed:
        echo(tr("uncommitted_changes", lang), err=True)
        for p in sorted(changed):
            echo(f"  - {p}", err=True)
        echo(tr("uncommitted_hint", lang), err=True)
        echo(tr("uncommitted_hint2", lang), err=True)
        raise typer.Exit(code=1)

    git("checkout", base, cwd=cwd)
    try:
        git("checkout", "-b", name, cwd=cwd)
    except subprocess.CalledProcessError:
        git("checkout", name, cwd=cwd)
        git("rebase", base, cwd=cwd)


def _commit_and_push_filtered(
    message: str,
    branch: str,
    cwd: Path | None = None,
    include_paths: list[str] | None = None,  # kept for compatibility; ignored
    exclude_paths: list[str] | None = None,
) -> None:
    # Stage everything, then unstage excluded paths if any
    git_call(["add", "-A"], cwd=cwd)
    if exclude_paths:
        for p in exclude_paths:
            try:
                git_call(["reset", "HEAD", "--", p], cwd=cwd)
            except Exception:
                pass

    # If nothing staged, we may still need to ensure the branch has an upstream
    def _ensure_upstream() -> None:
        try:
            # Check if upstream exists
            git("rev-parse", "--abbrev-ref", "@{u}", cwd=cwd)
        except Exception:
            # No upstream; push branch even without new commits
            try:
                git_call(["push", "-u", "origin", branch], cwd=cwd)
            except Exception:
                pass

    try:
        staged = git("diff", "--cached", "--name-only", cwd=cwd)
    except Exception:
        staged = ""
    if not staged.strip():
        _ensure_upstream()
        return

    git_call(["commit", "-m", message], cwd=cwd)
    git_call(["push", "-u", "origin", branch], cwd=cwd)


def commit_and_push(message: str, branch: str, cwd: Path | None = None):
    # Backward-compatible default: stage everything and push
    _commit_and_push_filtered(message, branch, cwd=cwd)


def create_pr(title: str, body: str, base: str, head: str, cwd: Path | None = None) -> str | None:
    """Create a PR using GitHub CLI and return the PR URL.
    - Prefer JSON output if supported by the installed gh.
    - Fall back to classic stdout parsing when --json is unavailable.
    """

    def _kwargs_capture():
        k: dict = {"text": True, "cwd": str(cwd) if cwd else None}
        if not DEBUG_ENABLED:
            k["stderr"] = subprocess.DEVNULL
        return k

    # Detect feature support
    supports_json = False
    try:
        help_txt = subprocess.check_output(
            ["gh", "pr", "create", "--help"], text=True, stderr=subprocess.DEVNULL
        )
        if "--json" in help_txt and "-q" in help_txt:
            supports_json = True
    except Exception:
        pass

    if supports_json:
        try:
            out = subprocess.check_output(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--base",
                    base,
                    "--head",
                    head,
                    "--json",
                    "url",
                    "-q",
                    ".url",
                ],
                **_kwargs_capture(),
            ).strip()
            if out:
                return out
        except Exception as e:
            debug_log(f"gh pr create (json) failed: {e}")
    else:
        try:
            # Classic mode: capture stdout and parse PR URL
            out2 = subprocess.check_output(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--base",
                    base,
                    "--head",
                    head,
                ],
                **_kwargs_capture(),
            )
            # Try to find URL like https://github.com/.../pull/123
            m = re.search(r"https?://[^\s]+/pull/\d+", out2)
            if m:
                return m.group(0)
        except Exception as e2:
            debug_log(f"gh pr create (classic) failed: {e2}")

    # Fallback: try to get existing PR for this branch
    try:
        # Detect json support for `pr view`
        supports_json_view = False
        help_view = subprocess.check_output(
            ["gh", "pr", "view", "--help"], text=True, stderr=subprocess.DEVNULL
        )
        if "--json" in help_view and "-q" in help_view:
            supports_json_view = True
        if supports_json_view:
            outv = subprocess.check_output(
                ["gh", "pr", "view", head, "--json", "url", "-q", ".url"],
                **_kwargs_capture(),
            ).strip()
            if outv:
                return outv
        else:
            outv2 = subprocess.check_output(["gh", "pr", "view", head], **_kwargs_capture())
            m2 = re.search(r"https?://[^\s]+/pull/\d+", outv2)
            if m2:
                return m2.group(0)
    except Exception as e3:
        debug_log(f"gh pr view fallback failed: {e3}")
        return None

    # No URL could be determined
    return None


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9-_]+", "-", text)
    slug = re.sub(r"-+", "-", text).strip("-")
    # Add 6 random alphanumeric chars for uniqueness
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{slug}-{rand}"


def load_config_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import tomllib  # Python 3.11+

        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# Serialize concurrent updates to the root TODO file
TODO_UPDATE_LOCK = threading.Lock()


def process_one_todo(
    item: TodoItem,
    cfg: Config,
    cwd: Path | None = None,
    *,
    skip_branch_ensure: bool = False,
    branch_name: str | None = None,
    row_updater: Callable[[int, str, str, bool], None] | None = None,
    row_index: int | None = None,
) -> str | None:
    branch = branch_name or f"{cfg.git_branch_prefix}{slugify(item.title)}"
    if not skip_branch_ensure:
        ensure_branch(
            cfg.git_base_branch,
            branch,
            cwd=cwd,
            prefer_local_todo=True,
            todo_relpath=cfg.input_path,
            lang=cfg.lang,
        )

    hooks_path = (cwd or Path.cwd()) / cfg.hooks_config
    ensure_hooks_config(hooks_path, cfg.max_keep_asking, cfg.task_done_message)

    # Build headless prompt from item
    children_bullets = "\n".join([f"- {c}" for c in item.children]) if item.children else "- (none)"
    prompt = cfg.headless_prompt_template.format(
        title=item.title,
        children_bullets=children_bullets,
        done_token=cfg.task_done_message,
    )

    # Always run Claude (dry-run option removed)
    try:
        rc = run_claude_code(
            cfg.claude_args,
            cfg.show_claude_output,
            cwd=cwd or Path.cwd(),
            prompt=prompt,
            output_format=cfg.headless_output_format,
            row_updater=row_updater,
            row_index=row_index,
        )
    except FileNotFoundError:
        echo(tr("claude_not_found", cfg.lang), err=True)
        raise typer.Exit(code=1) from None
    if rc != 0:
        echo(tr("claude_failed", cfg.lang, code=rc), err=True)
        raise typer.Exit(code=1)

    commit_msg = f"{cfg.git_commit_message_prefix}{item.title}"
    # Exclude TODO list file from the main code commit
    _commit_and_push_filtered(
        commit_msg,
        branch,
        cwd=cwd,
        exclude_paths=[cfg.input_path],
    )
    pr_title = f"{cfg.github_pr_title_prefix}{item.title}"
    pr_body = cfg.github_pr_body_template.format(todo_item=item.title)
    pr_url = create_pr(pr_title, pr_body, cfg.git_base_branch, branch, cwd=cwd)
    if pr_url:
        if cfg.pr_urls is not None:
            cfg.pr_urls.append(pr_url)
    else:
        # still collect placeholder for reporting
        if cfg.pr_urls is not None:
            cfg.pr_urls.append("")

    # Update TODO.md with PR link; do not commit it (it's git-ignored)
    todo_path = (cwd or Path.cwd()) / cfg.input_path
    if update_todo_with_pr(todo_path, item, pr_url):
        # No commit for TODO.md because it's ignored
        pass

    return pr_url


# Registry to track worktrees created during this run
CREATED_WORKTREES: list[Path] = []
CREATED_WORKTREES_LOCK = threading.Lock()


def _cleanup_created_worktrees(root: Path) -> None:
    """Best-effort removal of worktrees created during this run."""
    try:
        with CREATED_WORKTREES_LOCK:
            paths = list(CREATED_WORKTREES)
        for wt_path in paths:
            try:
                subprocess.run(
                    ["git", "worktree", "remove", "-f", str(wt_path)],
                    cwd=root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except Exception:
                pass
        # prune registry of paths that no longer exist
        with CREATED_WORKTREES_LOCK:
            remaining: list[Path] = []
            for p in CREATED_WORKTREES:
                try:
                    if p.exists():
                        remaining.append(p)
                except Exception:
                    pass
            CREATED_WORKTREES[:] = remaining
    except Exception:
        pass


def process_in_worktree(
    root: Path,
    item: TodoItem,
    cfg: Config,
    *,
    row_updater: Callable[[int, str, str, bool], None] | None = None,
    row_index: int | None = None,
) -> None:
    worktrees_dir = root / ".worktrees"
    worktrees_dir.mkdir(exist_ok=True)

    # Use a single slug for both branch and worktree path to avoid mismatch
    slug = slugify(item.title)
    branch = f"{cfg.git_branch_prefix}{slug}"
    wt_path = worktrees_dir / slug

    # Remove any existing directory silently if it is a registered worktree; suppress noisy errors
    try:
        subprocess.run(
            ["git", "worktree", "remove", "-f", str(wt_path)],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass

    git("fetch", cwd=root)
    # Create the worktree bound to branch based on base branch tip
    git("worktree", "add", "-B", branch, str(wt_path), cfg.git_base_branch, cwd=root)

    # Register created worktree for cleanup
    try:
        with CREATED_WORKTREES_LOCK:
            CREATED_WORKTREES.append(wt_path)
    except Exception:
        pass

    try:
        # Do NOT switch to base/main inside the worktree; it's already on the new branch
        pr_url = process_one_todo(
            item,
            cfg,
            cwd=wt_path,
            skip_branch_ensure=True,
            branch_name=branch,
            row_updater=row_updater,
            row_index=row_index,
        )

        # After worktree completes, update the ROOT TODO.md with a check and PR URL
        try:
            with TODO_UPDATE_LOCK:
                update_todo_with_pr(root / cfg.input_path, item, pr_url)
        except Exception:
            # Best-effort; ignore errors updating the shared TODO
            pass
    finally:
        # Always attempt to remove the worktree
        try:
            subprocess.run(
                ["git", "worktree", "remove", "-f", str(wt_path)],
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass
        # Unregister
        try:
            with CREATED_WORKTREES_LOCK:
                if wt_path in CREATED_WORKTREES:
                    CREATED_WORKTREES.remove(wt_path)
        except Exception:
            pass


def _print_final_report(cfg: Config) -> None:
    # Summary header
    echo("")
    echo(color_header("=== Summary Report ==="))

    if not cfg.pr_urls:
        echo(color_warn("No pull requests were created."))
        return

    # Print list of PR URLs
    echo(color_info("Pull Requests:"))
    for i, url in enumerate(cfg.pr_urls, start=1):
        label = url if url else "(no PR created)"
        echo(f"  {i}. {label}")

    echo(color_success("Done."))


@APP.command("run")
def run(
    cooldown: int = typer.Option(0, "--cooldown", "-c"),
    git_branch_prefix: str = typer.Option("todo/", "--git-branch-prefix", "-b"),
    git_commit_message_prefix: str = typer.Option("feat: ", "--git-commit-message-prefix", "-m"),
    git_base_branch: str = typer.Option("main", "--git-base-branch", "-g"),
    github_pr_title_prefix: str = typer.Option("feat: ", "--github-pr-title-prefix", "-t"),
    github_pr_body_template: str = typer.Option(
        "Implementing TODO item: {todo_item}", "--github-pr-body-template", "-p"
    ),
    config_path: str = typer.Option(".claude-manager.toml", "--config", "-f"),
    input_path: str = typer.Option("TODO.md", "--input", "-i"),
    claude_args: str = typer.Option("--dangerously-skip-permissions", "--claude-args"),
    hooks_config: str = typer.Option(".claude/settings.local.json", "--hooks-config"),
    max_keep_asking: int = typer.Option(3, "--max-keep-asking"),
    task_done_message: str = typer.Option("CLAUDE_MANAGER_DONE", "--task-done-message"),
    show_claude_output: bool = typer.Option(False, "--show-claude-output"),
    doctor: bool = typer.Option(False, "--doctor", "-D"),
    worktree_parallel: bool = typer.Option(False, "--worktree-parallel", "-w"),
    worktree_parallel_max_semaphore: int = typer.Option(
        1, "--worktree-parallel-max-semaphore", "-s"
    ),
    lang: str = typer.Option("en", "--lang", "-L"),
    i18n_path: str = typer.Option(
        ".claude-manager.i18n.toml", "--i18n-path", help="Path to i18n TOML file"
    ),
    # Headless options
    headless_prompt_template: str = typer.Option(
        None,
        "--headless-prompt-template",
        help="Template for the headless prompt (use {title}, {children_bullets}, {done_token})",
    ),
    headless_output_format: str = typer.Option(
        "stream-json", "--headless-output-format", help="Claude output format"
    ),
    # Color option
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    # Debug
    debug: bool = typer.Option(False, "--debug", help="Enable debug logs to stderr"),
):
    cfg = Config(
        cooldown=cooldown,
        git_branch_prefix=git_branch_prefix,
        git_commit_message_prefix=git_commit_message_prefix,
        git_base_branch=git_base_branch,
        github_pr_title_prefix=github_pr_title_prefix,
        github_pr_body_template=github_pr_body_template,
        config_path=config_path,
        input_path=input_path,
        claude_args=claude_args,
        hooks_config=hooks_config,
        max_keep_asking=max_keep_asking,
        task_done_message=task_done_message,
        show_claude_output=show_claude_output,
        doctor=doctor,
        worktree_parallel=worktree_parallel,
        worktree_parallel_max_semaphore=worktree_parallel_max_semaphore,
        lang=lang,
        i18n_path=i18n_path,
        headless_output_format=headless_output_format,
        pr_urls=[],
        color=not no_color,
    )
    if headless_prompt_template:
        cfg.headless_prompt_template = headless_prompt_template

    # Load config file overrides
    conf = load_config_toml(Path(config_path))
    if conf:
        # Shallow merge for known keys under [claude_manager]
        cm = conf.get("claude_manager") or {}
        for k, v in cm.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)

    root = Path.cwd()

    # Load i18n from TOML
    set_i18n(root / cfg.i18n_path)

    # set global color/debug flags considering TTY as well
    global COLOR_ENABLED, DEBUG_ENABLED
    COLOR_ENABLED = bool(cfg.color) and sys.stdout.isatty()
    DEBUG_ENABLED = bool(debug)

    if doctor:
        echo(tr("doctor_validating", cfg.lang))
        hooks_abspath = root / cfg.hooks_config
        todo_abspath = root / cfg.input_path
        echo(tr("base_branch", cfg.lang, branch=cfg.git_base_branch))

        ok = True
        if hooks_abspath.exists():
            echo(tr("hooks_file_exists", cfg.lang, path=str(hooks_abspath)))
        else:
            echo(tr("hooks_file_missing", cfg.lang, path=str(hooks_abspath)), err=True)
            ok = False

        if todo_abspath.exists():
            echo(tr("todo_file_exists", cfg.lang, path=str(todo_abspath)))
        else:
            echo(tr("todo_file_missing", cfg.lang, path=str(todo_abspath)), err=True)
            ok = False

        # Check claude CLI
        claude_ok = True
        if shutil.which("claude"):
            echo(tr("claude_cli_ok", cfg.lang))
        else:
            echo(tr("claude_cli_missing", cfg.lang), err=True)
            claude_ok = False

        # Check git repo and ignore status
        git_ok = True
        try:
            git("rev-parse", "--is-inside-work-tree")
            echo(tr("git_repo_ok", cfg.lang))
        except Exception as e:
            echo(tr("git_repo_failed", cfg.lang, error=e), err=True)
            git_ok = False

        ignore_ok = True
        try:
            if is_git_ignored(todo_abspath, cwd=root):
                echo(tr("todo_ignored_ok", cfg.lang))
            else:
                echo(tr("todo_not_ignored", cfg.lang, path=str(todo_abspath)), err=True)
                ignore_ok = False
        except Exception as e:
            echo(tr("gitignore_check_failed", cfg.lang, error=e), err=True)
            ignore_ok = False

        # Advisory warning about .worktrees ignore setting (does not affect success)
        _warn_if_worktrees_not_ignored(root, lang=cfg.lang)

        if ok and git_ok and ignore_ok and claude_ok:
            echo(tr("doctor_ok", cfg.lang))
            raise typer.Exit(code=0)
        else:
            echo(tr("doctor_failed", cfg.lang), err=True)
            raise typer.Exit(code=1)

    # Ensure TODO file is ignored before proceeding
    todo_abspath = root / cfg.input_path
    if not is_git_ignored(todo_abspath, cwd=root):
        echo(tr("todo_must_be_ignored", cfg.lang, path=str(todo_abspath)), err=True)
        raise typer.Exit(code=1)

    md = (
        (root / cfg.input_path).read_text(encoding="utf-8")
        if (root / cfg.input_path).exists()
        else ""
    )
    items = parse_todo_markdown(md)
    if not items:
        echo(tr("no_todo", cfg.lang))
        raise typer.Exit(code=0)

    if cfg.worktree_parallel:
        max_workers = max(1, int(cfg.worktree_parallel_max_semaphore))
        echo(tr("running_parallel", cfg.lang, workers=max_workers))
        _warn_if_worktrees_not_ignored(root, lang=cfg.lang)
        live = LiveRows(len(items), lines_per_row=1) if sys.stderr.isatty() else None
        ex = ThreadPoolExecutor(max_workers=max_workers)
        try:
            futures = [
                ex.submit(
                    process_in_worktree,
                    root,
                    item,
                    cfg,
                    row_updater=(live.update if live else None),
                    row_index=i,
                )
                for i, item in enumerate(items)
            ]
            for fut in as_completed(futures):
                exc = fut.exception()
                if exc:
                    raise exc
        except KeyboardInterrupt:
            # Cancel remaining futures and cleanup worktrees
            try:
                for fut in futures:
                    fut.cancel()
            except Exception:
                pass
        finally:
            try:
                ex.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            if live:
                live.finish()
            # Best-effort cleanup of any remaining worktrees
            _cleanup_created_worktrees(root)
            try:
                git("checkout", cfg.git_base_branch, cwd=root)
            except Exception:
                pass
        _print_final_report(cfg)
        return

    for idx, item in enumerate(items):
        echo(color_info(tr("processing", cfg.lang, title=item.title)))
        _ = process_one_todo(item, cfg, cwd=root)
        if idx < len(items) - 1 and cfg.cooldown > 0:
            time.sleep(cfg.cooldown)

    # After sequential run, return to base branch (best-effort)
    try:
        git("checkout", cfg.git_base_branch, cwd=root)
    except Exception:
        pass

    # After sequential run, print final report
    _print_final_report(cfg)


def main():  # entry point
    APP()
