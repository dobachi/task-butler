# Phase 2: AI統合機能の実装

## 概要

ロードマップ Phase 2 として、AI統合機能を実装します。タスク管理をよりスマートにするため、以下の3つの主要機能を追加します。

## 実装機能

### 1. タスク分析と優先順位付け (`tb analyze`)

タスクの内容、期限、依存関係、工数見積もりなどを分析し、AI による優先順位スコアと推奨理由を提供します。

**コマンド例：**
```bash
# 全タスクを分析
tb analyze

# 特定タスクを分析
tb analyze abc12345

# 分析結果をタスクに保存
tb analyze --save
```

**出力例：**
```
📊 タスク分析結果

1. [urgent] API認証の実装 (abc12345)
   スコア: 95/100
   理由: 期限が近く(2日後)、他の3タスクがブロックされています

2. [high] ドキュメント更新 (def67890)
   スコア: 75/100
   理由: 依存関係なし、すぐに着手可能
```

**分析要素：**
- 期限までの残り時間
- 依存タスク・被依存タスクの数
- 見積工数と利用可能時間
- プロジェクトの重要度
- タスクの滞留時間

### 2. スマート提案 (`tb recommend`)

現在の状況に基づいて、次に取り組むべきタスクを提案します。

**コマンド例：**
```bash
# 次のタスクを提案
tb recommend

# 利用可能時間を指定
tb recommend --hours 2

# エネルギーレベルを考慮
tb recommend --energy low

# 提案数を指定
tb recommend --count 5
```

**出力例：**
```
💡 おすすめタスク（2時間の作業時間）

1. メール返信 (30分) - 低エネルギーで完了可能
2. コードレビュー (1時間) - 依存タスクを解除できます
3. ドキュメント修正 (30分) - 期限が明日

合計見積: 2時間
```

**提案ロジック：**
- 利用可能時間内に収まるタスクの組み合わせ
- エネルギーレベルに適したタスク
- 依存関係の解除効果
- 期限の緊急度

### 3. 日次計画アシスタント (`tb plan`)

1日の作業計画を自動生成します。

**コマンド例：**
```bash
# 今日の計画を生成
tb plan

# 特定日の計画
tb plan --date 2025-02-01

# 作業時間を指定
tb plan --hours 6

# インタラクティブモード
tb plan --interactive
```

**出力例：**
```
📅 2025-02-01 の作業計画（8時間）

午前（4時間）:
  09:00-11:00 [high] API認証の実装 (2h)
  11:00-12:00 [medium] コードレビュー (1h)

午後（4時間）:
  13:00-15:00 [high] テスト作成 (2h)
  15:00-16:00 [low] ドキュメント更新 (1h)
  16:00-17:00 バッファ/予備時間

⚠️ 注意: 「デプロイ準備」は明日が期限です
```

## 技術的実装計画

### 新規ディレクトリ構成

```
src/task_butler/
├── ai/
│   ├── __init__.py
│   ├── base.py           # AIプロバイダー抽象クラス
│   ├── analyzer.py       # タスク分析エンジン
│   ├── recommender.py    # スマート提案エンジン
│   ├── planner.py        # 日次計画アシスタント
│   └── providers/
│       ├── __init__.py
│       ├── local.py      # ルールベース（デフォルト）
│       └── openai.py     # OpenAI API（オプション）
├── cli/commands/
│   ├── analyze.py        # 新規
│   ├── recommend.py      # 新規
│   └── plan.py           # 新規
```

### 依存関係の追加（pyproject.toml）

```toml
[project.optional-dependencies]
ai = [
    "openai>=1.0.0",      # OpenAI API（オプション）
]
```

### 設定の追加（config.toml）

```toml
[ai]
enabled = true
provider = "local"        # "local" or "openai"
openai_model = "gpt-4o-mini"

[ai.analysis]
weight_deadline = 0.3     # 期限の重み
weight_dependencies = 0.25 # 依存関係の重み
weight_effort = 0.2       # 工数の重み
weight_staleness = 0.15   # 滞留時間の重み
weight_priority = 0.1     # 優先度の重み

[ai.planning]
default_hours = 8         # デフォルト作業時間
buffer_ratio = 0.1        # バッファ時間の割合
morning_hours = 4         # 午前の時間
```

### タスクモデルの拡張

```python
class Task(BaseModel):
    # 既存フィールド...

    # AI関連フィールド（新規）
    ai_score: float | None = None           # AI優先度スコア (0-100)
    ai_reasoning: str | None = None         # AIの推論理由
    ai_last_analyzed: datetime | None = None # 最終分析日時
    energy_level: str | None = None         # 必要エネルギー (low/medium/high)
```

## 実装フェーズ

### Phase 2.1: 基盤構築
- [ ] `ai/` ディレクトリ構造の作成
- [ ] AIプロバイダー抽象クラスの実装
- [ ] ローカル（ルールベース）プロバイダーの実装
- [ ] 設定ファイルへのAIセクション追加

### Phase 2.2: タスク分析
- [ ] `ai/analyzer.py` の実装
- [ ] `cli/commands/analyze.py` の実装
- [ ] タスクモデルへのAIフィールド追加
- [ ] テストの追加

### Phase 2.3: スマート提案
- [ ] `ai/recommender.py` の実装
- [ ] `cli/commands/recommend.py` の実装
- [ ] テストの追加

### Phase 2.4: 日次計画
- [ ] `ai/planner.py` の実装
- [ ] `cli/commands/plan.py` の実装
- [ ] インタラクティブモードの実装
- [ ] テストの追加

### Phase 2.5: OpenAI統合（オプション）
- [ ] `ai/providers/openai.py` の実装
- [ ] APIキー管理の実装
- [ ] ドキュメントの追加

## 受け入れ基準

- [ ] `tb analyze` コマンドが動作する
- [ ] `tb recommend` コマンドが動作する
- [ ] `tb plan` コマンドが動作する
- [ ] ローカル（ルールベース）モードがデフォルトで動作する
- [ ] OpenAI統合がオプションで利用可能
- [ ] 既存機能に影響を与えない
- [ ] テストカバレッジ80%以上
- [ ] ドキュメントの更新

## 関連情報

- ロードマップ: README.md の Phase 2
- 既存CLI実装: `src/task_butler/cli/`
- 既存モデル: `src/task_butler/models/task.py`
