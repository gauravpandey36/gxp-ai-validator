#!/usr/bin/env python3
"""Expand the L7 scenario bank to 50 for vendor pilots + human rating.
Golden for S16+ is RULE-DERIVED from the pre-registered engine (documented as such);
the original S01-S15 remain human-verified. Independent-assessor kappa (Claude/Llama)
is the real test of whether the rule labels generalize."""
import json, sys
sys.path.insert(0, ".")
from engines import risk_engine

# (use_phrase, function, impact, records, autonomy, model_type, build, adaptive, data, agentic, governance)
SPECS = [
 ("Soft-sensor predicts product potency in continuous manufacturing; advisory to operators","Manufacturing / MES",True,False,"advisory","predictive","custom","locked","gxp_records","no","established"),
 ("Multivariate statistical process control flags batch excursions; human reviews","QC / LIMS",True,True,"decision_support","ml","configured","locked","gxp_records","no","developing"),
 ("Advanced process control autonomously adjusts a non-critical utility loop","Manufacturing / MES",False,False,"automated","ml","custom","learning","internal","no","established"),
 ("LLM converts master batch records into electronic batch records; QA approves","Manufacturing / MES",True,True,"advisory","llm","configured","locked","gxp_records","no","developing"),
 ("Agentic assistant drafts a deviation investigation and pulls prior cases via tools","Quality / QMS (deviation, CAPA)",True,False,"advisory","llm","cots","locked","internal","yes","developing"),
 ("Pharmacovigilance signal-detection ML over adverse-event data; advisory","Pharmacovigilance",True,False,"decision_support","ml","configured","learning","personal_phi","no","established"),
 ("LLM auto-codes ICSR adverse events into the safety database automatically","Pharmacovigilance",True,True,"automated","llm","finetuned","locked","personal_phi","no","developing"),
 ("Vision model detects particulates in vials; flags for human inspector","Manufacturing / MES",True,True,"decision_support","ml","custom","locked","gxp_records","no","established"),
 ("Agentic vision system auto-rejects vials and updates MES with no human review","Manufacturing / MES",True,True,"automated","ml","custom","learning","gxp_records","yes","developing"),
 ("LLM chatbot answers GMP training questions for operators; advisory","Other",False,False,"advisory","llm","cots","locked","internal","no","initial"),
 ("OCR+LLM extracts CoA values from supplier PDFs into LIMS automatically","QC / LIMS",True,True,"automated","llm","configured","locked","gxp_records","no","developing"),
 ("LLM drafts SOP revisions for author review; not entered until approved","Quality / QMS (deviation, CAPA)",True,False,"advisory","llm","cots","locked","internal","no","developing"),
 ("Agentic tool monitors public FDA enforcement to score supplier risk; advisory","Supply chain",False,False,"advisory","llm","cots","learning","public","yes","developing"),
 ("Predictive maintenance ML on GMP autoclaves writes work orders to the CMMS","Manufacturing / MES",True,True,"automated","predictive","cots","learning","gxp_records","no","established"),
 ("LLM summarizes stability data into a report section; statistician reviews","Regulatory authoring",True,False,"advisory","llm","configured","locked","gxp_records","no","developing"),
 ("Generative model designs DoE experiments for process development; advisory","Other",False,False,"advisory","llm","finetuned","locked","internal","no","developing"),
 ("Agentic LLM orchestrates sub-agents to assemble an IND module, auto-submits draft","Regulatory authoring",True,True,"automated","llm","finetuned","learning","gxp_records","yes","initial"),
 ("ML classifies environmental-monitoring excursions; microbiologist approves","QC / LIMS",True,True,"decision_support","ml","configured","locked","gxp_records","no","established"),
 ("LLM triages complaints and proposes severity; auto-files into complaint system","Quality / QMS (deviation, CAPA)",True,True,"automated","llm","cots","locked","gxp_records","no","developing"),
 ("Demand-forecasting ML for commercial planning; no GxP impact","Supply chain",False,False,"advisory","predictive","cots","learning","public","no","advanced"),
 ("Agentic CSV tool generates and executes IQ/OQ protocols into the validation record","Quality / QMS (deviation, CAPA)",True,True,"advisory","llm","finetuned","locked","gxp_records","yes","developing"),
 ("LLM cleaning-validation calculator; QA verifies every result","QC / LIMS",True,True,"decision_support","llm","configured","locked","gxp_records","no","developing"),
 ("Continuously-learning model optimizes lyophilization cycle in real time, acts on PLC","Manufacturing / MES",True,True,"automated","ml","custom","learning","gxp_records","yes","developing"),
 ("LLM drafts annual product review narrative; QA reviews before use","Quality / QMS (deviation, CAPA)",True,False,"advisory","llm","configured","locked","gxp_records","no","established"),
 ("Knowledge assistant over public guidance documents; advisory, no records","Regulatory authoring",False,False,"advisory","llm","cots","locked","public","no","initial"),
 ("ML predicts dissolution from process params; advisory to formulators","Other",True,False,"advisory","ml","finetuned","locked","internal","no","developing"),
 ("Agentic batch-release assistant checks the record and recommends disposition; QP signs","Quality / QMS (deviation, CAPA)",True,True,"advisory","llm","finetuned","locked","gxp_records","yes","developing"),
 ("Generative tool writes marketing copy (non-GxP)","Other",False,False,"advisory","llm","cots","locked","public","no","initial"),
 ("LLM extracts and reconciles values across an executed batch record; QA reviews flags","Quality / QMS (deviation, CAPA)",True,False,"decision_support","llm","configured","locked","gxp_records","no","developing"),
 ("Adaptive APC adjusts critical process parameters with operator confirmation each change","Manufacturing / MES",True,True,"decision_support","ml","custom","learning","gxp_records","no","developing"),
 ("Agentic data-integrity auditor scans audit trails and opens deviations automatically","Quality / QMS (deviation, CAPA)",True,True,"automated","llm","configured","locked","gxp_records","yes","developing"),
 ("LLM translates a regulatory dossier between languages; human verifies","Regulatory authoring",True,False,"advisory","llm","cots","locked","gxp_records","no","established"),
 ("ML supplier-risk scoring from internal quality history; advisory","Supply chain",True,False,"advisory","ml","configured","learning","internal","no","developing"),
 ("Locked LLM drafts CAPA effectiveness checks; QA approves and records","Quality / QMS (deviation, CAPA)",True,True,"advisory","llm","configured","locked","gxp_records","no","established"),
 ("Research literature-mining agent for discovery scientists; non-GxP","Other",False,False,"advisory","llm","cots","learning","public","yes","initial"),
]

