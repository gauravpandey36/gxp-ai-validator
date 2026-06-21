# GxP AI Validation Companion

An interview-driven **companion agent** that helps any team validate an AI system for GxP use.
You answer a short interview about your AI; it returns a **risk classification** across the major
frameworks, a **control-by-control gap register**, a best-effort **AI bill-of-materials**, and an
**inspector-ready readiness dossier** you can print or download.

> **Advisory only.** It drafts evidence and gaps; a Qualified Person / QA must review and sign. It
> makes no release decision and validates nothing by itself. Synthetic / educational logic. Not
> regulatory advice. Risk tiers are computed **deterministically**; an AI model only drafts the
> written summary, so the tool works even with no AI key at all.

## What it covers
Intended/context of use · risk classification (EU GMP **Annex 22**, **EU AI Act**, **GAMP 5**,
ICH **Q9(R1)**, **NIST AI RMF**, **ISO/IEC 42001**) · AI bill-of-materials (model, versions, APIs,
MCP servers, data connections) · golden/independent test data · acceptance criteria & comparator ·
explainability/traceability · human-in-the-loop & accountability · **ALCOA++** audit trail
(21 CFR Part 11 / Annex 11) · change control / **PCCP** · continuous monitoring & drift · supplier
qualification · security/access · data privacy · model/data/system cards · governance maturity ·
LLM hallucination/grounding controls.

## Try the hosted demo (zero setup)
The hosted demo runs on the author's API key, **rate-limited, budget-capped, and behind an access code**,
so you can try it without any key. (Link + code shared at the ISPE 2026 summit / on request.)

> **Demo = synthetic data only.** Do **not** enter real system details, real data, or a real API key into
> the hosted demo. Interview answers are processed in memory and **not stored**; AI summaries call the
> Anthropic API (per Anthropic policy, API data is **not** used to train models). For real systems,
> **self-host** (below) so nothing leaves your environment. The hosted demo runs with `DEMO_MODE=1`
> (bring-your-own-key disabled) and an access code; the budget ledger is on a persistent volume with a
> hard `DEMO_CAP_USD` cap, backstopped by an account-level spend limit.

## Run it in your own environment (recommended for real data)
Your data and key never leave your machine.

```bash
git clone <this repo> && cd gxp-ai-validator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...          # your own key
export VALIDATOR_MODEL=claude-haiku-4-5-20251001   # or claude-sonnet-4-6
uvicorn server:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

No key? It still runs — you get the full deterministic risk classification and gap register; only the
written executive summary is replaced by a deterministic fallback.

## Architecture (why it's defensible)
- **Deterministic spine** — risk tiering and control applicability are pure rules (`engines/risk_engine.py`,
  `engines/control_library.py`): same input → same output, fully inspectable. The AI never makes a gating decision.
- **LLM only at the edge** — drafts the narrative summary (`engines/llm.py`), budget-guarded, fail-soft.
- **Bring-your-own-key** — power users can paste a key for one session; self-hosters set their own env key.

## The honest limits (read before trusting it)
- The agent is itself software that influences GxP thinking → in a real deployment it must be **validated**
  ("validate the validator"), and its output is **advice, not a verdict**.
- Auto-discovery from a pasted manifest is **best-effort** and can miss shadow connections — verify manually.
- It surfaces **gaps first**, never a green "compliant" stamp it owns.

## Validation ("validate the validator")
See `l7/VALIDATION_PACK.md`. On a 12-scenario golden set, the **deterministic engine matches expert
ground truth 1.00** (including **100% recall on the safety-critical STOP flags**); two **independent
cross-family assessors** (Claude, Llama-3.3-70B) agree with the corrected engine at **κ 0.86 / 0.65** —
*after* a calibration fix the validation itself surfaced (the engine had over-floored no-GxP-impact
systems to MEDIUM). On the LLM-in-critical STOP rule the deterministic engine outperformed both LLM
assessors on recall — the empirical case for gating on rules, not the model. **Human-panel κ is pending**
(blinded rater sheet + key in `l7/`).

## License
MIT. © 2026 Gourav Pandey. Independent & self-built; synthetic/educational; not sponsored or endorsed
by any employer; no proprietary or client data used.
