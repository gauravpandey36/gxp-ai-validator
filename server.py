import os, time, json
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from engines import risk_engine, aibom, llm
from engines.control_library import applicable

app = FastAPI(title="GxP AI Validation Companion")

_RATE = defaultdict(deque)
_LIMIT, _WINDOW = 40, 3600  # 40 assessments / hour / IP on the demo key


def _ok_rate(ip):
    now = time.time()
    q = _RATE[ip]
    while q and now - q[0] > _WINDOW:
        q.popleft()
    if len(q) >= _LIMIT:
        return False
    q.append(now)
    return True


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/status")
def status():
    return llm.spend_status()


@app.post("/api/scope")
async def scope(req: Request):
    a = (await req.json()).get("answers", {})
    risk = risk_engine.classify(a)
    controls = [{"id": c["id"], "element": c["element"], "framework": c["framework"],
                 "question": c["question"], "evidence": c["evidence"], "severity": c["severity"]}
                for c in applicable(a)]
    return {"risk": risk, "controls": controls}


@app.post("/api/assess")
async def assess(req: Request):
    body = await req.json()
    a = body.get("answers", {})
    evidence = body.get("evidence", {})
    manifest = body.get("manifest", "")
    attestation = body.get("attestation", {})
    byo_key = (body.get("byo_key") or "").strip() or None

    ip = req.client.host if req.client else "?"
    if byo_key is None and not _ok_rate(ip):
        return JSONResponse({"error": "Demo rate limit reached (40/hour). Add your own API key to continue."}, status_code=429)

    risk = risk_engine.classify(a)
    bom = aibom.extract(manifest)
    reg = risk_engine.gap_register(a, evidence)
    verdict = risk_engine.readiness_verdict(reg, risk)

    narrative, meta = _narrative(risk, reg, bom, attestation, byo_key)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "risk": risk, "aibom": bom, "register": reg, "verdict": verdict,
        "narrative": narrative, "llm": meta, "spend": llm.spend_status(),
        "attestation": attestation,
    }


def _narrative(risk, reg, bom, attestation, byo_key):
    top_gaps = [r for r in reg["rows"] if r["status"] == "GAP"][:8]
    gaps_txt = "\n".join(f"- ({r['severity']}) {r['element']}: {r['control']} [{r['framework']}]"
                         for r in top_gaps) or "- none"
    prompt = f"""You are drafting the executive section of a GxP AI validation-readiness dossier.
This is ADVISORY only; a Qualified Person / QA must review and sign. Do NOT invent facts or evidence.
Use ONLY the deterministic findings below. Be specific and sober. No marketing language.

OVERALL RISK: {risk['overall']}
FRAMEWORK CLASSIFICATION: {json.dumps(risk['frameworks'])}
READINESS: {reg['controls_met']}/{reg['controls_total']} controls have evidence; {reg['high_severity_gaps']} high-severity gaps.
OPEN GAPS:
{gaps_txt}
DISCOVERED COMPONENTS (best-effort, unverified): {json.dumps({k: bom[k] for k in ('models','providers','mcp_servers','data_stores') if bom.get(k)})}

Write, in plain English:
1. A 2-3 sentence executive summary of where this system stands and why.
2. The 3-5 highest-priority actions to make it defensible to an inspector, in order.
3. One sentence naming what a Qualified Person must verify and sign before deployment.
Keep under 280 words. End with: "AI-drafted from deterministic findings; a qualified human owns the decision."""""
    text, meta = llm.complete(prompt, byo_key=byo_key, max_tokens=900)
    if not text:
        # deterministic fallback (no LLM / over budget / no key)
        text = (f"Overall risk: {risk['overall']}. {reg['controls_met']} of {reg['controls_total']} "
                f"in-scope controls have evidence; {reg['high_severity_gaps']} high-severity gap(s) remain. "
                "Close the high-severity gaps listed in the register before sign-off. "
                "(LLM narrative unavailable — deterministic summary shown.) "
                "A qualified human owns the decision.")
        meta = {**(meta or {}), "fallback": True}
    return text, meta


app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public"), html=True), name="static")
