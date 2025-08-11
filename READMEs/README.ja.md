# Claude Code Manager

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)

マークダウンTODOリストからClaude Codeの実行を統合管理し、自動的にタスクの実行とプルリクエストの作成を可能にする強力なCLIツール。

</div>

## 🚀 機能

- **TODOリスト駆動開発**: GitHub形式のマークダウンからTODOリストを解析し、各項目を実行
- **自動化ワークフロー**: ブランチの作成、機能の実装、プルリクエストの提出を自動化
- **ワークツリー並列モード**: Gitワークツリーを使用して複数のTODO項目を同時に実行
- **フック連携**: Claude Codeのフックとシームレスに連携し、タスクの確実な完了を実現
- **国際化対応**: シンプルな設定で複数言語をサポート
- **カスタマイズ可能**: ブランチ名、コミットメッセージ、PRタイトルなどをカスタマイズ

## 📋 インストール方法

```bash
# uvを使用してインストール
uv pip install -e .

# または通常のpipを使用
pip install -e .
```

## 🚀 クイックスタート

1. マークダウンTODOリストファイルを作成します:

```markdown
- [x] 完了した項目 [#1](https://github.com/user/repo/pull/1)
- [ ] ダークモードサポートを追加
  - [ ] トグルコンポーネントを作成
  - [ ] テーマ切り替え機能を実装
- [ ] ユーザーリストのページネーションを修正
```

2. Claude Code Managerを実行します:

```bash
claude-manager run --input TODO.md
```

3. チェックされていない各トップレベル項目は順次（または`--worktree-parallel`で並列に）処理されます:
   - 新しいブランチが作成されます
   - Claude Codeが要求された機能を実装します
   - 変更がコミットされてプッシュされます
   - プルリクエストが作成されます
   - TODOリストがチェックボックスとPRリンクで更新されます

## ⚙️ 設定

コマンドラインオプションまたは設定ファイルを使用してClaude Code Managerを設定できます:

```bash
# 利用可能なオプションをすべて表示
claude-manager run --help

# カスタム設定ファイルを使用
claude-manager run --config my-config.toml

# Gitワークツリーを使用した並列実行を有効化
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3
```

### 設定ファイル

プロジェクトのルートに`.claude-manager.toml`ファイルを作成します:

```toml
[claude_manager]
git_branch_prefix = "feature/"
git_commit_message_prefix = "feat: "
git_base_branch = "main"
github_pr_title_prefix = "Feature: "
github_pr_body_template = "Implements: {todo_item}"
```

### 国際化

Claude Code Managerは`.claude-manager.i18n.toml`ファイルを通じて複数の言語をサポートしています:

```toml
[i18n.en]
processing = "Processing todo: {title}"
claude_not_found = "Claude CLI not found. Please install it first."

[i18n.ja]
processing = "Todoを処理中: {title}"
claude_not_found = "Claude CLIが見つかりません。先にインストールしてください。"
```

## 🧰 高度な使用方法

### Doctorコマンド

設定と環境を検証します:

```bash
claude-manager run --doctor
```

### カスタムプロンプトテンプレート

Claude Codeへのプロンプト方法をカスタマイズできます:

```bash
claude-manager run --headless-prompt-template "Implement this feature: {title}\n\nDetails:\n{children_bullets}\n\nWhen finished, output: {done_token}"
```

### Gitワークツリー並列モード

複数のTODO項目を同時に処理します:

```bash
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3
```

## 🤝 貢献

貢献を歓迎します！設計計画と実装の詳細については、[IMPLEMENT_PROMPT.md](../IMPLEMENT_PROMPT.md)をご覧ください。

## 📄 ライセンス

MIT