# Task Butler

日本語 | [English](README.md)

タスク管理を支援するデジタル執事。タスクの管理、優先順位付け、整理を支援するCLIツールです。

## 特徴

- **シンプルなCLI**: 直感的なコマンドでタスクを管理
- **Markdownストレージ**: YAMLフロントマター付きの人間可読なMarkdownファイルとして保存
- **階層構造タスク**: 親子関係でタスクを構造化
- **依存関係**: タスク間の依存関係を定義し、ブロッキングを追跡
- **繰り返しタスク**: 日次、週次、月次、年次の繰り返しタスクを設定
- **AI機能**: ローカルLLMによるタスク分析、スマート提案、日次計画
- **Obsidian連携**: Obsidian Tasksプラグイン互換フォーマットでのエクスポート/インポート
- **リッチな出力**: カラーとフォーマットによる美しいターミナル出力
- **Git対応**: 全てのデータはプレーンテキストで保存、バージョン管理が容易

## インストール

### PyPIから（推奨）

```bash
pip install markdown-task-butler
# または
uv tool install markdown-task-butler
```

`task-butler`と`tb`コマンドがグローバルにインストールされます。

### GitHubから

```bash
uv tool install git+https://github.com/dobachi/task-butler.git
```

### アップグレード

```bash
pip install --upgrade markdown-task-butler
# または
uv tool upgrade markdown-task-butler
```

### uvxで試す

```bash
uvx markdown-task-butler
```

注: `uvx`は一時的な環境で実行されます。シェル補完は利用できません。

### ソースから

```bash
git clone https://github.com/dobachi/task-butler.git
cd task-butler
uv sync
uv run task-butler
```

## クイックスタート

### 1. 初期設定

対話式ウィザードで設定（推奨）：

```bash
task-butler config init
```

これにより以下を設定できます：
- ストレージ形式（frontmatter / hybrid）
- タスク保存ディレクトリ（デフォルト: `~/.task-butler/tasks/`）
- Obsidian Vault パス（オプション）
- 整理方法（flat / kanban）

または、環境変数で直接指定：

```bash
# 設定全体の場所を変更（デフォルト: ~/.task-butler/）
export TASK_BUTLER_HOME=~/my-task-butler

# タスク保存場所のみ変更
export TASK_BUTLER_DIR=~/my-tasks
```

### 2. 基本操作

```bash
# タスクを追加
task-butler add "ドキュメントを書く"

# 高優先度のタスクを期限付きで追加
task-butler add "重大なバグを修正" --priority urgent --due 2025-01-30

# 全タスクを一覧表示
task-butler list

# タスクの作業を開始（ショートID - 先頭8文字を使用）
task-butler start abc12345

# タスクを完了にする
task-butler done abc12345
```

### 3. ショートIDサポート

タスクIDを受け取るすべてのコマンドで**ショートID**（UUIDの先頭8文字）が使用できます：

```bash
# これらは同等:
task-butler show abc12345-1234-5678-9abc-def012345678
task-butler show abc12345

# 一意であればさらに短いプレフィックスも可能:
task-butler done abc1
```

ショートIDが複数のタスクにマッチする場合、マッチするタスクの一覧が表示されます。

## シェル補完

Task Butlerはコマンド、オプション、タスクIDのシェル補完をサポートしています。

### セットアップ

```bash
# Zsh（タスクタイトル表示）
task-butler --install-completion zsh

# Fish（タスクタイトル表示）
task-butler --install-completion fish

# Bash（タスクタイトル表示）
mkdir -p ~/.bash_completions
curl -o ~/.bash_completions/task-butler.sh \
  https://raw.githubusercontent.com/dobachi/task-butler/main/scripts/task-butler-completion.bash
echo 'source ~/.bash_completions/task-butler.sh' >> ~/.bashrc
source ~/.bash_completions/task-butler.sh
```

インストール後、シェルを再起動するか設定ファイルを再読み込みしてください。

