# Contributions

## Riffa Hammed
- Set up the repository, pinned versions, baseline config and prompt, and the pilot run.
- Wrote the run/prediction/scoring scripts (`run_agent.sh`, `make_preds.py`, `score.sh`,
  `score_gold.sh`) and ran the baseline agent on all 26 Hard and Easy instances.
- Scored the baseline with the SWT-Bench harness, diagnosed the evaluator failures (docutils /
  `roman` import in sphinx, setuptools_scm and pylint environment errors), made and documented
  the harness change, and ran the gold-patch validation that identified the 4 non-scoreable
  instances.
- Categorized the baseline failures.
- Wrote and ran the submission gate (`scripts/gate_run.py`) on the 10 testable Hard instances,
  found and fixed two classifier bugs, scored the gate predictions, and compared them with the
  baseline.
- Reviewed the teammate's draft gate and slide draft.

## Carlos Atienza
- Did not contribute until Nov 15 (the gate and the full experiment had already been built and
  run by Riffa). On Nov 15 he pushed a separate in-loop gate draft on branch `gate-draft`
  (`src/gate.py`, `configs/verification_gate.yaml`, `docs/gate.md`, `docs/next_steps.md`),
  tested only on pydata__xarray-3677.
- Created the presentation and full report.

## Notes
- Commits 6fbd49f to 7c4582e appear on GitHub with the author name `NAME FROM ABOVE`. This is a
  local git configuration error (placeholder values in the repository's `.git/config`, found and
  fixed on Nov 15). All of those commits were made by Riffa from her own machine.
- The project log kept during the work (problems, fixes, and the scoring mix-up described in
  the report) is the record of how the results were produced.
