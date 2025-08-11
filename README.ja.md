# Claude Code Manager

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)

Markdown形式のTODOリストからClaude Codeの実行を自動化するCLIツールで、タスク実行とプルリクエスト作成を可能にします。

</div>

## 🚀 特徴

- **Todo駆動型開発**: GitHubフレーバーのマークダウンからTODOリストを解析し、各項目を実行
- **自動化されたワークフロー**: ブランチの作成、機能の実装、プルリクエストの自動提出
- **ワークツリー並列モード**: Gitワークツリーを使用して複数のTODO項目を同時に実行
- **フック連携**: タスク完了の信頼性向上のためClaude Codeフックとシームレスに統合
- **国際化**: シンプルな設定による複数言語対応
- **カスタマイズ可能**: ブランチ名、コミットメッセージ、PRタイトルなどのカスタマイズ

## 📋 インストール

```bash
# uvでインストール
uv pip install -e .

# または通常のpipでインストール
pip install -e .
```

## 🚀 クイックスタート

1. マークダウン形式のTODOリストファイルを作成:

```markdown
- [x] 完了した項目 [#1](https://github.com/user/repo/pull/1)
- [ ] ダークモードのサポートを追加
  - [ ] トグルコンポーネントの作成
  - [ ] テーマ切り替えの実装
- [ ] ユーザーリストのページネーションを修正
```

2. Claude Code Managerを実行:

```bash
claude-manager run --input TODO.md
```

3. チェックされていない各トップレベル項目は順番に処理されます（または`--worktree-parallel`で並列処理）:
   - 新しいブランチが作成されます
   - Claude Codeが要求された機能を実装します
   - 変更がコミットされてプッシュされます
   - プルリクエストが作成されます
   - TODOリストにチェックボックスとPRリンクが更新されます

## ⚙️ 設定

コマンドラインオプションまたは設定ファイルを使用してClaude Code Managerを設定できます:

```bash
# すべての利用可能なオプションを表示
claude-manager run --help

# カスタム設定ファイルの使用
claude-manager run --config my-config.toml

# Gitワークツリーを使用した並列実行を有効化
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3
```

### 設定ファイル

プロジェクトのルートに`.claude-manager.toml`ファイルを作成:

```toml
[claude_manager]
git_branch_prefix = "feature/"
git_commit_message_prefix = "feat: "
git_base_branch = "main"
github_pr_title_prefix = "Feature: "
github_pr_body_template = "Implements: {todo_item}"
```

### 国際化

Claude Code Managerは`.claude-manager.i18n.toml`ファイルを通じて複数の言語をサポートします:

```toml
[i18n.en]
processing = "Processing todo: {title}"
claude_not_found = "Claude CLI not found. Please install it first."

[i18n.ja]
processing = "Todoを処理中: {title}"
claude_not_found = "Claude CLIが見つかりません。先にインストールしてください。"
```

## 🧰 高度な使用法

### ドクターコマンド

設定と環境を検証:

```bash
claude-manager run --doctor
```

### カスタムプロンプトテンプレート

Claude Codeのプロンプト方法をカスタマイズできます:

```bash
claude-manager run --headless-prompt-template "この機能を実装してください: {title}\n\n詳細:\n{children_bullets}\n\n終了したら、次を出力: {done_token}"
```

### Gitワークツリー並列モード

複数のTODO項目を同時に処理:

```bash
claude-manager run --worktree-parallel --worktree-parallel-max-semaphore 3
```

## 🤝 貢献

貢献は歓迎します！設計計画と実装の詳細については[IMPLEMENT_PROMPT.md](IMPLEMENT_PROMPT.md)を参照してください。

## 📄 ライセンス

MIT