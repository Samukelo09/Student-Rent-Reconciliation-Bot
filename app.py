# app.py (Console version of the reconciliation process, without Streamlit UI)

import pandas as pd
import os, sys
from recon.matcher import match
from recon.rules import compute_findings
from recon.summarizer import summarize_report
from recon.integrators import publish_recon_report

def main():
    # 1. Load Data
    try:
        bank = pd.read_csv("data/landlord_bank_transactions.csv")
        inv  = pd.read_csv("data/rent_ledger.csv")
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    print("--- Starting Reconciliation ---")

    # 2. Fuzzy Matching
    matches, bank_unmatched, inv_unmatched, findings = match(bank, inv)
    
    # 3. Strict Rules (The Fix)
    try:
        # compute_findings returns strict logical findings (e.g. exact duplicates)
        strict_findings = compute_findings(matches, bank_unmatched, inv_unmatched)
        
        # Merge strict findings into general findings
        # We prioritize strict findings if the fuzzy matcher returned empty/None for that key
        for k, v in strict_findings.items():
            existing = findings.get(k)
            # If key missing in findings OR existing is empty dataframe, take the strict one
            if k not in findings:
                findings[k] = v
            elif isinstance(existing, pd.DataFrame) and existing.empty and not v.empty:
                findings[k] = v
                
    except Exception as e:
        print(f"Warning: Rules engine failed: {e}")

    # 4. Generate AI Report
    stats = {
        "counts": {"matches": len(matches)},
        "unmatched_txns": bank_unmatched,
        "unmatched_invs": inv_unmatched,
        "findings": findings
    }
    
    print("Asking Gemini...")
    summary = summarize_report(stats)
    print("\n" + "="*50 + "\n" + summary + "\n" + "="*50)

    # 5. Publish
    publish_recon_report(matches, bank_unmatched, inv_unmatched, summary)

if __name__ == "__main__":
    main()