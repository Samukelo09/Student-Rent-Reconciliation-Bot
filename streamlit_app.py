#stremlit_app.py

import os
import sys
import traceback
from pathlib import Path
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# --- Configuration & Path Setup ---
load_dotenv()

# Ensure project root is on path so we can import 'recon' package
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import local modules
from recon.matcher import match
from recon.rules import compute_findings
from recon.summarizer import summarize_report
from recon.integrators import publish_recon_report

st.set_page_config(
    page_title="Finance AI Recon", 
    page_icon="🇿🇦",
    layout="wide"
)

# --- Helper Functions ---
def df_download_button(df, filename, label="Download CSV"):
    if df.empty:
        return
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
        key=filename
    )

# --- Sidebar UI ---
with st.sidebar:
    st.header("⚙️ Controls")
    st.markdown("### Environment Status")
    
    # Check for keys without revealing them
    has_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    has_slack = bool(os.environ.get("SLACK_WEBHOOK_URL"))
    
    if has_gemini:
        st.success("Gemini API Key Detected")
    else:
        st.error("Gemini API Key Missing")
        
    if has_slack:
        st.info("Slack Webhook Detected")
    else:
        st.caption("Slack Webhook Not Set")

    st.markdown("---")
    st.markdown("### About")
    st.caption("Automated reconciliation for South African rental management. Matches bank statements to rent ledgers.")

# --- Main Page Header ---
st.title("🇿🇦 Finance AI Recon")
st.markdown(
    """
    **Upload your financial data below.** The AI will match payments, identify shortfalls, 
    and generate a prioritized action plan.
    """
)

# --- File Upload Section ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Bank Statement")
    bank_file = st.file_uploader("Upload `landlord_bank_transactions.csv`", type=["csv"])

with col2:
    st.subheader("2. Rent Ledger")
    inv_file = st.file_uploader("Upload `rent_ledger.csv`", type=["csv"])

# --- Session State Management ---
if "results" not in st.session_state:
    st.session_state.results = None

# --- Execution Logic ---
if bank_file and inv_file:
    # Read files into DataFrames
    try:
        bank_df = pd.read_csv(bank_file)
        inv_df = pd.read_csv(inv_file)
        st.success(f"Loaded {len(bank_df)} transactions and {len(inv_df)} expected payments.")
    except Exception as e:
        st.error(f"Error reading CSV files: {e}")
        st.stop()

    # The "Run" Button
    if st.button("Run Reconciliation", type="primary", use_container_width=True):
        with st.spinner("AI is analyzing payments, matching records, and writing the report..."):
            try:
                # 1. Fuzzy Matching (Core Logic)
                # match returns: matches, unmatched_txns, unmatched_invs, findings(fuzzy)
                m, un_txns, un_invs, findings = match(bank_df, inv_df)

                # 2. Strict Rules Merge (CRITICAL FIX)
                # We calculate strict rules (like exact duplicates) and merge them in
                strict_findings = compute_findings(m, un_txns, un_invs)
                
                for k, v in strict_findings.items():
                    # If the finding key is missing, or if the fuzzy finding was empty, use strict rule
                    existing = findings.get(k)
                    if k not in findings:
                        findings[k] = v
                    elif isinstance(existing, pd.DataFrame) and existing.empty and not v.empty:
                        findings[k] = v

                # 3. Generate AI Summary
                stats = {
                    "counts": {
                        "matches": len(m),
                        "unmatched_txn": len(un_txns),
                        "unmatched_inv": len(un_invs),
                        "dup_txn": len(findings.get('duplicate_txn', []))
                    },
                    "unmatched_txns": un_txns,
                    "unmatched_invs": un_invs,
                    "findings": findings
                }
                summary_text = summarize_report(stats)

                # Save to Session State (so UI doesn't disappear)
                st.session_state.results = {
                    "matches": m,
                    "unmatched_txns": un_txns,
                    "unmatched_invs": un_invs,
                    "findings": findings,
                    "summary": summary_text
                }
                
            except Exception as e:
                st.error("Reconciliation failed! See details below.")
                st.code(traceback.format_exc())

# --- Results Display ---
if st.session_state.results:
    res = st.session_state.results
    
    st.markdown("---")
    st.header("Analysis Report")
    
    # Top Level Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Matched Payments", len(res["matches"]))
    m2.metric("Unpaid Invoices", len(res["unmatched_invs"]))
    m3.metric("Mystery Payments", len(res["unmatched_txns"]))
    m4.metric("Duplicates", len(res["findings"].get("duplicate_txn", [])))

    # AI Action Plan
    st.info("### AI Action Plan")
    st.markdown(res["summary"])

    # Detailed Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Unpaid Invoices", "Mystery Payments", "Discrepancies", "Matches"])
    
    with tab1:
        st.subheader("Action Required: Unpaid Invoices")
        if not res["unmatched_invs"].empty:
            st.dataframe(res["unmatched_invs"], use_container_width=True)
            df_download_button(res["unmatched_invs"], "unmatched_invoices.csv")
        else:
            st.success("No unpaid invoices found!")

    with tab2:
        st.subheader("Review Required: Unmatched Transactions")
        if not res["unmatched_txns"].empty:
            st.dataframe(res["unmatched_txns"], use_container_width=True)
            df_download_button(res["unmatched_txns"], "unmatched_transactions.csv")
        else:
            st.success("All transactions matched!")

    with tab3:
        st.subheader("Deep Dive: Discrepancies")
        
        # Display Partials
        partials = res["findings"].get("partials", [])
        if partials:
            st.warning(f"Found {len(partials)} partial or combined payments.")
            # Convert list of dicts to nice DataFrame for display
            st.dataframe(pd.DataFrame(partials), use_container_width=True)
        else:
            st.caption("No partial payment patterns detected.")

        # Display Duplicates
        duplicates = res["findings"].get("duplicate_txn", pd.DataFrame())
        if not duplicates.empty:
            st.error(f"Found {len(duplicates)} potential duplicate transactions.")
            st.dataframe(duplicates, use_container_width=True)
        else:
            st.caption("No duplicate transactions detected.")

    with tab4:
        st.subheader("Successful Matches")
        st.dataframe(res["matches"], use_container_width=True)
        df_download_button(res["matches"], "matches.csv")

    # --- Publishing Actions ---
    st.markdown("---")
    st.subheader("Publish Report")
    
    col_pub1, col_pub2 = st.columns([1, 4])
    with col_pub1:
        if st.button("Send to Slack/Notion"):
            try:
                publish_recon_report(
                    res["matches"], 
                    res["unmatched_txns"], 
                    res["unmatched_invs"], 
                    res["summary"]
                )
                st.toast("Report published successfully!", icon="✅")
            except Exception as e:
                st.error(f"Publishing failed: {e}")