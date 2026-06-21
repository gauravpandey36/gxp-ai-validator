"""Budget-guarded Anthropic client (no SDK; urllib only -> light Railway build).
- BYO key (passed in): used directly, NOT counted against the demo ledger.
- Demo key (env ANTHROPIC_API_KEY): counted against a hard USD cap; refused past the cap.
The engine works with NO LLM at all — this only drafts narrative at the edges, fail-soft.
Key values are never logged or returned."""
import json, os, urllib.request
from pathlib import Path

DATA = Path(os.environ.get("LEDGER_DIR") or (Path(__file__).resolve().parent.parent / "data"))
DATA.mkdir(parents=True, exist_ok=True)
LEDGER = DATA / "ledger.json"

DEMO_CAP_USD = float(os.environ.get("DEMO_CAP_USD", "45"))
# approximate prices ($/million tokens) for the budget GUARD only (not billing)
PRICES = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
}
DEFAULT_MODEL = os.environ.get("VALIDATOR_MODEL", "claude-haiku-4-5-20251001")


def _ledger():
    try:
        return json.loads(LEDGER.read_text())
    except Exception:
        return {"spent_usd": 0.0, "calls": 0}


def _save(l):
    LEDGER.write_text(json.dumps(l))


def spend_status():
    l = _ledger()
    return {"spent_usd": round(l["spent_usd"], 4), "cap_usd": DEMO_CAP_USD,
            "remaining_usd": round(max(0.0, DEMO_CAP_USD - l["spent_usd"]), 4), "calls": l["calls"]}


def complete(prompt, system="", byo_key=None, model=None, max_tokens=1200):
    """Returns (text|None, meta). None means: no key, over cap, or API error -> caller proceeds deterministically."""
    model = model or DEFAULT_MODEL
    using_demo = byo_key is None
    key = byo_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None, {"reason": "no_key"}
    if using_demo:
        l = _ledger()
        if l["spent_usd"] >= DEMO_CAP_USD:
            return None, {"reason": "demo_cap_reached"}

    body = json.dumps({
        "model": model, "max_tokens": max_tokens,
        "system": system or "You are a careful GxP validation assistant.",
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
    except Exception as e:
        return None, {"reason": f"api_error:{type(e).__name__}"}

    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    u = d.get("usage", {})
    pin, pout = PRICES.get(model, (3.0, 15.0))
    cost = u.get("input_tokens", 0) / 1e6 * pin + u.get("output_tokens", 0) / 1e6 * pout
    if using_demo:
        l = _ledger()
        l["spent_usd"] += cost
        l["calls"] += 1
        _save(l)
    return text, {"cost_usd": round(cost, 5), "demo": using_demo}
