# RX 9070 16 GB + 32 GB RAM: local LLMs for coding agents

RX 9070 16 GB (gfx1201) · Ryzen 7 7800X3D · 32 GB DDR5 · NVMe Gen4.
Linux: Ubuntu 24.04.5, kernel 7.0, ROCm 7.2.4. Earlier: Windows 11. Aug–Oct 2026.

## Key findings

```text
Gyro-S (Qwen3.8-Flash-Next 125B MoE), Strata rc2, Linux
  prefill 1145 / decode 61 t/s at 104K; ~1076 / ~62 at ~226K (262K ctx + vision)
  agent turn at 104K: +2K read at 634 t/s, decode 60.5
  Java agent task: 5 of 5 runs done, 21-48 min

Qwen3.8-27B UD-IQ4_XS, llama.cpp r28
  prefill 540 / decode 25 t/s at 127K; agent turn at 130K: 345 / 23.5
  Java task 49 min, the repeat failed
  lowest KLD of the 27B quants measured (0.086 en, 0.023 code)

Gyro-S, Strata 0.2.1 vs rc2 (Oct 21)
  decode +16%, agent-turn prefill ~2x; same quality (KL 0.018, perplexity within noise, blind review 4 vs 4 runs)
  KV int8 + --kv-resident 32768 instead of k8v4: prefill 1817 / 2229 t/s at 4K / 16K (k8v4: 1357 / 1492),
  2046-2077 t/s at 100-210K (k8v4: ~1410), recall 12/12 up to 210K, still 262K ctx; Java task on it: done in 29 min, review within noise, now our Gyro-S config
  Gyro-S on this config is our always-on server since Oct 22 (replaced Qwen 27B)

Gyro-S abliterated (Huihui), same engine and settings (Oct 22)
  equal to stock Gyro-S on every check: questions 14/14, long answers 0 of 8 degenerate, recall 12/12 at 183K and 210K,
  same speed; Java task (medium) done in 21 min, review 41 vs 38 for stock in the same batch (within noise)

Gyro-M tuned for 16 + 32 GB (Oct 24-26), Strata main + one-line HIP patch, 196K int8 KV
  decode 76 t/s short / 58 at 180K / 66-67 in Java agent runs (was 56-58 / - / 52-57); 196K ctx (was 131K)
  0 expert reads from the SSD (13 GB per fresh 32K prompt with --prefill 4096), PSI 0, >= 1.7 GiB RAM headroom
  Java task xhigh: 2 of 2 done in 27 / 25 min; blind review above Gyro-S in both batches (+2..+4 /60)
  fresh prompts still ~1.7x slower than Gyro-S (twice the expert bytes): 1100-1150 vs 1900-2000 t/s

Gyro-M     1014 / 50 at 106K; review scores within noise of Gyro-S; ~2.4 GiB RAM headroom on 32 GB (Strata rc2, before the tuning)
MTP2       Qwen 27B decode 55 vs 31 t/s (Java run medians), but ctx drops from 131K to 81-88K
Vulkan     llama.cpp, Qwen 27B: HIP is 13-41% faster on prefill at about equal decode
SSD        Strata on Windows paged experts out: 70-110 GB/h of writes; Linux + cgroup without swap: ~0
```

Speeds in t/s. `depth` = prompt tokens at the measurement, cold prompt unless noted.
`~` = average over several runs or turns (midpoint of the measured range).

