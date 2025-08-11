from __future__ import annotations

import json
import os
import random
import re
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

APP = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Manage claude-code runs from a TODO list",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def echo(msg: str, err: bool = False):
    stream = sys.stderr if err else sys.stdout
    print(msg, file=stream)


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
    content = f"""#!/usr/bin/env python3
import json, sys, os, io
from pathlib import Path

STATE_FILE = (
    Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    / ".claude"
    / "manager_state.json"
)

MAX_ASK = {int(max_keep_asking)}
DONE_TOKEN = {json.dumps(done_message, ensure_ascii=False)}


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {{}}


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
        print(json.dumps({{"continue": True, "suppressOutput": True}}, ensure_ascii=False))
        return

    # Count per-session asks
    state = load_state()
    key = f"{{sid}}:asks"
    cnt = int(state.get(key, 0))
    if cnt < MAX_ASK:
        state[key] = cnt + 1
        save_state(state)
        print(json.dumps({{
            "decision": "block",
            "reason": f"続けて。実装が終了し終わっていたら、{{DONE_TOKEN}}と返して。",
            "suppressOutput": True
        }}, ensure_ascii=False))
        return

    # Max reached: allow stop
    print(json.dumps({{"continue": True, "suppressOutput": True}}, ensure_ascii=False))

if __name__ == "__main__":
    main()
"""
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


def run_claude_code(
    args: str, show_output: bool, env: dict | None = None, cwd: Path | None = None
) -> int:
    cmd = ["claude"] + ([x for x in args.split() if x] if args else [])
    stdout = None if show_output else subprocess.DEVNULL
    proc = subprocess.run(
        cmd,
        stdout=stdout,
        stderr=subprocess.STDOUT,
        env={**os.environ, **(env or {})},
        cwd=str(cwd) if cwd else None,
    )
    return proc.returncode


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(["git", *args], text=True, cwd=str(cwd) if cwd else None).strip()


def git_call(args: list[str], cwd: Path | None = None) -> None:
    subprocess.check_call(["git", *args], cwd=str(cwd) if cwd else None)


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
    prefer_local_todo: bool = True,
    todo_relpath: str = "TODO.md",
) -> None:
    git("fetch", "--all", cwd=cwd)

    # Check for local changes (excluding TODO.md) before switching branches
    changed = _list_tracked_changes(cwd=cwd)
    # Normalize relative paths for comparison
    todo_rel_norm = todo_relpath.replace("\\", "/")
    changed_excl_todo = {p for p in changed if p.replace("\\", "/") != todo_rel_norm}
    if changed_excl_todo:
        echo("Uncommitted changes detected (excluding TODO.md):", err=True)
        for p in sorted(changed_excl_todo):
            echo(f"  - {p}", err=True)
        echo("Please commit or stash your changes before switching branches.", err=True)
        echo("Hint: git add -A && git commit -m 'WIP'  or  git stash -u", err=True)
        raise typer.Exit(code=1)

    # Optionally stash local TODO.md before switching
    stashed = False
    if prefer_local_todo:
        try:
            # Stash only TODO.md if modified
            git("stash", "push", "-m", "claude-manager: TODO.md", "--", todo_relpath, cwd=cwd)
            stashed = True
        except Exception:
            stashed = False

    git("checkout", base, cwd=cwd)
    # Removed: pull after checkout
    try:
        git("checkout", "-b", name, cwd=cwd)
    except subprocess.CalledProcessError:
        git("checkout", name, cwd=cwd)
        git("rebase", base, cwd=cwd)

    # Re-apply stashed TODO.md so local changes take precedence
    if stashed:
        try:
            git("stash", "pop", cwd=cwd)
        except Exception:
            # If conflict occurs, keep local version
            try:
                subprocess.check_call(
                    ["git", "checkout", "--ours", todo_relpath],
                    cwd=str(cwd) if cwd else None,
                )
                subprocess.check_call(
                    ["git", "add", todo_relpath],
                    cwd=str(cwd) if cwd else None,
                )
                # Do not commit here; later flow will commit when updating TODO
            except Exception:
                pass


