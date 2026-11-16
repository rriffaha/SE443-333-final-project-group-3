# Submission gate: procedure

The gate is the one deliberate workflow change. It sees only the issue, the buggy repository,
the generated patch and the local test output. It never uses the reference fix, the reference
tests or the evaluator's verdict. Official SWT-Bench scoring remains the final authority.

## Procedure (`scripts/gate_run.py`)
1. Run the baseline agent (same config and prompt) on an instance. It submits a test-only diff.
2. Write the diff as a prediction and run the SWT-Bench harness on that single instance to get
   the pre-fix output (the generated test on the unmodified repository).
3. Classify the output:
   - **Reject:** empty patch; no new `def test_...`; no output / test did not run; no failing
     result found for the new test (not collected or run); the new test PASSED on the
     unmodified code; or a test-side failure (ImportError, collection error, missing fixture,
     SyntaxError, NameError and similar).
   - **Accept:** the new test fails on the unmodified code with an assertion or an exception
     from library code.
4. On rejection, rerun the agent from scratch with a `<previous_attempt>` block in its prompt
   giving the rejection reason and asking for a test that fails because of the behavior in the
   issue. At most k=2 retries (3 attempts).
5. The first accepted candidate is final. If all attempts are rejected, the last candidate is
   submitted (fallback), so the gate can never produce an empty submission.

Per-instance records are in `results/gate/<instance>.final.json` (attempts, verdicts, reasons,
final patch). The run is resumable.

## Known limitations
- The gate checks the test only on the unmodified repository. It cannot see a test that also
  fails after the real fix (django-16631 baseline) or one that depends on code the fix removes
  (django-12155).
- Accepting "library exceptions" could accept environment errors if the agent's container shows
  the same problem as the evaluator.
- The Easy baseline already resolves 12/12 testable instances, so the gate has little headroom.

## Classifier bugs found and fixed (Nov 15)
1. pytest colour escape codes broke the output patterns on sphinx; fixed by stripping ANSI
   codes. Affected sphinx runs were redone.
2. For long parametrized test names pytest prints failure headers with a single underscore
   (`_ test_name[...] _`); the failing-block regex required three or more, missed the failure and
   reported "test PASSED". This falsely rejected sphinx-8621 attempts 1 and 2. Fixed; re-classifying
   all 17 stored attempts changed only those two verdicts. The corrected attempt 1 was scored
   separately (`results/gate8621/`) and is unresolved. Originals are kept in
   `results/gate/old_buggy_classifier/`.

## Alternative implementation
A teammate's in-loop version (an `InteractiveAgent` subclass that reruns the agent's last test
command in the same container) is on branch `gate-draft`. It was tested only on
pydata__xarray-3677 and is not used for the reported results.
