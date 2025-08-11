# claude-code-manager

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/igtm/claude-code-manager)](https://github.com/igtm/claude-code-manager/blob/main/LICENSE)

A CLI tool to orchestrate [claude-code](https://docs.anthropic.com/en/docs/claude-code) runs from a Markdown TODO list.

<p align="center">
  <img src="https://user-images.githubusercontent.com/6332/269356055-ff23a009-a096-4921-87e5-d20b673731bd.png" width="600">
</p>

## ✨ Features

- 📋 Parse GitHub-flavored Markdown TODO lists to orchestrate tasks
- 🌳 Automatically create Git branches, commits, and PRs for each task
- 🔄 Sequential or parallel execution with Git worktree support
- 🌍 Internationalization support
- 🛠️ Customizable hooks for claude-code integration
- 🔍 Diagnostic mode for setup validation

## 📦 Installation

### With uv (recommended)

```bash
uv pip install -e .
```

### With pip

```bash
pip install -e .
```

## 🚀 Quick Start

1. Create a TODO.md file with tasks in GitHub-flavored Markdown format:

```markdown
- [ ] Implement feature X
  - [ ] Add UI component
  - [ ] Write tests
- [ ] Fix bug Y
- [ ] Update documentation
```

2. Run claude-code-manager:

```bash
claude-manager run --input TODO.md
```

## 📋 Command Line Options

```bash
# Basic usage
claude-manager run --input TODO.md

# Show help
claude-manager --help

# Run diagnostic checks
claude-manager run --doctor

# Run in parallel with Git worktree
claude-manager run --worktree-parallel
```

### Core Options

| Option | Description | Default |
| ------ | ----------- | ------- |
| `--input`, `-i` | TODO list file path | `TODO.md` |
| `--git-base-branch`, `-g` | Git base branch | `main` |
| `--git-branch-prefix`, `-b` | Branch name prefix | `todo/` |
| `--claude-args` | Arguments to pass to claude-code | `--dangerously-skip-permissions` |
| `--worktree-parallel`, `-w` | Use Git worktree for parallel execution | `false` |
| `--show-claude-output` | Show claude-code output | `false` |
| `--doctor`, `-D` | Run diagnostic checks | `false` |

## ⚙️ Configuration

You can configure claude-code-manager using a `.claude-manager.toml` file:

```toml
[claude_manager]
git_base_branch = "develop"
git_branch_prefix = "feature/"
max_keep_asking = 5
```

## 📚 How It Works

1. Parse unchecked TODO items from a Markdown list
2. For each TODO item:
   - Create a new Git branch
   - Run claude-code with a tailored prompt
   - Verify implementation is complete
   - Create a commit and PR
   - Mark the TODO item as complete
3. Return to the base branch when done

## 🤝 Contributing

Contributions are welcome! See the design plan in `IMPLEMENT_PROMPT.md` for details on the project structure.

## 📄 License

MIT