def golden(ans):
    r = risk_engine.classify(ans)
    titles = {f["title"] for f in r["flags"]}
    return {"overall": r["overall"], "annex22": r["frameworks"]["EU GMP Annex 22"],
            "stop_llm": "Generative AI / LLM in a critical GMP use" in titles,
            "stop_dynamic": "Dynamic / continuously-learning model in a GxP-impacting use" in titles,
            "stop_agentic": "Autonomous agent taking GxP actions" in titles,
            "label_source": "rule-derived"}

data = json.load(open("l7/scenarios.json"))
existing = {s["id"] for s in data}
i = 16
for sp in SPECS:
    sid = f"S{i:02d}"
    if sid in existing:
        i += 1; continue
    use, fn, impact, rec, auto, mt, build, adp, dat, ag, gov = sp
    ans = {"functions": [fn], "impact": impact, "enters_records": rec, "autonomy": auto,
           "model_type": mt, "build": build, "adaptive": adp, "data_sensitivity": dat,
           "connections": [], "governance": gov, "agentic": ag}
    desc = f"{use}. Build: {build} {mt}{' (agentic/tool-using)' if ag=='yes' else ''}; data: {dat}."
    data.append({"id": sid, "desc": desc, "answers": ans, "golden": golden(ans)})
    i += 1

json.dump(data, open("l7/scenarios.json", "w"), indent=1)
print(f"scenario bank now: {len(data)} (added S16+; S01-S15 human-verified, S16+ rule-derived)")
