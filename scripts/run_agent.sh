#!/usr/bin/env bash
# Usage: bash scripts/run_agent.sh <arm> <config.yaml> <instances.txt> [overlay.yaml]
#   e.g. bash scripts/run_agent.sh gate configs/baseline_testonly.yaml scripts/instances_easy.txt configs/verification_gate.yaml
# Runs mini-swe-agent one instance at a time, resumable (skips instances whose trajectory exists).
set -u
ARM="$1"; CFG="$(realpath "$2")"; LIST="$(realpath "$3")"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
EXTRA_ARGS=()
if [ -n "${4:-}" ]; then EXTRA_ARGS=(-c "$(realpath "$4")"); fi
OUT="$REPO/results/$ARM"; mkdir -p "$OUT"
AGENT_REPO="${MINISWEAGENT_REPO:-$REPO/../mini-swe-agent}"
if [ -d "$AGENT_REPO/mini-swe-agent" ]; then AGENT_REPO="$AGENT_REPO/mini-swe-agent"; fi
cd "$AGENT_REPO" || exit 1
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
DATASET="nmuendler/SWT-Bench_Verified_bm25_27k_zsb"
while read -r ID; do
  [ -z "$ID" ] && continue
  if [ -f "$OUT/$ID.traj.json" ]; then echo "[skip] $ID"; continue; fi
  IMG="docker.io/swebench/sweb.eval.x86_64.${ID//__/_1776_}:latest"
  echo "[$(date +%H:%M:%S)] $ID: pulling image"
  docker pull "$IMG" >/dev/null || { echo "[fail-pull] $ID"; continue; }
  echo "[$(date +%H:%M:%S)] $ID: running agent"
  uv run mini-extra swebench-single --subset "$DATASET" --split test -i "$ID" \
      -c "$CFG" "${EXTRA_ARGS[@]}" -o "$OUT/$ID.traj.json" -y --exit-immediately > "$OUT/$ID.log" 2>&1
  echo "[$(date +%H:%M:%S)] $ID: done (exit $?)"
done < "$LIST"
