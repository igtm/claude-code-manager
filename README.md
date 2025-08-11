# Claude Code Manager

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-brightgreen.svg)](https://github.com/your-username/claude-code-manager)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Orchestrate claude-code runs from Markdown TODO lists with ease**

</div>

Claude Code Manager automates running [claude-code](https://docs.anthropic.com/en/docs/claude-code) to implement tasks from a structured Markdown TODO list. It handles the entire workflow from branch management to PR creation, making Claude AI development workflows seamless.

## ✨ Features

- 🤖 **Automated Implementation** - Process Claude Code tasks from a Markdown TODO list
- 🌿 **Git Workflow Integration** - Automatically creates branches, commits changes, and generates PRs
- 🔁 **Batch Processing** - Works through TODO items one-by-one or in parallel
- 🔧 **Customizable** - Configure branch naming, commit messages, and more
- 🚀 **Parallel Execution** - Optional git worktree mode for parallel task processing
- 🌐 **Internationalization** - Supports multiple languages through i18n configuration

## 📋 Quick Start

### Installation

```bash
# Install with uv
uv pip install -e .

# Or with regular pip
pip install -e .
```

### Basic Usage

Create a Markdown TODO list file (`TODO.md`):

```markdown
- [ ] Implement feature X
  - [ ] Add validation
  - [ ] Write tests
- [ ] Fix bug Y
```

Run Claude Code Manager:

```bash
claude-manager run --input TODO.md
```

## 📖 How It Works

1. Claude Code Manager reads your Markdown TODO list file
2. For each unchecked top-level item:
   - Creates a new git branch
   - Runs claude-code with the TODO item as prompt
   - Commits changes when implementation is complete
   - Creates a pull request
   - Updates the TODO list marking the item as done with PR link
3. Moves to the next item

## ⚙️ Configuration

### Command-line Options

```
Options:
  --cooldown, -c                     Seconds to wait between TODO items [default: 0]
  --git-branch-prefix, -b            Branch name prefix [default: "todo/"]
  --git-commit-message-prefix, -m    Commit message prefix [default: "feat: "]
  --git-base-branch, -g              Git base branch [default: "main"]
  --github-pr-title-prefix, -t       PR title prefix [default: "feat: "]
  --github-pr-body-template, -p      PR body template [default: "Implementing TODO item: {todo_item}"]
  --config, -f                       Config file path [default: ".claude-manager.toml"]
  --input, -i                        TODO list file path [default: "TODO.md"]
  --claude-args                      Additional arguments for claude-code
  --hooks-config                     Claude Code hooks config path [default: ".claude/settings.local.json"]
  --max-keep-asking                  Maximum retries for completion check [default: 3]
  --task-done-message                Completion indicator message [default: "CLAUDE_MANAGER_DONE"]
  --show-claude-output               Display claude-code output [default: false]
  --dry-run, -d                      Simulate execution without running claude-code [default: false]
  --doctor, -D                       Validate configuration [default: false]
  --worktree-parallel, -w            Use git worktree for parallel execution [default: false]
  --worktree-parallel-max-semaphore  Maximum parallel executions [default: 1]
  --lang, -L                         Language for output messages [default: "en"]
  --i18n-path                        Path to i18n configuration [default: ".claude-manager.i18n.toml"]
  --no-color                         Disable colored output [default: false]
  --version, -v                      Show version and exit
  --help, -h                         Show help message and exit
```

### Configuration File

You can store your configuration in `.claude-manager.toml`:

```toml
[claude_manager]
cooldown = 0
git_branch_prefix = "todo/"
git_commit_message_prefix = "feat: "
git_base_branch = "main"
# Add any other configuration options here
```

## 🔍 Checking Setup

Verify your configuration:

```bash
claude-manager run --doctor
```

This checks:
- Claude CLI availability
- Git repository status
- TODO list file setup
- Hooks configuration

## 🔄 Advanced Usage

### Parallel Processing

Run multiple tasks concurrently using git worktrees:

```bash
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3
```

### Internationalization

Create a `.claude-manager.i18n.toml` file for custom messages:

```toml
[i18n.en]
processing = "Processing: {title}"
claude_not_found = "Claude CLI not found. Please install it."

[i18n.ja]
processing = "処理中: {title}"
claude_not_found = "Claude CLIが見つかりません。インストールしてください。"
```

## 🧩 TODO List Format

```markdown
- [x] Completed task [#1](https://github.com/user/repo/pull/1)
- [ ] Task to implement
  - [ ] Subtask 1 (included in prompt)
  - [ ] Subtask 2 (included in prompt)
- [ ] Next task (processed after previous task)
```

## 📦 Project Structure

For details about the implementation, check out:
- `IMPLEMENT_PROMPT.md` - Design plan for the project

## 📄 License

MIT License

## 👥 Contributing

Contributions are welcome!