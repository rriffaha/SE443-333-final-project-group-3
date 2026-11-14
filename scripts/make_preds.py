"""Build a predictions JSONL from trajectory files.
Usage: python3 scripts/make_preds.py <arm> [instances.txt]
Writes results/<arm>/preds.jsonl and prints per-instance steps, cost, exit status.
"""
import json, sys, pathlib
arm = sys.argv[1]
root = pathlib.Path(__file__).resolve().parent.parent / "results" / arm
ids = [l.strip() for l in open(sys.argv[2])] if len(sys.argv) > 2 else sorted(p.name[:-10] for p in root.glob("*.traj.json"))
rows, tot = [], 0.0
for i in ids:
    if not i: continue
    p = root / f"{i}.traj.json"
    if not p.exists():
        print(f"{i}: MISSING"); continue
    t = json.load(open(p)); info = t["info"]; ms = info.get("model_stats", {})
    patch = info.get("submission") or ""
    tot += ms.get("instance_cost", 0)
    print(f"{i}: exit={info.get('exit_status')} calls={ms.get('api_calls')} cost=${ms.get('instance_cost', 0):.4f} patch_chars={len(patch)}")
    rows.append({"instance_id": i, "model_name_or_path": f"{arm}-deepseek-flash", "model_patch": patch})
with open(root / "preds.jsonl", "w") as f:
    for r in rows: f.write(json.dumps(r) + "\n")
print(f"{len(rows)} predictions, total agent cost ${tot:.4f} -> {root/'preds.jsonl'}")
