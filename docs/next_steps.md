# Next Steps: Easy Gate Experiment

This runbook starts from the current state:

- The Easy baseline trajectories already exist in `results/baseline/`.
- The gate accepted `pydata__xarray-3677`, which already exists in `results/gate/`.
- The remaining Easy gate instances still need to be generated and evaluated.

Run all commands from the final-project repository:

```bash
cd "/home/carlos/Documents/SE 333/SE443-333-final-project-group-3"
```

## 1. Check prerequisites

Confirm Docker is running and the DeepSeek key is configured without printing its value:

```bash
docker info >/dev/null && echo "Docker is ready"
grep -q '^DEEPSEEK_API_KEY=' ~/.config/mini-swe-agent/.env \
  && echo "DeepSeek key is configured"
```

## 2. Generate the remaining gate trajectories

```bash
bash scripts/run_agent.sh \
  gate \
  configs/baseline_testonly.yaml \
  scripts/instances_easy.txt \
  configs/verification_gate.yaml
```

The runner is resumable. It skips `pydata__xarray-3677` and any other instance that already has a `.traj.json` file. This phase makes paid DeepSeek API calls, with a configured limit of $0.10 per new instance.

In another terminal, monitor progress with:

```bash
find results/gate -maxdepth 1 -name '*.traj.json' | wc -l
tail -f results/gate/*.log
```

Generation is complete when there are 13 gate trajectory files:

```bash
test "$(find results/gate -maxdepth 1 -name '*.traj.json' | wc -l)" -eq 13 \
  && echo "All 13 Easy gate trajectories exist"
```

## 3. Build predictions for both Easy arms

Regenerate both files from the same 13-instance list so the comparison is paired and contains no Hard instances:

```bash
python3 scripts/make_preds.py baseline scripts/instances_easy.txt
python3 scripts/make_preds.py gate scripts/instances_easy.txt
```

Check that both prediction files contain 13 rows:

```bash
wc -l results/baseline/preds.jsonl results/gate/preds.jsonl
```

Review the `make_preds.py` output for `MISSING`, empty patches, `GateRejected`, limits, or timeouts. Keep all 13 assigned instances in the denominator; do not delete unsuccessful rows.

## 4. Run official SWT-Bench scoring

Use the standard SWE-bench Verified dataset in unit-test mode. Do not add `--is_swt`.

Start conservatively with one Docker worker:

```bash
bash scripts/score.sh baseline easy-baseline-20261115 1
bash scripts/score.sh gate easy-gate-20261115 1
```

These commands make no DeepSeek API calls. The first evaluation for a repository can be slow because Docker builds an environment image.

## 5. Run gold patches for coverage data

Use the matching run ID for each arm:

```bash
bash scripts/score_gold.sh \
  easy-baseline-20261115 \
  scripts/instances_easy.txt \
  1

bash scripts/score_gold.sh \
  easy-gate-20261115 \
  scripts/instances_easy.txt \
  1
```

Do not regenerate predictions in response to evaluator results. Retry only unchanged predictions after an infrastructure failure.

## 6. Record the required results

For each of the 13 Easy instances, record:

- Baseline resolved or unresolved
- Gate resolved or unresolved
- Patch applied or failed to apply
- Gate exit status, including `GateRejected`
- Generation cost and API calls
- Generation and evaluation time
- Coverage delta, or N/A when unavailable

Build the paired outcome table:

| Outcome | Count |
|---|---:|
| Both methods succeed | |
| Baseline only succeeds | |
| Gate only succeeds | |
| Neither method succeeds | |

Report success and applicability over all 13 assigned Easy instances. Missing predictions, rejected candidates, generation failures, and method-caused timeouts count as unsuccessful.

## 7. Complete the required case analysis

Select six distinct instances using a documented systematic rule, such as sorting instance IDs within each category. Include, when available:

- Two successful reproductions
- Two unsuccessful reproductions
- Two cases where baseline and gate disagree

For every selected instance, discuss the issue, generated test, behavior before and after the fix, whether the test meaningfully represents the issue, and what the result reveals about the workflow.

## 8. Freeze and preserve artifacts

Once full generation begins, do not change the gate logic or frozen configurations. Preserve:

- `configs/baseline_testonly.yaml`
- `configs/verification_gate.yaml`
- `src/gate.py`
- All trajectories and logs
- Both prediction JSONL files
- Harness reports and coverage output
- Per-instance costs and paired outcomes

Mutation testing is optional follow-up analysis only; it should not replace the primary baseline-versus-gate comparison.