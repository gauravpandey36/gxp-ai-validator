#!/usr/bin/env python3
"""Document-heterogeneity generator for the OCR/format -> hallucination study.
Takes clean synthetic batch-record snippets and emits degraded variants (OCR noise,
layout drift, color/format tags) + a manifest + a golden values key, so a vendor's
extraction tool can be run on each variant and scored vs ground truth.
Self-contained, synthetic, deterministic (seeded by index — no RNG that breaks repro)."""
import json, os
from pathlib import Path

OUT = Path(__file__).parent
(OUT / "variants").mkdir(exist_ok=True)

# Clean synthetic batch-record snippets WITH ground-truth values embedded
DOCS = [
 {"id": "BR1", "text": "Batch No: GC301-DP-0042  Product: gelizumab 150 mg lyophilized\n"
                       "Fill weight target: 2.10 mL  Result: 2.08 mL  Operator: A.K.  Date: 14-Mar-2026\n"
                       "Shelf temp (primary drying): -25 C  Chamber pressure: 100 mTorr\n"
                       "Residual moisture: 1.2%  Result: PASS",
  "golden": {"batch_no": "GC301-DP-0042", "fill_result_ml": "2.08", "shelf_temp_c": "-25",
             "chamber_pressure_mtorr": "100", "residual_moisture_pct": "1.2", "disposition": "PASS"}},
 {"id": "BR2", "text": "Batch No: GC301-DS-0017  Step: Low-pH viral inactivation\n"
                       "Target pH: 3.6  Recorded pH: 3.58  Hold time: 60 min  Temp: 19 C\n"
                       "Protein A pool titer: 4.2 g/L  Reviewed by: M.C.  Date: 02-Feb-2026",
  "golden": {"batch_no": "GC301-DS-0017", "recorded_ph": "3.58", "hold_min": "60",
             "temp_c": "19", "titer_g_l": "4.2"}},
 {"id": "BR3", "text": "Deviation DV-2026-031  Lyophilization shelf temp excursion to -18 C for 12 min\n"
                       "Impact assessment: cake appearance within spec  CAPA: CAPA-2026-019\n"
                       "QA disposition: APPROVED with justification  Date: 21-Apr-2026",
  "golden": {"deviation_id": "DV-2026-031", "excursion_temp_c": "-18", "duration_min": "12",
             "capa_id": "CAPA-2026-019", "disposition": "APPROVED"}},
]

def ocr_noise(t, level):
    # deterministic char substitutions emulating common OCR confusions
    sub = {"0": "O", "1": "l", "5": "S", "8": "B", "rn": "m", "C": "C"}
    out = []
    for i, ch in enumerate(t):
        if level == "heavy" and ch in sub and i % 3 == 0:
            out.append(sub[ch])
        elif level == "light" and ch in sub and i % 7 == 0:
            out.append(sub[ch])
        else:
            out.append(ch)
    return "".join(out)

def layout_drift(t):
    # collapse line structure into a single reflowed block (column/merge drift)
    return "  ".join(line.strip() for line in t.splitlines())

VARIANTS = [
 ("clean", "white", "structured", lambda t: t),
 ("ocr_light", "white", "scanned", lambda t: ocr_noise(t, "light")),
 ("ocr_heavy", "yellow", "scanned", lambda t: ocr_noise(t, "heavy")),
 ("layout_drift", "white", "reflowed", layout_drift),
 ("ocr_heavy_drift", "green", "scanned+reflowed", lambda t: layout_drift(ocr_noise(t, "heavy"))),
]

manifest = []
golden_key = {}
for d in DOCS:
    golden_key[d["id"]] = d["golden"]
    for vname, color, fmt, fn in VARIANTS:
        vid = f"{d['id']}_{vname}"
        text = fn(d["text"])
        (OUT / "variants" / f"{vid}.txt").write_text(text)
        # rough char-error estimate vs clean
        clean = d["text"]
        err = sum(1 for a, b in zip(text, clean) if a != b) + abs(len(text) - len(clean))
        manifest.append({"variant_id": vid, "source_id": d["id"], "degradation": vname,
                         "color": color, "format": fmt, "approx_char_delta": err,
                         "n_golden_fields": len(d["golden"])})

(OUT / "manifest.csv").write_text(
    "variant_id,source_id,degradation,color,format,approx_char_delta,n_golden_fields\n" +
    "\n".join(f"{m['variant_id']},{m['source_id']},{m['degradation']},{m['color']},{m['format']},{m['approx_char_delta']},{m['n_golden_fields']}" for m in manifest))
(OUT / "golden_values.json").write_text(json.dumps(golden_key, indent=2))
print(f"generated {len(manifest)} variants from {len(DOCS)} docs -> {OUT/'variants'}")
print("manifest.csv + golden_values.json written")
print("USE: run a vendor's extraction tool on each variant, score extracted vs golden_values, "
      "plot accuracy/hallucination vs degradation level.")
