# Claude Code Manager

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A CLI tool that orchestrates Claude Code runs from a Markdown TODO list. Automatically manages GitHub branches, runs Claude Code to implement each TODO item, and creates pull requests when implementations are complete.

## Features

- 🔄 Processes TODO items sequentially from a Markdown file
- 🌿 Creates Git branches for each TODO implementation
- 🤖 Runs Claude Code to implement features automatically
- 🔍 Verifies implementation completion
- 🔀 Creates pull requests with customizable titles and descriptions
- ⚙️ Uses Claude Code hooks for enhanced control
- 🚀 Supports parallel execution with Git worktree

## Installation

```bash
# Using uv (recommended)
uv pip install -e .

# Using pip
pip install -e .
```

## Quick Start

1. Create a TODO.md file with your implementation requests:

```markdown
- [x] Completed request 1 [#1](https://github.com/user/repo/pull/1)
- [ ] Add user authentication
  - [ ] Implement login endpoint
  - [ ] Add JWT token verification
- [ ] Implement search functionality
```

2. Run the Claude Code Manager:

```bash
claude-manager run --input TODO.md
```

3. The tool will:
   - Create a new branch for the first unchecked TODO item
   - Run Claude Code to implement the feature
   - Commit changes and create a pull request when complete
   - Update the TODO.md file with a link to the PR
   - Continue with the next TODO item

## Command Line Options

```
claude-manager run [OPTIONS]

Options:
  --cooldown, -c                  Seconds to wait between TODO items (default: 0)
  --git-branch-prefix, -b         Prefix for branch names (default: "todo/")
  --git-commit-message-prefix, -m Prefix for commit messages (default: "feat: ")
  --git-base-branch, -g           Base branch for PRs (default: "main")
  --github-pr-title-prefix, -t    Prefix for PR titles (default: "feat: ")
  --config, -f                    Config file path (default: ".claude-manager.toml")
  --input, -i                     TODO list file path (default: "TODO.md")
  --claude-args                   Arguments to pass to Claude Code
  --hooks-config                  Claude Code hooks config path (default: ".claude/settings.local.json")
  --max-keep-asking               Max times to ask Claude to continue (default: 3)
  --show-claude-output            Show Claude Code stdout (default: false)
  --dry-run, -d                   Simulate operations without executing Claude Code (default: false)
  --doctor, -D                    Validate configuration (default: false)
  --worktree-parallel, -w         Use Git worktree for parallel execution (default: false)
  --worktree-parallel-max         Max parallel processes (default: 1)
  --help, -h                      Show help information
  --version, -v                   Show version information
```

## How It Works

1. The tool reads your TODO.md file and processes each unchecked top-level item
2. For each item:
   - Creates a Git branch named with the item's content
   - Runs Claude Code with the item and its sub-items as the prompt
   - Uses Claude Code hooks to detect when implementation is complete
   - Commits changes, pushes to remote, and creates a pull request
   - Updates the TODO.md with a checkbox and PR link
3. Proceeds to the next TODO item until all are processed

## Configuration

You can configure Claude Code Manager using:

1. Command line arguments
2. A `.claude-manager.toml` configuration file
3. Environment variables

## Development

For development and testing:

```bash
# Install development dependencies
uv pip install -e ".[dev,test]"

# Run tests
pytest

# Run linting
ruff check .
```

## License

MIT

---

See [IMPLEMENT_PROMPT.md](IMPLEMENT_PROMPT.md) for the complete design plan.