def _commit_and_push_filtered(
    message: str,
    branch: str,
    cwd: Path | None = None,
    include_paths: list[str] | None = None,
    exclude_paths: list[str] | None = None,
) -> None:
    # Stage files according to filters
    if include_paths:
        git_call(["add", "--", *include_paths], cwd=cwd)
    else:
        git_call(["add", "-A"], cwd=cwd)
        if exclude_paths:
            for p in exclude_paths:
                # Unstage excluded paths if they were staged
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
    pattern = re.compile(rf"^- \[ \] {re.escape(item.title)}$", re.MULTILINE)
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
    )

    hooks_path = (cwd or Path.cwd()) / cfg.hooks_config
    ensure_hooks_config(hooks_path, cfg.max_keep_asking, cfg.task_done_message)

    if not cfg.dry_run:
        rc = run_claude_code(cfg.claude_args, cfg.show_claude_output, cwd=cwd or Path.cwd())
        if rc != 0:
            raise RuntimeError(f"claude exited with {rc}")

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
        echo(f"PR created: {pr_url}")

    # Update TODO.md with PR link and commit so working tree stays clean
    todo_path = (cwd or Path.cwd()) / cfg.input_path
    if update_todo_with_pr(todo_path, item, pr_url):
        # Commit only the TODO list file
        _commit_and_push_filtered(
            f"{cfg.git_commit_message_prefix}{item.title} [todo]",
            branch,
            cwd=cwd,
            include_paths=[cfg.input_path],
        )


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
    )

    # Now process inside the worktree path
    process_one_todo(item, cfg, cwd=wt_path)


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
    )

    # Load config file overrides
    conf = load_config_toml(Path(config_path))
    if conf:
        # Shallow merge for known keys under [claude_manager]
        cm = conf.get("claude_manager") or {}
        for k, v in cm.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)

    root = Path.cwd()

    if doctor:
        echo("Doctor: validating configuration...")
        hooks_abspath = root / cfg.hooks_config
        todo_abspath = root / cfg.input_path
        echo(f"base branch: {cfg.git_base_branch}")

        ok = True
        if hooks_abspath.exists():
            echo(f"✅ hooks file exists: {hooks_abspath}")
        else:
            echo(f"❌ hooks file missing: {hooks_abspath}", err=True)
            ok = False

        if todo_abspath.exists():
            echo(f"✅ TODO file exists: {todo_abspath}")
        else:
            echo(f"❌ TODO file missing: {todo_abspath}", err=True)
            ok = False

        git_ok = True
        try:
            git("rev-parse", "--is-inside-work-tree")
            echo("✅ git repository: OK")
        except Exception as e:
            echo(f"❌ git repository check failed: {e}", err=True)
            git_ok = False

        if ok and git_ok:
            echo("✅ Doctor: OK")
            raise typer.Exit(code=0)
        else:
            echo("❌ Doctor: Failed", err=True)
            raise typer.Exit(code=1)

    md = (
        (root / cfg.input_path).read_text(encoding="utf-8")
        if (root / cfg.input_path).exists()
        else ""
    )
    items = parse_todo_markdown(md)
    if not items:
        echo("No TODO items found.")
        raise typer.Exit(code=0)

    if cfg.worktree_parallel:
        max_workers = max(1, int(cfg.worktree_parallel_max_semaphore))
        echo(f"Running in worktree-parallel mode with {max_workers} workers...")
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(process_in_worktree, root, item, cfg) for item in items]
            for fut in as_completed(futures):
                exc = fut.exception()
                if exc:
                    raise exc
        return

    for idx, item in enumerate(items):
        echo(f"Processing: {item.title}")
        process_one_todo(item, cfg, cwd=root)
        if idx < len(items) - 1 and cfg.cooldown > 0:
            time.sleep(cfg.cooldown)


def main():  # entry point
    APP()
