"""Best-effort AI bill-of-materials extractor.
Parses a pasted manifest (JSON or free text / requirements.txt / config snippets)
into a normalized inventory. Honest by design: flags coverage as best-effort, never
claims completeness."""
import json, re

_PATTERNS = {
    "models": r"\b(gpt-?[\w.\-]+|claude[\w.\-]*|gemini[\w.\-]*|llama[\w.\-]*|mistral[\w.\-]*|"
              r"command[\w.\-]*|titan[\w.\-]*|bert|roberta|xgboost|random ?forest|resnet|yolo[\w.\-]*)",
    "providers": r"\b(openai|anthropic|google|azure|aws|bedrock|vertex|cohere|mistral|hugging ?face|databricks)\b",
    "mcp_servers": r"\b(mcp[\w\-/]*|model context protocol)\b",
    "apis": r"\b(rest api|graphql|/v1/|endpoint|webhook|openapi|swagger)\b",
    "data_stores": r"\b(qdrant|pinecone|weaviate|chroma|pgvector|postgres|mysql|mongo|s3|sharepoint|"
                   r"lims|mes|qms|ctms|etmf|veeva|vault)\b",
    "frameworks": r"\b(langchain|langgraph|llamaindex|haystack|semantic kernel|dspy|autogen|crewai)\b",
}


def extract(manifest_text):
    text = (manifest_text or "").strip()
    bom = {k: [] for k in _PATTERNS}
    bom["raw_chars"] = len(text)
    if not text:
        bom["coverage"] = "none — no manifest supplied; rely on interview answers"
        return bom

    # try JSON first
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    haystack = json.dumps(parsed).lower() if parsed is not None else text.lower()

    for k, pat in _PATTERNS.items():
        found = sorted({m.group(0).strip() for m in re.finditer(pat, haystack, re.I)})
        bom[k] = found[:20]

    discovered = sum(len(bom[k]) for k in _PATTERNS)
    bom["coverage"] = ("best-effort parse — VERIFY MANUALLY; auto-discovery can miss "
                       "shadow connections and undocumented components") if discovered else \
                      "no recognizable components parsed — supply a structured manifest or list them"
    return bom
