# Task Butler

日本語 | [English](README.md)

タスク管理を支援するデジタル執事。タスクの管理、優先順位付け、整理を支援するCLIツールです。

## 特徴

- **シンプルなCLI**: 直感的なコマンドでタスクを管理
- **Markdownストレージ**: YAMLフロントマター付きの人間可読なMarkdownファイルとして保存
- **階層構造タスク**: 親子関係でタスクを構造化
- **依存関係**: タスク間の依存関係を定義し、ブロッキングを追跡
- **繰り返しタスク**: 日次、週次、月次、年次の繰り返しタスクを設定
- **リッチな出力**: カラーとフォーマットによる美しいターミナル出力
- **Git対応**: 全てのデータはプレーンテキストで保存、バージョン管理が容易

## インストール

### uvxを使用（推奨）

```bash
uvx task-butler
```

### pipを使用

```bash
pip install task-butler
```

### ソースから

```bash
git clone https://github.com/dobachi/task-butler.git
cd task-butler
uv sync
uv run task-butler
```

## クイックスタート

```bash
# タスクを追加
task-butler add "ドキュメントを書く"

# 高優先度のタスクを期限付きで追加
task-butler add "重大なバグを修正" --priority urgent --due 2025-01-30

# 全タスクを一覧表示
task-butler list

# タスクの作業を開始
task-butler start abc123

# タスクを完了にする
task-butler done abc123
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

タスクは `~/.task-butler/tasks/` にYAMLフロントマター付きのMarkdownファイルとして保存されます：

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

### テストの実行

```bash
uv run pytest
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

- [ ] **Phase 2**: AI統合
  - タスク分析と優先順位付け
  - スマート提案
  - 日次計画アシスタント

- [ ] **Phase 3**: 高度な機能
  - ファイル監視（Markdownからの自動インポート）
  - エクスポート（JSON, CSV）
  - インタラクティブチャットモード

- [ ] **Phase 4**: 配布
  - スタンドアロン実行ファイル
  - ドキュメント拡充

## ライセンス

MIT

## 作者

dobachi
