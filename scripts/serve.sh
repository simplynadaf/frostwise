#!/usr/bin/env bash
# Dev helper: launch FrostWise in the background (used during development/testing).
cd "$(dirname "$0")/.." || exit 1
export FROSTWISE_MODEL="${FROSTWISE_MODEL:-gemma3:1b}"
pkill -9 -f "uvicorn frostwise.api" 2>/dev/null
sleep 1
nohup python3 -m uvicorn frostwise.api:app --host 127.0.0.1 --port 8077 \
  > /tmp/frostwise.log 2>&1 &
echo "launched pid $! (model=$FROSTWISE_MODEL) -> http://127.0.0.1:8077"
