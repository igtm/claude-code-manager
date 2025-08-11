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
import time
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
    dry_run: bool = False
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


CLAUDE_HOOKS_MARK = "// added by claude-code-manager"

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

    def has_our_command(entry: dict) -> bool:
        for h in entry.get("hooks", []) or []:
            if (
                isinstance(h, dict)
                and h.get("type") == "command"
                and h.get("command") == STOP_HOOK_COMMAND
            ):
                return True
        return False

    # Remove any duplicate inner hook objects with our command
    new_stop_arr: list[dict] = []
    for entry in stop_arr:
        existing_hooks = entry.get("hooks") or []
        if existing_hooks and isinstance(existing_hooks, list):
            filtered = [
                h
                for h in existing_hooks
                if not (
                    isinstance(h, dict)
                    and h.get("type") == "command"
                    and h.get("command") == STOP_HOOK_COMMAND
                )
            ]
            entry = {**entry, "hooks": filtered}
        new_stop_arr.append(entry)

    stop_entry = {
        # No matcher for Stop per reference
        "hooks": [
            {
                "type": "command",
                "command": STOP_HOOK_COMMAND,
                "comment": CLAUDE_HOOKS_MARK,
            }
        ]
    }

    # Append our entry at the end
    new_stop_arr.append(stop_entry)
    hooks["Stop"] = new_stop_arr

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
        # Parse JSONL quietly and live-update a one-line status with counts
        counts: dict[str, int] = {"system": 0, "assistant": 0, "user": 0}
        allowed = set(counts.keys())

        spinner = "|/-\\"
        spin_idx = 0
        last_len = 0

        def _print_status(prefix_char: str | None = None):
            nonlocal last_len
            ch = prefix_char if prefix_char is not None else spinner[spin_idx % len(spinner)]
            msg = f"{ch} running claude...: " + ", ".join(
                [
                    f"assistant: {counts['assistant']}",
                    f"user: {counts['user']}",
                    f"system: {counts['system']}",
                ]
            )
            pad = max(0, last_len - len(msg))
            try:
                sys.stderr.write("\r" + msg + (" " * pad))
                sys.stderr.flush()
            except Exception:
                pass
            last_len = len(msg)

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
        try:
            for line in p_head.stdout:
                debug_log(f"line: {line.rstrip()}")
                try:
                    obj = json.loads(line)
                    typ = str(obj.get("type", "")).strip()
                    debug_log(f"parsed type={typ}")
                    if typ in allowed:
                        counts[typ] = counts.get(typ, 0) + 1
                        spin_idx = (spin_idx + 1) % len(spinner)
                        _print_status()
                except Exception as e:
                    debug_log(f"non-json or parse error: {e}")
                    # ignore non-JSON lines
                    pass
            p_head.wait()
            rc = int(p_head.returncode or 0)
        finally:
            try:
                p_head.stdout.close()
            except Exception:
                pass
        # finalize status line with a check mark and newline
        try:
            _print_status(prefix_char="✓")
            sys.stderr.write("\n")
            sys.stderr.flush()
        except Exception:
            pass
        return rc


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(["git", *args], text=True, cwd=str(cwd) if cwd else None).strip()


def git_call(args: list[str], cwd: Path | None = None) -> None:
    subprocess.check_call(["git", *args], cwd=str(cwd) if cwd else None)


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

    # If nothing staged, skip commit/push
    try:
        staged = git("diff", "--cached", "--name-only", cwd=cwd)
    except Exception:
        staged = ""
    if not staged.strip():
        return

    git_call(["commit", "-m", message], cwd=cwd)
    git_call(["push", "-u", "origin", branch], cwd=cwd)


def commit_and_push(message: str, branch: str, cwd: Path | None = None):
    # Backward-compatible default: stage everything and push
    _commit_and_push_filtered(message, branch, cwd=cwd)


def create_pr(title: str, body: str, cwd: Path | None = None) -> str | None:
    # Try gh CLI if available
    try:
        out = subprocess.check_output(
            ["gh", "pr", "create", "--title", title, "--body", body, "--fill"],
            text=True,
            cwd=str(cwd) if cwd else None,
        )
        return out.strip()
    except Exception:
        return None


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
    pattern = re.compile(rf"^- \\[ \\] {re.escape(item.title)}\s*$", re.MULTILINE)
    new_text, n = pattern.subn(f"- [x] {item.title}{replacement_suffix}", text, count=1)
    if n:
        todo_path.write_text(new_text, encoding="utf-8")
        return True
    return False


def process_one_todo(item: TodoItem, cfg: Config, cwd: Path | None = None) -> None:
    branch = f"{cfg.git_branch_prefix}{slugify(item.title)}"
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

    if not cfg.dry_run:
        try:
            rc = run_claude_code(
                cfg.claude_args,
                cfg.show_claude_output,
                cwd=cwd or Path.cwd(),
                prompt=prompt,
                output_format=cfg.headless_output_format,
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
    pr_url = create_pr(pr_title, pr_body, cwd=cwd)
    if pr_url:
        echo(color_success(tr("pr_created", cfg.lang, url=pr_url)))
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


def process_in_worktree(root: Path, item: TodoItem, cfg: Config) -> None:
    worktrees_dir = root / ".worktrees"
    worktrees_dir.mkdir(exist_ok=True)
    branch = f"{cfg.git_branch_prefix}{slugify(item.title)}"
    wt_path = worktrees_dir / slugify(item.title)

    # Create or reset worktree pointing to the branch
    try:
        git("worktree", "remove", "-f", str(wt_path), cwd=root)
    except Exception:
        pass
    git("fetch", cwd=root)
    # Create the worktree bound to branch based on base branch tip
    git("worktree", "add", "-B", branch, str(wt_path), cfg.git_base_branch, cwd=root)
    # After creating worktree, ensure branch logic inside that tree respects local TODO
    ensure_branch(
        cfg.git_base_branch,
        branch,
        cwd=wt_path,
        prefer_local_todo=True,
        todo_relpath=cfg.input_path,
        lang=cfg.lang,
    )

    # Now process inside the worktree path
    process_one_todo(item, cfg, cwd=wt_path)


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
    dry_run: bool = typer.Option(False, "--dry-run", "-d"),
    doctor: bool = typer.Option(False, "--doctor", "-D"),
    worktree_parallel: bool = typer.Option(False, "--worktree-parallel", "-w"),
    worktree_parallel_max_semaphore: int = typer.Option(1, "--worktree-parallel-max-semaphore"),
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
        dry_run=dry_run,
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
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(process_in_worktree, root, item, cfg) for item in items]
            for fut in as_completed(futures):
                exc = fut.exception()
                if exc:
                    raise exc
        # After parallel run, return to base branch in root (best-effort)
        try:
            git("checkout", cfg.git_base_branch, cwd=root)
        except Exception:
            pass
        # After parallel run, print final report
        _print_final_report(cfg)
        return

    for idx, item in enumerate(items):
        echo(color_info(tr("processing", cfg.lang, title=item.title)))
        process_one_todo(item, cfg, cwd=root)
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
