---
license: apache-2.0
base_model: 0bserverx/RVN-Qwen3.8-Flash-Next-Abliterated-Uncensored
datasets: []
language:
  - en
  - zh
pipeline_tag: text-generation
tags:
  - gguf
  - strata
  - abliterated
  - uncensored
  - moe
  - qwen
inference: false
---

# RVN-Qwen3.8-Flash-Next-Abliterated-Uncensored — Strata-ready (merged single-file GGUF + pack)

**English** | [繁體中文](#繁體中文)

A **Strata-ready** repackaging of [`0bserverx/RVN-Qwen3.8-Flash-Next-Abliterated-Uncensored-GGUF`](https://huggingface.co/0bserverx/RVN-Qwen3.8-Flash-Next-Abliterated-Uncensored-GGUF) (IQ3_S quant family):
1. **`RVN-Qwen3.8-Flash-Next-IQ3_S-merged.gguf`** — the original 8-shard *split* GGUF merged into a **single file** (83 GiB), ready to feed directly to a Strata native pack.
2. **`pack/`** — a **pre-built Strata pack** (from the same version of `iq_pack.py --compat-bf16` shipped in Strata 0.1.30). Point `--pack` at it and Strata reads the experts/PLE table straight from the merged GGUF — no merge step, no pack step, no calibration needed for a first run.

## Why this repo exists

The upstream RVN release ships as 8 shards, and some transformer layers' expert tensors are **split across shard boundaries**. [Strata](https://github.com/Niko1221/Strata)'s `tools/iq_pack.py` requires the gate/up/down expert tensors of each layer to live in the *same* file, so the upstream files fail to pack (`layer 1: its gate/up/down tensors are in different shards`). This repo provides the bit-identical merge so Strata users can use RVN out of the box.

## What was done (reproducibility)

| Step | Tool | Notes |
|---|---|---|
| Merge 8 shards → 1 GGUF | `llama-gguf-split --merge` (llama.cpp, Strata's vendored copy, commit `30ec18e`) | pure data relocation; weight bytes are **bit-identical** to upstream; `split.*` metadata removed; 1224 tensors |
| Build Strata pack | `Strata 0.1.30 tools/iq_pack.py --compat-bf16` | 484 small projections dequantized to BF16 (see caveat below); expert and PLE-table bytes unchanged |

Experts layout: gate/up = `IQ3_S`, down = `IQ4_NL` (both natively supported by Strata's MMQ kernels). PLE n-gram table = `IQ4_NL`, read directly from the merged GGUF.

## Files

```
RVN-Qwen3.8-Flash-Next-IQ3_S-merged.gguf   83 GiB  single-file GGUF (qwen4exp arch)
pack/index.txt          — tensor table (1079 tensors, 302 served natively)
pack/native_experts.txt — per-layer expert layout (v3, all tensors in the merged file)
pack/dense.bin          — 1.5 GiB BF16/F16 dense tensors (compat-bf16 applied)
pack/tokenizer/         — vocab/merges/chat template extracted from the GGUF
pack/compat-bf16.json   — the list of dequantized projection tensors
```

## Run it (Strata ≥ 0.1.30, ~64 GB RAM + ~32 GB VRAM class hardware)

1. Download **both** the merged GGUF and the whole `pack/` folder, keeping their relative paths.
2. Launch:
```sh
strata --serve \
  --pack   /path/to/pack \
  --native /path/to/RVN-Qwen3.8-Flash-Next-IQ3_S-merged.gguf \
  --ple-gguf /path/to/RVN-Qwen3.8-Flash-Next-IQ3_S-merged.gguf \
  --expert-profile /path/to/Strata/data/expert-profile.bin \
  --expert-cache auto --prefill auto --spec 4 \
  --max-context 262144 --kv int8 --kv-resident 32768
```
(`expert-profile.bin` is Strata's shipped generic profile — RVN weights are an abliteration of the base model, so routing is near-identical and no re-calibration is needed. `--mtp` is optional.)

3. To build the pack yourself instead: `iq_pack.py --gguf RVN-Qwen3.8-Flash-Next-IQ3_S-merged.gguf --out pack/ --compat-bf16`.

## Measured on RTX 5090 + i9-13900KF + 125 GB RAM

- Decode: **103–127 tok/s** (MTP spec-decode on, ~71% draft acceptance)
- Expert cache hit rate: ~95%; KV streaming ~99.6% VRAM hits @ 262K context
- Working set: ~50 GB experts in RAM + ~30 GB VRAM

## What "abliterated / uncensored" means here

Refusal-direction removal applied by [0bserverx](https://huggingface.co/0bserverx) (RVN), quant-matched: upstream reports only −0.49% perplexity vs base at Q6_K. **Abliteration removes safety refusals — the model will comply with harmful requests. You are responsible for what you generate.** License: Apache-2.0 (inherited from base Qwen3.8-Flash-Next, Apache-2.0).

### Known caveat (`--compat-bf16`)

Strata's engine reads small projections (hyper-connection, router, ssm, indexer, PLE-key) as BF16. Upstream RVN stores them quantized; `--compat-bf16` dequantizes those 484 tensors (1.4 GiB) with round-to-nearest-even. This is lossy *for those tensors only* (they are not reconstructed to original BF16), and it is exactly what the shipped `pack/dense.bin` contains. Experts and the PLE table are untouched.

## 繁體中文

這是 [`0bserverx/RVN-Qwen3.8-Flash-Next-Abliterated-Uncensored-GGUF`](https://huggingface.co/0bserverx/RVN-Qwen3.8-Flash-Next-Abliterated-Uncensored-GGUF)（IQ3_S 量化家族）的 **Strata 就緒版**重新打包：

1. **`RVN-Qwen3.8-Flash-Next-IQ3_S-merged.gguf`** — 原本 8 個 split shards 以 llama.cpp 官方 `llama-gguf-split --merge` 合併成**單一 GGUF**（83 GiB），權重 bit 級完全不變，只移除 `split.* metadata。
2. **`pack/`** — 已建好的 **Strata pack**（Strata 0.1.30 的 `iq_pack.py --compat-bf16` 產出）。直接 `--pack` 指過來即可啟動，省去 merge 與 pack 兩步驟。

**為什麼需要這個 repo**：RVN 原版的 8 shards 有數層的專家權重被切跨 shard 邊界，Strata 的 `iq_pack.py` 要求同一層 gate/up/down 必須在同一檔案內，原版直接打包會失敗（`layer 1: its gate/up/down tensors are in different shards`）。本 repo 提供 bit 級相同的合併檔解決此問題。

**格式**：專家 gate/up = IQ3_S、down = IQ4_NL、PLE n-gram 表 = IQ4_NL，全部是 Strata MMQ kernel 原生支援的格式。

**啟動**：下載 merged GGUF 與完整的 `pack/` 目錄（保持相對路徑），照上面「Run it」的指令啟動即可。`expert-profile.bin` 用 Strata 內建的通用版即可（RVN 是基座模型的 abliteration，路由分佈幾乎相同）。

**實測**（RTX 5090 + i9-13900KF + 125GB RAM）：decode **103–127 tok/s**（MTP 投機解碼接受率 ~71%）、expert cache hit ~95%、262K context 下 KV streaming 99.6% 命中 VRAM。記憶體需求：RAM ~50GB 專家 + VRAM ~30GB。

**名詞說明**：abliterated／uncensored = 移除拒答方向（由 0bserverx 製作，量化對照下僅 −0.49% perplexity）。**此模型不會拒絕有害請求，生成內容自負其責。**授權 Apache-2.0（繼承自 Qwen3.8-Flash-Next 基座）。

**已知取捨（--compat-bf16）**：Strata 引擎需以 BF16 讀取小投影張量（hyper-connection、router、ssm、indexer、PLE-key），RVN 原版把它們量化了；`--compat-bf16` 將這 484 個張量（1.4 GiB）反量化並round-to-nearest-even 成 BF16——僅這些張量有損耗（無法還原原始 BF16），專家權重與 PLE 表完全不動。`pack/dense.bin` 即為此處理後的產物。

## Credit

- Weights, abliteration, quantization: [0bserverx](https://huggingface.co/0bserverx)
- Base model: [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
- Engine: [Strata](https://github.com/Niko1221/Strata) (MoE CPU-GPU streaming, [Niko1221])
- Merge tooling: llama.cpp `gguf-split`