> **注意**: Bashでは `--install-completion bash` を使用しないでください。タスクタイトルが表示されない基本版がインストールされます。

### 機能

- **コマンド補完**: Tabでコマンド名を補完（`task-butler st<TAB>` -> `start`）
- **オプション補完**: Tabでオプション名を補完（`--pri<TAB>` -> `--priority`）
- **タスクID補完**: TabでマッチするタスクIDとタイトルを表示
  - オープンコマンド（`start`、`done`、`cancel`）はpending/in_progressのタスクのみ表示
  - その他のコマンド（`show`、`delete`、`note`）は全タスクを表示
- **プロジェクト名補完**: `--project`オプションで利用可能
- **タグ名補完**: `--tag`オプションで利用可能

### 使用例

```bash
# タスクを追加
task-butler add "タスク1"
task-butler add "タスク2"

# タスクIDを補完
task-butler show <TAB>
# 表示: abc12345 (タスク1)  def67890 (タスク2)

task-butler start <TAB>
# ステータスインジケータ付きでオープンタスクのみ表示
```

## コマンド

### タスクの追加

```bash
# 基本的なタスク
task-butler add "タスク名"

# オプション付き
task-butler add "タスク名" \
  --priority high \           # low, medium, high, urgent
  --due 2025-02-01 \         # 期限 (YYYY-MM-DD, today, tomorrow)
  --project "my-project" \   # プロジェクト名
  --tags "仕事,重要" \       # カンマ区切りのタグ
  --hours 4 \                # 見積時間
  --desc "説明"              # タスクの説明

# サブタスク（親タスクの子）
task-butler add "サブタスク" --parent abc123

# 依存関係のあるタスク
task-butler add "デプロイ" --depends abc123,def456

# 繰り返しタスク
task-butler add "週次レビュー" --recur weekly
task-butler add "隔週ミーティング" --recur "every 2 weeks"
```

### タスクの一覧表示

```bash
# 未完了タスクを一覧（デフォルト）
task-butler list

# 完了タスクも含める
task-butler list --all

# 優先度でフィルタ
task-butler list --priority high

# プロジェクトでフィルタ
task-butler list --project my-project

# タグでフィルタ
task-butler list --tag 重要

# テーブル形式
task-butler list --table

# ツリー形式（階層表示）
task-butler list --tree

# エイリアス
task-butler ls
```

### タスク詳細の表示

```bash
task-butler show abc123
```

### タスクステータスの変更

```bash
# タスクの作業を開始
task-butler start abc123

# 完了にする
task-butler done abc123

# 実績時間を記録して完了
task-butler done abc123 --hours 2.5

# キャンセル
task-butler cancel abc123
```

### タスクの管理

```bash
# メモを追加
task-butler note abc123 "進捗メモ：API完成"

# タスクを削除
task-butler delete abc123

# 強制削除（確認をスキップ）
task-butler delete abc123 --force
```

### その他のコマンド

```bash
# タスクを検索
task-butler search "バグ"

# 全プロジェクトを一覧
task-butler projects

# 全タグを一覧
task-butler tags

# バージョン表示
task-butler version

# ヘルプ
task-butler --help
task-butler add --help
```

## データストレージ

タスクは `~/.task-butler/tasks/` にYAMLフロントマター付きのMarkdownファイルとして保存されます。

**ファイル名形式**: `{short_id}_{title}.md`（例: `abc12345_認証機能の実装.md`）

```markdown
---
id: abc12345-1234-5678-9abc-def012345678
title: 認証機能の実装
status: in_progress
priority: high
created_at: 2025-01-25T10:00:00
updated_at: 2025-01-25T14:30:00
due_date: 2025-02-01T00:00:00
tags:
  - backend
  - security
project: api-v2
estimated_hours: 8
---

APIのJWTベース認証を実装する。

## Notes

- [2025-01-25 10:30] 調査開始
- [2025-01-25 14:30] JWTライブラリ選定完了
```

### ストレージ形式

2つのストレージ形式をサポート：

