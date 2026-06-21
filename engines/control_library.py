"""The brain: machine-readable control library.
Each control: framework -> clause -> control -> question -> evidence type, plus an
`applies(a)` predicate over the intake answers. Deterministic; LLM never touches this.
All synthetic/educational. Not regulatory advice.
"""

# Intake answer schema (keys produced by the UI):
#  functions:[str]  impact:bool  enters_records:bool  autonomy:'decision_support'|'advisory'|'automated'
#  model_type:'llm'|'ml'|'predictive'|'other'  build:'cots'|'configured'|'finetuned'|'custom'
#  adaptive:'locked'|'learning'  data_sensitivity:'public'|'internal'|'gxp_records'|'personal_phi'
#  connections:[str]  governance:'none'|'initial'|'developing'|'established'|'advanced'

def _llm(a):      return a.get("model_type") == "llm"
def _impact(a):   return bool(a.get("impact"))
def _records(a):  return bool(a.get("enters_records"))
def _auto(a):     return a.get("autonomy") == "automated"
def _adaptive(a): return a.get("adaptive") == "learning"
def _vendor(a):   return a.get("build") in ("cots", "configured", "finetuned")

CONTROLS = [
    dict(id="C01", element="Intended / context of use", framework="FDA AI credibility framework; GAMP 5",
         clause="Context of use; intended use", control="A written, specific intended-use & context-of-use statement exists and bounds the claim.",
         question="Is there a written statement of exactly what this AI is for and where it is used?",
         evidence="Intended-use / context-of-use document", severity="high", applies=lambda a: True),
    dict(id="C02", element="Risk classification", framework="EU GMP Annex 22; EU AI Act; ICH Q9(R1)",
         clause="Criticality determination", control="Risk is classified against each applicable framework with documented rationale.",
         question="Has the AI's risk/criticality been formally classified and justified?",
         evidence="Risk classification record", severity="high", applies=lambda a: True),
    dict(id="C03", element="Architecture & AI BOM", framework="AI BOM (SPDX 3.0); GAMP supplier qualification",
         clause="Transparency; provenance", control="A complete inventory of model(s), versions, APIs, MCP servers, data connections exists.",
         question="Do you maintain an inventory (AI BOM) of the model, versions, APIs, MCP servers, and connections?",
         evidence="AI bill of materials", severity="high", applies=lambda a: True),
    dict(id="C04", element="Golden / independent test data", framework="EU GMP Annex 22",
         clause="Validation with independent test data", control="A representative golden dataset and an independent hold-out test set are defined.",
         question="Do you have a representative golden dataset AND independent hold-out test data?",
         evidence="Dataset definition + provenance", severity="high", applies=lambda a: _impact(a) or _llm(a)),
    dict(id="C05", element="Performance vs acceptance criteria", framework="FDA AI credibility framework",
         clause="Acceptance criteria; comparator", control="Pre-defined acceptance criteria and a comparator/baseline are set and met.",
         question="Are there pre-defined acceptance criteria and a comparator/baseline (not just 'accuracy')?",
         evidence="Validation/test report", severity="high", applies=lambda a: _impact(a)),
    dict(id="C06", element="Explainability / traceability", framework="EU GMP Annex 22; FDA-EMA Joint Principles",
         clause="Explainability", control="Each output is traceable to its source(s); explainability appropriate to risk is provided.",
         question="Can every output be traced to its source (citations / SHAP / source-to-claim)?",
         evidence="Traceability / explainability design", severity="high", applies=lambda a: _impact(a)),
    dict(id="C07", element="Human-in-the-loop & accountability", framework="EU GMP Annex 22; EU AI Act Art. 14",
         clause="Human oversight", control="A named human reviews/approves outputs before any GxP record action; accountability is assigned.",
         question="Does a named human review and sign off outputs before any GxP record action?",
         evidence="HITL procedure + role assignment", severity="high",
         applies=lambda a: _records(a) or _auto(a) or _impact(a)),
    dict(id="C08", element="ALCOA++ audit trail", framework="21 CFR Part 11; EU GMP Annex 11; Annex 22",
         clause="Data integrity; audit trail", control="Inference is logged (input, model version, prompt, params, timestamp, user, edits) and is reconstructable.",
         question="Is every inference logged so an inspector can reconstruct exactly what the model saw and did?",
         evidence="Audit-trail design / sample log", severity="high", applies=lambda a: _records(a)),
    dict(id="C09", element="Change control / PCCP", framework="FDA PCCP guidance; Annex 22 lifecycle",
         clause="Predetermined change control", control="A predetermined change control plan governs updates/retraining for adaptive models.",
         question="If the model learns/retrains, is there a Predetermined Change Control Plan (PCCP)?",
         evidence="PCCP / change-control SOP", severity="high", applies=lambda a: _adaptive(a)),
    dict(id="C10", element="Continuous monitoring & drift", framework="EU GMP Annex 22 lifecycle",
         clause="Ongoing monitoring", control="Live performance and data drift are monitored against thresholds that trigger revalidation.",
         question="Do you monitor live performance and data drift with thresholds that trigger revalidation?",
         evidence="Monitoring plan + thresholds", severity="medium",
         applies=lambda a: _adaptive(a) or _impact(a)),
    dict(id="C11", element="Supplier qualification", framework="GAMP 5; ISPE GAMP AI Guide 2025",
         clause="Supplier assessment", control="Third-party model/API providers are qualified and their controls assessed.",
         question="Have you qualified the third-party model/API provider(s)?",
         evidence="Supplier qualification record", severity="medium", applies=_vendor),
    dict(id="C12", element="Security & access", framework="Annex 11; agentic-AI governance",
         clause="Access control; security", control="Least-privilege access, identity, and security controls are in place for the AI and its connections.",
         question="Are least-privilege access and security controls in place for the AI and its connections?",
         evidence="Security/access design", severity="medium", applies=lambda a: True),
    dict(id="C13", element="Data privacy", framework="GDPR; 21 CFR Part 11",
         clause="Personal data handling", control="Personal/PHI handling is lawful, minimized, and documented.",
         question="If personal/PHI data is used, is its handling lawful, minimized, and documented?",
         evidence="DPIA / data-handling record", severity="high",
         applies=lambda a: a.get("data_sensitivity") == "personal_phi"),
    dict(id="C14", element="Documentation (cards)", framework="Model Cards / Data Cards",
         clause="Transparency documentation", control="Model card, data card, and system card document the system for reviewers.",
         question="Do model/data/system cards document the system for reviewers?",
         evidence="Model/data/system cards", severity="low", applies=lambda a: True),
    dict(id="C15", element="Governance maturity", framework="NIST AI RMF GOVERN; ISO/IEC 42001",
         clause="AI management system", control="An AI policy, inventory/registry, and governance body oversee the system.",
         question="Is there an AI policy, an AI registry, and a governance body overseeing this system?",
         evidence="AI governance SOP / registry", severity="medium",
         applies=lambda a: a.get("governance") in (None, "none", "initial")),
    dict(id="C16", element="LLM-specific hallucination control", framework="EU GMP Annex 22; FDA drugs AI guidance",
         clause="Output reliability", control="Generative outputs are constrained to approved sources and checked for fabrication.",
         question="Are generative outputs constrained to approved sources and checked for hallucination/fabrication?",
         evidence="Grounding / guardrail design", severity="high", applies=_llm),
]


def applicable(answers):
    return [c for c in CONTROLS if c["applies"](answers)]
