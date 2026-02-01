# AI Feature Setup Guide

Setup instructions for using local LLM (llama-cpp-python) with GPU acceleration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [CUDA Toolkit Installation (WSL2)](#cuda-toolkit-installation-wsl2)
3. [llama-cpp-python Installation](#llama-cpp-python-installation)
4. [Configuration File](#configuration-file)
5. [Model Download](#model-download)
6. [Verification](#verification)
7. [Available Models](#available-models)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.12** (enforced by `.python-version`)
- **NVIDIA GPU** (CUDA compatible)
- **For WSL2**: NVIDIA GPU driver must be installed on Windows side

> **Note**: CUDA-enabled llama-cpp-python wheels may not be available for Python 3.13. Python 3.12 is recommended.

---

## CUDA Toolkit Installation (WSL2)

Instructions for installing CUDA Toolkit in WSL2 environment.

### 1. Add CUDA Repository

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
```

### 2. Install CUDA Toolkit

```bash
sudo apt-get install cuda-toolkit-12-6
```

### 3. Set Environment Variables

Add the following to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH=/usr/local/cuda-12.6/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:$LD_LIBRARY_PATH
```

Apply the changes:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### 4. Verify Installation

```bash
nvcc --version
nvidia-smi
```

---

## llama-cpp-python Installation

### CPU Version (Default)

The CPU version can be installed simply:

```bash
uv sync --extra llm
```

### GPU/CUDA Version

Use pre-built wheels for GPU support:

```bash
uv pip install llama-cpp-python \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124 \
  --force-reinstall
```

> **Note**: `--force-reinstall` is required if CPU version is already installed.

---

## Configuration File

Create/edit the configuration file at `~/.task-butler/config.toml`:

```toml
[ai]
provider = "llama"
language = "ja"

[ai.llama]
model_name = "elyza-7b"
n_ctx = 2048
n_gpu_layers = 99  # Offload all layers to GPU
```

### Configuration Options

| Option | Description | Recommended Value |
|--------|-------------|-------------------|
| `provider` | AI provider | `"llama"` |
| `language` | Language setting | `"ja"` or `"en"` |
| `model_name` | Model to use | `"elyza-7b"` |
| `n_ctx` | Context length | `2048` |
| `n_gpu_layers` | Number of layers to offload to GPU | `99` (all layers) |

---

## Model Download

Download available models:

```bash
tb ai download elyza-7b
```

Models are saved to `~/.task-butler/models/`.

---

## Verification

### Run AI Analysis

```bash
tb analyze -n 1
```

Check the output:
- **🤖 mark**: LLM analysis is working
- **📋 mark**: Rule-based fallback is being used

### Check GPU Usage

```bash
nvidia-smi
```

Verify that `llama-cpp-python` or related processes are using GPU memory.

---

## Available Models

| Model Name | Size | Features | Use Case |
|------------|------|----------|----------|
| `tinyllama-1.1b` | ~1GB | Lightweight, fast | Testing, low-resource environments |
| `elyza-7b` | ~4GB | Japanese support | **Recommended**: Japanese tasks |

List available models:

```bash
tb ai models
```

---

## Troubleshooting

### `libcudart.so.12 not found` Error

**Cause**: CUDA Toolkit is not installed or environment variables are not set.

**Solution**:
1. Install CUDA Toolkit (see instructions above)
2. Verify environment variables are set correctly:
   ```bash
   echo $LD_LIBRARY_PATH
   # Should include /usr/local/cuda-12.6/lib64
   ```

### CUDA Version Not Working with Python 3.13

**Cause**: CUDA-enabled wheels are not yet available for Python 3.13.

**Solution**: Use Python 3.12.
```bash
# If using pyenv
pyenv install 3.12.0
pyenv local 3.12.0
```

### GPU Utilization Stays at 0%

**Cause**: `n_gpu_layers` is not set or set to 0.

**Solution**: Set `n_gpu_layers = 99` in the configuration file.

### Model Loading is Slow

**Cause**: First load takes time to transfer model files to GPU memory.

**Solution**: Subsequent loads will be faster. If using a large model, consider using a smaller one (tinyllama-1.1b).

---

## Related Links

- [llama-cpp-python GitHub](https://github.com/abetlen/llama-cpp-python)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
- [ELYZA Japanese LLM](https://huggingface.co/elyza)
