#!/usr/bin/env python3
"""L7 — validate the validator.
Compares (a) the deterministic engine and (b) two independent cross-family LLM assessors
(Claude + Llama) against an expert golden label set. Reports accuracy + Cohen's kappa.
Run locally: keys from the iCloud secrets file. Budget-light (~24 LLM calls)."""
import json, re, sys, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engines import risk_engine  # noqa

SEC = Path.home()/"Library"/"Mobile Documents"/"com~apple~CloudDocs"/"PJ_Memory"/".secrets"/"api_keys.env"
K = {}
for l in SEC.read_text().splitlines():
    l = l.strip()
    if "=" in l and not l.startswith("#"):
        k, v = l.split("=", 1); K[k.strip()] = v.strip().strip('"').strip("'")

SCEN = json.loads((Path(__file__).parent/"scenarios.json").read_text())
OUTD = Path(__file__).parent/"results"; OUTD.mkdir(exist_ok=True)

RUBRIC = """You are an independent GxP + AI validation expert. Classify the AI system described.
Definitions:
- overall: HIGH, MEDIUM, or LOW regulatory/validation risk.
- annex22 (EU GMP Annex 22 criticality): "Critical" = direct impact on patient safety, product quality,
  or data integrity AND it enters/acts on GxP records or acts autonomously; "Significant" = such impact
  but it does NOT enter GxP records and is not autonomous; "Non-critical" = no such direct impact.
- llm_stop (true/false): is this a Generative AI / Large Language Model used in a CRITICAL GMP application?
  (Under the Annex 22 draft, LLMs should not be used in critical GMP applications.)
- dynamic_stop (true/false): is this a dynamic/continuously-learning model used in a GxP-impacting application?
Output ONLY compact JSON: {"overall":"...","annex22":"...","llm_stop":bool,"dynamic_stop":bool}"""


def _json(txt):
    m = re.search(r"\{.*\}", txt or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


def claude(desc):
    body = json.dumps({"model": "claude-sonnet-4-6", "max_tokens": 200,
                       "system": RUBRIC, "messages": [{"role": "user", "content": desc}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": K["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return _json("".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"))


def llama(desc):
    body = json.dumps({"model": "meta-llama/llama-3.3-70b-instruct",
                       "messages": [{"role": "system", "content": RUBRIC}, {"role": "user", "content": desc}],
                       "max_tokens": 200}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {K['OPENROUTER_API_KEY']}", "content-type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=90).read())
    return _json(d["choices"][0]["message"]["content"])


def engine_assess(ans):
    r = risk_engine.classify(ans)
    titles = " ".join(f["title"] for f in r["flags"])
    return {"overall": r["overall"], "annex22": r["frameworks"]["EU GMP Annex 22"],
            "llm_stop": "Generative AI / LLM" in titles, "dynamic_stop": "Dynamic" in titles}


def kappa(a, b):
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(l)/n) * (b.count(l)/n) for l in labels)
    return round((po - pe) / (1 - pe), 3) if pe != 1 else 1.0, round(po, 3)


rows = []
for s in SCEN:
    g = s["golden"]
    eng = engine_assess(s["answers"])
    try:
        cl = claude(s["desc"])
    except Exception as e:
        cl = {"_err": str(e)}
    try:
        ll = llama(s["desc"])
    except Exception as e:
        ll = {"_err": str(e)}
    rows.append({"id": s["id"], "golden": g, "engine": eng, "claude": cl, "llama": ll})
    print(f"{s['id']}  gold={g['overall']:<6} eng={eng['overall']:<6} claude={cl.get('overall','?'):<6} llama={ll.get('overall','?')}", flush=True)

def col(rows, who, key):
    return [str(r[who].get(key, "NA")) for r in rows]

gold_o = col(rows, "golden", "overall")
metrics = {"n": len(rows)}
for who in ("engine", "claude", "llama"):
    o = col(rows, who, key="overall")
    acc_overall = round(sum(1 for x, y in zip(o, gold_o) if x == y)/len(o), 3)
    a22 = col(rows, who, "annex22"); ga22 = col(rows, "golden", "annex22")
    acc_a22 = round(sum(1 for x, y in zip(a22, ga22) if x == y)/len(a22), 3)
    k_overall, po = kappa(o, gold_o)
    # stop-flag recall (only items where golden stop is true)
    def recall(gkey, akey):
        idx = [i for i, r in enumerate(rows) if r["golden"].get(gkey)]
        if not idx: return None
        return round(sum(1 for i in idx if rows[i][who].get(akey))/len(idx), 3)
    metrics[who] = {"overall_accuracy": acc_overall, "overall_kappa_vs_golden": k_overall,
                    "annex22_accuracy": acc_a22, "llm_stop_recall": recall("stop_llm","llm_stop"),
                    "dynamic_stop_recall": recall("stop_dynamic","dynamic_stop")}
# inter-assessor kappa (claude vs llama)
metrics["claude_vs_llama_overall_kappa"] = kappa(col(rows,"claude","overall"), col(rows,"llama","overall"))[0]

(OUTD/"per_item.json").write_text(json.dumps(rows, indent=2))
(OUTD/"metrics.json").write_text(json.dumps(metrics, indent=2))
print("\n=== METRICS ==="); print(json.dumps(metrics, indent=2))

# blinded human rating sheet + key
import csv
with open(Path(__file__).parent/"human_rating_sheet.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["scenario_id", "description", "rater_id", "human_overall(HIGH/MEDIUM/LOW)", "human_annex22(Critical/Significant/Non-critical)", "llm_in_critical_stop(Y/N)", "dynamic_in_critical_stop(Y/N)"])
    for s in SCEN: w.writerow([s["id"], s["desc"], "", "", "", "", ""])
with open(Path(__file__).parent/"human_rating_KEY.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["scenario_id", "golden_overall", "golden_annex22", "llm_stop", "dynamic_stop"])
    for s in SCEN: g = s["golden"]; w.writerow([s["id"], g["overall"], g["annex22"], g["stop_llm"], g["stop_dynamic"]])
print("wrote human_rating_sheet.csv + KEY")
