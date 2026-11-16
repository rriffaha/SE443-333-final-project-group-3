"""Submission gate that verifies generated tests on the buggy repository."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import NoReturn

from minisweagent.agents.interactive import InteractiveAgent, InteractiveAgentConfig
from minisweagent.exceptions import Submitted


_ASSERTION_PATTERNS = (
    re.compile(r"\bAssertionError\b"),
    re.compile(r"^E\s+assert\b", re.MULTILINE),
    re.compile(r"\bassertion failed\b", re.IGNORECASE),
)
_INVALID_PATTERNS = (
    ("collection error", re.compile(r"ERROR collecting|Interrupted: \d+ error[s]? during collection", re.IGNORECASE)),
    ("import error", re.compile(r"ImportError while importing test module|ModuleNotFoundError|ImportError:", re.IGNORECASE)),
    ("missing fixture", re.compile(r"fixture ['\"].+?['\"] not found", re.IGNORECASE)),
    ("syntax error", re.compile(r"SyntaxError|IndentationError|TabError")),
    ("pytest internal error", re.compile(r"INTERNALERROR>")),
    ("process crash", re.compile(r"segmentation fault|core dumped|Fatal Python error", re.IGNORECASE)),
    ("timeout", re.compile(r"timed? out|TimeoutExpired", re.IGNORECASE)),
)
_TEST_COMMAND_PATTERN = re.compile(
    r"(?:^|\s)(?:python(?:\d+(?:\.\d+)?)?\s+-m\s+pytest|pytest|py\.test|"
    r"python(?:\d+(?:\.\d+)?)?\s+[^;&|\n]*(?:runtests\.py|test\.py)|"
    r"\./[^;&|\n]*(?:runtests\.py|test\.py))(?:\s|$)"
)
_TRACEBACK_FRAME_PATTERN = re.compile(r"^([^\s][^:]*\.py):(\d+):", re.MULTILINE)
_PYTHON_TRACEBACK_FRAME_PATTERN = re.compile(r'^\s*File "([^"]+\.py)", line \d+', re.MULTILINE)
_SUMMARY_FAILURE_PATTERN = re.compile(r"(?:\b\d+ failed\b|^FAILED \(.+\)$)", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class GateDecision:
    accepted: bool
    category: str
    reason: str


class VerificationGateConfig(InteractiveAgentConfig):
    gate_max_retries: int = 2
    gate_timeout: int = 120


def test_paths_from_patch(patch: str) -> list[str]:
    """Return changed Python test paths from a unified diff."""
    paths: list[str] = []
    for path in changed_paths_from_patch(patch):
        parts = path.split("/")
        filename = parts[-1]
        if path.endswith(".py") and ("tests" in parts or filename.startswith("test_") or filename.endswith("_test.py")):
            if path not in paths:
                paths.append(path)
    return paths


def changed_paths_from_patch(patch: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(r"^\+\+\+ b/(.+)$", patch, re.MULTILINE)
        if match.group(1).strip() != "/dev/null"
    ]


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    filename = parts[-1]
    return (
        "tests" in parts
        or "test" in parts
        or filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename in {"conftest.py", "tox.ini"}
    )


def classify_test_result(returncode: int, output: str, test_paths: list[str]) -> GateDecision:
    """Classify whether execution demonstrates a valid buggy-repository failure."""
    if returncode == 0:
        return GateDecision(False, "passing", "The generated test passes on the buggy repository.")
    if returncode == 5 or re.search(r"no tests ran|collected 0 items", output, re.IGNORECASE):
        return GateDecision(False, "no-tests", "The command did not collect or execute a test.")

    for category, pattern in _INVALID_PATTERNS:
        if pattern.search(output):
            return GateDecision(False, category, f"Rejected because execution ended with a {category}.")

    if any(pattern.search(output) for pattern in _ASSERTION_PATTERNS):
        return GateDecision(True, "assertion-failure", "The test reached an assertion and failed.")

    if not _SUMMARY_FAILURE_PATTERN.search(output):
        return GateDecision(False, "unclassified-crash", "The command failed without a pytest test-failure summary.")

    normalized_tests = {path.removeprefix("./") for path in test_paths}
    traceback_paths = {
        match.group(1).removeprefix("./")
        for pattern in (_TRACEBACK_FRAME_PATTERN, _PYTHON_TRACEBACK_FRAME_PATTERN)
        for match in pattern.finditer(output)
    }
    library_frames = {
        path
        for path in traceback_paths
        if path not in normalized_tests
        and not any(path.endswith(f"/{test_path}") for test_path in normalized_tests)
        and "/site-packages/" not in path
        and not path.startswith("_pytest/")
        and "/tests/" not in f"/{path}"
        and not path.endswith("/conftest.py")
        and path != "conftest.py"
    }
    if library_frames:
        return GateDecision(
            True,
            "library-exception",
            "The test failed with an exception after execution entered library code.",
        )

    return GateDecision(
        False,
        "test-exception",
        "The exception originates only from the generated test, not from library code.",
    )


def build_fallback_command(test_paths: list[str]) -> str:
    quoted_paths = " ".join(shlex.quote(path) for path in test_paths)
    return f"python -m pytest -q --tb=long -- {quoted_paths}"


class VerificationGateAgent(InteractiveAgent):
    """Interactive agent that accepts only bug-reproducing test submissions."""

    def __init__(self, *args, config_class=VerificationGateConfig, **kwargs):
        super().__init__(*args, config_class=config_class, **kwargs)
        self._gate_rejections = 0

    def _latest_test_command(self) -> str | None:
        for message in reversed(self.messages):
            for action in reversed(message.get("extra", {}).get("actions", [])):
                command = action.get("command", "")
                if _TEST_COMMAND_PATTERN.search(command) and "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" not in command:
                    return command
        return None

    def _gate_feedback(self, decision: GateDecision, command: str, output: str) -> str:
        remaining = self.config.gate_max_retries - self._gate_rejections
        excerpt = output[-6000:]
        return (
            "Verification gate rejected the submitted patch.\n"
            f"Category: {decision.category}\n"
            f"Reason: {decision.reason}\n"
            f"Retries remaining: {remaining}\n"
            f"Verification command: {command}\n"
            "Revise the test, run it, rebuild patch.txt, and submit again.\n\n"
            f"Verification output:\n{excerpt}"
        )

    def _check_for_new_task_or_submit(self, submitted: Submitted) -> NoReturn:
        patch = submitted.messages[0].get("extra", {}).get("submission", "")
        changed_paths = changed_paths_from_patch(patch)
        test_paths = test_paths_from_patch(patch)
        production_paths = [path for path in changed_paths if not is_test_path(path)]
        if production_paths:
            decision = GateDecision(
                False,
                "production-change",
                f"The patch modifies non-test paths: {', '.join(production_paths)}.",
            )
            command = "<not run>"
            output = "Generation may modify test files only."
        elif not test_paths:
            decision = GateDecision(
                False,
                "invalid-patch",
                "The patch does not contain a changed Python test file.",
            )
            command = "<not run>"
            output = "No eligible test path was found in the submitted patch."
        else:
            command = self._latest_test_command() or build_fallback_command(test_paths)
            try:
                result = self.env.execute({"command": command, "timeout": self.config.gate_timeout})
                output = result.get("output", "")
                if result.get("exception_info"):
                    output = f"{output}\n{result['exception_info']}"
                decision = classify_test_result(result.get("returncode", 1), output, test_paths)
            except Exception as error:
                output = f"{type(error).__name__}: {error}"
                decision = GateDecision(
                    False,
                    "gate-execution-error",
                    "The verification command could not complete normally.",
                )

        if decision.accepted:
            raise submitted

        self._gate_rejections += 1
        feedback = self._gate_feedback(decision, command, output)
        if self._gate_rejections <= self.config.gate_max_retries:
            self._interrupt(feedback, itype="GateRejection")

        raise Submitted(
            {
                "role": "exit",
                "content": feedback,
                "extra": {
                    "exit_status": "GateRejected",
                    "submission": "",
                    "gate_category": decision.category,
                    "gate_attempts": self._gate_rejections,
                },
            }
        )