# recon/llm_gemini.py

import os
import time
from typing import Dict, Any
import pandas as pd
import google.genai as genai
from google.genai import types

# LLM Integration: Gemini 2.0 Flash
def _retry_call(fn, retries=2, backoff_base=0.6):
    last_exc = None
    # Simple retry mechanism with exponential backoff
    for attempt in range(1, retries + 2):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            time.sleep(backoff_base * attempt)
    raise last_exc

# Builds the prompt for Gemini using the structured stats format from summarizer.py. 
# It includes counts and sample data for unmatched transactions and invoices.
def _build_prompt(stats: Dict[str, Any]) -> str:
    """Builds the prompt using the 'rich' stats structure from summarizer.py."""
    counts = stats.get("counts", {})
    # Access raw data preserved in the 'raw' key by summarizer
    raw = stats.get("raw", {})
    unmatched_txns = raw.get("unmatched_txns", pd.DataFrame()).head(3)
    unmatched_invs = raw.get("unmatched_invs", pd.DataFrame()).head(3)
    partials_list = raw.get("findings", {}).get("partials", [])

    # 1. Unpaid Invoices
    unpaid_inv_lines = []
    if not unmatched_invs.empty:
        for _, i in unmatched_invs.iterrows():
            unpaid_inv_lines.append(f"- Tenant: {i.get('customer','N/A')}, Amount Due: R{i.get('amount','N/A'):.2f}, Ref: {i.get('reference','')}")
    else:
        unpaid_inv_lines.append("- All expected rent payments have been matched.")

    # 2. Shortfalls
    partial_lines = []
    if partials_list:
        for p in partials_list:
             partial_lines.append(f"- Tenant: {p.get('customer','N/A')} (Invoice {p.get('invoice_id')}). Received R{p.get('received_total'):.2f}.")
    else:
        partial_lines.append("- No short/partial payments detected.")

    # 3. Mystery Payments
    mystery_txn_lines = []
    if not unmatched_txns.empty:
        for _, t in unmatched_txns.iterrows():
            mystery_txn_lines.append(f"- TXN {t.get('txn_id')}: R{t.get('amount'):.2f}, Desc: {t.get('description','').strip()[:40]}...")
    else:
        mystery_txn_lines.append("- No mystery or extra payments to investigate.")

    prompt_parts = [
        "You are a **Landlord Operations Assistant** in South Africa.",
        "Generate a prioritized action plan for the landlord.",
        "",
        "## STATUS COUNTS",
        f"- Matches: {counts.get('matches', 0)}",
        f"- Unpaid Invoices: {counts.get('unmatched_inv', 0)}",
        f"- Mystery Payments: {counts.get('unmatched_txn', 0)}",
        "",
        "## DISCREPANCY DATA",
        "### UNPAID RENT",
        *unpaid_inv_lines,
        "\n### PARTIAL/SHORTFALLS",
        *partial_lines,
        "\n### MYSTERY PAYMENTS",
        *mystery_txn_lines,
        "",
        "## OUTPUT FORMAT",
        "1. Summary statement.",
        "2. 3-5 prioritized actions.",
        "3. 2 automation suggestions.",
        "Use ZAR currency (R)."
    ]
    
    return "\n".join(prompt_parts)

# Main function to call Gemini and get the action plan. It handles API key retrieval, error handling, and retries.
def generate_action_plan_with_gemini(
    stats: Dict[str, Any],
    model: str = "gemini-2.0-flash",
    timeout_seconds: int = 15
) -> str:
    """Generates AI plan using Gemini 2.0 Flash."""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return get_local_fallback()
    
    try:
        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(stats)
        
        def call_gemini():
            # Corrected call using the config object for new SDK
            resp = client.models.generate_content(
                model=model, 
                contents=prompt, 
                config=types.GenerateContentConfig(
                    max_output_tokens=800,
                    temperature=0.4
                )
            )
            return resp.text
    
        return _retry_call(call_gemini, retries=2)
    
    except Exception as e:
        print(f"[Gemini Error] {e}")
        return get_local_fallback() + f"\n\n*(API Error: {str(e)})*"

def get_local_fallback():
    return ("**[AI Summary: Local Fallback]** Gemini key not detected or API failed. \n\n"
            "**Priority Actions:**\n"
            "1. Review Unpaid Invoices list.\n"
            "2. Check Partial Payments for shortfalls.\n"
            "3. Manually reconcile Mystery Payments.")