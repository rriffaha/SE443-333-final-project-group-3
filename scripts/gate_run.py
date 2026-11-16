#!/usr/bin/env python3
"""Submission gate (arm B). Usage: python3 scripts/gate_run.py <instances.txt> [--k 2]

For each instance: run the baseline agent, run the generated test on the UNMODIFIED repo
(using the SWT-Bench harness pre-fix run), classify the outcome, and retry up to k times with
the rejection reason appended to the prompt. Falls back to the last candidate.
Reject: test passes on unmodified repo; test-side failure (ImportError, NameError, SyntaxError,
collection error, missing fixture); empty patch. Accept: assertion failure or exception from library code.
"""
import glob, json, os, re, subprocess, sys, time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MINI = os.path.join(REPO, "..", "mini-swe-agent", "mini-swe-agent")
SWT = os.path.join(REPO, "..", "swt-bench", "swt-bench")
BASE_CFG = os.path.join(REPO, "configs", "baseline_testonly.yaml")
OUT = os.path.join(REPO, "results", "gate")
DATASET = "nmuendler/SWT-Bench_Verified_bm25_27k_zsb"
RUN_ID = "hard-baseline"  # reuse so gold results are shared; model name differs so no clash
os.makedirs(OUT, exist_ok=True)

TEST_SIDE = [r"ImportError", r"ModuleNotFoundError", r"SyntaxError", r"IndentationError", r"NameError",
             r"fixture '[^']+' not found", r"ERROR collecting", r"_FailedTest", r"ERROR at setup"]


def sh(cmd, timeout=None):
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout)


def make_cfg(path, feedback):
    txt = open(BASE_CFG).read()
    if feedback:
        fb = feedback.replace("{", "(").replace("}", ")")
        block = "\n".join("    " + l for l in (
            "<previous_attempt>\n" + fb + "\n</previous_attempt>").splitlines()) + "\n"
        marker = "    </instructions>"
        assert marker in txt
        txt = txt.replace(marker, block + marker, 1)
    open(path, "w").write(txt)


def run_agent(iid, attempt, feedback):
    cfg = os.path.join(OUT, f"{iid}.a{attempt}.yaml")
    traj = os.path.join(OUT, f"{iid}.a{attempt}.traj.json")
    make_cfg(cfg, feedback)
    img = "docker.io/swebench/sweb.eval.x86_64." + iid.replace("__", "_1776_") + ":latest"
    sh(f"docker pull {img} >/dev/null")
    sh(f'cd "{MINI}" && uv run mini-extra swebench-single --subset {DATASET} --split test -i {iid} '
       f'-c "{cfg}" -o "{traj}" -y --exit-immediately > "{OUT}/{iid}.a{attempt}.log" 2>&1')
    if not os.path.exists(traj):
        return "", 0.0, "NoTrajectory"
    t = json.load(open(traj))
    info = t.get("info", {})
    return info.get("submission") or "", (info.get("model_stats") or {}).get("instance_cost", 0.0), info.get("exit_status")


def pre_fix_output(iid, attempt, patch):
    preds = os.path.join(OUT, f"{iid}.a{attempt}.preds.jsonl")
    json.dump({"instance_id": iid, "model_name_or_path": f"gate-a{attempt}", "model_patch": patch}, open(preds, "w"))
    open(preds, "a").write("\n")
    rid = f"{RUN_ID}"
    sh(f'cd "{SWT}" && uv run python -m src.main --dataset_name princeton-nlp/SWE-bench_Verified '
       f'--predictions_path "{preds}" --filter_swt --max_workers 1 --instance_ids {iid} --run_id {rid}', timeout=3600)
    files = glob.glob(f"{SWT}/run_instance_swt_logs/{rid}/pred_pre__gate-a{attempt}/{iid}/test_output.txt")
    return open(files[0], errors="replace").read() if files else ""


def classify(patch, out):
    out = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", out or "")  # strip pytest color codes
    names = re.findall(r"^\+\s*(?:async\s+)?def (test\w*)", patch, re.M)
    if not patch.strip():
        return "reject", "empty patch (nothing was submitted)"
    if not names:
        return "reject", "the patch contains no test function (no new 'def test_...')"
    if not out:
        return "reject", "the test run produced no output (it did not run)"
    failed_block, passed = None, False
    for n in names:
        m = re.search(r"^_+ [^\n]*" + re.escape(n) + r"[^\n]* _+\n(.*?)(?=\n_+ [^\n]* _+\n|\n={3,} |\Z)", out, re.S | re.M)
        if not m:
            m = re.search(r"(?:FAIL|ERROR): " + re.escape(n) + r" \(.*?\n(.*?)(?=\n={5,}|\n-{5,}\nRan |\Z)", out, re.S)
        if m:
            failed_block = m.group(0)
            break
        if re.search(re.escape(n) + r"[^\n]* \.\.\. ok", out) or re.search(r"PASSED\s+\S*" + re.escape(n), out):
            passed = True
    if failed_block is None:
        if passed:
            return "reject", "your test PASSED on the unmodified code, so it does not reproduce the issue"
        return "reject", "could not find a failing result for your new test (it may not have been collected or run)"
    for pat in TEST_SIDE:
        if re.search(pat, failed_block):
            ex = failed_block[:700]
            return "reject", f"your test failed for a test-side reason ({pat}), not because of the behavior in the issue. Excerpt:\n{ex}"
    return "accept", "test fails on the unmodified code with an assertion/library exception"


def run_instance(iid, k):
    final = os.path.join(OUT, f"{iid}.final.json")
    if os.path.exists(final):
        print("[skip]", iid); return
    feedback, attempts, patch = "", [], ""
    for a in range(k + 1):
        t0 = time.time()
        patch, cost, status = run_agent(iid, a, feedback)
        out = pre_fix_output(iid, a, patch) if patch.strip() else ""
        verdict, reason = classify(patch, out)
        attempts.append({"attempt": a, "verdict": verdict, "reason": reason[:300], "cost": cost,
                         "exit": status, "patch_chars": len(patch), "secs": int(time.time() - t0)})
        print(f"[{time.strftime('%H:%M:%S')}] {iid} attempt {a}: {verdict} - {reason[:90]!r}", flush=True)
        if verdict == "accept":
            break
        feedback = ("An automated check ran your submitted test on the unmodified repository and rejected it: "
                    + reason + "\nWrite a corrected test: it must FAIL on the current unfixed code because of "
                    "the behavior in the issue (an assertion about that behavior), not for any other reason.")
    json.dump({"instance_id": iid, "final_patch": patch, "attempts": attempts,
               "accepted": attempts[-1]["verdict"] == "accept"}, open(final, "w"), indent=1)


def write_preds():
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, "*.final.json"))):
        d = json.load(open(f))
        rows.append({"instance_id": d["instance_id"], "model_name_or_path": "gate-deepseek-flash",
                     "model_patch": d["final_patch"]})
    with open(os.path.join(OUT, "preds.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"{len(rows)} predictions -> {OUT}/preds.jsonl")


if __name__ == "__main__":
    lst = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    k = int(sys.argv[sys.argv.index("--k") + 1]) if "--k" in sys.argv else 2
    for iid in lst:
        run_instance(iid, k)
    write_preds()
