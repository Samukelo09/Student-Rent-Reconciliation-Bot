# recon/integrators.py

import os
import requests
import pandas as pd

def export_csv(df, filename):
    path = os.path.join("reports", filename)
    os.makedirs("reports", exist_ok=True)
    df.to_csv(path, index=False)
    return path

def send_slack_message(msg):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if url:
        requests.post(url, json={"text": msg})
        print("Slack sent.")
    else:
        print("Slack skipped (no URL).")

def publish_recon_report(matches, un_txns, un_invs, summary):
    try:
        export_csv(matches, "matches.csv")
        export_csv(un_txns, "unmatched_txns.csv")
        send_slack_message(summary)
    except Exception as e:
        print(f"Publish error: {e}")