# AI disclosure

## The system under evaluation
DeepSeek-Flash (`deepseek/deepseek-flash`) run through mini-swe-agent v2.4.6 generates the tests
that are being evaluated. This is the object of the experiment, not a writing aid.

## AI assistance in building and analyzing the project (Claude, Anthropic)
Claude was used as an assistant throughout the work, with Riffa running every command and
checking the outputs:
- Writing and debugging helper scripts: the prediction and scoring scripts and the gate
  (`scripts/gate_run.py`), including the classifier fixes.
- Diagnosing evaluator and environment failures from the logs (docutils / `roman`,
  setuptools_scm, pylint), suggesting the gold-patch validation, and finding the two gate
  classifier bugs by comparing the gate's verdicts with the harness output.
- Reading and comparing results (resolved counts, failure categories), and reviewing the
  teammate's draft gate.
- Drafting the README and the files in `docs/` from the project log.
- Explaining concepts and outlining the presentation and report.
- Organized sections, formatting tables and references, and providing guidance for compiling the document with Overleaf.

## What AI did not do
- All numbers come from the SWT-Bench harness output committed in `results/`; none were
  produced by the assistant from memory.
- The report text and the slides are written by the students; AI was used to explain, to
  check numbers against the results, and to tighten wording afterwards.

## Where AI was wrong during the work (kept for honesty)
- Early on the assistant gave an incorrect explanation for the sphinx failures and wrongly
  assumed all five failed at environment setup before checking each one; both were corrected by
  looking at the actual logs.
- A scoring run was started on the wrong predictions file (documented in the project log and
  caught by checking the resolved list).
