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
        "flags": _flags(a, annex22),
    }


def _flags(a, annex22):
    """Primary-source-verified regulatory advisories (the part experts respect)."""
    f = []
    llm = a.get("model_type") == "llm"
    adaptive = a.get("adaptive") == "learning"
    impact = bool(a.get("impact"))
    critical = annex22 == "Critical"
    if llm and (critical or impact):
        f.append({"level": "stop", "title": "Generative AI / LLM in a critical GMP use",
                  "text": "The EU GMP Annex 22 (AI) draft covers deterministic models only and states "
                          "Generative AI and LLMs “should not be used in critical GMP applications.” "
                          "Confine this to non-critical use, wrap it in a deterministic + human-signed control "
                          "layer, or use a deterministic model for the critical decision."})
    if adaptive and impact:
        f.append({"level": "stop", "title": "Dynamic / continuously-learning model in a GxP-impacting use",
                  "text": "The Annex 22 draft excludes dynamic, continuously-learning models from critical GMP. "
                          "Lock the model, or file a Predetermined Change Control Plan (PCCP) with a defined "
                          "revalidation trigger before deployment."})
    if a.get("autonomy") == "automated" and impact:
        f.append({"level": "warn", "title": "Automated action without mandatory human review",
                  "text": "FDA cited 21 CFR 211.22 in the first AI cGMP warning letter (Purolea, 04/2026): "
                          "AI-generated GxP outputs must be reviewed and cleared by the Quality Unit before use."})
    f.append({"level": "info", "title": "Human accountability is non-transferable",
              "text": "AI may draft and recommend; a Qualified Person / Quality Unit must review, approve, and "
                      "sign every GxP decision (FDA 21 CFR 211.22; ISPE GAMP AI 2026 — qualify the tool itself, "
                      "final responsibility stays with qualified personnel)."})
    return f


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
