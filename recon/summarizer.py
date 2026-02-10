# recon/summarizer.py

import pandas as pd
from typing import Dict, Any
from recon.llm_gemini import generate_action_plan_with_gemini

# Summarizer: Takes raw stats and findings, formats them, and generates a summary action plan using Gemini.
def _to_markdown_safe(df, max_rows=3):
    if df.empty: return "(no samples)"
    try: return df.head(max_rows).to_markdown(index=False)
    except: return df.head(max_rows).to_csv(index=False)

# Transforms the raw stats and findings into a structured format that Gemini can understand.
# It preserves the original data in a 'raw' key for potential future use, while also creating a 'counts' summary and markdown samples for the prompt.
def generate_stats_from_inputs(raw_stats):
    findings = raw_stats.get("findings", {})
    un_txns = raw_stats.get("unmatched_txns", pd.DataFrame())
    un_invs = raw_stats.get("unmatched_invs", pd.DataFrame())
    
    return {
        "counts": {
            "matches": raw_stats.get("counts", {}).get("matches", 0),
            "unmatched_txn": len(un_txns),
            "unmatched_inv": len(un_invs),
            "dup_txn": len(findings.get("duplicate_txn", []))
        },
        "mismatch_samples": {
            "txns": _to_markdown_safe(un_txns),
            "invs": _to_markdown_safe(un_invs)
        },
        "raw": raw_stats
    }

# Main function to summarize the report.
def summarize_report(stats: Dict[str, Any]) -> str:
    # If the stats don't already have the 'mismatch_samples' key
    # It means we need to generate the structured stats from the raw inputs before calling Gemini.
    if "mismatch_samples" not in stats:
        stats = generate_stats_from_inputs(stats)
    
    # Call Gemini
    return generate_action_plan_with_gemini(stats)