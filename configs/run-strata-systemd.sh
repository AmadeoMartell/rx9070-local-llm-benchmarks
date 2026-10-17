#!/usr/bin/env bash
# Start the Strata rc2 server (Gyro-S or Gyro-M) as a systemd transient unit.
#  - MemoryMax=29G: on a 32 GB box an OOM kills only the model server, never the machine.
#  - MemorySwapMax=0: the server is never swapped out -> ~0 SSD writes (resident experts + PLE table read with O_DIRECT).
#  - LimitMEMLOCK=infinity: resident experts are page-locked.
# CFG = one of the JSON files in this folder (port 8081, put "api_key" in it or set STRATA_API_KEY).
A=~/strata-agention          # agentionai/Strata, branch rc2, built for HIP gfx1201
CFG=${1:-$A/strata-gyro-s-262k-vision.json}
sudo systemd-run --unit=strata-gyro --uid="$USER" --gid="$USER" -p WorkingDirectory=$A -p LimitMEMLOCK=infinity \
  -p MemoryMax=29G -p MemorySwapMax=0 -p IOAccounting=yes -E HOME=$HOME -E HIP_VISIBLE_DEVICES=0 \
  -p StandardOutput=append:$HOME/strata-gyro-server.log -p StandardError=append:$HOME/strata-gyro-server.log \
  $A/.venv/bin/python -m serve.server --engine strata --config "$CFG" --port 8081
# ready when:   curl -sf -H "Authorization: Bearer $KEY" http://127.0.0.1:8081/v1/models
# stop:         sudo systemctl stop strata-gyro
