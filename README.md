# SE443-333 Final Project, Group 3

DeepSeek-Flash test generation with mini-SWE-agent, evaluated on SWT-Bench (unit-test mode).
We compare an unchanged baseline against the baseline plus ONE deliberate workflow change
(a scripted submission gate) on 13 Hard and 13 Easy SWT-Bench instances.

## Versions (pinned for reproducibility)
- mini-swe-agent: v2.4.6, commit 04d809ce
- swt-bench harness: commit be12d4c (plus one local change, see "Harness change" below)
- Model: DeepSeek-Flash, model ID `deepseek/deepseek-flash`

## Workflow change
A scripted **submission gate**. Before a generated test is accepted, it is run on the
unmodified repository and its failure reason is classified. A test that fails with an
assertion or a library exception is accepted. A test that passes, was never collected or run,
contains no test function, or fails for a test-side reason (import, collection, fixture,
syntax or name error) is rejected, and the agent is rerun with the rejection reason in its
prompt. At most 2 retries (3 attempts); if all are rejected, the last candidate is submitted.
Full procedure: `docs/gate.md`. Implementation: `scripts/gate_run.py`.

## Results (SWT-Bench harness, unit-test mode, one run per arm)
Gold patches fail on 3 Hard instances (matplotlib-25311, sphinx-8638, sphinx-8721) and 1 Easy
instance (pylint-6903), so those cannot be scored correctly by the evaluator; we report both
raw and "testable" counts.

| Arm | Hard raw (13) | Hard testable (10) | Easy raw (13) | Easy testable (12) |
|---|---|---|---|---|
| Baseline | 7/13 | 7/10 | 12/13 | 12/12 |
| Gate, as executed | n/a | 8/10 | not run | not run |
| Gate, classifier bug fixed | n/a | 7/10 | not run | not run |

The gate was run only on the 10 testable Hard instances (the Easy baseline is already at the
ceiling). Its net effect on resolve rate is not measurable here: the one extra resolved
instance (django-16631) was accepted at attempt 0, so the gate did not intervene there, and
the 8621 difference comes from a classifier bug that we found and fixed (see `docs/gate.md`).
Reports: `results/baseline/reports/`, `results/gate/reports/`.

## Harness change
In the SWT-Bench harness (`src/constants.py`, sphinx loop) we added
`sed -i 's/docutils>=0.12/docutils>=0.12,<0.18/' setup.py` after the `markupsafe<=2.0.1` line,
because unpinned docutils broke the sphinx environments (`ModuleNotFoundError: roman`).
The harness is a separate repository and is not part of this repo.

## How to reproduce
Prerequisites: Docker, `uv`, the three repos side by side (this repo, `mini-swe-agent`,
`swt-bench`), and a DeepSeek API key configured for mini-swe-agent (never commit it).
All commands from this repo's root.
1. Baseline agent runs (resumable, one instance at a time, pre-pulls the Docker image):
   `bash scripts/run_agent.sh baseline configs/baseline_testonly.yaml scripts/instances_hard.txt`
   `bash scripts/run_agent.sh baseline configs/baseline_testonly.yaml scripts/instances_easy.txt`
2. Build predictions for ONE set at a time and check it lists the right instances (`score.sh`
   always reads `results/<arm>/preds.jsonl`):
   `python3 scripts/make_preds.py baseline scripts/instances_hard.txt`
3. Score: `bash scripts/score.sh baseline hard-baseline 2`
4. Validate which instances the evaluator can score (gold patches, same run id):
   `bash scripts/score_gold.sh hard-baseline scripts/instances_hard.txt 2`
5. Gate arm (10 testable Hard instances):
   `python3 scripts/gate_run.py scripts/instances_hard_testable.txt --k 2`
   then `bash scripts/score.sh gate hard-baseline 2`.

## Layout
- `configs/` frozen baseline config, including the prompt
- `scripts/` run, scoring and prediction scripts, instance lists, and the gate (`gate_run.py`)
- `results/baseline/` baseline trajectories, predictions, `reports/` (harness summaries)
- `results/gate/` per-attempt gate trajectories and predictions, `*.final.json` records,
  `reports/`, and `old_buggy_classifier/` (records made before the classifier fixes)
- `results/gate8621/` corrected sphinx-8621 candidate, scored separately
- `docs/` gate procedure, contributions, AI disclosure

## Running things (verified on the pilot, pydata__xarray-3677)
1. Agent (mini-swe-agent, dataset = SWT-Bench Verified, config = configs/baseline_testonly.yaml):
   `uv run mini-extra swebench-single --subset nmuendler/SWT-Bench_Verified_bm25_27k_zsb --split test -i <instance> -c <config> -o <traj> -y --exit-immediately`
2. Pre-pull the instance image first (`docker pull docker.io/swebench/sweb.eval.x86_64.<id with __ -> _1776_>:latest`), otherwise mini-swe-agent's 120 s docker-run timeout fires.
3. Score (swt-bench, unit-test mode): use the STANDARD dataset, no `--is_swt`:
   `python -m src.main --dataset_name princeton-nlp/SWE-bench_Verified --predictions_path <preds.jsonl> --filter_swt --max_workers 1 --instance_ids <id> --run_id <run>`
   (Scoring against the nmuendler SWT dataset, with or without `--is_swt`, never applied the real code fix: all tests were F->F.)
4. Limits (both arms): step_limit 75, cost_limit 0.10 USD. Pilot cost: 7 calls, about 0.0024 USD.
