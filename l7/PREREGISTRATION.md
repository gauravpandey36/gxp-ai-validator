# L7 pre-registration — "validate the validator" (frozen before running)

**Object under test:** the GxP AI Validation Companion's risk classification (deterministic engine) and
its trustworthiness as judged by independent assessors.

**Design:** 12 synthetic AI-system scenarios spanning the decision space, each with an expert **golden**
label (overall risk; EU Annex 22 criticality; expected LLM-in-critical and dynamic-in-critical STOP flags).
Three assessors classify each scenario blind to the golden: the **deterministic engine**, an independent
**Claude (sonnet-4-6)** assessor, and an independent cross-family **Llama-3.3-70B** assessor. The two LLM
assessors are given the framework definitions but NOT the engine's scoring formula.

**Pre-registered acceptance criteria (set now, not editable after the run):**
- **H1 — engine correctness/reproducibility:** engine vs golden = **1.00** on overall tier AND Annex 22
  tier AND STOP-flag recall. (Anything <1.00 = the engine does not encode its intended rules → fix.)
- **H2 — not idiosyncratic:** at least one independent LLM assessor reaches **overall accuracy ≥ 0.75**
  and **Cohen's κ ≥ 0.60** (substantial) vs golden. Report both assessors.
- **H3 — cross-family convergence:** Claude-vs-Llama overall **κ ≥ 0.40** (moderate).
- Report **Annex 22 accuracy** and **STOP-flag recall** separately (do not fold into one score).

**Honest limits stated up front:** n=12 (small); golden labels are author-derived from the published
frameworks, not consensus of multiple humans; LLM assessors are a *proxy* for human assessors. The real
human-κ gate is **pending** — collect ≥3 QA/RA raters via `human_rating_sheet.csv`, then compute human
agreement against `human_rating_KEY.csv`. Until then this is "validated against an expert golden + two
independent AI assessors," NOT "validated against a human panel."
