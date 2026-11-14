#!/usr/bin/env bash
# Usage: bash scripts/score.sh <arm> <run_id> [max_workers]
# Scores results/<arm>/preds.jsonl in unit-test mode against the STANDARD SWE-bench Verified dataset.
set -eu
ARM="$1"; RUN="$2"; W="${3:-2}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO/../swt-bench/swt-bench"
uv run python -m src.main --dataset_name princeton-nlp/SWE-bench_Verified \
  --predictions_path "$REPO/results/$ARM/preds.jsonl" --filter_swt \
  --max_workers "$W" --run_id "$RUN"
