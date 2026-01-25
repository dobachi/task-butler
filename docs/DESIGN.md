# Task Butler - 設計ドキュメント

日本語 | [English](DESIGN.en.md)

## 概要

ユーザーのタスク管理・優先度付け・推奨対応方針を提示する「執事」のようなツール。

## 決定事項

| 項目 | 決定内容 |
|------|----------|
| プロジェクト名 | task-butler |
| 入力方式 | CLI対話 + Markdownファイル編集の両対応 |
| AI方式 | llama-cpp-python + 初回起動時に小型モデル自動ダウンロード（Phase 2） |
| 言語 | Python 3.11+ (uv管理、uvx実行対応) |
| 階層構造 | 自由に階層化可能（再帰的親子関係） |
| 依存関係 | データモデルで明示的に管理 |
| 繰り返しタスク | Phase 1から実装 |

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                      User Interface                      │
├─────────────────┬───────────────────────────────────────┤
│   CLI (typer)   │   Markdown File Watcher (Phase 3)     │
└────────┬────────┴───────────────────┬───────────────────┘
         │                            │
         ▼                            ▼
┌─────────────────────────────────────────────────────────┐
│                     Core Engine                          │
├─────────────────────────────────────────────────────────┤
│  TaskManager  │  RecurrenceGenerator  │  (AI Phase 2)   │
└───────────────┴─────────┬─────────────┴─────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
│   Repository    │ │MarkdownStore│ │ Data Models  │
│   (CRUD API)    │ │ (File I/O)  │ │  (Pydantic)  │
└─────────────────┘ └──────────────┘ └──────────────┘
```

## ディレクトリ構造

```
task-butler/
├── pyproject.toml          # プロジェクト設定・依存関係
├── README.md               # 使用方法
├── src/
│   └── task_butler/
│       ├── __init__.py     # バージョン情報
│       ├── models/         # データモデル
│       │   ├── task.py     # Task, Note, RecurrenceRule
│       │   └── enums.py    # Status, Priority, Frequency
│       ├── storage/        # ストレージ層
│       │   ├── markdown.py # Markdownファイル読み書き
│       │   └── repository.py # CRUD操作
│       ├── core/           # ビジネスロジック
│       │   ├── task_manager.py # タスク管理
│       │   └── recurrence.py   # 繰り返しタスク生成
│       ├── cli/            # CLIインターフェース
│       │   ├── main.py     # エントリーポイント
│       │   └── commands/   # 各コマンド実装
│       └── ai/             # AI機能（Phase 2）
├── tests/                  # テストコード
└── docs/                   # ドキュメント
    └── DESIGN.md          # この設計書
```

## データモデル

### Task

```python
class Task(BaseModel):
    id: str                          # UUID
    title: str                       # タスク名
    description: str = ""            # 詳細説明
    status: Status = "pending"       # pending/in_progress/done/cancelled
    priority: Priority = "medium"    # low/medium/high/urgent

    # 時間関連
    due_date: datetime | None        # 期限
    estimated_hours: float | None    # 見積時間
    actual_hours: float | None       # 実績時間

    # 分類
    tags: list[str] = []             # タグ
    project: str | None              # プロジェクト名

    # 階層・依存関係
    parent_id: str | None            # 親タスクID
    dependencies: list[str] = []     # 依存タスクID

    # 繰り返し
    recurrence: RecurrenceRule | None # 繰り返しルール
    recurrence_parent_id: str | None  # 繰り返し元タスクID

    # メタデータ
    created_at: datetime
    updated_at: datetime
    notes: list[Note] = []
```

### RecurrenceRule

```python
class RecurrenceRule(BaseModel):
    frequency: Frequency    # daily/weekly/monthly/yearly
    interval: int = 1       # 間隔（2なら隔週など）
    days_of_week: list[int] | None  # 0=月曜〜6=日曜
    day_of_month: int | None        # 月の何日
    end_date: datetime | None       # 終了日
