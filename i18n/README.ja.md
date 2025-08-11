# Claude Code Manager

<div align="right">
  <a href="../README.md">English</a> | <a href="README.ja.md">日本語</a>
</div>

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)

マークダウンTODOリストからClaudeコードの実行を調整するパワフルなCLIツール。タスクの自動実行とプルリクエストの作成を実現します。

</div>

## 🚀 機能

- **TODOドリブン開発**: GitHubフレーバーのマークダウンからTODOリストを解析し、各項目を実行
- **自動化ワークフロー**: ブランチ作成、機能実装、プルリクエストの自動提出
- **Worktree並行モード**: Gitワークツリーを使用して複数のTODO項目を同時に実行
- **フック連携**: 確実なタスク完了のためのClaudeコードフックとの連携
- **国際化**: シンプルな設定による複数言語サポート
- **設定可能**: ブランチ名、コミットメッセージ、PRタイトルなどのカスタマイズ

## 📋 インストール

```bash
# uvでインストール
uv pip install -e .

# 通常のpipでインストール
pip install -e .
```

## 🚀 クイックスタート

1. マークダウンTODOリストファイルを作成:

```markdown
- [x] 完了した項目 [#1](https://github.com/user/repo/pull/1)
- [ ] ダークモードサポートの追加
  - [ ] トグルコンポーネントの作成
  - [ ] テーマ切り替えの実装
- [ ] ユーザーリストのページネーション修正
```

2. Claude Code Managerを実行:

```bash
claude-manager run --input TODO.md
```

3. 未チェックの最上位項目が順次（または`--worktree-parallel`で並行して）処理されます:
   - 新しいブランチが作成されます
   - Claude Codeが要求された機能を実装します
   - 変更がコミットされプッシュされます
   - プルリクエストが作成されます
   - TODOリストがチェックボックスとPRリンクで更新されます

## ⚙️ 設定

Claude Code Managerはコマンドラインオプションまたは設定ファイルで設定できます:

```bash
# 利用可能なオプションをすべて表示
claude-manager run --help

# カスタム設定ファイルを使用
claude-manager run --config my-config.toml

# Gitワークツリーを使用した並行実行を有効化
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3
```

### 設定ファイル

プロジェクトルートに`.claude-manager.toml`ファイルを作成:

```toml
[claude_manager]
git_branch_prefix = "feature/"
git_commit_message_prefix = "feat: "
git_base_branch = "main"
github_pr_title_prefix = "Feature: "
github_pr_body_template = "Implements: {todo_item}"
```

### 国際化

Claude Code Managerは`.claude-manager.i18n.toml`ファイルを通じて複数言語をサポートします:

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

設定と環境を検証:

```bash
claude-manager run --doctor
```

### カスタムプロンプトテンプレート

Claudeコードの指示方法をカスタマイズ:

```bash
claude-manager run --headless-prompt-template "この機能を実装してください: {title}\n\n詳細:\n{children_bullets}\n\n完了したら出力: {done_token}"
```

### Gitワークツリー並行モード

複数のTODO項目を同時に処理:

```bash
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3
```

## 🤝 貢献

貢献は歓迎します！設計計画と実装の詳細は[IMPLEMENT_PROMPT.md](IMPLEMENT_PROMPT.md)を参照してください。

## 📄 ライセンス

MIT