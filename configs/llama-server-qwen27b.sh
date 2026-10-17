#!/usr/bin/env bash
# Dense baseline used as "prod" in these tests: Qwen3.8-27B UD-IQ4_XS on llama.cpp (HIP, RX 9070), 131K context, q4_0 KV,
# ngram speculative decoding, mmproj (vision) on the CPU. Run as a systemd service with MemorySwapMax=0.
# Runtime: the "rdna-boosts" llama.cpp fork, release r28 (an upstream build also works; numbers in the README are r28).
M=~/models/qwen-ud-iq4xs
export HIP_VISIBLE_DEVICES=0                      # hide the iGPU (gfx1036)
export GGML_CUDA_SLAB=0 GGML_COMPUTE_BUFFER_CHUNK_MIB=0 GGML_CUDA_FA_STAGE_MAX_MB=1   # rdna-boosts specifics (SLAB=0: else prefill ~2x slower)
export LLAMA_ARG_MMPROJ=$M/mmproj-F16.gguf LLAMA_ARG_MMPROJ_OFFLOAD=0                # vision encoder on the CPU
exec ~/llama/r28/llama-server --model $M/Qwen3.8-27B-UD-IQ4_XS.gguf --alias qwen-ud-iq4xs \
  --device ROCm0 --split-mode none --ctx-size 131072 --threads 8 --threads-batch 16 \
  --batch-size 512 --ubatch-size 256 --n-gpu-layers all --fit off --load-mode none --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 --parallel 1 \
  --reasoning on --reasoning-effort xhigh --reasoning-format deepseek --reasoning-preserve \
  --jinja --chat-template-file ./qwen3.8-chat-template.jinja \
  --spec-type ngram-mod --spec-ngram-mod-n-min 16 --spec-ngram-mod-n-max 32 \
  --host 127.0.0.1 --port 8081 --api-key-file ~/.config/llama/api-keys.txt --metrics
