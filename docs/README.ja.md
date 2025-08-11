# Claude Code Manager

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)

マークダウン TODO リストから Claude Code の実行を調整する強力な CLI ツールで、タスクの自動実行とプルリクエストの作成を可能にします。

</div>

## 🚀 機能

- **Todo 駆動開発**: GitHub 形式のマークダウンから TODO リストを解析し、各項目を実行
- **自動化ワークフロー**: ブランチの作成、機能の実装、プルリクエストの自動提出
- **Worktree 並列モード**: Git ワークツリーを使用して複数の Todo 項目を同時に実行
- **フック連携**: Claude Code フックとシームレスに統合し、タスクの確実な完了を実現
- **国際化**: シンプルな設定で複数言語をサポート
- **設定可能**: ブランチ名、コミットメッセージ、PR タイトルなどのカスタマイズ

## 📋 インストール

```bash
# PyPI からインストール（推奨）
uv tool install claude-code-manager

# もしくは仮想環境内で
pip install -U claude-code-manager

# uvx で実行（グローバルインストール不要）
uvx --from claude-code-manager claude-manager --version
# または（提供元パッケージは自動解決されます）
uvx claude-manager run --input TODO.md

# 後からアップグレード
uv tool upgrade claude-code-manager
```

## 🚀 クイックスタート

1. マークダウン TODO.md リストファイルを作成:

```markdown
- [x] 完了した項目 [#1](https://github.com/user/repo/pull/1)
- [ ] ダークモードサポートの追加
  - [ ] トグルコンポーネントの作成
  - [ ] テーマ切り替えの実装
- [ ] ユーザーリストのページネーション修正
```

注意: TODO.md はリポジトリにコミットしないように .gitignore に追加してください:

```gitignore
# claude-manager 用のローカルチェックリスト
TODO.md
```

2. Claude Code Manager を実行:

```bash
claude-manager run -L ja
```

3. 未チェックのトップレベル項目が順番に（または `--worktree-parallel` で並列に）処理されます:
   - 新しいブランチが作成されます
   - Claude Code が要求された機能を実装します
   - 変更がコミットされ、プッシュされます
   - プルリクエストが作成されます
   - TODO リストがチェックボックスと PR リンクで更新されます

## ⚙️ 設定

コマンドラインオプションまたは設定ファイルを使用して Claude Code Manager を設定できます:

```bash
# 利用可能なすべてのオプションを表示
claude-manager run --help

# カスタム設定ファイルを使用
claude-manager run --config my-config.toml

# Gitワークツリーを使用した並列実行を有効化
claude-manager run -w -s 3
```

### 設定ファイル

プロジェクトルートに `.claude-manager.toml` ファイルを作成:

```toml
[claude_manager]
git_branch_prefix = "feature/"
git_commit_message_prefix = "feat: "
git_base_branch = "main"
github_pr_title_prefix = "Feature: "
github_pr_body_template = "Implements: {todo_item}"
```

### 国際化

Claude Code Manager は `.claude-manager.i18n.toml` ファイルを通じて複数言語をサポートします:

```toml
[i18n.en]
processing = "Processing todo: {title}"
claude_not_found = "Claude CLI not found. Please install it first."

[i18n.ja]
processing = "Todoを処理中: {title}"
claude_not_found = "Claude CLIが見つかりません。先にインストールしてください。"
```

## 🧰 高度な使用法

### Doctor コマンド

設定と環境を検証:

```bash
claude-manager run --doctor
```

### カスタムプロンプトテンプレート

Claude Code へのプロンプト方法をカスタマイズできます:

```bash
claude-manager run --headless-prompt-template "この機能を実装してください: {title}\n\n詳細:\n{children_bullets}\n\n完了したら出力: {done_token}"
```

### Git ワークツリー並列モード

複数の Todo 項目を同時に処理:

```bash
claude-manager run -w -s 3
```

## 🤝 貢献

貢献を歓迎します！

## 📄 ライセンス

MIT
