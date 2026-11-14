# SE443-333 Final Project, Group 3

DeepSeek-Flash test generation with mini-SWE-agent, evaluated on SWT-Bench (unit-test mode).

## Versions (pinned for reproducibility)
- mini-swe-agent: v2.4.6, commit 04d809ce
- swt-bench harness: commit be12d4c
- Model: DeepSeek-Flash (exact model ID: TODO)

## Workflow change
TODO

## How to reproduce
TODO

## Layout
- `configs/` frozen baseline and workflow configs, including prompts
- `src/` gate subclass and failure classifier
- `scripts/` predictions conversion, paired-table builder
- `results/` predictions, trajectories, evaluation output, logs
- `docs/` workflow procedure, contributions, AI disclosure

## Running things (verified on the pilot, pydata__xarray-3677)
1. Agent (mini-swe-agent, dataset = SWT-Bench Verified, config = configs/baseline_testonly.yaml):
   `uv run mini-extra swebench-single --subset nmuendler/SWT-Bench_Verified_bm25_27k_zsb --split test -i <instance> -c <config> -o <traj> -y --exit-immediately`
2. Pre-pull the instance image first (`docker pull docker.io/swebench/sweb.eval.x86_64.<id with __ -> _1776_>:latest`), otherwise mini-swe-agent's 120 s docker-run timeout fires.
3. Score (swt-bench, unit-test mode): use the STANDARD dataset, no `--is_swt`:
   `python -m src.main --dataset_name princeton-nlp/SWE-bench_Verified --predictions_path <preds.jsonl> --filter_swt --max_workers 1 --instance_ids <id> --run_id <run>`
   (Scoring against the nmuendler SWT dataset, with or without `--is_swt`, never applied the real code fix: all tests were F->F.)
4. Limits (both arms): step_limit 75, cost_limit 0.10 USD. Pilot cost: 7 calls, about 0.0024 USD.
