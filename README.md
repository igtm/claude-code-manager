# claude-code-manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful CLI tool that orchestrates `claude-code` runs from a Markdown TODO list, automating the implementation of tasks through Git branches and pull requests.

<div align="center">

![Claude Code Manager](https://raw.githubusercontent.com/anthropics/claude/main/claude-logo.png)

</div>

## 🌟 Features

- 📋 Automatically processes TODO items from a Markdown checklist
- 🔄 Creates Git branches for each task and manages the workflow
- 🤖 Leverages Claude Code to implement requested features
- 🚀 Creates pull requests when implementations are complete
- 🔁 Supports parallel execution via Git worktrees
- 🌐 Internationalization support
- 📊 Live progress reporting

## 📦 Installation

```bash
# Install with uv
uv pip install -e .

# Or with pip
pip install -e .
```

## 🚀 Quick Start

1. Create a `TODO.md` file with your tasks in GitHub Flavored Markdown format:

```markdown
- [ ] Add dark mode to the UI
  - [ ] Create a theme toggle component
  - [ ] Add theme persistence
- [ ] Implement user authentication
  - [ ] Set up login/register forms
  - [ ] Add JWT validation
```

2. Run the manager:

```bash
claude-manager run --input TODO.md
```

3. Claude Code Manager will:
   - Process each item one by one (or in parallel with worktree mode)
   - Create Git branches for each task
   - Use Claude to implement the requested features
   - Create pull requests when implementations are complete
   - Update your TODO.md with completed items and PR links

## 📝 TODO Format

The TODO.md file should follow this format:

```markdown
- [x] Completed task 1 [#1](https://github.com/user/repo/pull/1)
- [x] Completed task 2 [#2](https://github.com/user/repo/pull/2)
- [ ] Task to implement next
  - [ ] Subtask 1 (included in the prompt)
  - [ ] Subtask 2 (included in the prompt)
- [ ] Another task to implement later
```

## ⚙️ Configuration

Create a `.claude-manager.toml` file for custom configuration:

```toml
[claude_manager]
cooldown = 5
git_branch_prefix = "feature/"
git_base_branch = "main"
show_claude_output = true
```

## 🛠️ Command Line Options

```
Usage: claude-manager [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --version                   Show version and exit
  -h, --help                      Show this message and exit

Commands:
  run                             Run the manager on a TODO list

Run Options:
  -c, --cooldown INT              Seconds to wait between tasks
  -b, --git-branch-prefix TEXT    Branch name prefix
  -g, --git-base-branch TEXT      Git base branch
  -i, --input TEXT                Path to TODO.md file
  -w, --worktree-parallel         Use Git worktrees for parallel execution
  --show-claude-output            Display Claude's output
  -D, --doctor                    Validate configuration
```

## 🌐 Internationalization

The tool supports internationalization through a TOML configuration file:

```bash
claude-manager run --lang ja --i18n-path .claude-manager.i18n.toml
```

## 🔍 Development

Requirements:
- Python 3.11+
- Claude Code CLI
- Git

To run tests:

```bash
pytest
```

## 📄 License

MIT