```

## Markdownフォーマット

タスクは以下の形式でMarkdownファイルとして保存されます：

```markdown
---
id: abc12345-1234-5678-9abc-def012345678
title: APIエンドポイントの実装
status: pending
priority: high
created_at: 2025-01-25T10:00:00
updated_at: 2025-01-25T10:00:00
due_date: 2025-02-01T00:00:00
tags:
  - development
  - backend
project: my-project
estimated_hours: 4
---

ユーザー認証APIを実装する。

## Notes

- [2025-01-25 10:30] 初期調査完了。JWTを使用予定。
- [2025-01-25 14:00] エンドポイント設計完了。
```

## CLIコマンド

### 基本操作

```bash
# タスク追加
task-butler add "新しいタスク" --priority high --due 2025-02-01
task-butler add "サブタスク" --parent <parent-id>
task-butler add "依存タスク" --depends <task-id>
task-butler add "週次レビュー" --recur weekly

# 一覧表示
task-butler list                    # 未完了タスク一覧
task-butler list --all              # 完了含む全タスク
task-butler list --priority high    # 優先度でフィルタ
task-butler list --project myproj   # プロジェクトでフィルタ
task-butler list --table            # テーブル形式
task-butler list --tree             # ツリー形式（階層表示）

# タスク詳細
task-butler show <task-id>

# ステータス変更
task-butler start <task-id>         # 着手開始
task-butler done <task-id>          # 完了
task-butler done <task-id> -h 2.5   # 実績時間を記録して完了
task-butler cancel <task-id>        # キャンセル

# メモ追加
task-butler note <task-id> "進捗メモ"

# 削除
task-butler delete <task-id>        # 確認あり
task-butler delete <task-id> -f     # 強制削除

# 検索
task-butler search "キーワード"

# その他
task-butler projects                # プロジェクト一覧
task-butler tags                    # タグ一覧
task-butler version                 # バージョン表示
```

### エイリアス

- `task-butler` または `tb` で実行可能

## 依存関係管理

- タスクは他のタスクに依存できる（`--depends`オプション）
- 依存タスクが完了するまで、そのタスクは開始できない
- 依存関係があるタスクは削除できない

## 繰り返しタスク

- `--recur` オプションで繰り返しルールを設定
- 対応パターン: `daily`, `weekly`, `monthly`, `yearly`, `every N days/weeks/months`
- インスタンスが完了すると次のインスタンスが自動生成される

## 実装状況

### Phase 1: 基盤（MVP） ✅

- [x] データモデル実装
- [x] Markdownストレージ実装
- [x] 基本CLI（add, list, show, start, done, cancel, delete, note）
- [x] 階層構造（親子関係）
- [x] 依存関係管理
- [x] 繰り返しタスク
- [x] uvx実行対応
- [x] テスト実装

### Phase 2: AI統合（未実装）

- [ ] llama-cpp-python + 自動モデルDL
- [ ] タスク分析機能（analyze）
- [ ] 推奨機能（suggest）
- [ ] 計画機能（plan）

### Phase 3: 高度な機能（未実装）

- [ ] ファイル監視（watchdog）
- [ ] エクスポート（JSON, CSV）
- [ ] 対話モード（chat）

### Phase 4: 配布（未実装）

- [ ] exe化（PyInstaller/Nuitka）
- [ ] ドキュメント整備

## 技術スタック

| 領域 | 技術 | 理由 |
|------|------|------|
| 言語 | Python 3.11+ | 幅広い互換性 |
| パッケージ管理 | uv | 高速、モダン |
| CLI | typer | 型安全、自動補完、ヘルプ生成 |
| データ検証 | pydantic | 堅牢なバリデーション |
| 出力整形 | rich | 美しいターミナル出力 |
| ストレージ | Markdown + YAML frontmatter | 人間可読、Git管理可能 |
| テスト | pytest | Python標準的テストフレームワーク |