- **frontmatter**（デフォルト）: YAMLフロントマターのみ
- **hybrid**: YAMLフロントマター + Obsidian Tasks行（Obsidian連携向け）

ハイブリッド形式の例：
```markdown
---
id: abc12345-...
title: 会議準備
...
---

- [ ] 会議準備 ⏫ 📅 2025-02-01

説明文...
```

### 設定

設定は以下の順序で優先されます：

1. **CLIオプション**: `--format hybrid`
2. **環境変数**: `TASK_BUTLER_FORMAT=hybrid`
3. **設定ファイル**: `~/.task-butler/config.toml`

```toml
# ~/.task-butler/config.toml
[storage]
format = "hybrid"  # "frontmatter" または "hybrid"
```

すべての設定オプションは [`config.sample.toml`](config.sample.toml) を参照してください。

### カスタムストレージ場所

環境変数で設定：
```bash
export TASK_BUTLER_DIR=/path/to/tasks
```

またはコマンドラインオプションで：
```bash
task-butler --storage-dir /path/to/tasks list
```

## 開発

### セットアップ

```bash
git clone https://github.com/dobachi/task-butler.git
cd task-butler
uv sync --dev
```

### チェックの実行（コミット前に必須）

コミット前に必ず `make check` を実行して、CIが通ることを確認してください：

```bash
make check    # lint + format + test を実行（CIと同等）
```

### 利用可能なMakeターゲット

| コマンド | 説明 |
|---------|------|
| `make check` | 全CIチェックを実行（lint + format + test） |
| `make lint` | ruff linterを実行 |
| `make format` | コードフォーマットをチェック |
| `make test` | テストを実行 |
| `make fix` | lint・formatの問題を自動修正 |
| `make ci` | 完全なCIシミュレーション（typecheckを含む） |

### テストの実行

```bash
uv run pytest
# または
make test
```

### カバレッジ付きテスト

```bash
uv run pytest --cov=task_butler
```

## ロードマップ

- [x] **Phase 1**: 基本機能（MVP）
  - タスクのCRUD操作
  - 階層構造タスク
  - 依存関係
  - 繰り返しタスク
  - CLIインターフェース

- [x] **Phase 2**: AI機能
  - タスク分析と優先順位付け
  - スマート提案
  - 日次計画アシスタント
  - ローカルLLMサポート（llama-cpp-python）
  - 日本語モデル対応

- [x] **Phase 3**: Obsidian連携
  - ObsidianのVaultをストレージディレクトリとして使用
  - Obsidian Tasksプラグイン互換性（エクスポート/インポート）
  - 差分検知・解決機能

- [ ] **Phase 4**: 高度な機能
  - ファイル監視（Markdownからの自動インポート）
  - エクスポート（JSON, CSV）
  - インタラクティブチャットモード

- [x] **Phase 5**: 配布
  - PyPI公開（`pip install markdown-task-butler`）
  - シェル補完（Bash/Zsh/Fish）
  - ドキュメント拡充

- [ ] **Phase 6**: Windows対応
  - Windows互換性テスト
  - PowerShell補完
  - Windowsインストーラー / スタンドアロン実行ファイル

## Obsidian連携

