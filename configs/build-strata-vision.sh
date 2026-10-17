#!/usr/bin/env bash
# CPU image encoder for Strata (strata-vision = llama.cpp mtmd + the model's mmproj).
# Build it against agentionai's llama.cpp fork: Strata's own pinned llama.cpp does not know the Gyro architecture
# (qwen4exp) and cannot open the text model vocab-only. Portable (AVX2) build: per Strata's docs the AVX2 build with
# flash attention encodes faster on the CPU than the native AVX-512 build (which turns FA off).
cd ~/strata-agention
cmake -S tools/vision -B build-vision -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_DIR=$HOME/src/agention-llama -DSTRATA_VISION_CUDA=OFF
cmake --build build-vision --target strata-vision
# mmproj: mmproj-F16.gguf from agentionai/Qwen3.8-Flash-Next-Gyro-GGUF.
# Measured: 640x480 image -> 300 image tokens in ~1.4 s on 8 threads (Ryzen 7 7800X3D); +0.6-0.9 GiB RAM.
