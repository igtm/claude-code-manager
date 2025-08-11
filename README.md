# Claude Code Manager

![GitHub License](https://img.shields.io/github/license/igtm/claude-code-manager)
![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)

A powerful CLI that orchestrates Claude Code runs from a Markdown TODO list. Automate implementing feature requests with Claude and streamline your development workflow with Git integration.

## ✨ Features

- 📋 Execute Claude Code tasks from a structured Markdown TODO list
- 🌲 Branch, commit, and PR creation for each TODO item
- 🪝 Automatic Claude hooks configuration
- 🚦 Continuation management to ensure task completion
- 🔀 Parallel execution via Git worktree for improved performance
- 🌐 i18n support for internationalized messages
- 🔍 Built-in diagnostic tools to verify your setup

## 🚀 Quick Start

### Installation

```bash
# Install with uv (recommended)
uv pip install -e .

# Or with regular pip
pip install -e .
```

### Basic Usage

1. Create a `TODO.md` file with your tasks:

```markdown
- [ ] Implement dark mode for the UI
  - [ ] Add theme toggle in settings
  - [ ] Create dark color palette
- [ ] Add user authentication
```

2. Run the manager:

```bash
claude-manager run --input TODO.md
```

## 📖 Command Reference

```
claude-manager run [OPTIONS]
```

### Common Options

| Option | Default | Description |
|--------|---------|-------------|
| `--cooldown`, `-c` | 0 | Cooldown period (seconds) between tasks |
| `--input`, `-i` | `TODO.md` | Path to your TODO list file |
| `--git-branch-prefix`, `-b` | `todo/` | Prefix for created Git branches |
| `--git-base-branch`, `-g` | `main` | Base Git branch to branch from |
| `--show-claude-output` | `False` | Show Claude's output in terminal |
| `--dry-run`, `-d` | `False` | Simulate without running Claude |
| `--worktree-parallel`, `-w` | `False` | Enable parallel task execution using Git worktree |

### Advanced Options

| Option | Default | Description |
|--------|---------|-------------|
| `--max-keep-asking` | 3 | Maximum number of continuation prompts |
| `--task-done-message` | `CLAUDE_MANAGER_DONE` | Completion token for tasks |
| `--hooks-config` | `.claude/settings.local.json` | Claude hooks config path |
| `--doctor`, `-D` | `False` | Validate your setup and configuration |
| `--lang`, `-L` | `en` | Language for CLI messages |

Run `claude-manager --help` for a complete list of options.

## 📋 TODO Format

Your TODO list should follow this GitHub-flavored Markdown format:

```markdown
- [x] Completed task [#1](https://github.com/user/repo/pull/1)
- [ ] Task to implement next
  - [ ] Subtask 1 (included in Claude's prompt)
  - [ ] Subtask 2 (included in Claude's prompt)
- [ ] Another pending task
```

## 🔧 Configuration

You can create a `.claude-manager.toml` file to configure default options:

```toml
[claude_manager]
git_base_branch = "develop"
max_keep_asking = 5
worktree_parallel = true
worktree_parallel_max_semaphore = 3
```

## 📚 Design & Implementation

See `IMPLEMENT_PROMPT.md` for the complete design plan.

## 🧪 Development

### Prerequisites

- Python 3.11+
- Git
- Claude Code CLI

### Testing

```bash
# Install test dependencies
uv pip install -e ".[test]"

# Run tests
pytest
```

### Linting

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run linter
ruff check
```

## 📄 License

MIT