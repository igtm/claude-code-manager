# Claude Code Manager

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI Version](https://img.shields.io/badge/pypi-0.1.0-blue.svg)](https://pypi.org/project/claude-code-manager/)

**A powerful CLI to orchestrate claude-code runs from a Markdown TODO list.**

</div>

## 📋 Overview

Claude Code Manager is a Python CLI tool that automates the workflow of implementing TODO items using Anthropic's Claude AI. It processes a markdown TODO list, creates git branches for each item, implements the feature using claude-code, and creates pull requests automatically.

## ✨ Features

- 🤖 **Claude AI Integration**: Leverages claude-code to implement features automatically
- 📝 **Markdown TODO Processing**: Works with GitHub flavored markdown TODO lists
- 🌲 **Git Workflow**: Creates branches, commits changes, and generates PRs
- 🔀 **Parallel Execution**: Supports parallel processing with git worktrees
- 🌐 **i18n Support**: Configurable localization for messages
- 🧰 **Highly Configurable**: Customize behavior through CLI options or config file

## 🚀 Quick Start

### Installation

```bash
# Install with uv (recommended)
uv pip install -e .

# Or with standard pip
pip install -e .
```

### Basic Usage

1. Create a TODO.md file with your feature requests in markdown format:
```markdown
- [x] Completed task 1 [#1](https://github.com/user/repo/pull/1)
- [ ] Add dark mode support
  - [ ] Create toggle component
  - [ ] Implement theme switching logic
- [ ] Improve error handling
```

2. Run claude-manager:
```bash
claude-manager run --input TODO.md
```

## 📖 Example Usage

```bash
# Basic usage
claude-manager run

# With custom options
claude-manager run --cooldown 5 --git-base-branch develop --show-claude-output

# Run tasks in parallel using git worktrees
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3

# Validate configuration
claude-manager run --doctor
```

## ⚙️ Configuration

Configure claude-manager through command line arguments or a `.claude-manager.toml` file:

```toml
[claude_manager]
cooldown = 0
git_branch_prefix = "todo/"
git_commit_message_prefix = "feat: "
git_base_branch = "main"
github_pr_title_prefix = "feat: "
github_pr_body_template = "Implementing TODO item: {todo_item}"
hooks_config = ".claude/settings.local.json"
max_keep_asking = 3
task_done_message = "CLAUDE_MANAGER_DONE"
show_claude_output = false
worktree_parallel = false
worktree_parallel_max_semaphore = 1
```

## 🔧 Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--cooldown`, `-c` | Seconds to wait between tasks | 0 |
| `--git-branch-prefix`, `-b` | Branch name prefix | "todo/" |
| `--git-base-branch`, `-g` | Base branch for new branches | "main" |
| `--input`, `-i` | Path to TODO markdown file | "TODO.md" |
| `--claude-args` | Arguments to pass to claude-code | "--dangerously-skip-permissions" |
| `--show-claude-output` | Show claude-code output | false |
| `--worktree-parallel`, `-w` | Enable parallel execution with git worktrees | false |
| `--doctor`, `-D` | Check configuration | false |
| `--lang`, `-L` | Language for messages | "en" |
| `--help`, `-h` | Show help message | |
| `--version`, `-v` | Show version | |

## 🧪 Development

```bash
# Install development dependencies
uv pip install -e ".[dev,test]"

# Run tests
pytest

# Run linting
ruff check
```

## 📄 License

MIT

## 📚 Learn More

For more details on the implementation design, see [IMPLEMENT_PROMPT.md](IMPLEMENT_PROMPT.md).