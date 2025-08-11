<div align="center">

# Claude Code Manager

[![GitHub license](https://img.shields.io/github/license/igtm/claude-code-manager)](https://github.com/igtm/claude-code-manager/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-black)](https://github.com/astral-sh/ruff)

**Automate Claude Code tasks from a structured Markdown TODO list**

🤖 Automated branch creation | 🔄 Sequential task execution | 📋 Todo tracking | 🔀 Pull request generation

</div>

## Overview

Claude Code Manager is a CLI tool that automates the execution of Claude Code tasks based on a Markdown TODO list. It handles the entire workflow from branch creation to pull request generation, making it easy to systematically implement features or fixes using Claude.

### Key Features

- 📋 **Todo-driven development**: Organizes work from a structured Markdown checklist
- 🌿 **Git workflow automation**: Creates branches, commits changes, and generates PRs
- 🤖 **Claude Code integration**: Uses hooks to manage Claude Code execution
- ⚙️ **Customizable options**: Configure branch names, commit messages, and more
- 🔄 **Sequential or parallel execution**: Process tasks one-by-one or in parallel with worktree support

## Installation

```bash
# Using uv (recommended)
uv pip install -e .

# Using pip
pip install -e .
```

## Quick Start

1. Create a Markdown TODO list (`TODO.md`):

```markdown
- [ ] Implement dark mode
  - [ ] Add theme toggle component
  - [ ] Create dark CSS variables
- [ ] Add user settings page
```

2. Run Claude Code Manager:

```bash
claude-manager run
```

Claude Code Manager will:
1. Process each unchecked top-level item sequentially
2. Create a git branch for each task
3. Execute Claude Code with a task-specific prompt
4. Commit changes and create a pull request when completed
5. Update the TODO list with completion status and PR link

## Usage

```bash
claude-manager run [OPTIONS]
```

### Common Options

| Option | Description | Default |
|--------|-------------|--------|
| `--cooldown, -c` | Seconds between tasks | `0` |
| `--input, -i` | Path to TODO file | `TODO.md` |
| `--git-base-branch, -g` | Base branch for new branches | `main` |
| `--show-claude-output` | Show Claude Code output | `false` |
| `--dry-run, -d` | Simulate without Claude execution | `false` |
| `--doctor, -D` | Validate configuration | `false` |
| `--worktree-parallel, -w` | Use parallel execution with git worktrees | `false` |

For a complete list of options:

```bash
claude-manager run --help
```

## Configuration

Claude Code Manager can be configured through command-line options or a configuration file.

### Configuration File

Create a `.claude-manager.toml` file:

```toml
[claude_manager]
# General settings
cooldown = 0
input_path = "TODO.md"
show_claude_output = false

# Git settings
git_branch_prefix = "todo/"
git_commit_message_prefix = "feat: "
git_base_branch = "main"

# GitHub settings
github_pr_title_prefix = "feat: "
github_pr_body_template = "Implementing TODO item: {todo_item}"

# Advanced settings
hooks_config = ".claude/settings.local.json"
max_keep_asking = 3
task_done_message = "CLAUDE_MANAGER_DONE"
```

## TODO Format

Claude Code Manager uses GitHub Flavored Markdown checklists:

```markdown
- [x] Completed task [#1](https://github.com/user/repo/pull/1)
- [ ] Current task
  - [ ] Subtask 1 (included in prompt)
  - [ ] Subtask 2 (included in prompt)
- [ ] Future task
```

## Advanced Usage

### Parallel Execution

Process multiple tasks simultaneously using git worktrees:

```bash
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3
```

### Validation

Verify your configuration:

```bash
claude-manager run --doctor
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms of the license included in the repository.
