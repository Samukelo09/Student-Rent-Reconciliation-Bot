# recon/matcher.py

import re
from datetime import timedelta
from typing import Tuple, Optional, List, Dict, Any
import pandas as pd
from dateutil.parser import parse
from rapidfuzz import fuzz, process

# --- Helpers ---
REF_PATTERNS = [r'\b[A-Z]{2,}-\d{1,}\b', r'\b[A-Z]{2,}\d{2,}\b']
NOISE_WORDS_RE = re.compile(r'\b(payment|eft|incoming|debit order|txn|ref:|paid)\b', flags=re.I)

def safe_float(x):
    try: return float(x) if pd.notna(x) else None
    except: return None

def _to_date(s):
    try: return parse(str(s)).date() if pd.notna(s) else None
    except: return None

def extract_reference(text: str) -> str:
    if not text: return ''
    txt = str(text).upper()
    for p in REF_PATTERNS:
        m = re.search(p, txt)
        if m: return m.group(0)
    return ''

def normalize_text(s: str) -> str:
    if not s: return ''
    s = NOISE_WORDS_RE.sub(' ', str(s))
    s = re.sub(r'[^A-Za-z0-9\s]', ' ', s).lower()
    return re.sub(r'\s+', ' ', s).strip()

def _ensure_cols(df: pd.DataFrame, cols: List[str]):
    """Safely adds missing columns with None values."""
    for c in cols:
        if c not in df.columns:
            df[c] = None

def preprocess(bank_df: pd.DataFrame, inv_df: pd.DataFrame):
    bank, inv = bank_df.copy(), inv_df.copy()
    
    # 1. Standardize Headers (Rename known variations)
    # Check your CSV headers! If they are different, add them here.
    bank.rename(columns={
        'TransactionID': 'txn_id', 
        'DatePaid': 'date', 
        'AmountPaid': 'amount', 
        'Description': 'description', 
        'Reference': 'reference'
    }, inplace=True)
    
    inv.rename(columns={
        'InvoiceID': 'invoice_id', 
        'TenantName': 'customer', 
        'MonthlyRent': 'amount', 
        'DueDate': 'due_date', 
        'PaymentReference': 'reference'
    }, inplace=True)
    
    # 2. Lowercase all columns
    bank.columns = bank.columns.str.lower()
    inv.columns = inv.columns.str.lower()

    # 3. Ensure columns exist (even if empty)
    _ensure_cols(bank, ['txn_id', 'date', 'amount', 'description', 'reference'])
    _ensure_cols(inv, ['invoice_id', 'customer', 'amount', 'due_date', 'reference'])
    
    # 4. Type Conversions
    bank['date'] = bank['date'].apply(_to_date)
    inv['due_date'] = inv['due_date'].apply(_to_date)
    if 'issue_date' not in inv.columns: inv['issue_date'] = inv['due_date']
    
    bank['amount'] = pd.to_numeric(bank['amount'], errors='coerce')
    inv['amount'] = pd.to_numeric(inv['amount'], errors='coerce')
    
    # 5. Helper columns for matching
    bank['_extracted_ref'] = bank['description'].fillna('').astype(str).apply(extract_reference)
    
    # If extracted ref is empty try to extract from the reference column as well (some banks put it there)
    bank['_extracted_ref'] = bank['_extracted_ref'].replace('', pd.NA).fillna(
        bank['reference'].fillna('').astype(str).apply(extract_reference)
    ).fillna('')

    bank['_norm_text'] = (bank['description'].fillna('') + ' ' + bank['reference'].fillna('')).astype(str).apply(normalize_text)
    inv['_norm_customer'] = inv['customer'].fillna('').astype(str).apply(normalize_text)
    
    return bank, inv

def match(bank_df, inv_df) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:
    bank, inv = preprocess(bank_df, inv_df)
    
    unmatched_txns_idx = set(bank.index)
    unmatched_inv_idx = set(inv.index)
    results = []
    
    bank_amts = bank['amount'].to_dict()
    inv_amts = inv['amount'].to_dict()
    
    # 1. Exact Ref + Amount
    inv_by_ref = {str(r).strip().upper(): i for i, r in inv['reference'].items() if pd.notna(r)}
    
    for bi in list(unmatched_txns_idx):
        ref = bank.at[bi, '_extracted_ref']
        if ref in inv_by_ref:
            ii = inv_by_ref[ref]
            # Floating point comparison safety
            if ii in unmatched_inv_idx:
                b_amt = bank_amts.get(bi)
                i_amt = inv_amts.get(ii)
                if b_amt is not None and i_amt is not None and abs(b_amt - i_amt) < 0.05:
                    results.append({**bank.loc[bi].to_dict(), **inv.loc[ii].to_dict(), 'match_type': 'exact_ref'})
                    unmatched_txns_idx.discard(bi)
                    unmatched_inv_idx.discard(ii)
                
    # 2. Amount + Fuzzy Name (Placeholder / simplified)
    
    matches = pd.DataFrame(results)
    unmatched_txns = bank.loc[sorted(unmatched_txns_idx)] if unmatched_txns_idx else pd.DataFrame(columns=bank.columns)
    unmatched_invs = inv.loc[sorted(unmatched_inv_idx)] if unmatched_inv_idx else pd.DataFrame(columns=inv.columns)
    
    findings = {'duplicate_txn': pd.DataFrame(), 'partials': []}
    
    return matches, unmatched_txns, unmatched_invs, findings