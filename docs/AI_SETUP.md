# AI機能セットアップガイド

ローカルLLM（llama-cpp-python）をGPUで使用するためのセットアップ手順です。

## 目次

1. [前提条件](#前提条件)
2. [CUDA Toolkit インストール（WSL2）](#cuda-toolkit-インストールwsl2)
3. [llama-cpp-python インストール](#llama-cpp-python-インストール)
4. [設定ファイル](#設定ファイル)
5. [モデルダウンロード](#モデルダウンロード)
6. [動作確認](#動作確認)
7. [利用可能なモデル](#利用可能なモデル)
8. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

- **Python 3.12**（`.python-version`で強制）
- **NVIDIA GPU**（CUDA対応）
- **WSL2環境の場合**: Windows側にNVIDIA GPUドライバがインストールされていること

> **注意**: Python 3.13ではCUDA版llama-cpp-pythonのホイールが利用できない場合があります。Python 3.12の使用を推奨します。

---

## CUDA Toolkit インストール（WSL2）

WSL2環境でCUDA Toolkitをインストールする手順です。

### 1. CUDAリポジトリの追加

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
```

### 2. CUDA Toolkitのインストール

```bash
sudo apt-get install cuda-toolkit-12-6
```

### 3. 環境変数の設定

`~/.bashrc` または `~/.zshrc` に以下を追加：

```bash
export PATH=/usr/local/cuda-12.6/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:$LD_LIBRARY_PATH
```

設定を反映：

```bash
source ~/.bashrc  # または source ~/.zshrc
```

### 4. インストール確認

```bash
nvcc --version
nvidia-smi
```

---

## llama-cpp-python インストール

### CPU版（デフォルト）

CPU版はシンプルにインストールできます：

```bash
uv sync --extra llm
```

### GPU/CUDA版

GPU対応版は事前ビルド済みホイールを使用します：

```bash
uv pip install llama-cpp-python \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124 \
  --force-reinstall
```

> **注意**: `--force-reinstall` はCPU版がすでにインストールされている場合に必要です。

---

## 設定ファイル

設定ファイル `~/.task-butler/config.toml` を作成・編集します：

```toml
[ai]
provider = "llama"
language = "ja"

[ai.llama]
model_name = "elyza-7b"
n_ctx = 2048
n_gpu_layers = 99  # 全レイヤーをGPUへ
```

### 設定項目の説明

| 項目 | 説明 | 推奨値 |
|------|------|--------|
| `provider` | AIプロバイダー | `"llama"` |
| `language` | 言語設定 | `"ja"` または `"en"` |
| `model_name` | 使用するモデル名 | `"elyza-7b"` |
| `n_ctx` | コンテキスト長 | `2048` |
| `n_gpu_layers` | GPUにオフロードするレイヤー数 | `99`（全レイヤー） |

---

## モデルダウンロード

利用可能なモデルをダウンロードします：

```bash
tb ai download elyza-7b
```

モデルは `~/.task-butler/models/` に保存されます。

---

## 動作確認

### AI分析の実行

```bash
tb analyze -n 1
```

出力を確認：
- **🤖 マーク**: LLMによる分析が動作しています
- **📋 マーク**: ルールベースのフォールバックが使用されています

### GPU使用状況の確認

```bash
nvidia-smi
```

`llama-cpp-python` または関連プロセスがGPUメモリを使用していることを確認してください。

---

## 利用可能なモデル

| モデル名 | サイズ | 特徴 | 用途 |
|----------|--------|------|------|
| `tinyllama-1.1b` | 約1GB | 軽量・高速 | テスト・低リソース環境 |
| `elyza-7b` | 約4GB | 日本語対応 | **推奨**：日本語タスク |

モデル一覧の確認：

```bash
tb ai models
```

---

## トラブルシューティング

### `libcudart.so.12 not found` エラー

**原因**: CUDA Toolkitがインストールされていない、または環境変数が設定されていません。

**解決策**:
1. CUDA Toolkitをインストール（上記手順参照）
2. 環境変数が正しく設定されているか確認：
   ```bash
   echo $LD_LIBRARY_PATH
   # /usr/local/cuda-12.6/lib64 が含まれていること
   ```

### Python 3.13でCUDA版が動作しない

**原因**: Python 3.13用のCUDA対応ホイールがまだ提供されていません。

**解決策**: Python 3.12を使用してください。
```bash
# pyenvを使用している場合
pyenv install 3.12.0
pyenv local 3.12.0
```

### GPU使用率が0%のまま

**原因**: `n_gpu_layers` が設定されていない、または0になっています。

**解決策**: 設定ファイルで `n_gpu_layers = 99` を設定してください。

### モデルのロードが遅い

**原因**: 初回ロード時はモデルファイルをGPUメモリに転送するため時間がかかります。

**解決策**: 2回目以降のロードは高速化されます。大きなモデルを使用している場合は、より小さいモデル（tinyllama-1.1b）の使用を検討してください。

---

## 関連リンク

- [llama-cpp-python GitHub](https://github.com/abetlen/llama-cpp-python)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
- [ELYZA Japanese LLM](https://huggingface.co/elyza)
