# Verification Gate Procedure

1. DeepSeek-Flash follows the baseline prompt and submits a test-only unified diff.
2. The gate extracts changed Python test paths from the diff.
3. It reruns the most recent test command issued by the agent on the unchanged buggy repository. If no test command is available, it runs those paths with `python -m pytest -q --tb=long`.
4. It accepts assertion failures and exceptions with a traceback frame in non-test library code.
5. It rejects passing or uncollected tests, import and collection errors, missing fixtures, syntax errors, test-originated exceptions, timeouts, internal errors, and process crashes.
6. For a rejection, the model receives the category, command, and bounded output excerpt. It may revise and resubmit twice.
7. The first accepted candidate is final. After the initial attempt plus two rejected retries, the run ends with `GateRejected` and an empty patch.

The gate sees only the issue, buggy repository, generated patch, and local execution output. It does not use the reference fix, reference tests, or evaluator results. Official SWT-Bench scoring remains the final authority for fail-before/pass-after success.