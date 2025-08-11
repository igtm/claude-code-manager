# claude-code-manager

<div align="center">

🤖 A CLI to orchestrate claude-code runs from a Markdown TODO list

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)

</div>

## ✨ Features

- **Automated Task Execution**: Processes todo items from your Markdown checklist one by one
- **Git Integration**: Creates branches, commits changes, and opens pull requests automatically
- **Claude Code Control**: Manages claude-code execution with customizable hooks
- **Parallel Processing**: Supports parallel task execution with git worktrees
- **Extensible**: Highly configurable with command-line options and config files
- **i18n Support**: Localization support for messages

## 📋 Prerequisites

- Python 3.11+
- Git installed and configured
- [claude-code](https://docs.anthropic.com/en/docs/claude-code) installed
- GitHub CLI (for PR creation)

## 🚀 Installation

Install using `uv`:

```bash
uv pip install -e .
```

## 🏁 Quick Start

1. Create a `TODO.md` file with your tasks in GitHub Flavored Markdown format:

```markdown
- [ ] Implement user authentication
  - [ ] Create login form
  - [ ] Set up JWT token system
- [ ] Add unit tests for API endpoints
```

2. Run claude-manager:

```bash
claude-manager run --input TODO.md
```

The tool will:
- Process each top-level unchecked item one by one
- Create a git branch for each task
- Use claude-code to implement the changes
- Commit, push, and create a PR for each task
- Update the TODO.md with PR links and completion status

## ⚙️ Configuration

### Command-line Options

```
Options:
  --cooldown, -c                     Cooldown between TODO items (seconds) [default: 0]
  --git-branch-prefix, -b            Branch name prefix [default: "todo/"]
  --git-commit-message-prefix, -m    Commit message prefix [default: "feat: "]
  --git-base-branch, -g              Git base branch [default: "main"]
  --github-pr-title-prefix, -t       PR title prefix [default: "feat: "]
  --github-pr-body-template, -p      PR body template [default: "Implementing TODO item: {todo_item}"]
  --config, -f                       Config file path [default: ".claude-manager.toml"]
  --input, -i                        TODO list file path [default: "TODO.md"]
  --claude-args                      Additional claude-code arguments [default: "--dangerously-skip-permissions"]
  --hooks-config                     Hooks config file path [default: ".claude/settings.local.json"]
  --max-keep-asking                  Max times to ask Claude to continue [default: 3]
  --task-done-message                Completion message token [default: "CLAUDE_MANAGER_DONE"]
  --show-claude-output               Show claude-code output [default: False]
  --dry-run, -d                      Simulate execution without claude-code [default: False]
  --doctor, -D                       Validate configuration [default: False]
  --worktree-parallel, -w            Enable parallel execution [default: False]
  --worktree-parallel-max-semaphore  Max parallel tasks [default: 1]
  --lang, -L                         Language for messages [default: "en"]
  --i18n-path                        i18n file path [default: ".claude-manager.i18n.toml"]
  --no-color                         Disable colored output [default: False]
  -h, --help                         Show help message
  -v, --version                      Show version and exit
```

### Config File

You can create a `.claude-manager.toml` file for persistent configuration:

```toml
[claude_manager]
cooldown = 5
git_branch_prefix = "feature/"
git_base_branch = "develop"
```

## 📝 TODO Format

The tool expects a GitHub Flavored Markdown checklist:

```markdown
- [x] Completed task [#1](https://github.com/user/repo/pull/1)
- [ ] Task to implement next
  - [ ] Subtask (included in the prompt)
  - [ ] Another subtask
- [ ] Another task (processed after the previous one)
```

## 🔍 Hooks System

claude-code-manager configures hooks in `.claude/settings.local.json` to interact with claude-code. The system:

1. Sets up a "keep asking" hook that prompts Claude to continue until it outputs the completion token
2. Manages hook configurations to avoid duplicates
3. Supports customization of the completion message token

## 🛠️ Development

To contribute to the project:

1. Clone the repository
2. Install development dependencies: `uv pip install -e ".[dev,test]"`
3. Run tests: `pytest`

## 📚 Related Resources

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [UV Package Building Guide](https://docs.astral.sh/uv/guides/package/#building-your-package)
- [Claude Code Hooks Documentation](https://docs.anthropic.com/ja/docs/claude-code/hooks#stop%E3%81%A8subagentstop%E5%85%A5%E5%8A%9B)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎓 Implementation Details

For more information about the implementation plan and design, see [IMPLEMENT_PROMPT.md](IMPLEMENT_PROMPT.md).