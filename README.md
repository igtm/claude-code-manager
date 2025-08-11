# Claude Code Manager

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+"/>
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License"/>
</p>

A powerful CLI tool to orchestrate and automate claude-code runs from a Markdown TODO list. Claude Code Manager helps you implement features, fix bugs, and manage code changes by automatically:

- Processing tasks from a markdown TODO list
- Creating Git branches for each task
- Executing claude-code with appropriate prompts
- Committing changes and creating pull requests
- Updating your TODO list with completion status

## Features

- ✅ **Automated Task Processing**: Execute claude-code against each TODO item sequentially
- 🌿 **Git Integration**: Automatically create branches, commit changes, and make PRs
- 🔄 **Intelligent Workflow**: Processes TODO items one by one with configurable cooldown
- 🧪 **Smart Completion Detection**: Uses hooks to determine when claude-code has finished
- 🚀 **Parallel Execution**: Optional git worktree-based parallel processing
- 🌍 **Internationalization**: Supports multiple languages through i18n
- 🔍 **Diagnostics**: Doctor command to verify your configuration

## Installation

```bash
# Install with uv
uv pip install -e .

# Or with regular pip
pip install -e .
```

## Quick Start

1. Create a markdown TODO list file (default: `TODO.md`):
   ```markdown
   - [ ] Implement user authentication
     - [ ] Add login form
     - [ ] Create authentication middleware
   - [ ] Add unit tests for the auth module
   ```

2. Run claude-manager:
   ```bash
   claude-manager run --input TODO.md
   ```

3. Claude Code Manager will:
   - Process each top-level unchecked item
   - Create a git branch for the task
   - Run claude-code with appropriate prompts
   - Check for completion 
   - Commit changes and create a PR
   - Update the TODO list with completion status and PR link

## Usage

```bash
# Basic usage
claude-manager run

# Show claude-code output
claude-manager run --show-claude-output

# Parallel execution using git worktrees
claude-manager run --worktree-parallel

# Check configuration
claude-manager run --doctor
```

## Configuration

You can configure Claude Code Manager in several ways:

### Command Line Options

```bash
# Full options list
claude-manager run --help

# Common options
claude-manager run \
  --cooldown 5 \
  --git-branch-prefix "feature/" \
  --git-base-branch "develop" \
  --input "TASKS.md" \
  --claude-args "--dangerously-skip-permissions" \
  --max-keep-asking 5
```

### Configuration File

Create a `.claude-manager.toml` file:

```toml
[claude_manager]
cooldown = 5
git_branch_prefix = "feature/"
git_base_branch = "develop"
input_path = "TASKS.md"
claude_args = "--dangerously-skip-permissions"
max_keep_asking = 5
```

## Options Reference

| Option | Description | Default |
|--------|-------------|---------|
| `--cooldown`, `-c` | Seconds to wait between TODO items | `0` |
| `--git-branch-prefix`, `-b` | Prefix for git branches | `todo/` |
| `--git-commit-message-prefix`, `-m` | Prefix for commit messages | `feat: ` |
| `--git-base-branch`, `-g` | Base branch name | `main` |
| `--github-pr-title-prefix`, `-t` | Prefix for PR titles | `feat: ` |
| `--github-pr-body-template`, `-p` | Template for PR body | `Implementing TODO item: {todo_item}` |
| `--config`, `-f` | Path to config file | `.claude-manager.toml` |
| `--input`, `-i` | Path to TODO list file | `TODO.md` |
| `--claude-args` | Arguments for claude-code | `--dangerously-skip-permissions` |
| `--hooks-config` | Path to hooks config | `.claude/settings.local.json` |
| `--max-keep-asking` | Max tries for completion check | `3` |
| `--task-done-message` | Completion message token | `CLAUDE_MANAGER_DONE` |
| `--show-claude-output` | Show claude-code output | `false` |
| `--dry-run`, `-d` | Simulate without running claude-code | `false` |
| `--doctor`, `-D` | Validate configuration | `false` |
| `--worktree-parallel`, `-w` | Use git worktrees for parallel execution | `false` |
| `--worktree-parallel-max-semaphore` | Max parallel executions | `1` |

## TODO List Format

Claude Code Manager expects GitHub Flavored Markdown checklists:

```markdown
- [x] Completed item [#1](https://github.com/user/repo/pull/1)
- [ ] Item to process
  - [ ] Subtask 1 (included in prompt)
  - [ ] Subtask 2 (included in prompt)
- [ ] Next item to process
```

## Development

1. Clone the repository
2. Install development dependencies: `uv pip install -e ".[dev]"`
3. Run tests: `pytest`

See [IMPLEMENT_PROMPT.md](IMPLEMENT_PROMPT.md) for the detailed design plan.

## License

MIT