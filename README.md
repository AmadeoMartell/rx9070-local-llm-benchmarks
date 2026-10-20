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

Gyro-M     1014 / 50 at 106K; review scores within noise of Gyro-S; ~2.4 GiB RAM headroom on 32 GB
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

² In the Java run the agent let the context grow to 203K without compaction; decode medians by context of its
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
| Qwen3.8-27B UD-IQ4_XS, adaptive-KV-stream fork ² | 262K | medium | 78 min | done | 27.5 | 32.5 |
| Gyro-S | 131K | medium | 21 min | done | 39 | 35.5 |
| Gyro-S | 131K | xhigh | 33 min | done | 43.5 | 34.5 |
| Gyro-S | 131K | xhigh | 29 min | done | 36 | 31.5 |
| Gyro-S + vision | 262K | xhigh | 39 min | done | 40.5 | 31 |
| Gyro-S + vision | 262K | medium | 48 min¹ | done | 43.5 | 29 |
| Gyro-M | 131K | xhigh | 37 min | done | 42.5 | 34 |
| Gyro-M | 131K | medium | 53 min¹ | done | 44 | 29 |
| Qwen3.8-27B UD-IQ4_XS (Windows, r28) | 106K | medium | 55 min | 7/8 checklist | — | — |
| Qwen3.8-27B GSQ IQ3_S q8_0 KV (Windows) | 106K | medium | 65 min | 7/8 checklist | — | — |
| Qwen3.8-27B heretic-ara IQ4_XS (Windows) | 106K | medium | — | 5/8 checklist | 22 (other batch) | — |
| Qwen3.8-27B Fable i1-IQ3_M (Windows) | 106K | medium | — | 4/8 checklist | 18 (other batch) | — |

¹ Waiting on `search.maven.org`: ~17 min (Gyro-S), ~9 min (Gyro-M). It also returned stale versions (grpc-api 1.73.0 vs 1.85.0 in `repo1`).

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
