# recon/rules.py

import pandas as pd
from typing import Dict

def compute_findings(matches: pd.DataFrame, bank_unmatched: pd.DataFrame, inv_unmatched: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    findings = {}

    # Rule 1: Duplicates (Same amount & date)
    if not bank_unmatched.empty and {'amount', 'date'}.issubset(bank_unmatched.columns):
        dup_mask = bank_unmatched.duplicated(subset=['amount', 'date'], keep=False)
        findings['duplicate_txn'] = bank_unmatched[dup_mask].copy().reset_index(drop=True)
    else:
        findings['duplicate_txn'] = pd.DataFrame()

    # Rule 2: High Value Unmatched
    if not bank_unmatched.empty and 'amount' in bank_unmatched.columns:
        threshold = bank_unmatched['amount'].quantile(0.90)
        findings['high_value_unmatched'] = bank_unmatched[bank_unmatched['amount'] >= threshold].copy().reset_index(drop=True)
        
    return findings