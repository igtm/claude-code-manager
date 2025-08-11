# このリポジトリで実装するライブラリの内容
claude-code の実行を制御するpython製のcliライブラリ claude-code-manager を作りたい。
ユーザーの要望TODOリスト(github flavored markdown)から、１つずつブランチ切って、
要望を実装できたことを確認できたらpushしてPullRequestを作成する。終わったら、次のTODOを実行する。

## 実装上の注意点
- claude-code の hooks機能を利用した実装を行う。claude-code-managerで内部的に使うhooksは.claude/settings.local.jsonに設定を記述する。コメントなどでこのライブラリが自動追加したものかどうかを判断できるようにしておき重複設定しないように管理する。
- 様々な理由で、claude-code hooks の Stop 時に、「続けて。実装が終了し終わっていたら、CLAUDE_MANAGER_DONEと返して。」と聞き返すようにする。設定で回数を制限できるようにする。CLAUDE_MANAGER_DONE が返ってきたら、終了と判断し終了処理を行う。
- TODOごとに、claude-codeを実行しなおす。
- claude-code のプロセスの標準出力とこのライブラリの標準出力を分ける。デフォルトでは claude-code の標準出力は表示しない。オプションで見れるようにする。
- uv で実装すること。pip install -e . でインストールできるようにする。pyproject.toml [build-system]セクションを設定すること。
- pytest でテストを行うこと。特に、hooksの設定が重複しないことを確認するテストを行うこと。各種処理はなるべく小さな関数にしUnitテストを行うこと。claude-code はモック化し、実装すること
- このリポジトリ内で開発中に実行検証ができるように かんたんに実行できるエントリポイントも用意して。
- git worktreeを使い、ブランチを切るモードも用意する。このモードの場合は並列実行し、semaphoreの最大実行数をオプションで設定できる。(default: 1)

## 実行の流れ
1. 各種 hooks の設定を行う(すでにある場合はスキップ)
2. ユーザーの要望TODOリストから一番親のリストを1つずつ要望を取得(Github flavored markdown. チェックがついているものは除外)
    - 読み取れる書式になっているか検証。
    - 親リストの子要素はすべてプロンプトに含めるだけ。
    - TODOリストのフォーマットは、以下のようにする。
```markdown
- [x] 完了した要望1 [#1](https://github.com/user/repo/pull/1)
- [x] 完了した要望2 [#2](https://github.com/user/repo/pull/2)
- [ ] 要望1(ここから実行する)
  - [ ] 要望1のサブ要望1(ここはプロンプトに渡すだけ)
  - [ ] 要望1のサブ要望2(ここはプロンプトに渡すだけ)
- [ ] 要望2(要望1が終わったらこれを実行する)
```

3. ブランチを切る
4. claude-codeを実行し、要望を実装
5. 実装が完了したか確認する
6. 実装が完了していれば、コミット、pushしPullRequestを作成する。(TODOリストにチェック付けて、github pr のリンクを末尾に追加)
7. 次のTODOがあれば、2に戻る

## コマンド
```
コマンド名: claude-manager

オプション:
  --cooldown, -c: 次のTODOを実行するまでのクールタイムの秒数 (default: 0)
  --git-branch-prefix, -b: ブランチ名の接頭辞 (default: "todo/")
  --git-commit-message-prefix, -m: コミットメッセージの接頭辞 (default: "feat: ")
  --git-base-branch, -g: Gitのベースブランチ (default: "main")
  --github-pr-title-prefix, -t: PullRequestのタイトルの接頭辞 (default: "feat: ")
  --github-pr-body-template, -p: PullRequestの本文のテンプレート (default: "Implementing TODO item: {todo_item}")
  --h, --help: ヘルプメッセージの表示
  --version, -v: バージョン情報の表示
  --config, -f: 設定ファイルのパス (default: ".claude-manager.toml")
  --input, -i: ユーザーの要望TODOリストのファイルパス (default: "TODO.md")
  --claude-args: claude-codeの引数 (default: "")
  --hooks-config: claude-codeのhooks設定ファイルパス (default: ".claude/settings.local.json")
  --max-keep-asking: hooksの「続けて」確認の最大回数 (default: 3)
  --task-done-message: 実装完了時のメッセージ (default: "CLAUDE_MANAGER_DONE")
  --show-claude-output: claude-codeの標準出力を表示するかどうか (default: false)
  --dry-run, -d: 実際の操作を行わずにシミュレーションする. claude-code の実行以外はやる. (default: false)
  --doctor, -D: 設定の検証を行う (default: false)
  --worktree-parallel, -w: git worktreeを使用し並列実行するモード (default: false)
  --worktree-parallel-max-semaphore: 並列実行時の最大セマフォ数 (default: 1)
```

## 参照
- https://docs.astral.sh/uv/guides/package/#building-your-package
- https://docs.anthropic.com/ja/docs/claude-code/hooks#stop%E3%81%A8subagentstop%E5%85%A5%E5%8A%9B
