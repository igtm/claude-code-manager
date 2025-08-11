# Claude Code Manager

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/status-alpha-orange.svg" alt="Status">
</p>

A CLI tool to orchestrate [claude-code](https://docs.anthropic.com/en/docs/claude-code) runs from a Markdown TODO list. Automatically handles branch creation, task execution, and PR generation for systematic implementation of tasks.

## 🌟 Features

- **Markdown-Driven Workflow**: Implement tasks from a structured TODO markdown list
- **Automated Git Workflow**: Auto-creates branches, commits changes, and generates PRs
- **Claude Code Integration**: Seamlessly integrates with claude-code for AI-powered implementation
- **Parallel Execution**: Support for git worktree-based parallel task execution
- **Configurable**: Extensive configuration options via CLI or config file

## 📦 Installation

```bash
# Install with uv (recommended)
uv pip install -e .

# Install with pip
pip install -e .
```

## 🚀 Quick Start

1. Create a TODO.md file with tasks:

```markdown
- [ ] Implement feature X
  - [ ] Add validation for input data
  - [ ] Create error handling
- [ ] Add unit tests for module Y
```

2. Run Claude Code Manager:

```bash
claude-manager run --input TODO.md
```

## 📋 Command Reference

```bash
# Basic usage
claude-manager run --input TODO.md

# With custom options
claude-manager run --input TODO.md --cooldown 5 --git-branch-prefix "feature/" --max-keep-asking 5

# Parallel execution with worktrees
claude-manager run --input TODO.md --worktree-parallel --worktree-parallel-max-semaphore 3

# Validate configuration
claude-manager doctor
```

## ⚙️ Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--cooldown`, `-c` | Cooldown seconds between tasks | 0 |
| `--git-branch-prefix`, `-b` | Git branch name prefix | "todo/" |
| `--git-commit-message-prefix`, `-m` | Git commit message prefix | "feat: " |
| `--git-base-branch`, `-g` | Git base branch | "main" |
| `--github-pr-title-prefix`, `-t` | PR title prefix | "feat: " |
| `--input`, `-i` | Path to TODO markdown file | "TODO.md" |
| `--claude-args` | Additional arguments for claude-code | "" |
| `--max-keep-asking` | Maximum retry attempts | 3 |
| `--show-claude-output` | Show claude-code output | false |
| `--dry-run`, `-d` | Simulation mode (no claude-code execution) | false |
| `--worktree-parallel`, `-w` | Use git worktree for parallel execution | false |

For complete options, run `claude-manager --help`.

## 🧪 Development

```bash
# Install dev dependencies
uv pip install -e ".[dev,test]"

# Run tests
pytest

# Run linting
ruff check
ruff format
```

## 📄 License

MIT

## 📚 See Also

- [IMPLEMENT_PROMPT.md](./IMPLEMENT_PROMPT.md) for design documentation