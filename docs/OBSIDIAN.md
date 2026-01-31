# Obsidian連携ガイド

[English](OBSIDIAN.en.md)

Task ButlerとObsidian Tasksプラグインの連携方法について詳しく説明します。

## 目次

- [概要](#概要)
- [Obsidian Tasksフォーマット](#obsidian-tasksフォーマット)
- [基本的な使い方](#基本的な使い方)
- [ストレージ形式オプション（--format）](#ストレージ形式オプションformat)
- [コマンドリファレンス](#コマンドリファレンス)
- [日付フィールド](#日付フィールド)
- [優先度](#優先度)
- [差分検知と解決](#差分検知と解決)
- [ワークフロー例](#ワークフロー例)
- [トラブルシューティング](#トラブルシューティング)

## 概要

Task Butlerは[Obsidian Tasks](https://github.com/obsidian-tasks-group/obsidian-tasks)プラグインと互換性のあるフォーマットをサポートしています。これにより：

- **双方向の連携**: Task ButlerからObsidian形式でエクスポート、ObsidianからTask Butlerへインポート
- **絵文字ベースのメタデータ**: 優先度、日付、繰り返しを絵文字で表現
- **差分検知**: YAMLフロントマターとObsidian Tasks行の不整合を検出・修正

## Obsidian Tasksフォーマット

Obsidian Tasksプラグインは、Markdownのチェックボックスに絵文字でメタデータを付加します：

```markdown
- [ ] タスク名 🔺 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20 ➕ 2025-01-15 🔁 every week #work #important
- [x] 完了タスク ✅ 2025-01-20
```

### 絵文字の意味

| 絵文字 | 意味 | 説明 |
|--------|------|------|
| 📅 | 期限日 (Due) | タスクの締め切り |
| ⏳ | 予定日 (Scheduled) | 作業を予定している日 |
| 🛫 | 開始日 (Start) | 作業を開始できる日 |
| ➕ | 作成日 (Created) | タスクを作成した日 |
| ✅ | 完了日 (Done) | タスクを完了した日 |
| 🔁 | 繰り返し (Recurrence) | 繰り返しルール |

### 優先度の絵文字

| 絵文字 | Obsidian Tasks | Task Butler |
|--------|---------------|-------------|
| 🔺 | Highest | urgent |
| ⏫ | High | high |
| 🔼 | Medium | medium |
| 🔽 | Low | low |
| ⏬ | Lowest | lowest |

## 基本的な使い方

### ObsidianのVaultをストレージとして使用

Task ButlerのストレージディレクトリをObsidian Vault内に設定することで、両方のツールから同じタスクにアクセスできます：

```bash
# 環境変数で設定（推奨）
export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks

# または毎回オプションで指定
task-butler --storage-dir ~/Documents/MyVault/Tasks list
```

### タスクの作成（新しい日付フィールド対応）

```bash
# 期限日、予定日、開始日を指定してタスク作成
task-butler add "重要な会議の準備" \
  --due 2025-02-01 \
  --scheduled 2025-01-25 \
  --start 2025-01-20 \
  --priority high \
  --tags "仕事,会議"
```

出力:
```
✓ Created task: 重要な会議の準備
  ID: abc12345
  Due: 2025-02-01
  Scheduled: 2025-01-25
  Start: 2025-01-20
```

### Obsidian形式でエクスポート

```bash
# 全タスクをObsidian Tasks形式で表示
task-butler obsidian export

# ファイルに出力
task-butler obsidian export --output tasks.md

# 完了タスクも含める
task-butler obsidian export --include-done
```

出力例:
```markdown
- [ ] 重要な会議の準備 ⏫ 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20 ➕ 2025-01-25 #仕事 #会議
- [ ] 週次レポート作成 🔼 📅 2025-01-31 🔁 every week #仕事
- [x] バグ修正 ✅ 2025-01-24 #開発
```

### 単一タスクをObsidian形式で表示

```bash
# タスクIDを指定してObsidian形式で表示
task-butler obsidian format abc12345
```

コピーしてObsidianのノートに貼り付けられます。

### Obsidianからインポート

```bash
# 単一ファイルからインポート
task-butler obsidian import ~/Documents/MyVault/daily/2025-01-25.md

# ディレクトリから一括インポート
task-butler obsidian import ~/Documents/MyVault/daily/

# サブディレクトリも含めて再帰的にインポート
task-butler obsidian import ~/Documents/MyVault/ --recursive

# プレビュー（実際には作成しない）
task-butler obsidian import ~/Documents/MyVault/daily/ --dry-run

# 重複タスクを更新
task-butler obsidian import ~/Documents/MyVault/daily/ --update

# 重複確認をインタラクティブに
task-butler obsidian import ~/Documents/MyVault/daily/ --interactive

# ソース行をリンクに置換
task-butler obsidian import ~/Documents/MyVault/daily/ --link

# 埋め込み形式でリンク
task-butler obsidian import ~/Documents/MyVault/daily/ --link --link-format embed
```

## ストレージ形式オプション（--format）

### 概要

`--format` オプションは、タスクファイルの**保存形式**を制御します。

```bash
# ハイブリッド形式で保存（YAML frontmatter + Obsidian Tasks行）
task-butler --format hybrid add "タスク名"

# frontmatter形式で保存（デフォルト、YAML frontmatterのみ）
task-butler --format frontmatter add "タスク名"
```

### 重要：読み込みと表示への影響

`--format` オプションは**書き込み時のみ**影響します：

| 処理 | --format の影響 |
|------|----------------|
| **保存（add, done, start等）** | ✅ 影響する |
| **読み込み（list, show等）** | ❌ 影響しない |
| **表示形式** | ❌ 影響しない |

読み込み時の動作：
- データは常に**YAML frontmatter**から読み込まれます（source of truth）
- ファイル本文のObsidian Tasks行は、重複防止のため除去されます
- `--format hybrid` を指定しても `list` や `show` の表示形式は変わりません

### Obsidian形式で表示するには

`list` や `show` でObsidian Tasks形式の出力が必要な場合は、専用コマンドを使用してください：

```bash
# 全タスクをObsidian形式で表示
task-butler obsidian export

# 単一タスクをObsidian形式で表示
task-butler obsidian format abc12345
```

### 設定方法

ストレージ形式は以下の優先順で決定されます：

1. **CLIオプション**: `--format hybrid`
2. **環境変数**: `TASK_BUTLER_FORMAT=hybrid`
3. **設定ファイル**: `~/.task-butler/config.toml`

```toml
# ~/.task-butler/config.toml
[storage]
format = "hybrid"  # "frontmatter" または "hybrid"
```

## コマンドリファレンス

### `task-butler add` の新オプション

```bash
task-butler add "タスク名" [オプション]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--due` | `-d` | 期限日（📅） |
| `--scheduled` | `-s` | 予定日（⏳）- いつ作業するか |
| `--start` | - | 開始日（🛫）- いつから作業可能か |
| `--priority` | `-p` | 優先度（lowest, low, medium, high, urgent） |

### `task-butler obsidian` サブコマンド

#### `obsidian export`

タスクをObsidian Tasks形式でエクスポートします。

```bash
task-butler obsidian export [オプション]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--format` | `-f` | 出力形式: `tasks`（デフォルト）または `frontmatter` |
| `--output` | `-o` | 出力ファイルパス（省略時は標準出力） |
| `--include-done` | - | 完了タスクも含める |

#### `obsidian import`

Obsidian MarkdownファイルまたはディレクトリからTask Butlerにタスクをインポートします。

```bash
task-butler obsidian import <パス> [オプション]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--recursive` | `-r` | サブディレクトリも含める（ディレクトリ指定時） |
| `--pattern` | `-p` | ファイルパターン（デフォルト: `*.md`） |
| `--skip` | - | 重複タスクをスキップ（デフォルト） |
| `--update` | - | 重複タスクを既存タスクで更新 |
| `--force` | - | 重複でも新規タスクとして作成 |
| `--interactive` | `-i` | 重複ごとにユーザーに確認 |
| `--dry-run` | `-n` | 実際には作成せずプレビューのみ |
| `--link` | `-l` | ソース行をwikiリンクに置換 |
| `--link-format` | - | リンク形式: `wiki`（デフォルト）または `embed` |

**リンク置換モードについて:**

`--link` オプションを使用すると、インポート後に元のObsidianノート内のタスク行がwikiリンクに置換されます。これにより、Obsidian Tasksプラグインでの重複表示を防ぎ、タスクの一元管理を実現できます。

インポート前:
```markdown
- [ ] 会議準備 📅 2025-02-01
```

インポート後（`--link`使用）:
```markdown
- [[Tasks/abc12345_会議準備|会議準備]]
```

**注意:**
- Obsidian Vault内（`.obsidian`ディレクトリがある場所）で実行する必要があります
- Task Butlerストレージ（`--storage-dir`）がVault外にある場合、リンクが正常に動作しない可能性があります
- `--link-format embed`を使用すると、埋め込み形式（`![[...]]`）でリンクが生成されます

**重複検知について:**

タスクの重複は「タイトル」と「期限日」の組み合わせで判定されます。同じタイトルと期限日を持つタスクが既に存在する場合、指定したオプションに応じて処理されます。

- `--skip`（デフォルト）: 重複をスキップして次のタスクへ
- `--update`: 既存タスクの優先度、日付、タグを更新
- `--force`: 重複を無視して新規タスクとして作成
- `--interactive`: 重複ごとに `[s]kip, [u]pdate, [f]orce, [a]ll skip, [A]ll update` を選択

**ディレクトリインポートの例:**

```bash
# dailyディレクトリ内のすべてのmdファイルをインポート
task-butler obsidian import ~/Vault/daily/

# daily-*.md のパターンにマッチするファイルのみ
task-butler obsidian import ~/Vault/daily/ --pattern "daily-*.md"

# Vault全体を再帰的にインポート（プレビュー）
task-butler obsidian import ~/Vault/ --recursive --dry-run
```

#### `obsidian check`

YAMLフロントマターとObsidian Tasks行の間の差分を検知します。

```bash
task-butler obsidian check
```

出力例:
```
⚠ Conflict in task abc12345: 重要な会議の準備
  status: frontmatter=pending, obsidian_line=done
  priority: frontmatter=high, obsidian_line=urgent

Found 1 task(s) with conflicts
Use 'task-butler obsidian resolve' to fix conflicts
```

#### `obsidian resolve`

検知された差分を解決します。

```bash
task-butler obsidian resolve [オプション]
```

| オプション | 短縮形 | 説明 |
|-----------|--------|------|
| `--strategy` | `-s` | 解決戦略: `frontmatter`（デフォルト）または `obsidian` |
| `--task` | `-t` | 特定のタスクIDのみ解決 |
| `--dry-run` | `-n` | 実際には変更せずプレビューのみ |

解決戦略:
- `frontmatter`: YAMLフロントマターの値を正として、Obsidian Tasks行を更新
- `obsidian`: Obsidian Tasks行の値を正として、フロントマターを更新

#### `obsidian format`

単一のタスクをObsidian Tasks形式で表示します。

```bash
task-butler obsidian format <タスクID>
```

## 日付フィールド

Task Butlerは4種類の日付フィールドをサポートしています：

### 期限日（Due Date）📅

タスクの締め切り。この日までに完了する必要があります。

```bash
task-butler add "レポート提出" --due 2025-02-01
```

### 予定日（Scheduled Date）⏳

作業を予定している日。「この日にやる」という計画です。

```bash
task-butler add "資料作成" --scheduled 2025-01-25
```

### 開始日（Start Date）🛫

作業を開始できる日。この日より前には着手できない（または着手すべきでない）タスクに使用します。

```bash
task-butler add "新機能実装" --start 2025-01-20
```

### 完了日（Completed At）✅

タスク完了時に自動設定されます。手動で設定する必要はありません。

```bash
task-butler done abc12345
# → completed_at が自動的に現在日時に設定される
```

### 日付の組み合わせ例

```bash
# 1月20日から着手可能、1月25日に作業予定、2月1日が締め切り
task-butler add "プロジェクト計画書作成" \
  --start 2025-01-20 \
  --scheduled 2025-01-25 \
  --due 2025-02-01
```

Obsidian形式:
```markdown
- [ ] プロジェクト計画書作成 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20 ➕ 2025-01-25
```

## 優先度

Task Butlerは5段階の優先度をサポートしています：

| レベル | CLI値 | 絵文字 | 説明 |
|--------|-------|--------|------|
| 最高 | `urgent` | 🔺 | 今すぐ対応が必要 |
| 高 | `high` | ⏫ | 優先的に対応 |
| 中 | `medium` | 🔼 | 通常の優先度（デフォルト） |
| 低 | `low` | 🔽 | 時間があるときに |
| 最低 | `lowest` | ⏬ | いつかやる |

```bash
# 最低優先度のタスク
task-butler add "いつかやるアイデア" --priority lowest
```

**注意**: `medium`（中）優先度はObsidian形式では絵文字を省略します（デフォルトのため）。

## 差分検知と解決

### なぜ差分が発生するか

Task ButlerはタスクをYAMLフロントマター付きのMarkdownファイルとして保存します。ハイブリッド形式を使用する場合、ファイル本文にもObsidian Tasks形式の行が含まれることがあります：

```markdown
---
id: abc12345
title: 会議準備
status: pending
priority: high
due_date: 2025-02-01T00:00:00
---

- [ ] 会議準備 ⏫ 📅 2025-02-01

詳細な説明...
```

Obsidian上でタスクを直接編集すると（チェックボックスをクリックするなど）、Obsidian Tasks行は更新されますが、YAMLフロントマターは更新されません。これが差分（コンフリクト）の原因になります。

### 差分の確認

```bash
task-butler obsidian check
```

### 差分の解決

```bash
# YAMLフロントマターを正として統一（推奨）
task-butler obsidian resolve --strategy frontmatter

# Obsidian Tasks行を正として統一
task-butler obsidian resolve --strategy obsidian

# 特定のタスクのみ解決
task-butler obsidian resolve --task abc12345 --strategy frontmatter

# プレビュー
task-butler obsidian resolve --dry-run
```

## ワークフロー例

### ワークフロー1: Task Butler中心の運用

1. Task ButlerのストレージをObsidian Vault内に設定
2. Task ButlerのCLIでタスクを管理
3. Obsidianでタスクファイルを閲覧・メモ追記
4. 定期的に `obsidian export` でObsidian Tasks形式のサマリーを生成

```bash
# 設定
export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks

# 日常操作
task-butler add "新機能実装" --due 2025-02-01 --priority high
task-butler list
task-butler start abc12345
task-butler done abc12345

# 週次: サマリー生成
task-butler obsidian export --output ~/Documents/MyVault/Tasks/summary.md
```

### ワークフロー2: Obsidian中心の運用

1. Obsidianでデイリーノートにタスクを記録（Obsidian Tasks形式）
2. 定期的にTask Butlerにインポート
3. Task Butlerで分析・レポート生成

```bash
# デイリーノートディレクトリから一括インポート（重複はスキップ）
task-butler obsidian import ~/Documents/MyVault/daily/

# または特定ファイルのみ
task-butler obsidian import ~/Documents/MyVault/daily/2025-01-25.md

# 既存タスクを更新する場合
task-butler obsidian import ~/Documents/MyVault/daily/ --update

# タスク一覧確認
task-butler list

# プロジェクト別確認
task-butler list --project my-project
```

### ワークフロー3: ハイブリッド運用

1. 両方のツールでタスクを編集
2. 定期的に差分をチェック
3. 必要に応じて解決

```bash
# 差分チェック（毎日）
task-butler obsidian check

# 差分があれば解決
task-butler obsidian resolve --strategy frontmatter
```

## トラブルシューティング

### Q: インポート時に一部のタスクが読み込めない

**A**: Obsidian Tasks形式として認識されるには、行が `- [ ]` または `- [x]` で始まる必要があります。

正しい形式:
```markdown
- [ ] タスク名
- [x] 完了タスク
```

認識されない形式:
```markdown
* [ ] タスク名    # *ではなく-を使用
- [] タスク名     # スペースが必要
  - [ ] タスク名  # インデントは可（ただし階層情報は失われる）
```

### Q: 優先度が正しく変換されない

**A**: Task Butlerの5段階優先度とObsidian Tasksの優先度は以下のようにマッピングされます：

- `urgent` ↔ 🔺 (Highest)
- `high` ↔ ⏫ (High)
- `medium` ↔ 🔼 (Medium) ※省略可能
- `low` ↔ 🔽 (Low)
- `lowest` ↔ ⏬ (Lowest)

### Q: 繰り返しタスクがうまく動作しない

**A**: 現在サポートしている繰り返し形式:

- `daily`, `weekly`, `monthly`, `yearly`
- `every day`, `every week`, `every month`, `every year`
- `every N days`, `every N weeks`, `every N months`, `every N years`

複雑な繰り返し（「毎週月曜日」など）は現在サポートしていません。

### Q: Obsidianで編集したのにTask Butlerに反映されない

**A**: Obsidianで直接編集した場合、YAMLフロントマターは更新されません。以下の手順で同期してください：

```bash
# 差分確認
task-butler obsidian check

# Obsidian側の編集を反映
task-butler obsidian resolve --strategy obsidian
```

### Q: ファイルのエンコーディングエラー

**A**: Task ButlerはUTF-8エンコーディングを使用します。ファイルがUTF-8で保存されていることを確認してください。

## 関連ドキュメント

- [README](../README.ja.md) - Task Butlerの基本的な使い方
- [DESIGN](DESIGN.md) - 設計ドキュメント
- [Obsidian Tasks公式ドキュメント](https://publish.obsidian.md/tasks/)
