#!/usr/bin/env bash
# usage: bash scripts/score_gold.sh <run_id> <instances.txt> [workers=2]
# Runs the harness on the gold patches for the listed instances, in the same run_id
# as the agent scoring, so base/gold results and coverage delta are available.
set -euo pipefail
RUN=$1; LIST=$(realpath "$2"); W=${3:-2}
cd "$(dirname "$0")/../../swt-bench/swt-bench"
uv run python -m src.main --dataset_name princeton-nlp/SWE-bench_Verified \
  --predictions_path gold --filter_swt --max_workers "$W" --run_id "$RUN" \
  --instance_ids $(tr '\n' ' ' < "$LIST")