Task Butlerは[Obsidian](https://obsidian.md/)のVaultと連携して動作します。[Obsidian Tasks](https://github.com/obsidian-tasks-group/obsidian-tasks)プラグインと互換性のあるフォーマットをサポートしています。

詳細は[Obsidian連携ガイド](docs/OBSIDIAN.md)を参照してください。

### クイックスタート

```bash
# ObsidianのVaultをストレージとして使用
export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks

# 日付フィールドを指定してタスク作成
task-butler add "会議準備" --due 2025-02-01 --scheduled 2025-01-25 --priority high

# Obsidian Tasks形式でエクスポート
task-butler obsidian export
# → - [ ] 会議準備 ⏫ 📅 2025-02-01 ⏳ 2025-01-25 ➕ 2025-01-25

# Obsidianノートからインポート
task-butler obsidian import ~/Documents/MyVault/daily/2025-01-25.md
```

### サポートする絵文字

| 絵文字 | 意味 | CLIオプション |
|--------|------|--------------|
| 📅 | 期限日 | `--due` |
| ⏳ | 予定日 | `--scheduled` |
| 🛫 | 開始日 | `--start` |
| 🔺⏫🔼🔽⏬ | 優先度 | `--priority` |
| ✅ | 完了日 | 自動設定 |
| 🔁 | 繰り返し | `--recur` |

### Obsidianコマンド

```bash
task-butler obsidian export    # Obsidian形式でエクスポート
task-butler obsidian import    # Obsidianファイルからインポート
task-butler obsidian import --link  # インポート＋ソース行をリンクに置換
task-butler obsidian check     # フロントマターとの差分を検知
task-butler obsidian resolve   # 差分を解決
task-butler obsidian format    # 単一タスクをObsidian形式で表示
```

## AI機能

Task ButlerにはAIによるタスク分析、スマート提案、日次計画機能が含まれています。

> **GPU対応**: NVIDIA GPUでの高速推論については [AI機能セットアップガイド](docs/AI_SETUP.md) を参照してください。

### クイックスタート

```bash
# モデルをダウンロード（初回のみ）
tb ai download tinyllama-1.1b    # 英語（軽量、670MB）
tb ai download elyza-jp-7b       # 日本語（推奨、4GB）

# LLMプロバイダーを有効化
tb config set ai.provider llama
tb config set ai.llama.model_name elyza-jp-7b  # 日本語用

# 出力言語を設定
tb config set ai.language ja     # 日本語
tb config set ai.language en     # 英語
```

### AIコマンド

```bash
# タスクを分析して優先度スコアを取得
tb analyze                # 全タスクを分析
tb analyze abc123         # 特定タスクを分析
tb analyze --save         # 分析結果をタスクのノートに保存

# スマートなタスク提案を取得
tb suggest                # 次のタスクを提案
tb suggest --hours 2      # 2時間以内に終わるタスク
tb suggest --energy low   # 低エネルギー向けタスク
tb suggest --count 5      # 5件の提案を取得

# 日次計画を生成
tb plan                   # 今日の計画（8時間）
tb plan --hours 6         # カスタム時間
tb plan --date 2025-02-01 # 特定日の計画
```

### 利用可能なモデル

| モデル | サイズ | 言語 | 説明 |
|--------|-------|------|------|
| `tinyllama-1.1b` | 670MB | 英語 | 軽量・高速 |
| `phi-2` | 1.6GB | 英語 | より高度な推論 |
| `elyza-jp-7b` | 4GB | 日本語 | 日本語に最適 |

### モデル管理

```bash
tb ai status              # 現在のAI設定を表示
tb ai models              # 利用可能なモデル一覧
tb ai download MODEL      # モデルをダウンロード
tb ai delete MODEL        # モデルを削除
```

### 設定

```toml
# ~/.task-butler/config.toml
[ai]
provider = "llama"        # "llama", "rule_based", or "openai"
language = "ja"           # 出力言語: "en" or "ja"

[ai.llama]
model_name = "elyza-jp-7b"
n_ctx = 2048              # コンテキストウィンドウサイズ
n_gpu_layers = 0          # GPUレイヤー数（0 = CPUのみ）

[ai.analysis]
weight_deadline = 0.3     # 期限の重要度
weight_dependencies = 0.25
weight_effort = 0.2
weight_staleness = 0.15
weight_priority = 0.1
```

### フォールバックモード

LLMがインストールされていない場合、ルールベースの分析器が使用されます：
- 期限、依存関係、工数に基づく優先度スコアリング
- 利用可能時間に基づくタスク提案
- 基本的な日次計画

拡張AI機能を使用するには、LLMオプション依存をインストール：

```bash
uv tool install markdown-task-butler[llm]
# or
pip install markdown-task-butler[llm]
```

## ライセンス

MIT

## 作者

dobachi
