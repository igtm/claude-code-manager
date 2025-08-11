<div align="center">

# Claude Code Manager

🤖 A powerful CLI to orchestrate Claude Code runs from a Markdown TODO list.

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/igtm/claude-code-manager/releases)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-≥3.11-blue)](https://www.python.org/downloads/)

</div>

## Overview

Claude Code Manager helps you manage and automate Claude Code runs by processing tasks from a markdown TODO list. Create structured task lists, and the manager will:

1. Automatically create feature branches for each task
2. Run Claude Code to implement the tasks
3. Commit changes and create pull requests
4. Update your TODO list with completion status and PR links

## Features

- 📋 **Markdown TODO Processing** - Parse GitHub-flavored markdown TODO lists
- 🔄 **Git Integration** - Automated branch creation, commits, and PR management
- 🤖 **Claude Code Automation** - Run Claude Code in headless mode with configurable prompts
- 🪝 **Hooks Management** - Configure Claude Code hooks for better task completion
- 🌲 **Git Worktree Support** - Parallel execution using Git worktrees
- 🌐 **i18n Support** - Configurable internationalization

## Installation

### Using uv (Recommended)

```bash
uv pip install -e .
```

### Using pip

```bash
pip install -e .
```

## Quick Start

1. Create a TODO.md file with tasks in GitHub-flavored markdown format:

```markdown
- [ ] Implement feature X
  - [ ] Subtask 1
  - [ ] Subtask 2
- [ ] Fix bug Y
```

2. Run the manager:

```bash
claude-manager run --input TODO.md
```

## Usage Examples

### Basic Usage

```bash
# Run with default settings
claude-manager run

# Run with a custom TODO file
claude-manager run --input my-tasks.md

# Run with a cooldown period between tasks
claude-manager run --cooldown 60
```

### Advanced Usage

```bash
# Run in parallel mode using Git worktrees
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 2

# Use custom Git branch prefix and base branch
claude-manager run --git-branch-prefix feature/ --git-base-branch develop

# See Claude Code output during execution
claude-manager run --show-claude-output

# Run in dry-run mode (simulates execution without actually running Claude Code)
claude-manager run --dry-run
```

### Configuration Validation

```bash
# Verify your configuration setup
claude-manager run --doctor
```

## Configuration

You can configure Claude Code Manager using command-line options or a TOML configuration file:

### Command-line Options

| Option | Short | Description | Default |
|--------|-------|-------------|--------|
| `--cooldown` | `-c` | Cooldown seconds between tasks | `0` |
| `--git-branch-prefix` | `-b` | Git branch name prefix | `todo/` |
| `--git-commit-message-prefix` | `-m` | Git commit message prefix | `feat: ` |
| `--git-base-branch` | `-g` | Git base branch | `main` |
| `--github-pr-title-prefix` | `-t` | GitHub PR title prefix | `feat: ` |
| `--github-pr-body-template` | `-p` | GitHub PR body template | `Implementing TODO item: {todo_item}` |
| `--config` | `-f` | Config file path | `.claude-manager.toml` |
| `--input` | `-i` | TODO list file path | `TODO.md` |
| `--claude-args` |  | Claude Code CLI arguments | `--dangerously-skip-permissions` |
| `--hooks-config` |  | Claude Code hooks config file | `.claude/settings.local.json` |
| `--max-keep-asking` |  | Max times to ask Claude to continue | `3` |
| `--task-done-message` |  | Task completion token | `CLAUDE_MANAGER_DONE` |
| `--show-claude-output` |  | Show Claude Code output | `false` |
| `--dry-run` | `-d` | Simulate execution | `false` |
| `--doctor` | `-D` | Validate configuration | `false` |
| `--worktree-parallel` | `-w` | Use Git worktrees for parallel execution | `false` |
| `--worktree-parallel-max-semaphore` |  | Max parallel tasks | `1` |
| `--lang` | `-L` | Language code | `en` |
| `--i18n-path` |  | i18n TOML file path | `.claude-manager.i18n.toml` |

### TOML Configuration

You can create a `.claude-manager.toml` file with the following format:

```toml
[claude_manager]
cooldown = 0
git_branch_prefix = "todo/"
git_base_branch = "main"
# ... other options
```

## TODO List Format

Claude Code Manager expects a GitHub-flavored markdown TODO list format:

```markdown
- [x] Completed task 1 [#1](https://github.com/user/repo/pull/1)
- [ ] Task to implement
  - [ ] Subtask 1 (included in prompt)
  - [ ] Subtask 2 (included in prompt)
- [ ] Next task (processed after previous task)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
