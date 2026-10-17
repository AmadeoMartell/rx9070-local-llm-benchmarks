# Configs

Everything here ran on one box: **AMD RX 9070 16 GB (gfx1201, RDNA4) + Ryzen 7 7800X3D + 32 GB DDR5**, Ubuntu 24.04.5,
kernel 7.0 HWE, ROCm 7.2.4 (inbox amdgpu driver). Paths are shortened to `~/...`; API keys removed.

| File | What |
|---|---|
| [strata-gyro-s-262k-vision.json](strata-gyro-s-262k-vision.json) | Strata rc2 server config: Gyro-S (TQ1_0), 262K context, KV `k8v4`, MTP, resident experts, CPU vision |
| [strata-gyro-m-131k-vision.json](strata-gyro-m-131k-vision.json) | Same for Gyro-M (TQ2_0), 131K context |
| [llama-server-qwen27b.sh](llama-server-qwen27b.sh) | The dense baseline: Qwen3.8-27B UD-IQ4_XS on llama.cpp (HIP), 131K, q4_0 KV |
| [qwen3.8-chat-template.jinja](qwen3.8-chat-template.jinja) | Chat template used with llama.cpp (Qwen3.8 template with `reasoning_effort` low / medium / xhigh) |
| [run-strata-systemd.sh](run-strata-systemd.sh) | How the Strata server is started: systemd transient unit with a 29 GB memory cap and swap disabled |
| [build-strata-vision.sh](build-strata-vision.sh) | Building the CPU image encoder (`strata-vision`) against agentionai's llama.cpp |

Notes on the Strata configs:
- Engine: the **agentionai fork of Strata, branch `rc2`** (commit `9ff02c9`, = Strata 0.1.40.3 + the Gyro trellis types),
  built for HIP gfx1201. Models: [agentionai/Qwen3.8-Flash-Next-Gyro-GGUF](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-GGUF)
  (revision `1ada0842`). Packs built with `tools/iq_pack.py --gguf <file> --out packs/gyro-s --compat-bf16` (no `experts.bin`);
  `build/native_expert_parity --load-check` must end with `0 failures`.
- `"sampling"` in the config is only a default: the request's own values win. Our agent client sends none, so these apply.
- `reasoning_budget_tokens`: 16384 for medium effort, 24576 for xhigh (the client's `max_tokens` is 24576 / 32768, so ~8K
  always stays for the answer).
- The vision block points `"model"` at the Gyro-S GGUF even for Gyro-M on purpose: the encoder opens it vocab-only and both
  files share the vocabulary.
- `--vision` must be in the engine `args` as well as the `"vision"` block — without it the server accepts images and the
  engine refuses them (`this engine was started without --vision`).
