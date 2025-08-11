# Claude Code Manager

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/badge/pypi-0.1.0-blue)](https://pypi.org/project/claude-code-manager/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**A powerful CLI to orchestrate Claude Code runs from a Markdown TODO list.**

</div>

## ✨ Features

- 🚀 **Automated Task Execution** - Process TODO items one by one with Claude Code
- 🌱 **Git Branch Management** - Automatically create branches for each task
- 🔀 **Parallel Processing** - Run multiple tasks simultaneously with Git worktree
- 🔄 **Full GitHub Integration** - Create PRs and update TODO list with links
- 🌐 **Internationalization Support** - Configurable language settings
- ⚙️ **Highly Configurable** - Customize everything via CLI flags or config file

## 📋 Overview

Claude Code Manager streamlines AI-assisted development by turning a Markdown TODO list into a series of automated coding tasks. Each task is:

1. Processed by Claude Code in its own Git branch
2. Committed and pushed when completed
3. Submitted as a Pull Request
4. Marked as complete in your TODO list with a link to the PR

Perfect for managing multi-step implementation projects with Claude Code.

## 🚀 Installation

```bash
# Install with pip
pip install claude-code-manager

# Install with uv (recommended)
uv pip install claude-code-manager

# Install from source (development)
git clone https://github.com/yourusername/claude-code-manager.git
cd claude-code-manager
uv pip install -e .
```

## 🏁 Quick Start

1. Create a TODO.md file with your tasks in GitHub-flavored Markdown checklist format:

```markdown
- [ ] Add dark mode support
  - [ ] Create theme toggle component
  - [ ] Implement CSS variables for theming
- [ ] Implement user profile page
  - [ ] Create profile view component
  - [ ] Add avatar upload feature
```

2. Run Claude Code Manager:

```bash
claude-manager run --input TODO.md
```

The tool will process each task one by one, creating branches, PRs, and updating your TODO list.

## 🛠️ Configuration

### Command Line Options

```
claude-manager run [OPTIONS]

Options:
  --cooldown, -c                      Seconds to wait between tasks [default: 0]
  --git-branch-prefix, -b TEXT        Branch name prefix [default: todo/]
  --git-commit-message-prefix, -m TEXT
                                      Commit message prefix [default: feat: ]
  --git-base-branch, -g TEXT          Git base branch [default: main]
  --github-pr-title-prefix, -t TEXT   PR title prefix [default: feat: ]
  --github-pr-body-template, -p TEXT  PR body template [default: Implementing TODO item: {todo_item}]
  --config, -f TEXT                   Config file path [default: .claude-manager.toml]
  --input, -i TEXT                    TODO list path [default: TODO.md]
  --claude-args TEXT                  Claude Code CLI args [default: --dangerously-skip-permissions]
  --hooks-config TEXT                 Hooks config path [default: .claude/settings.local.json]
  --max-keep-asking INTEGER           Max times to keep asking [default: 3]
  --task-done-message TEXT            Completion token [default: CLAUDE_MANAGER_DONE]
  --show-claude-output                Show Claude's output [default: False]
  --doctor, -D                        Validate configuration [default: False]
  --worktree-parallel, -w             Run tasks in parallel [default: False]
  --worktree-parallel-max-semaphore INTEGER
                                      Max parallel tasks [default: 1]
  --lang, -L TEXT                     Language code [default: en]
  --i18n-path TEXT                    i18n TOML file path [default: .claude-manager.i18n.toml]
  --no-color                          Disable colored output [default: False]
  --debug                             Enable debug logs [default: False]
  --version, -v                       Show version and exit
  --help, -h                          Show this message and exit
```

### Configuration File

Create a `.claude-manager.toml` file in your project root to store configuration:

```toml
[claude_manager]
cooldown = 5
git_branch_prefix = "feature/"
git_base_branch = "develop"
max_keep_asking = 5
worktree_parallel = true
worktree_parallel_max_semaphore = 4
```

### Internationalization

Create a `.claude-manager.i18n.toml` file to customize messages:

```toml
[i18n.en]
processing = "Processing task: {title}"
doctor_ok = "All checks passed successfully!"

[i18n.ja]
processing = "タスクを処理中: {title}"
doctor_ok = "すべてのチェックに合格しました！"
```

## 📖 Advanced Usage

### Parallel Execution with Git Worktree

Process multiple TODO items simultaneously:

```bash
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 4
```

### Configuration Validation

Ensure your environment is properly set up:

```bash
claude-manager run --doctor
```

### Custom Hooks

The tool automatically configures Claude Code hooks for task completion detection:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/stop-keep-asking.py"
          }
        ]
      }
    ]
  }
}
```

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.