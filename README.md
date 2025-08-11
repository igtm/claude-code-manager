# claude-code-manager

<div align="center">

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/your-username/claude-code-manager)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)]()

**A CLI to orchestrate claude-code runs from a Markdown TODO list**

</div>

## Features

- 📋 **Automated Task Execution** - Process TODO items from a markdown checklist one by one
- 🌿 **Git Integration** - Automatically creates branches, commits changes, and opens PRs
- 🔄 **Claude Code Hooks** - Utilizes Claude Code hooks for reliable completions
- 🚀 **Parallel Execution** - Optional parallel processing using Git worktrees
- 🌐 **Internationalization** - Supports multiple languages
- ⚙️ **Configurable** - Extensive CLI options and config file support

## Installation

```bash
# Using uv (recommended)
uv pip install -e .

# Using pip
pip install -e .
```

## Quick Start

1. Create a TODO.md file with your tasks in GitHub-flavored markdown format:

```markdown
- [x] Completed task [#1](https://github.com/user/repo/pull/1)
- [ ] Add dark mode support
  - [ ] Create dark theme CSS
  - [ ] Add theme switcher
- [ ] Improve error handling
```

2. Run claude-code-manager:

```bash
claude-manager run --input TODO.md
```

3. The tool will:
   - Create a branch for the first unchecked task
   - Run Claude Code to implement the requested changes
   - Commit the changes, push to remote, and create a PR
   - Update the TODO.md file with a link to the PR
   - Proceed to the next task

## Configuration

### Command Line Options

```
Options:
  --cooldown, -c                     Seconds to wait between tasks [default: 0]
  --git-branch-prefix, -b            Branch name prefix [default: "todo/"]
  --git-commit-message-prefix, -m    Commit message prefix [default: "feat: "]
  --git-base-branch, -g              Base Git branch [default: "main"]
  --github-pr-title-prefix, -t       PR title prefix [default: "feat: "]
  --github-pr-body-template, -p      PR body template [default: "Implementing TODO item: {todo_item}"]
  --config, -f                       Config file path [default: ".claude-manager.toml"]
  --input, -i                        TODO list file path [default: "TODO.md"]
  --claude-args                      Additional claude-code arguments
  --hooks-config                     Hooks config file path [default: ".claude/settings.local.json"]
  --max-keep-asking                  Max retry count for completion check [default: 3]
  --task-done-message                Task completion message token [default: "CLAUDE_MANAGER_DONE"]
  --show-claude-output               Show claude-code output [default: false]
  --doctor, -D                       Validate configuration [default: false]
  --worktree-parallel, -w            Use git worktree for parallel execution [default: false]
  --worktree-parallel-max-semaphore  Max parallel executions [default: 1]
  --lang, -L                         Language code [default: "en"]
  --version, -v                      Show version and exit
  --help, -h                         Show this message and exit
```

### Configuration File

You can use a TOML configuration file (default: `.claude-manager.toml`):

```toml
[claude_manager]
cooldown = 5
git_base_branch = "develop"
max_keep_asking = 5
```

## How It Works

claude-code-manager uses Claude Code to implement TODO items from a markdown list:

1. Parses uncompleted tasks from your TODO.md file
2. Creates a new git branch for each task
3. Sets up Claude Code hooks to manage LLM completions
4. Runs Claude Code with a prompt containing the task details
5. Checks for the completion token ("CLAUDE_MANAGER_DONE")
6. Commits changes, pushes branch, and creates a Pull Request
7. Updates the TODO list with PR link and checked status
8. Continues with the next task

For detailed implementation, see [IMPLEMENT_PROMPT.md](IMPLEMENT_PROMPT.md).

## Requirements

- Python 3.11+
- Claude Code CLI
- Git
- GitHub CLI (for PR creation)

## Contributing

Contributions are welcome! See [IMPLEMENT_PROMPT.md](IMPLEMENT_PROMPT.md) for project structure and implementation details.

## License

[MIT License]()