# Claude Code Manager

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful CLI tool that orchestrates Claude Code runs from a Markdown TODO list, automatically creating branches, implementing features, and creating pull requests.

## Features

- 🤖 **Automated Implementation**: Processes TODO items one by one using Claude Code
- 🌲 **Git Integration**: Automatically creates branches, commits changes, and creates pull requests
- 📝 **Markdown Support**: Works with GitHub flavored markdown TODO lists
- 🔄 **Parallel Processing**: Support for parallel execution using Git worktree
- 🪝 **Hooks Management**: Configures and manages Claude Code hooks for seamless integration

## Installation

```bash
# Install using uv (recommended)
uv pip install -e .

# Or install using pip
pip install -e .
```

## Quick Start

1. Create a TODO.md file with your tasks:
```markdown
- [x] Completed task 1 [#1](https://github.com/user/repo/pull/1)
- [ ] Implement feature X
  - [ ] Add support for Y
  - [ ] Update tests
- [ ] Fix bug Z
```

2. Run the manager:
```bash
claude-manager run --input TODO.md
```

## Usage

```bash
# Basic usage
claude-manager run --input TODO.md

# Enable parallel processing with Git worktree
claude-manager run --input TODO.md --worktree-parallel

# Dry run (simulation mode)
claude-manager run --input TODO.md --dry-run

# Check configuration
claude-manager doctor
```

## Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--cooldown`, `-c` | Cooldown seconds between tasks | 0 |
| `--git-branch-prefix`, `-b` | Git branch name prefix | "todo/" |
| `--git-base-branch`, `-g` | Git base branch | "main" |
| `--input`, `-i` | Path to TODO list file | "TODO.md" |
| `--show-claude-output` | Show Claude Code output | false |
| `--worktree-parallel`, `-w` | Use Git worktree for parallel execution | false |
| `--worktree-parallel-max-semaphore` | Max parallel executions | 1 |
| `--help`, `-h` | Show help message | |
| `--version`, `-v` | Show version | |

For a full list of options, run `claude-manager --help`.

## Configuration

You can configure Claude Code Manager using a `.claude-manager.toml` file:

```toml
cooldown = 0
git-branch-prefix = "todo/"
git-base-branch = "main"
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-code-manager.git
cd claude-code-manager

# Install in development mode
uv pip install -e .
```

### Testing

```bash
# Run tests
pytest
```

## License

MIT

## Acknowledgements

This tool works with [Claude Code](https://www.anthropic.com/claude) by Anthropic.