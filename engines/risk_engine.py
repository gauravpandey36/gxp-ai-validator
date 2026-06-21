"""Deterministic risk-tier + gap engine. Same input -> same output, every run.
The LLM never makes a gating decision here."""
from engines.control_library import applicable


def classify(a):
    impact = bool(a.get("impact"))
    records = bool(a.get("enters_records"))
    auto = a.get("autonomy") == "automated"
    adaptive = a.get("adaptive") == "learning"
    build = a.get("build")
    llm = a.get("model_type") == "llm"

    # EU GMP Annex 22 criticality
    if impact and (records or auto):
        annex22 = "Critical"
    elif impact:
        annex22 = "Significant"
    else:
        annex22 = "Non-critical"

    # EU AI Act
    euaiact = "High-risk (GxP impact)" if impact else "Limited / minimal risk"

    # GAMP 5 software category
    gamp = {"cots": "Category 3", "configured": "Category 4",
            "finetuned": "Category 5", "custom": "Category 5"}.get(build, "Category 4")
    if adaptive:
        gamp += " + dynamic (App. D11)"

    # autonomy posture
    if auto:
        autonomy = "Elevated — automated action; HITL strongly indicated"
    elif a.get("autonomy") == "advisory":
        autonomy = "Moderate — advisory without per-output review"
    else:
        autonomy = "Lower — decision support, human approves each output"

    # overall
    if annex22 == "Critical" or impact and auto:
        overall = "HIGH"
    elif impact or "Category 5" in gamp or adaptive or llm:
        overall = "MEDIUM"
    else:
        overall = "LOW"

    return {
        "overall": overall,
        "frameworks": {
            "EU GMP Annex 22": annex22,
            "EU AI Act": euaiact,
            "GAMP 5": gamp,
            "Autonomy posture": autonomy,
        },
        "rationale": _rationale(impact, records, auto, adaptive, llm),
    }


def _rationale(impact, records, auto, adaptive, llm):
    bits = []
    bits.append("Direct impact on patient safety / product quality / data integrity: "
                + ("YES" if impact else "no"))
    bits.append("Outputs enter or change GxP records: " + ("YES" if records else "no"))
    bits.append("Autonomy: " + ("automated action" if auto else "human in the loop"))
    bits.append("Adaptive / learning model: " + ("YES — PCCP territory" if adaptive else "locked"))
    if llm:
        bits.append("Generative/LLM: hallucination + grounding controls required")
    return bits


def gap_register(answers, evidence):
    """evidence: {control_id: {'have': bool, 'note': str}}"""
    rows = []
    for c in applicable(answers):
        ev = evidence.get(c["id"], {})
        have = bool(ev.get("have"))
        rows.append({
            "id": c["id"], "element": c["element"], "framework": c["framework"],
            "clause": c["clause"], "control": c["control"], "evidence": c["evidence"],
            "severity": c["severity"], "status": "Provided" if have else "GAP",
            "note": (ev.get("note") or "").strip(),
        })
    gaps = [r for r in rows if r["status"] == "GAP"]
    high_gaps = [r for r in gaps if r["severity"] == "high"]
    score = round(100 * (len(rows) - len(gaps)) / len(rows)) if rows else 0
    return {
        "controls_total": len(rows), "controls_met": len(rows) - len(gaps),
        "gaps": len(gaps), "high_severity_gaps": len(high_gaps),
        "readiness_pct": score, "rows": rows,
    }


def readiness_verdict(reg, risk):
    if reg["high_severity_gaps"] == 0 and reg["gaps"] == 0:
        return "Evidence complete for the controls in scope — ready for QA review and sign-off."
    if reg["high_severity_gaps"] > 0:
        return (f"NOT ready: {reg['high_severity_gaps']} high-severity evidence gap(s) must close "
                f"before this {risk['overall']}-risk system is defensible to an inspector.")
    return (f"Conditionally ready: {reg['gaps']} lower-severity gap(s) open. Close or risk-justify "
            "before sign-off.")
