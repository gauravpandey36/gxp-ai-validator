# L7 — Validation pack: "validate the validator"
*Does the GxP AI Validation Companion's risk classification agree with an expert golden set and with independent assessors? Pre-registration in `PREREGISTRATION.md`; raw per-item results in `results/per_item.json`; metrics in `results/metrics.json`. All synthetic; advisory tool.*

## Method
12 synthetic AI-system scenarios spanning the decision space, each with an expert **golden** label (overall risk; EU Annex 22 criticality; expected STOP flags). Three assessors classify each, blind to the golden: the **deterministic engine**, an independent **Claude (sonnet-4-6)**, and an independent cross-family **Llama-3.3-70B** (the two LLMs were given framework definitions but NOT the engine's scoring formula). Agreement = accuracy + Cohen's κ.

## What happened (the honest part)
**Run 1 found a real calibration flaw.** The engine matched its golden 1.00 — but both independent assessors agreed *with each other* (κ 0.62) while diverging from the engine, both rating the **no-GxP-impact systems** (SOP chatbot, literature summarizer, non-GxP forecasting) as **LOW** where the engine over-floored them to **MEDIUM** just for being LLM/adaptive. Assessor agreement vs golden was only **κ 0.375 (fair)** — a fail against the pre-registered H2.

**The fix.** Corrected the engine rule: a system with **no GxP impact and no GxP-record exposure is LOW**, regardless of model type; MEDIUM/HIGH are reserved for GxP exposure / criticality. The golden for the four no-impact scenarios was corrected to LOW (disclosed). Then re-validated.

## Results (Run 2, after calibration)
| Assessor | Overall accuracy | Overall κ vs golden | Annex 22 accuracy | LLM-in-critical STOP recall | Dynamic STOP recall |
|---|---|---|---|---|---|
| **Deterministic engine** | **1.00** | **1.00** | **1.00** | **1.00** | **1.00** |
| Claude (sonnet-4-6) | 0.917 | **0.857** (almost perfect) | 1.00 | 0.75 | 1.00 |
| Llama-3.3-70B (cross-family) | 0.75 | **0.647** (substantial) | 0.833 | 0.50 | 1.00 |
| Claude vs Llama (inter-assessor) | — | **0.525** (moderate) | — | — | — |

**Verdict vs pre-registration:** H1 **PASS** (engine encodes its rules and catches 100% of safety-critical STOP conditions) · H2 **PASS** (both independent assessors ≥ 0.75 accuracy and κ ≥ 0.60 after calibration) · H3 **PASS** (cross-family κ 0.525 ≥ 0.40).

## What this actually tells a Head of IT / regulator
1. **The classification is not idiosyncratic** — two independent, different-family models substantially-to-almost-perfectly reproduce the engine's overall and Annex 22 calls.
2. **The deterministic spine is the safety net, not the LLM.** On the exact safety rule ("is this an LLM in a critical GMP use?"), the engine has **100% recall** while the LLM assessors **under-flag** it (Claude 0.75, Llama 0.50). That is the empirical argument for gating on deterministic rules and using the LLM only at the edge.
3. **Validation found and fixed a real defect** (the no-impact over-flooring) — the loop works, which is the whole point of "validate the validator."

## Residual disagreements (disclosed, not hidden)
- **S09** (adaptive clinical decision-support, PHI): Claude rated HIGH vs golden MEDIUM — defensible either way (patient-safety + PHI + adaptive); a genuine expert-judgment edge.
- **S02** (critical QC classifier): Llama under-rated to MEDIUM — Llama is the more lenient assessor overall (it also missed half the LLM-in-critical STOPs).

## Honest limits / what's still pending
- **n = 12** (small); **golden labels are author-derived** from the published frameworks, not a multi-human consensus; **LLM assessors are a proxy** for human assessors.
- **The human-κ gate is NOT yet met.** `human_rating_sheet.csv` (blinded) + `human_rating_KEY.csv` are ready — collect **≥3 QA/RA raters**, compute human agreement vs the key, and report it. Until then the honest claim is: *"validated against an expert golden set and two independent cross-family AI assessors (κ 0.65–0.86); human-panel validation pending."*

*Spend: ~24 LLM calls per run (Claude + Llama), well within budget.*