| Engine | Used for |
|---|---|
| llama.cpp [rdna-boosts](https://github.com/stew675/llama-cpp-rdna-boosts) r27/r28 (HIP), v16 on Windows | dense Qwen3.8-27B quants, Gemma 4, Ornith |
| [agentionai/Strata](https://github.com/agentionai/Strata) `rc2` (HIP, resident experts) | [Gyro-S / Gyro-M](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-GGUF) (Qwen3.8-Flash-Next 125B MoE) |
| [Niko1221/Strata](https://github.com/Niko1221/Strata) 0.2.0-beta / 0.2.1.3 (engines 0.1.45 / 0.1.46, HIP) | Gyro-S / Gyro-M since Oct 20: own build against the agentionai ggml fork (GYRO.md §1) and the release engine, see [Strata 0.2.1](#strata-021-oct-2026) |
| [Niko1221/Strata](https://github.com/Niko1221/Strata) main `7dd5cf18` (0.2.4.2) + [one-line patch](configs/strata-hip-tq-sub8.patch), built with `-DSTRATA_PREFILL_MMQ=ON` | Gyro-M since Oct 25, see [Gyro-M on 16 + 32 GB](#gyro-m-on-16--32-gb-tuning-oct-2426) |
| Strata 0.1.38–0.1.44 (HIP) | [ISTA-DASLab Flash-Next GSQ-RCO](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF): Coder "IQ1_M" (256 of 512 experts, 3.63 bpw avg), Q2_0 (all experts) |

## Linux, ROCm 7.2.4 (Oct 2026)

### depth ~32K

| Model | Engine | ctx | KV | prefill t/s | decode t/s |
|---|---|---|---|---|---|
| Flash-Next Gyro-S TQ1_0 | Strata rc2, MTP4 | 131K | k8v4 | 1318 | 65.4 |
| Flash-Next Gyro-S TQ1_0 + vision | Strata rc2, MTP4 | 131K | k8v4 | 1199 | 59.4 |
| Flash-Next Gyro-S TQ1_0 + vision | Strata rc2, MTP4 | 196K | k8v4 | 1217 | 59.2 |
| Flash-Next Gyro-S TQ1_0 + vision | Strata rc2, MTP4 | 262K | k8v4 | 1174 | 58.7 |
| Flash-Next Gyro-M TQ2_0 | Strata rc2, MTP4 | 65K | k8v4 | 1234 | 54.4 |
| Flash-Next Gyro-M TQ2_0 | Strata rc2, MTP4 | 98K | k8v4 | 1238 | 50.1 |
| Flash-Next Gyro-M TQ2_0 | Strata rc2, MTP4 | 131K | k8v4 | 807 | 53.1 |
| Qwen3.8-27B UD-IQ4_XS | r28, ngram | 106K | q4_0 | 854 | 32.4 |
| Qwen3.8-27B UD-IQ4_XS | r28, MTP2 | 81K | q4_0 | 915 | 59.1 |
| Qwen3.8-27B UD-IQ4_XS | llama-bench d32K, HIP | — | q4_0 | 765 | 30.1 |
| Qwen3.8-27B-pi Q3_K_M | r28, ngram | 131K | q4_0 | 835 | 33.2 |
| Swift-1.5 Qwen3.8-27B Q3_K_L | r28, ngram | 131K | q4_0 | 720 | 30.7 |

llama-bench pp2048 / tg128, Qwen3.8-27B UD-IQ4_XS, HIP: prefill 1183, decode 33.5. Vulkan: see [Vulkan vs HIP](#vulkan-vs-hip).

### depth ~50–85K

| Model | Engine | ctx | KV | depth | prefill t/s | decode t/s |
|---|---|---|---|---|---|---|
| Qwen3.8-27B UD-IQ4_XS | r28, ngram | 131K | q4_0 | 58.6K | 728 | 28.7 |
| Qwen3.8-27B UD-IQ4_XS | r28, MTP2 | 81K | q4_0 | 52K | 800 | 50.8 |
| Qwen3.8-27B heretic-ara IQ4_XS + GPU vision | r28 | 106K | q4_0 | 81K | 724 | 28.5 |
| Flash-Next Coder IQ1_M | Strata 0.1.44, resident | 131K | k8v4 | 64K | ~1476 | ~72 |
| Flash-Next Q2_0 | Strata, mmap | — | — | 64K | 386 | 65 |

### depth ~90–130K

| Model | Engine | ctx | KV | depth | prefill t/s | decode t/s |
|---|---|---|---|---|---|---|
| Gyro-S TQ1_0 | Strata rc2, MTP4 | 131K | k8v4 | 104K | 1145 | 61.0 |
| Gyro-S TQ1_0 + vision | Strata rc2, MTP4 | 131K | k8v4 | 90–116K | 1088 | 62.0 |
| Gyro-S TQ1_0 + vision | Strata rc2, MTP4 | 196K | k8v4 | 90–116K | 1202 | 54.5 |
| Gyro-S TQ1_0 + vision | Strata rc2, MTP4 | 262K | k8v4 | 90–116K | 1080 | 53.0 |
| Gyro-M TQ2_0 | Strata rc2, MTP4 | 131K | k8v4 | 106K | 1014 | 50.1 |
| Flash-Next Coder IQ1_M | Strata 0.1.44, resident | 131K | k8v4 | 100K | ~1441 | — |
| Qwen3.8-27B UD-IQ4_XS | r28, ngram | 131K | q4_0 | 127K | 540 | 25.2 |
| Qwen3.8-27B heretic-ara IQ4_XS + CPU vision | r28 | 131K | q4_0 | 98K | 666 | 27.5 |
| Qwen3.8-27B-pi Q3_K_M | r28, ngram | 131K | q4_0 | 110K | 563 | 25.6 |
| Swift-1.5 Q3_K_L | r28, ngram | 131K | q4_0 | 121K | 494 | 24.4 |

### depth 145K+

| Model | Engine | ctx | KV | depth | prefill t/s | decode t/s |
|---|---|---|---|---|---|---|
| Gyro-S TQ1_0 + vision | Strata rc2, MTP4 | 196K | k8v4 | 147K | 1166 | 55.0 |
| Gyro-S TQ1_0 | Strata rc2, MTP4 | 262K | k8v4 | 205K | 1076 | 55.0 |
| Gyro-S TQ1_0 + vision | Strata rc2, MTP4 | 262K | k8v4 | ~226K | ~1076 | ~62.5 |
| Flash-Next Coder IQ1_M | Strata 0.1.44, resident | 262K | k8v4 | 208K | 1230 | 51 |

### Agent turn: +2–4K tokens appended to a cached conversation

| Model | ctx | cached depth | prefill t/s | decode t/s |
|---|---|---|---|---|
| Gyro-S TQ1_0 | 131K | 32K | 950 | 68.7 |
| Gyro-S TQ1_0 | 131K | 104K | 634 | 60.5 |
| Gyro-S TQ1_0 + vision | 131K | 90–116K | 655 | 59.3 |
| Gyro-S TQ1_0 + vision | 196K | 90–116K | 542 | 58.3 |
| Gyro-S TQ1_0 + vision | 262K | 90–116K | 566 | 56.3 |
| Gyro-S TQ1_0 | 262K | 205K | 533 | 52.9 |
| Gyro-M TQ2_0 | 131K | 32K | 580 | 50.1 |
| Gyro-M TQ2_0 | 131K | 106K | 474 | 45.4 |
| Qwen3.8-27B UD-IQ4_XS, ngram | 131K | 30K | 755 | 36.6 |
| Qwen3.8-27B UD-IQ4_XS, ngram | 131K | 54K | 604 | 38.9 |
| Qwen3.8-27B UD-IQ4_XS, ngram | 131K | 130K | 345 | 23.5 |
| Qwen3.8-27B UD-IQ4_XS, MTP2 | 81K | 30K | 674 | 55.9 |
| Qwen3.8-27B UD-IQ4_XS, MTP2 | 81K | 54K | 555 | 55.1 |

### `-ub` sweep, Qwen3.8-27B UD-IQ4_XS, r28, ctx 131K, prefill t/s (decode unchanged)

| depth | ub128 | ub256 | ub512 | ub1024 |
|---|---|---|---|---|
| 52–61K | 740 | 836 | 810 | 811 |
| 112–124K | 569 | 587 | 592 | 633 |

### Memory and SSD (Strata in a systemd unit, `MemoryMax=29G`, `MemorySwapMax=0`)

| Model | RAM (anon), max | headroom, min | PSI full max | SSD writes / agent run | SSD reads / agent run |
|---|---|---|---|---|---|
| Gyro-S, 131K | 21.9–22.0 GiB | 7.0–7.1 GiB | 0.3% | < 1 MB | ~3 GB |
| Gyro-S, 262K + vision | 24.4–24.5 GiB | 4.5–4.6 GiB | — | < 1 MB | ~4 GB |
| Gyro-M, 131K | 26.5–26.7 GiB | 2.4–2.5 GiB | 11% (17–27% in mode sweeps) | ~50 MB (logs) | ~78 GB |
| Gyro-M finalist, 196K int8 (Oct 25) | 26.9–27.2 GiB | 1.84 GiB | 0 | 42–54 MB (logs) | ~4 GB (n-gram table only) |

Experts on GPU at 131K: Gyro-S 8456, Gyro-M 5941. k8v4 = int8 on the 100K recall test (12/12 both).
Gyro-S MTP4 on vs off: decode ~59 vs ~47 t/s; prefill of ~3K additions 697 vs 980 t/s.

Gyro-M expert placement, ctx 131K, depth 32K:

| Mode | prefill t/s | decode t/s |
|---|---|---|
| resident (all non-GPU experts locked in RAM) | 807 | 53.1 |
| `--resident-budget-gib 18` | 735 | 47.1 |
| `--mmap-experts` | 768 | 28.1 |

Gyro-M resident, fresh 32K prompt, by ctx (PSI and reads measured over the whole bench):

| ctx | experts on GPU | prefill t/s | decode t/s | PSI full max | SSD reads |
|---|---|---|---|---|---|
| 65K | 6582 | 1234 | 54.4 | 16.7% | 7.7 GB |
| 98K | 6263 | 1238 | 50.1 | 26.6% | 10.5 GB |
| 131K | 5941 | 807 | 53.1 | 21.7% | 51.7 GB |

The pressure comes from the 23.3 GiB of experts locked in RAM, so a smaller ctx does not remove it. Repeat on the
working server (131K + vision): fresh 28K prefill 599 t/s, decode 42.9; fresh 117K 947 / 47.5; 100.9 GB read from
the SSD in ~3.5 min, PSI full above 1% in 97 of 101 samples (max 14.7%). No OOM in any run.

Real Gyro-M sessions, PSI full sampled every 15 s:

| Session | samples | > 1% | > 5% | > 10% | mean | max |
|---|---|---|---|---|---|---|
| Java task via Pi, xhigh (37 min) | 152 | 9% | 4% | 1% | 0.4% | 11.9% |
| Java task via Pi, medium (53 min) | 214 | 7% | 3% | 0% | 0.3% | 9.4% |
| tool-eval-bench (short requests, 70 min) | 279 | 0% | 0% | 0% | 0.0% | 1.0% |
| KCORES via Pi with vision, medium | 47 | 6% | 2% | 2% | 0.4% | 11.8% |
| KCORES via Pi with vision, xhigh | 92 | 9% | 3% | 1% | 0.5% | 11.2% |

So in agent work the pressure shows up in short bursts, ~6–9% of the time; min headroom 2.35 GiB. Gyro-M is ~1.3–1.5× slower than Gyro-S: ~16 s vs ~11 s per turn (+3K in, ~500 out), ~47 s vs ~21 s for a fresh 30K prompt.

**Why SSD writes are tracked.** Strata 0.1.38 + Flash-Next Coder IQ1_M on Windows was dropped because of them
(it also looped in long answers). Windows paged the experts out to the pagefile: +81 GB host writes in ~35 min in
resident mode (pagefile 13.3 → 19.5 GB), +26.4 GB in 22 min of agent work with `--mmap-experts`, +29.1 GB in ~16 min
after tuning (ctx 106K, k8v4, prompt cache 1) — 70–110 GB/h, against ~0.5 GB/h for llama.cpp with Qwen 27B.
On Linux, in a cgroup with `MemorySwapMax=0`, the same engine writes ~0: reads replace writes.

**How memory, PSI and SSD were measured.** The server runs as its own systemd unit, so its cgroup holds only the
model server. Sampled every 15 s in agent runs and every 2 s in benches:
- RAM: `memory.stat` `anon` and `file`, `memory.peak`; OOM: `memory.events` `oom_kill`; headroom = `MemoryMax` (29 GiB = 29696 MiB) − anon; kernel memory of the cgroup (~0.16 GiB: page tables, slab) also counts
  against the limit, so the real distance to OOM is ~0.15 GiB smaller than the table shows; ranges are over 3–7 agent runs per config;
- PSI: `/proc/pressure/memory`, the `full avg10` value (share of the last 10 s when all non-idle tasks were stalled
  on memory); the tables give its max and the share of samples above a threshold;
- SSD: `io.stat` of the server cgroup (`rbytes`, `wbytes`) for the server's own reads and writes, `/proc/diskstats`
  for the whole drive, `/proc/vmstat` `pswpout` for swap; drive wear from `smartctl -a -d nvme` (Data Units Written);
- Windows: SMART host writes before and after a run, plus pagefile size.

## Strata 0.2.1 (Oct 2026)

Gyro-S TQ1_0 unless noted, same model files and MTP head as with rc2, 262K + vision, `--prompt-cache-spread`.

### 0.2.1 vs 0.2.0 vs rc2

| | rc2 | 0.2.0-beta | 0.2.1.3 |
|---|---|---|---|
| fresh 26K prompt, t/s (fresh starts) | — | 1100–1109 in 5 of 6 starts, 1408 in 1 | 1405–1410 in 6 of 6 |
| +1.7K turn on that prompt, t/s | — | 515–524 (slow starts) | 842–872 |
| Java runs via Pi, xhigh: decode t/s | 54–59 | 65–66 | 65–66 |
| same runs: agent-turn prefill (0.5–8K appends), t/s | 300–400 | 450–580 | 600–700 |

0.2.0's "slow starts" are the RX 9000 GPU-queue placement that 0.2.1 fixes (Strata docs/AMD_HIP.md, "Fast and slow starts"):
confirmed here on an RX 9070 (non-XT). 0.2.0 and 0.2.1 built against the agentionai ggml fork give bit-identical greedy
output (10 of 10 prompts); the 0.2.1 release engine (`strata-engine-0.1.46-linux-x86_64-hip-rx9070`) reads prompts at the
same speed, decode-path logits are bit-identical to our build, its batched-prompt logits differ slightly (below).

Quality, teacher-forced on Strata's `tools/quant_quality.py` set (5 × 999 positions: code, docs, English, other languages,
an agent transcript; no Q8_0 reference fits in 32 GB, so engines are compared with each other):

| | top-1 agreement | mean KL | perplexity |
|---|---|---|---|
| 0.2.1 own build vs its own repeat (noise floor) | 100% | 0 | 4.457 / 4.457 |
| 0.2.1 release engine vs own build, decode path | 100% | 0 | 4.457 / 4.457 |
| 0.2.1 release engine vs own build, prompt path (20 prompts) | 19 of 20 | 0.007 (CPU experts), 0.019 (GPU) | — |
| rc2 vs 0.2.1, decode path | 95.6% | 0.018 (p99 0.25) | 4.434 vs 4.457 |

rc2 vs 0.2.1: the paired bootstrap 95% interval of the mean log-probability difference, [−0.013, +0.003], includes zero.
Per segment: −0.9% to +0.4% perplexity, except the agent transcript (+2.9% for 0.2.1, one segment).
Blind review of the Java task (Pi, xhigh, 4 runs per engine, same batch): 0.2.x 35.9 ± 4.3, rc2 37.6 ± 1.0 /60.
Strata's docs/GYRO.md says gfx1201 gave "identical output to rc2"; here greedy answers of 0.2.x and rc2 matched in 1 of 10.

### KV type and `--kv-resident` (0.2.1 release engine)

Fresh engine per row, our settings (reasoning budget 24576), only the KV type, ctx and `--kv-resident` change.
Strata's standard prompts (thinking on, xhigh), medians of 3; 100K = one ~90K-token needle prompt.

| Model | ctx | KV | `--kv-resident` | experts on GPU | prefill 4K / 16K | decode 4K / 16K | prefill / decode at 100K | recall @100K |
|---|---|---|---|---|---|---|---|---|
| Gyro-S | 262K | k8v4 | — | 7195 | 1357 / 1492 | 62.9 / 63.1 | 1412 / 73.8 | 12/12 |
| Gyro-S | 131K | int8 | — | 8434 | 1820 / 2232 | 70.0 / 66.7 | 2095 / 82.5 | 12/12 |
| Gyro-S | 131K | k8v4 | — | 8794 | 1371 / 1494 | 69.5 / 67.0 | 1408 / 78.8 | 12/12 |
| **Gyro-S** | **262K** | **int8** | **32768** | **9505** | **1817 / 2229** | **67.1 / 71.2** | **2077 / 79.5** | **12/12** |
| Gyro-S | 262K | k8v4 | 32768 | 9595 | 1370 / 1471 | 68.5 / 62.4 | 1402 / 79.9 | 12/12 |
| Gyro-M | 131K | k8v4 | — | 6218 | 590 / 845 | 58.7 / 51.1 | 1257 / 74.1 | 12/12 |
| **Gyro-M** | **131K** | **int8** | **32768** | **6972** | **653 / 1125** | **56.3 / 55.0** | **1744 / 70.3** | **12/12** |

- **The prefill speed follows the KV type, not the window:** k8v4 stays at ~1.4K t/s with any ctx and any number of
  experts on the GPU; int8 reads 1.8–2.2K. The window moves decode (fewer experts fit next to a bigger KV). The
  matrix-core prompt attention reports "on" in every row, so it is not the cause; why k8v4 is slower is not resolved.
- **`--kv-resident 32768`** keeps only the newest 32K tokens of KV in VRAM and streams the rest from RAM: 262K with int8 KV
  gets the most experts on the GPU and the 131K/int8 speed. Gyro-S, own 0.2.1 build, 262K int8 `--kv-resident 32768`:
  recall at 183K and 210K tokens 12/12 on two seeds, prefill 2059 / 2046 t/s, decode 77–80 t/s at that depth
  (k8v4 read 174K at ~1400 t/s).
- Gyro-M gains less: prefill +11–39%, decode −5% to +8%.
- RAM: the engine locks 18.7–20.3 GiB of experts in every row, but cgroup `anon` reads 23 GB at 262K and 2.8 GB at
  131K, so anon-based headroom is not comparable across these rows.

Java task (Pi, xhigh, own 0.2.1 build, our settings), int8 against k8v4:

| Model | KV | time | result | decode t/s (median) | agent-turn prefill t/s | MTP | SSD reads | PSI full > 1% / mean | review /60 |
|---|---|---|---|---|---|---|---|---|---|
| Gyro-S 262K | k8v4 | 73 / 27 min | done ×2 | 65.2 / 65.6 | 706 / 596 | 68.6 / 68.8% | — | — | 37.5 / 35 |
| Gyro-S 262K | **int8 + `--kv-resident 32768`** | 29 min | done | **69.6** (71.8) | **736** | 69.8% | — | — | 34 |
| Gyro-M 131K | k8v4 | 47 min | done | 57.5 (60.1) | 340 | 68.8% | 203 GB/h | 6% / 0.27% | — |
| Gyro-M 131K | int8 (Strata default) | 40 min | done | 57.2 (59.5) | 317 | 70.7% | 330 GB/h | 9% / 0.36% | — |
| Gyro-M 131K | int8 + `--kv-resident 32768` | 34 min | done | 56.8 (59.1) | 279 | 71.0% | 437 GB/h | 10% / 0.43% | — |

Review: one blind batch for the three Gyro-S projects (Claude / Codex: 42/33, 40/30 for k8v4; 36/32 for int8):
inside the reviewer noise. Agent time is set by how much work the agent chose, not by the engine.
**What we run now:** Gyro-S on int8 + `--kv-resident 32768` (prompts ~1.5× faster at the same 262K, decode +7%);
Gyro-M stays on k8v4. For Gyro-M int8 only helps big fresh prompts (1418–1744 vs 1257 t/s at 100K); agent turns are small
appends, where all three read ~280–340 t/s, while RAM pressure and SSD reads go up. Strata's GYRO.md lists 35 GB of
VRAM + RAM for Gyro-M; here the server's cgroup has 29 GB, so the rest is read from the SSD (about half of the file is
the n-gram table, read for every token).

### Strata standard benchmark (`strata bench run`, protocol `strata-qwen38-thinking-v1-draft.1`)

0.2.1 release engine, the runner starts the engine itself, fresh load, loopback, thinking xhigh, 512-token output cap
(capped answers count as `truncated` there), 12 sanity checks:

| Config | prefill 4K / 16K | decode 4K / 16K | TTFT 16K | capped (of 9) | sanity |
|---|---|---|---|---|---|
| ours: 262K, k8v4, spread, vision, budget 24576 | 997–1028 / 1334–1369 | 61.6–62.9 / 64.3–64.8 | 12.0–12.3 s | 4–5 | 12/12 |
| Strata GYRO.md §4: 131K, int8 | 1821–1824 / 1734–2228 | 68.1–72.5 / 62.7–62.8 | 7.4–9.5 s | 2–4 | 12/12 |

Ranges = medians of two report runs per config. In these report runs 2 of 3 4K prompts of the 262K/k8v4 config read at ~1000 t/s against
1357 in the KV table above (same engine and pinning); not explained.

## Gyro-M on 16 + 32 GB: tuning (Oct 24–26)

Goal: make Gyro-M (better code than Gyro-S in our reviews, ~IQ3_XXS quality by the authors' KLD) usable as the daily
server on this box. Limits we set: **no expert reads from the SSD**, **≥ 1.5–2 GiB RAM headroom** to the 29 GB cgroup
cap, **KV not below int8** (no q4_0 KV), no image encoder (it needs ~0.95 GiB of RAM that is not there at 196K).
Benches: `dec-ab` (temperature 0; `gen1k` = 1024 tokens of Java from a short prompt; `f32` / `f180` = fresh 32K / 180K
prompt; `t32` = +2K turn on it), cold engine start per row, A/B in ABBA order with bootstrap 95% intervals over starts.

### What changed, one step at a time

| Step | Effect (measured) |
|---|---|
| `--prefill 2048` + `STRATA_RESIDENT_HEADROOM_GIB=2` + `--prompt-cache 2` | the prompt path borrows only slots whose experts are also in RAM (845 of 845): SSD expert reads per fresh 32K prompt 13 GB → 0 (`--prefill 4096`: 13 GB, 32–35 GB on a fresh 100K) |
| KV `int8` instead of `k8v4` | fresh prompt +35% (1540 vs 1140 t/s at 131K); k8v4 caps prompts at ~1.4K t/s, as on Gyro-S |
| `--mtp-draft-vocab data/draft_vocab_cyrillic.bin` | +99 experts on the GPU, −130 MiB RAM, decode not lower |
| Strata main `7dd5cf18` built with `-DSTRATA_PREFILL_MMQ=ON` | prompt = 0.2.1 (±2%); without MMQ the expert GEMMs of the prompt run in FP16 and prompts are ~35% slower |
| `STRATA_EXCHANGE_ROTATE=1` | agent-turn time −4.8% [−7.8, −1.8], 8 + 8 cold starts |
| `STRATA_TQ_SUB8=1` with [the patch](configs/strata-hip-tq-sub8.patch) (lets the CUDA-only staged trellis kernel run on HIP, opt-in) | decode +7.1% [+6.6, +7.6] at 196K, +7.3% [+6.0, +8.7] at 131K; teacher-forced KL vs off: 0 (top-1 100%, 2 runs, 4995 positions) |

Result, Gyro-M TQ2_0, MTP4, int8 KV, resident experts:

| Config | experts on GPU | decode (`gen1k`) | decode at 180K | fresh prompt | +2K turn | RAM headroom, min |
|---|---|---|---|---|---|---|
| start, Oct 24 (0.2.1, 131K, int8 + `--kv-resident 32768`, vision; or k8v4 without vision) | 6952 / 6198 | 56–58 ⁵ | — | 600–1115 (4K–16K) ⁵ | — | — |
| finalist 131K, `--prefill 3072`, `--prompt-cache 3` | 6008 | ~76 | — | 1450–1550 (32K) | ~1000 (at 32K) | 2.17 GiB |
| **finalist 196K** (config: [strata-gyro-m-196k-int8-finalist.json](configs/strata-gyro-m-196k-int8-finalist.json)) | 5210–5221 | **~76.5** | **~58** | 1050–1150 (32K–180K) | 780–1000 (at 28K–110K) | 1.71 GiB (bench), 1.84 GiB (agent runs) |

⁵ Measured with `strata bench` (4K / 16K prompts), not `dec-ab`; the 32K fresh prompt on 0.2.1 with k8v4 read ~1140 t/s.

- **262K does not fit** these limits: with k8v4 (int8 is bigger) the prompt path covers 645 of 845 slots, a fresh prompt
  reads 7–14 GB of experts from the SSD, 815 t/s at 240K. It needs ~0.5–1 GiB more RAM.
- **Did not help** (one cold start each on top of the 131K config; ~70 decode / ~1530 prompt / ~1000 turn = noise band):
  `HIP_QUEUE_PRIME=0` (prompt 863), `MTP_SIDE_STREAM=1` (1163), `GDN_SPLIT=1` (1261), `B6_MMVQ_ROWS=1` (1299),
  `SH_STREAM=1` (decode 63), `SIDE_MIXER=2` (decode 51); `SPEC_COST`, `ADAPT_OVERLAP`, `TSUM`, `LFUSE`, `QFUSE`, `PLE_BATCH`,
  `MMVF_ROWS`, `ATTN_LANECELL`, `ATTN_DAILY`, `GR_UP75`, `GR_DOWN_TG`, `QSA_ROWS` within noise. `--kv-resident` costs Gyro-M
  more RAM than KV in VRAM. Forcing the GPU power profile to `high` was slower.
- **Approximations that stay on** (Strata's gfx12 defaults, also on our Gyro-S): `ROUTE_TAIL_SKIP=7` — turning it off costs
  −9.6% decode, +9.9% turn time; KL vs off ≤ 0.053 (upper bound: the test tool's expert-cache hit rate was 28–79%, the
  server's is 88–93%). `HC_Q8` — off costs −4.9% decode and 0.4 GiB of RAM headroom; KL 0.021.
- **Memory rule of thumb** that held to the MiB: every MiB of VRAM not used for experts (bigger KV, prompt buffers)
  moves the same amount of experts into RAM.

### Where the time goes

Prompt-path phases (`STRATA_PREFILL_TIMING=1`), 3 passes each, fresh engine; read speeds from the engine log:

| | Gyro-M finalist 196K | Gyro-S, Oct 22 server (0.2.1, 262K, int8 + `--kv-resident 32768`) |
|---|---|---|
| fresh 26–31K prompt | 1144–1153 (one slow: 775) | 1926–2011 (one slow: 1346) |
| fresh 97–111K prompt | 876–1012 | 1469–1987 |
| +2K turn at ~28K | 780–844 | 1123–1155 (one slow: 629) |
| +2K turn at ~100K | 950–995 | 1069–1087 (one slow: 562) |

- Attention (QSA select + attn) is ~5–6% of a turn on both at 100K: depth is not what slows Gyro-M down. Expert GEMMs,
  gathering and copies are ~65%; Gyro-M's experts are twice the bytes of Gyro-S's.
- **Slow fresh prompts** (~1 in 10, at 55–65% speed; the gather phase takes 3–4× longer) happen on both models, with and
  without `EXCHANGE_ROTATE`; a patch that skips repeated stream waits in the prompt path did not change them. Cost:
  ~−4% on average fresh-prompt speed. Not resolved.
- **Decode speed follows MTP draft acceptance**, not context depth (hybrid model: GDN layers + sparse QSA attention):

  | Workload | MTP accepted | decode t/s |
  |---|---|---|
  | `dec-ab` runs, temperature 0 (code + short answers) | 78–79% | 72–74 (`gen1k` alone: 76.5) |
  | Java agent run, temperature 1.0 (code, tool calls) | 69% | 65.8 |
  | LiveCodeBench reasoning, temperature 1.0, 12–50K tokens per answer | 65% | 61.0 |
  | Java run by context of the request: 0–40K / 40–80K / 80–120K | 63% / 72% / 70% | 63.6 / 67.9 / 65.2 |

- **SSD reads while serving are the n-gram table, not experts.** Flash-Next keeps a 320M-row n-gram embedding table in the GGUF
  (about half of the 92 GB Gyro-M file) that is never loaded into RAM: 16 rows per token are read with 4 KiB `O_DIRECT` reads (seen with
  bpftrace in Strata's `ngram/ple_reader` thread; row cache 1M rows by default). ~0.8 GB per fresh 32K prompt, ~2 MB/s
  in agent work, ~4 GB per Java run. Strata's own counter shows 0 expert reads.

### Java task on the finalist (Pi, xhigh, budget 24576)

| Run | time | tool calls | max context | decode median (p10–p90) | prefill ≥ 8K / turns 0.5–8K | RAM headroom min | SSD writes |
|---|---|---|---|---|---|---|---|
| 1 | 27 min, done | 131 | 120.7K | 66 (58–78) | 1144 / 510 | 1838 MiB | 54 MB |
| 2 | 25 min, done | 95 | 100.9K | 67 (59–76) | 1131 / 583 | 1845 MiB | 42 MB |

No context compaction, PSI 0, no OOM; GPU hotspot ≤ 76 °C, ≤ 267 W. Same task before the tuning (Gyro-M, Strata rc2 /
0.2.1, 131K): 34–47 min, decode 52–57. Gyro-S xhigh on the Oct 22 server: 29 min, decode 66–67.

Blind reviews (three projects per batch, renamed; Claude / Codex, /60):

| Batch | Gyro-M finalist | Gyro-M, Oct 22 (0.2.1, 131K int8, vision) | Gyro-S, Oct 22 server |
|---|---|---|---|
| 25 | run 1: 45 / 37 | 45 / 39 | 41 / 34 |
| 26 | run 1: 41 / 36, run 2: 42 / 34 | — | 39 / 32 |

Gyro-M scored above Gyro-S in every pair (generated server-side order ids and correct SOAP fault codes vs client order ids
and all faults as `Client`, a connection pool, order-independent tests). All projects share two defects: no stock
compensation when the order insert fails after the reservation, and a fixed `PII_KEY` in docker-compose.

LiveCodeBench v6 (175 problems, Jan–Apr 2025, LCB generic prompt, xhigh, 64K output cap, temperature 1.0): only 5 done
so far, 4 pass; the failed one stopped at the reasoning budget (49,152 tokens). Full run pending; references: ISTA-DASLab
BF16 87.4, GSQ IQ3_XXS 86.3, Q2_0 81.1.

## Windows 11 (Sep–Oct 2026)

### depth ≤ 45K

| Model | Engine | ctx | KV | depth | prefill t/s | decode t/s |
|---|---|---|---|---|---|---|
| Qwen3.8-27B UD-IQ4_XS | r27, ngram | 106K | q4_0 | 8K | 945 | 33 |
| Qwen3.8-27B UD-IQ4_XS | r27, ngram | 106K | q4_0 | 29K | 865 | 32 |
| Qwen3.8-27B UD-IQ4_XS | r27, ngram | 32K | q4_0 | 32K | 873 | 33.9 |
| Qwen3.8-27B UD-IQ4_XS + DFlash2 Q4_K_M drafter | r27 | 32K | q4_0 | 32K | 771 | 36.1 |
| Qwen3.8-27B UD-IQ4_XS | v16, MTP2 | 102K | q4_0 | 17.4K | ~594 | 53.5 |
| Qwen3.8-27B UD-Q3_K_XL | v16, MTP2 | 131K | q4_0 | 17.4K | ~732 | 49.8 |
| Qwen3.8-27B IQ4_XS (jrell) | v16, MTP2 | 131K | q4_0 | 17.4K | ~791 | 47.4 |
| Qwen3.8-27B GSQ IQ3_S-mtp | v16, MTP2 | 131K | q4_0 | 17.4K | ~624 | 48.0 |
| Qwen3.8-27B IQ4_XS (jrell) | v16, MTP2 | 102K | q4_0 | 15.7K | 951 | 37.4 |
| Qwen3.8-27B IQ4_XS (jrell) | v16, MTP2 | 131K | q4_0 | 15.7K | 900.5 | 36.6 |
| Swift Qwen3.8-27B IQ4_XS-Smaller | v16, MTP2 | 131K | q4_0 | 15.7K | 906.7 | 39.5 |
| Qwen3.8-27B UD-IQ3_XXS | rdna | 176–224K | q4_0 | 16K | ~630 | 43.5 |
| Qwen3.8-27B IQ3-MIX | rdna | 100K | q8_0 | 32K | 713 | 27.1 |
| Qwen3.8-27B OBLITERATUS Q3_K_M | rdna, MTP2 | 102K | q4_0 | 31K | 635.5 | — |
| Qwen3.8-27B huihui UD-IQ4_XS | r28 | 106K | q4_0 | 44K | 790 | ~31 |
| Qwen3.8-27B heretic-ara IQ4_XS | r28 | 106K | q4_0 | 44K | ~793 | ~33.5 |
| Gemma 4 26B-A4B UD-IQ4_XS | r28 | 131K | q8_0 | short | — | ~90 |
| Ornith-1.5-35B-A3B AD-Q4_K-IQ4_XS | r30 | 262K | q4_0 | 44K | — | ~40.5 |
| Ornith-1.5-35B-A3B AD-Q5_K-Q4_K | r30, ub2048 ncmoe20 | 262K | q4_0 | 44K | 2451 | 38.7 |
| Ornith-1.5-35B-A3B AD-Q6_K | r30, mmap ncmoe24 | 262K | q4_0 | 44K | 1216 | 35.5 |
| Flash-Next Coder IQ1_M | Strata 0.1.38 | 131K | int8 | 34K | 734 | 45 |
| Qwen3.8-27B mq3 | HipFire 0.4.0 | 40K | fp8 | 32K | 528 | 36.1 |
| Qwen3.8-27B IQ4_XS (jrell) | WHIRL 0.1.4, MTP + ngram | 59K pool | q8h | 31K | 1110 | 46.5 |
| Qwen3.8-27B IQ4_XS (jrell) | BeeLlama 0.4.6, MTP2 | 102K | q4_0 | 31K | 593.1 | 30.9 |
| Qwen3.8-27B GSQ IQ3_S | KVMem beta2, MTP2 | 28K window | q8_0 | 28K | 547 | 35 |

### depth ≥ 60K

| Model | Engine | ctx | KV | depth | prefill t/s | decode t/s |
|---|---|---|---|---|---|---|
| Qwen3.8-27B UD-IQ4_XS | r27, ngram | 106K | q4_0 | 70K | 709 | 28 |
| Qwen3.8-27B UD-IQ4_XS | r27, ngram | 106K | q4_0 | 81K | 671 | 29 |
| Qwen3.8-27B UD-IQ4_XS | r28, ngram | 106K | q4_0 | ~96K | 639 | ~25.5 |
| Qwen3.8-27B UD-IQ4_XS + CPU vision | r28 | 106K | q4_0 | 85K | 673 | 28.1 |
| Qwen3.8-27B UD-IQ4_XS | r27 | 131K | q4_0 | ~125K | 562 | ~22.8 |
| Qwen3.8-27B UD-IQ4_XS | v16, MTP2, FA cap | 102K | q4_0 | 63K | ~591 | ~29.0 |
| Qwen3.8-27B UD-IQ4_XS | v16, no spec | 102K | q4_0 | 63K | ~477 | 23.6 |
| Qwen3.8-27B UD-IQ4_XS | v16 r4, ngram, FA cap | 131K | q4_0 | 63K | ~697 | ~22.7 |
| Qwen3.8-27B UD-Q3_K_XL | v16, MTP2, FA cap | 131K | q4_0 | 63K | ~661 | ~28.6 |
| Qwen3.8-27B UD-Q3_K_XL | v16, no spec | 131K | q4_0 | 63K | ~690 | 22.3 |
| Qwen3.8-27B IQ4_XS (jrell) | v16, MTP2, FA cap | 131K | q4_0 | 63K | ~674 | ~29.6 |
| Qwen3.8-27B IQ4_XS (jrell) | v16, no spec | 131K | q4_0 | 63K | ~460 | 21.1 |
| Qwen3.8-27B IQ4_XS (jrell) | v16, MTP2 | 102K | q4_0 | 63.9K | 461 | 24.9 |
| Qwen3.8-27B IQ4_XS (jrell) | v16, MTP2 | 102K | q4_0 | 83K | 392 | 23.9 |
| Qwen3.8-27B GSQ IQ3_S | r28 | 98–106K | q8_0 | ~92K | ~512 | ~27 |
| Qwen3.8-27B GSQ IQ3_S | r28 | 164K | q4_0 | ~158K | 440 | ~22.6 |
| Qwen3.8-27B GSQ IQ3_S | r28 | 196K | q4_0 | ~186K | 405 | ~20.9 |
| Qwen3.8-27B huihui UD-IQ4_XS | r28 | 98–106K | q4_0 | ~92K | ~643 | 26.5 |
| Qwen3.8-27B heretic-ara IQ4_XS | r28 | 98–106K | q4_0 | ~92K | ~635 | ~26 |
| Qwen3.8-27B heretic IQ4_XS + GPU vision | r28 | 73K | q4_0 | 64K | 717 | 29.2 |
| Qwen3.8-27B Fable Cold Fusion i1-IQ3_M | r28 | 106K | q4_0 | 85K | 673 | 27.7 |
| Swift-1.5 Qwen3.8-27B Q3_K_L | r28 | 106K | q4_0 | ~96K | 545 | ~25.4 |
| Swift-1.5 Qwen3.8-27B Q3_K_L | r28 | 114K | q4_0 | ~104K | 516 | ~24.7 |
| Qwen3.8-27B IQ3-MIX | rdna | 164K | q4_0 | 100K | 475.7 | 17.0 |
| Gemma 4 26B-A4B UD-IQ4_XS | r28 | 131K | q8_0 | 99K | 737 | 74.6 |
| Ornith-1.5-35B-A3B AD-Q4_K-IQ4_XS | r27, ncmoe23 | 262K | q4_0 | 252K | 1131 | ~25.4 |
| Ornith-1.5-35B-A3B AD-Q5_K-Q4_K | r30 | 262K | q4_0 | 251K | 998 | 27.2 |
| Ornith-1.5-35B-A3B AD-Q6_K | r30, mmap | 262K | q4_0 | 251K | 670 | ~27.7 |
| Flash-Next Coder IQ1_M | Strata 0.1.38 | 131K | int8 | 75K | 1005 | 49 |
| Flash-Next Coder IQ1_M | Strata 0.1.38 | 131K | int8 | 90K | 1092 | 51 |
| Qwen3.8-27B UD-IQ4_XS, 2 FFN layers in RAM | r27, ngram | 119K | q4_0 | ~109K | — | ~23.0 |
| Qwen3.8-27B UD-IQ4_XS, 7 FFN layers in RAM | r27 | 164K | q4_0 | ~154K | — | ~12.5 |
| Qwen3.8-27B (quant not recorded) | BeeLlama 0.4.8 | 106K | q4_0 | ~96K | 187 | 16.5 |

### Agent turn: +4K tokens appended to a cached conversation

| Model | Engine | ctx | cached depth | prefill t/s |
|---|---|---|---|---|
| Qwen3.8-27B UD-IQ4_XS | r27, ngram | 106K | ~96K | ~444 |
| Qwen3.8-27B UD-IQ4_XS, 2 FFN layers in RAM | r27, ngram | 119K | ~109K | ~400 |
| Qwen3.8-27B UD-IQ4_XS | v16, MTP2, FA cap | 102K | 63K | ~455 |
| Qwen3.8-27B UD-IQ4_XS | v16 r4, ngram, FA cap | 131K | 63K | ~508 |
| Qwen3.8-27B UD-Q3_K_XL | v16, MTP2, FA cap | 131K | 63K | ~478 |
| Qwen3.8-27B IQ4_XS (jrell) | v16, MTP2, FA cap | 131K | 63K | ~490 |
| Qwen3.8-27B GSQ IQ3_S | r28 | 164K | ~158K | 306 |
| Qwen3.8-27B (quant not recorded) | BeeLlama 0.4.8 | 106K | ~96K | 115 |

## Vulkan vs HIP

Vulkan never beat HIP here on prefill; decode is about the same. SAM / ReBAR was on for all runs.

| Model | OS | HIP | Vulkan | depth | prefill HIP | prefill Vulkan | decode HIP | decode Vulkan |
|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B UD-IQ4_XS | Linux | r28 | agentionai fork, Mesa 26.2.5, ub1024 | llama-bench pp2048, tg128 | 1183 | 1029 | 33.5 | 35.7 |
| Qwen3.8-27B UD-IQ4_XS | Linux | r28 | agentionai fork, Mesa 26.2.5, ub1024 | llama-bench d32K | 765 | 587 | 30.1 | 32.9 |
| Qwen3.8-27B UD-IQ4_XS | Linux | r28 | agentionai fork, Mesa 25.2.8, ub256 | llama-bench pp2048, tg128 | 1183 | 816 | 33.5 | 34.7 |
| Qwen3.8-27B UD-IQ4_XS | Linux | r28 | agentionai fork, Mesa 25.2.8, ub256 | llama-bench d32K | 765 | 453 | 30.1 | 31.4 |
| Qwen3.8-27B UD-IQ4_XS, ctx 106K, ngram | Windows | r27, ub128 | mainline b11393, ub512 | ~30K (HIP 31K, Vulkan 28K) | 851 | 585 | 30.8 | 29.6 |
| Qwen3.8-27B UD-IQ4_XS, ctx 106K, ngram | Windows | r27, ub128 | mainline b11393, ub512 | 60K HIP, 72K Vulkan | 741 | 482 | 30.9 | 29.6 |
| Gyro-S TQ1_0 | Linux | Strata rc2, MTP4 | agentionai llama.cpp, ncmoe 28–30 | 32K | 1318 | ~365 | 65.4 | ~12.5 |

Windows, 20 agent turns on the same bench: HIP 155 s, Vulkan 194 s; decode in turns min 27.6 vs 11.2 (Vulkan also warned
`failed to fit params to free device memory` and used 0.85 GB of pagefile).
On the AMD driver 32.0.31021 (Adrenalin 26.6.4) Vulkan crashed Windows with BSOD 0x116 three times out of three, even
at idle ~30 s after load. After updating to Adrenalin 26.9.2 (32.0.32015) the same setup ran ~25 min with no driver events.

## Adaptive KV streaming fork (Qwen 27B at 262K)

[achyudh/llama.cpp `feature/adaptive-kv-stream-rocm`](https://github.com/achyudh/llama.cpp/tree/feature/adaptive-kv-stream-rocm)
(`9e24be0`): the KV cache lives in host RAM, a fixed window is streamed to the GPU over PCIe, plus RDNA4 kernel fusions.
The author measured an RX 9070 XT on PCIe 5.0; here it is a non-XT RX 9070 on **PCIe 4.0 x16** (B650). Unsloth UD-IQ4_XS
(not the author's ASCII-condensed file), mmproj on CPU, KV q8_0/q4_0, `--kv-stream --kv-resident-mib 450
--kv-resident-mib-decode 1600`, `-b 2048 -ub 512`, MTP + ngram-mod with probabilistic draft sampling. Single runs.

| ctx | spec | depth | prefill | decode | agent turn prefill | agent turn decode |
|---|---|---|---|---|---|---|
| 262K | MTP + ngram | 28K | 961 | 62.9 | 582 | 48.2 |
| 262K | MTP + ngram | 69K | 789 | 64.4 | 465 | 61.1 |
| 262K | MTP + ngram | 136K | 606 | 31.8 | 333 | 28.7 |
| 262K | MTP + ngram | 204K | 489 | 18.3 | 262 | 17.6 |
| 262K | ngram only | 28K | 1023 | 31.9 | 629 | 31.8 |
| 262K | ngram only | 134K | 648 | 13.8 | 355 | 12.4 |
| 262K | ngram only | 228K | 488 | 6.0 | 247 | 5.8 |
| prod r28, 131K | ngram only | 31K / 62K | 954 / 791 | 30.2 / 28.5 | 740 / 556 | 38.3 / 30.7 |

- **Correct:** KLD against clean llama.cpp 0.000000 (en and code). Long-context recall (the test above): 12/12 ×3 at
  ~100K and ~170K, 11/12 / 12/12 / 12/12 at 241K / 233K / 210K.
- **Decode** with MTP is 2× r28 up to ~70K, then drops: the KV no longer fits the 1.6 GB window and crosses PCIe 4.0 on
  every step (~4 GiB at 204K / ~25 GB/s ≈ 6 t/s without MTP, as measured). The author gets 31 t/s at 262K on PCIe 5.0.
- **Prefill** is not faster than r28; agent-turn additions are ~15% slower (about −15% from the fork itself, measured
  with ngram only, and ~−8% more from the MTP head reading the prompt).
- Tuning on this card: `--kv-resident-mib-decode 2100` (the author's value), `--spec-draft-n-max 5`, and `-ub 1024/2048`
  at 262K do not fit in VRAM (the MTP draft context needs +416 MiB). At ctx 131K, `-ub 1024` fits; a larger `-ub` or a
  prefill window of 900 MiB do not speed up additions (477–500 t/s at ~60K either way).
- 20 agent turns from ~32K (+1.6K, 150-token replies): fork 262K 159 s, fork 131K `-ub 1024` 144 s, prod r28 175 s.

³ In the Java run the agent let the context grow to 203K without compaction; decode medians by context of its
requests: 71 (0–64K), 57 (64–128K), 33 (128–192K), 22 t/s (192K+). Same model and task on prod r28 took 49 min.

## Java agent task ([Pi](https://github.com/earendil-works/pi), 120 min cap)

Multi-module Gradle / Java 21: contract-first SOAP (WSDL + XSD), gRPC inventory, Postgres, AES-256-GCM, Docker Compose,
Testcontainers. Clean dir per run; "done" = the agent finished itself and an independent `gradle clean build` passed.

Files: [java-task/SPEC.md](java-task/SPEC.md) (put in the empty project dir), [java-task/PROMPT.txt](java-task/PROMPT.txt)
(the task message, verbatim), [java-task/review-prompt.md](java-task/review-prompt.md) (reviewer prompt with the A–F rubric).
Setup (current versions): Pi 1.2.0 on a Windows 11 laptop (Git Bash), OpenJDK 21.0.12, Gradle 9.0.0, Docker 29.5.3; model served over the
LAN. Pi: `maxTokens` 32768, thinking medium or xhigh as in the table, MCP context7 + web search, loop guard
pi-anti-doom-loop, empty agent memory, no `AGENTS.md`. Pi sends no sampling parameters: Strata (Gyro) runs with
temperature 1.0, top_p 0.95, top_k 20, min_p 0.05 in its config; llama.cpp (Qwen) with its defaults. Library versions are not pinned on purpose: choosing and finding them is part of the task.
Reproducible only roughly: agent runs vary from run to run, and the same reviewer drifts by ~±5 between batches.
Review /60 = average of two LLM reviewers (Claude, Codex). Scores drift between review batches, so compare a run only
with Qwen 27B from the same batch (last column).

| Model | ctx | effort | time | result | review /60 | Qwen 27B, same batch |
|---|---|---|---|---|---|---|
| Qwen3.8-27B UD-IQ4_XS (Linux) | 131K | medium | 49 min | done | 35 | — |
| Qwen3.8-27B UD-IQ4_XS, repeat | 131K | medium | 110 min | failed | — | — |
| Qwen3.8-27B-pi Q3_K_M | 131K | medium | 68 min | done | 30 | 35 |
| Swift-1.5 Q3_K_L | 131K | medium | 73 min | failed | — | — |
| Qwen3.8-27B UD-IQ4_XS, adaptive-KV-stream fork ³ | 262K | medium | 78 min | done | 27.5 | 32.5 |
| Gyro-S | 131K | medium | 21 min | done | 39 | 35.5 |
| Gyro-S | 131K | xhigh | 33 min | done | 43.5 | 34.5 |
| Gyro-S | 131K | xhigh | 29 min | done | 36 | 31.5 |
| Gyro-S + vision | 262K | xhigh | 39 min | done | 40.5 | 31 |
| Gyro-S + vision | 262K | medium | 48 min¹ | done | 43.5 | 29 |
| Gyro-M | 131K | xhigh | 37 min | done | 42.5 | 34 |
| Gyro-M | 131K | medium | 53 min¹ | done | 44 | 29 |
| Gyro-S + vision, Strata 0.2.1, int8 + `--kv-resident 32768`, Pi 1.4.0 | 262K | medium | 36 min | done | 38 | — ⁴ |
| Gyro-S abliterated + vision, same settings, Pi 1.4.0 | 262K | medium | 21 min | done | 41 | — ⁴ |
| Gyro-M tuned (Strata main + sub8 + rotate, int8, no vision) | 196K | xhigh | 27 min | done | 41 / 38.5 (two batches) | — ⁶ |
| same, repeat | 196K | xhigh | 25 min | done | 38 | — ⁶ |
| Qwen3.8-27B UD-IQ4_XS (Windows, r28) | 106K | medium | 55 min | 7/8 checklist | — | — |
| Qwen3.8-27B GSQ IQ3_S q8_0 KV (Windows) | 106K | medium | 65 min | 7/8 checklist | — | — |
| Qwen3.8-27B heretic-ara IQ4_XS (Windows) | 106K | medium | — | 5/8 checklist | 22 (other batch) | — |
| Qwen3.8-27B Fable i1-IQ3_M (Windows) | 106K | medium | — | 4/8 checklist | 18 (other batch) | — |

¹ Waiting on `search.maven.org`: ~17 min (Gyro-S), ~9 min (Gyro-M). It also returned stale versions (grpc-api 1.73.0 vs 1.85.0 in `repo1`).
⁴ One blind batch with just these two projects (Claude / Codex: stock 41/35, abliterated 44/38). Both had the same kind
of top defects: a fixed `PII_KEY` in docker-compose and no stock compensation when the order insert fails after the
reservation. Abliterated used 117 tool calls vs 220 for stock; decode 68–74 t/s, PSI 0, 3–4 GB SSD reads per run for both.

⁶ Same batches, Gyro-S xhigh on the Oct 22 server: 37.5 and 35.5; details in [Gyro-M on 16 + 32 GB](#java-task-on-the-finalist-pi-xhigh-budget-24576).

Strata rc2 vs 0.2.x, Gyro-S + vision, 262K, xhigh, Pi, one blind review batch (projects renamed, the reviewers did not
know the engine): 0.2.x 39, 39, 35.5, 30 (mean 35.9); rc2 38.5, 38.5, 37, 36.5 (mean 37.6). Agent time 27–73 min
(0.2.x) and 16–39 min (rc2): set by how much work the agent chose (81–97K vs 42–80K generated tokens), not by the engine.

Agent harnesses, same model and server (Gyro-M + vision, 131K, xhigh, Strata 0.2.1), one blind batch:

| Harness | time | tool calls | generated | review /60 |
|---|---|---|---|---|
| [Pi](https://github.com/earendil-works/pi) 1.2.0 | 47 min | 162 | 99K | 33.5 |
| [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 0.2.1-rc.2 | 46 min | 166 | 104K | 31 |
| [oh-my-pi](https://github.com/can1357/oh-my-pi) 18.12.5 | 120 min (cap) | 366 | 287K | 42.5 |
| Pi 1.2.0 on Strata rc2 (anchor) | 38 min | 146 | 84K | 33 |

The same rc2 project scored 41 in the previous batch: the reviewers drift a lot, compare within a batch only.
oh-my-pi wrote a custom XJC plugin to put Bean Validation on the generated SOAP types (true contract-first, the most
complete tests) but needed 2.5× the time: answers twice as long (~1.4K vs ~0.7K tokens per request), probe scripts and
library internals first, tests late (its system prompt asks for throwaway probe scripts and "new tests only for
uncertain edges"). DeepSeek Harness vs Pi over five same-condition pairs: −2, 0, −4, −5, −5 points (it exposes every MCP tool
directly: 70 tools per request vs Pi's 26, and runs PowerShell on Windows). One run per cell: not a ranking.
Side model calls (session titles, recaps, subagents, background compaction) were switched off in DeepSeek Harness and oh-my-pi:
on a single local server each of them evicts the agent's prompt cache.

## Quality checks

| Test | Gyro-S | Gyro-M | Qwen3.8-27B UD-IQ4_XS |
|---|---|---|---|
| Java/Gradle/SOAP/SQL/crypto questions | 14 of 14 | 14 of 14 | 12 of 14 |
| Recall @~100K (10 near-duplicate keys + 3 corrections + 2 API facts), 3 seeds | 12/12 ×3 | 12/12 ×3 | — |
| Recall @~170K, 3 seeds | 12/12 ×3 | — | — |
| Recall @~240K, 3 seeds | 12/12 ×3 | — | — |
| Degenerate long answers (8 × 4–6K tokens) | 0 of 8 | 0 of 8 | — |
| [tool-eval-bench](https://github.com/SeraphimSerapis/tool-eval-bench), 69 scenarios, medium | 89 (262K + vision) | 91 | 93 |
| [KCORES heptagon](https://github.com/KCORES/kcores-llm-arena/tree/main/benchmark-ball-bouncing-inside-spinning-heptagon), blind, best of 3, /90 ² | 88 (2 of 3 ran) | 88 (1 of 3 ran) | 78 (1 of 3 ran) |
| KCORES via Pi agent with screenshots, medium ² | 78 | 78 | — |
| KCORES via Pi agent with screenshots, xhigh | 78 | 78 | — |
| same, xhigh + one review remark | 88 | — | — |

² Blind generation (no running, no screenshots) often gave a non-working program: crash or no animation in 1 of 3 (Gyro-S)
and 2 of 3 (Gyro-M, Qwen 27B). With vision the agent ran its program, looked at screenshots and fixed it: every run
ended with a working program, but none of them noticed from the screenshots that the digits on the balls must rotate,
not just move along. For Gyro-S xhigh one remark about it was enough to fix that (88).

[Gyro-S abliterated (Huihui)](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-abliterated-Huihui-GGUF) TQ1_0,
Strata 0.2.1, 262K int8 `--kv-resident 32768`, against stock Gyro-S on the same server: questions 14 of 14 (stock 14),
degenerate long answers 0 of 8 (stock 0), recall 12/12 at 183K and 210K, `native_expert_parity` 0 failures. A probe of
8 legal but edgy requests (profane roast, lock picking, violent fiction, dark jokes, dangerous chemical mixes, flirting,
skipping the Microsoft account in Windows setup, a drug-legalization essay): neither model refused any, with no
disclaimers, so this probe does not show what abliteration changes.

Flash-Next Coder IQ1_M (half the experts): 3–4 of 8 long answers degenerated (`java java …`, line loops), also in deterministic mode.
Gyro kernels on gfx1201: Strata `native_expert_parity` 0 failures, GPU rel. error 1.8–2.0% (bound 3%).

## KLD vs Q8_0 (Qwen3.8-27B, `-c 512`)

| Quant | en | code | ru |
|---|---|---|---|
| UD-IQ4_XS (unsloth) | 0.086 | 0.023 | 0.035 |
| UD-Q3_K_XL (unsloth) | 0.136 | 0.034 | 0.056 |
| GSQ IQ3_S-mtp (ISTA-DASLab) | 0.150 | 0.048 | 0.071 |
| IQ4_XS (jrell), v16 | 0.192 | 0.055 | 0.076 |
| IQ4_XS (jrell), b10587 | 0.195 | 0.055 | 0.076 |
| Swift IQ4_XS (UkisAI) | 0.195 | 0.057 | 0.078 |
| UD-IQ3_XXS (unsloth) | 0.224 | 0.068 | 0.112 |
| IQ3-MIX | 0.263 | 0.091 | 0.134 |
| OBLITERATUS Q3_K_M | 0.368 | 0.165 | 0.343 |

Same quant, different runtime: r27 vs r4 mean 0.0025 (top-1 98.99%); FA stage cap on vs off 0.000000.

**rdna-boosts r28 is wrong with several sequences in one batch.** Against clean llama.cpp (a0e6dc738), same UD-IQ4_XS,
`-c 512 --chunks 16`: one sequence per pass (`-b 512`) KLD 0.0025 (en) / 0.0013 (code), but four sequences per pass
(perplexity's default `-b 2048`) 0.198 / 0.167, PPL +10–13%. A server with `--parallel 1` is likely unaffected (not
verified); do not use `--parallel > 1` on r28 and measure KLD on it only with `-b 512`. Not re-checked on r84+.
Gyro (author's numbers, vs Flash-Next Q8_0): S 0.401 (code 0.109), M 0.291 (code 0.066).

## Configs

[configs/](configs/) — Strata and llama.cpp launch configs as used.
