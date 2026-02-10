# **Finance AI Recon (South African Edition)**
**Automated Rent Reconciliation for Landlords & Property Managers.**

Finance AI Recon is a Python-based tool designed to solve the "matching problem" in property management. It takes raw bank statements and tenant rent ledgers, automates the reconciliation process using fuzzy logic and business rules, and uses Google Gemini AI to generate prioritized action plans for landlords.

---

### **Key Features**
- **Intelligent Matching:** Matches payments based on Reference/Amount (exact) and fuzzy logic (Tenant Name + Amount).
- **SA Banking Context:** Specifically tuned to handle South African banking "noise" (e.g., handling "EFT", "REF:", "CAPITEC" prefixes).
- **Discrepancy Detection:** Automatically flags:
  - **Partial Payments:** Tenants who paid less than the invoiced amount.
  - **Duplicates:** Double payments needing reversal.
  - **Unpaid Invoices:** Tenants who haven't paid at all.
- **AI Executive Summary:** Uses Google Gemini 2.0 Flash to write a human-readable action plan for the landlord, prioritizing financial risks.
- **Interactive Report:** A Streamlit dashboard to view, filter, and download results (CSV).

---

### **Tech Stack**
- **Frontend:** Streamlit
- **Core Logic:** Python 3.10+, Pandas, RapidFuzz
- **AI Model:** Google Gemini (via `google-genai` SDK)
- **Integration:** Slack Webhooks (Optional)

---

### **Project Structure**
```
  student_rent_recon/
  ├── .env                     # API Keys (Gemini, Slack)
  ├── app.py                   # CLI entry point (optional)
  ├── streamlit_app.py         # Main Web Interface
  ├── requirements.txt         # Dependencies
  ├── data/                    # Local storage for CSV inputs
  │   ├── landlord_bank_transactions.csv
  │   └── rent_ledger.csv
  └── recon/                   # Logic Package
      ├── matcher.py           # Core fuzzy matching engine
      ├── rules.py             # Strict business rules (Duplicates, etc.)
      ├── llm_gemini.py        # Google Gemini AI integration
      ├── summarizer.py        # Report generator
      └── integrators.py       # Slack/Export utilities
```

---

### **Quick Start**
1. **Prerequisites**
  - Python 3.9 or higher
  - A Google Gemini API Key (Get one [here](https://aistudio.google.com/))
2. **Installation**
    Clone the repository and install dependencies:
    ```
      git clone https://github.com/Samukelo09/Student-Rent-Reconciliation-Bot.git
      cd Student-Rent-Reconciliation-Bot
      pip install -r requirements.txt
    ```
3. **Configuration**
  Create a `.env` file in the root directory:
  ```
    GEMINI_API_KEY=your_actual_api_key_here
    # Optional
    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
  ```
4. **Running the App**
   Launch the dashboard:
   ```
    streamlit run streamlit_app.py
   ```
   Upload your `landlord_bank_transactions.csv` and `rent_ledger.csv` to see the magic happen.

---

### **Future Roadmap (Architecture v2)**
We are currently refactoring this tool from a local script into a multi-tenant SaaS platform hosted on Azure.
**Planned Architecture:**
- **Backend:** Migration to FastAPI hosted on Azure App Service.
- **Database:** Azure Database for PostgreSQL to store user profiles, organizations, and reconciliation history.
- **Storage:** Azure Blob Storage for secure management of uploaded financial documents.
- **Security:** Multi-tenancy support (Org/User scoping) and Azure Key Vault for secrets management.
- **Observability:** Integration with Azure Application Insights.

---

### **License**
Distributed under the MIT License. See `LICENSE` for more information.

### **Contributing**
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
