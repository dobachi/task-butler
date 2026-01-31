# Task Butler クックブック

[English](COOKBOOK.en.md)

Task Butlerの定番の使い方をレシピ形式でまとめたガイドです。

## 目次

- [基本ワークフロー](#基本ワークフロー)
- [タスク整理](#タスク整理)
- [Obsidian連携](#obsidian連携)
- [繰り返しタスク](#繰り返しタスク)
- [高度な使い方](#高度な使い方)

---

## 基本ワークフロー

### レシピ: 新しいタスクを追加する

**状況**: 新しい作業が発生したとき

**手順**:
```bash
# シンプルなタスク
task-butler add "ドキュメントを更新する"

# 期限と優先度を指定
task-butler add "バグを修正する" --due 2025-02-01 --priority high

# プロジェクトとタグを指定
task-butler add "API設計" --project backend --tags "設計,重要"
```

**ポイント**:
- 期限は `today`, `tomorrow`, `YYYY-MM-DD` 形式で指定可能
- 優先度は `lowest`, `low`, `medium`, `high`, `urgent` の5段階

---

### レシピ: タスク一覧を確認する

**状況**: 今やるべきことを確認したいとき

**手順**:
```bash
# 未完了タスクを一覧表示
task-butler list

# テーブル形式で表示
task-butler list --table

# ツリー形式で階層表示
task-butler list --tree

# 高優先度のみ表示
task-butler list --priority high

# 特定プロジェクトのみ
task-butler list --project backend
```

**ポイント**:
- `task-butler ls` は `list` のエイリアス
- `--all` で完了タスクも表示

---

### レシピ: タスクを開始〜完了する

**状況**: タスクに取り掛かり、完了させるとき

**手順**:
```bash
# タスク一覧でIDを確認
task-butler list

# タスクを開始（ステータスが in_progress に）
task-butler start abc12345

# 作業中にメモを追加
task-butler note abc12345 "APIのレスポンス形式を決定"

# タスクを完了
task-butler done abc12345

# 作業時間を記録して完了
task-butler done abc12345 --hours 2.5
```

**ポイント**:
- タスクIDは最初の数文字（短縮ID）でOK
- 短縮IDが複数にマッチする場合は候補が表示される

---

### レシピ: タスクの詳細を確認する

**状況**: タスクの全情報を確認したいとき

**手順**:
```bash
task-butler show abc12345
```

**ポイント**:
- 説明、メモ、作成日時、更新日時などが表示される

---

## タスク整理

### レシピ: 優先度でタスクを整理する

**状況**: 重要なタスクを見つけて優先的に処理したいとき

**手順**:
```bash
# 緊急タスクを確認
task-butler list --priority urgent

# 高優先度以上を確認
task-butler list --priority high
```

**ポイント**:
- `urgent` > `high` > `medium` > `low` > `lowest`
- 未指定時は `medium` がデフォルト

---

### レシピ: プロジェクト別にタスクを管理する

**状況**: 複数のプロジェクトを並行して進めているとき

**手順**:
```bash
# プロジェクト一覧を確認
task-butler projects

# 特定プロジェクトのタスクを表示
task-butler list --project backend

# プロジェクトを指定してタスク追加
task-butler add "DB設計" --project backend
```

**ポイント**:
- プロジェクト名は自由に設定可能
- 同じプロジェクト名を使うことでグループ化

---

### レシピ: タグでタスクを分類する

**状況**: プロジェクト横断で特定の種類のタスクを管理したいとき

**手順**:
```bash
# タグ一覧を確認
task-butler tags

# 特定タグのタスクを表示
task-butler list --tag 重要

# 複数タグを指定してタスク追加
task-butler add "セキュリティ監査" --tags "セキュリティ,重要,Q1"
```

**ポイント**:
- タグはカンマ区切りで複数指定可能
- プロジェクトと組み合わせて柔軟に分類

---

## Obsidian連携

### レシピ: Obsidian Vaultでタスク管理を始める

**状況**: ObsidianをメインのノートアプリとしてTask Butlerと連携したいとき

**手順**:
```bash
# 1. ストレージをVault内に設定
export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks

# 2. 設定を永続化（.bashrc または .zshrc に追加）
echo 'export TASK_BUTLER_DIR=~/Documents/MyVault/Tasks' >> ~/.bashrc

# 3. タスクを追加（Vault内に保存される）
task-butler add "Obsidian連携テスト" --due tomorrow
```

**ポイント**:
- `~/.task-butler/config.toml` でも設定可能
- Vault内の任意のフォルダを指定可能（例: `Tasks/`, `GTD/`）

---

### レシピ: ハイブリッド形式でObsidianと共存する

**状況**: ObsidianでタスクファイルをそのままObsidian Tasks形式で表示したいとき

**手順**:
```bash
# ハイブリッド形式でタスク追加
task-butler --format hybrid add "会議準備" --due 2025-02-01 --priority high

# 設定で永続化
cat >> ~/.task-butler/config.toml << 'EOF'
[storage]
format = "hybrid"
EOF
```

**ポイント**:
- ハイブリッド形式ではYAMLフロントマターに加えてObsidian Tasks行も生成
- Obsidian Tasksプラグインでそのまま表示・操作可能

---

### レシピ: デイリーノートからタスクをインポートする

**状況**: Obsidianのデイリーノートに書いたタスクをTask Butlerに取り込みたいとき

**手順**:
```bash
# 単一ファイルからインポート
task-butler obsidian import ~/Documents/MyVault/daily/2025-01-31.md

# ディレクトリから一括インポート
task-butler obsidian import ~/Documents/MyVault/daily/

# プレビュー（実際には作成しない）
task-butler obsidian import ~/Documents/MyVault/daily/ --dry-run

# 重複タスクは更新
task-butler obsidian import ~/Documents/MyVault/daily/ --update
```

**ポイント**:
- `- [ ]` または `- [x]` で始まる行がタスクとして認識される
- `--link` オプションでインポート後にwikiリンクに置換可能

---

### レシピ: デイリーノートにタスクをエクスポートする

**状況**: Task Butlerのタスクをデイリーノートに出力したいとき

**手順**:
```bash
# Obsidian Tasks形式で全タスクを表示
task-butler obsidian export

# ファイルに出力
task-butler obsidian export --output ~/Documents/MyVault/Tasks/all-tasks.md

# 完了タスクも含める
task-butler obsidian export --include-done
```

**ポイント**:
- エクスポート結果はObsidian Tasksプラグインと互換性あり
- 日次/週次レビュー用のサマリーとして活用可能

---

### レシピ: 差分を検知・解決する

**状況**: ObsidianとTask Butler両方でタスクを編集して不整合が発生したとき

**手順**:
```bash
# 差分を検知
task-butler obsidian check

# YAMLフロントマターを正として解決
task-butler obsidian resolve --strategy frontmatter

# Obsidian Tasks行を正として解決
task-butler obsidian resolve --strategy obsidian

# プレビュー
task-butler obsidian resolve --dry-run
```

**ポイント**:
- 週次で `obsidian check` を実行するのがおすすめ
- 差分が発生したらどちらの編集を優先するか選択

---

## 繰り返しタスク

### レシピ: 週次タスクを設定する

**状況**: 毎週行う定例タスクを自動生成したいとき

**手順**:
```bash
# 毎週の週次レビュー
task-butler add "週次レビュー" --recur weekly --priority high

# 隔週のタスク
task-butler add "隔週ミーティング準備" --recur "every 2 weeks"
```

**ポイント**:
- 繰り返しタスクを完了すると、次回分が自動生成される
- `daily`, `weekly`, `monthly`, `yearly` が使用可能

---

### レシピ: 定期的なレビュータスクを作成する

**状況**: 月次や四半期ごとのレビュータスクを管理したいとき

**手順**:
```bash
# 月次レポート
task-butler add "月次レポート作成" --recur monthly --priority high --project reports

# 四半期レビュー
task-butler add "Q1レビュー" --recur "every 3 months" --tags "レビュー,重要"
```

**ポイント**:
- 期限日（`--due`）と組み合わせて、開始日を固定可能

---

## 高度な使い方

### レシピ: 依存関係のあるタスクを管理する

**状況**: タスクAが完了しないとタスクBに着手できないとき

**手順**:
```bash
# 先行タスクを作成
task-butler add "データベース設計"
# → ID: abc12345

# 依存タスクを作成
task-butler add "API実装" --depends abc12345
```

**ポイント**:
- 依存先タスクが未完了の場合、依存タスクは「ブロック中」として表示
- 複数の依存先を指定可能（カンマ区切り）

---

### レシピ: サブタスクで作業を分解する

**状況**: 大きなタスクを小さな作業に分割したいとき

**手順**:
```bash
# 親タスクを作成
task-butler add "リリース準備"
# → ID: abc12345

# サブタスクを作成
task-butler add "テスト実行" --parent abc12345
task-butler add "ドキュメント更新" --parent abc12345
task-butler add "デプロイ" --parent abc12345

# ツリー形式で確認
task-butler list --tree
```

**ポイント**:
- サブタスクは親タスクの下に階層表示される
- 親タスクと独立して完了可能

---

## 関連ドキュメント

- [README](../README.ja.md) - Task Butlerの基本的な使い方
- [Obsidian連携ガイド](OBSIDIAN.md) - 詳細なObsidian連携方法
- [設計ドキュメント](DESIGN.md) - 内部設計について
