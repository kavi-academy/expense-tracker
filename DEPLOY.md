# Deployment Guide

This guide will help you host your Expense Tracker for free on Streamlit Cloud with Google Sheets persistence.

## Prerequisites

1.  **GitHub Account**: To host the code.
2.  **Google Cloud Account**: To enable Google Sheets API.
3.  **Streamlit Cloud Account**: To host the app.

## Step 1: Push Code to GitHub

1.  Create a new repository on GitHub.
2.  Upload all files (`app.py`, `data_handler.py`, `requirements.txt`, etc.) to this repository.

## Step 2: Google Cloud Setup

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project (e.g., "Expense Tracker").
3.  Search for **"Google Sheets API"** and enable it.
4.  Search for **"Google Drive API"** and enable it.
5.  Go to **IAM & Admin > Service Accounts**.
6.  Create a new Service Account.
7.  Go to the **Keys** tab of your new Service Account -> **Add Key** -> **Create new key** -> **JSON**.
8.  A JSON file will download. **Keep this safe!**

## Step 3: Configure Google Solution

1.  Open the JSON file you just downloaded. It looks like this:
    ```json
    {
      "type": "service_account",
      "project_id": "...",
      "private_key_id": "...",
      "private_key": "-----BEGIN PRIVATE KEY-----...",
      "client_email": "example@project.iam.gserviceaccount.com",
      ...
    }
    ```
2.  Copy the `client_email` address.
3.  Create a new Google Sheet.
4.  Name the Sheet **"ExpenseTracker"** (or whatever you prefer).
5.  Click **Share** in the top right.
6.  Paste the `client_email` and ensure it has **Editor** access. This allows your app to read/write to the sheet.
7.  Copy the URL of your Google Sheet.

## Step 4: Deploy to Streamlit Cloud

1.  Go to [share.streamlit.io](https://share.streamlit.io/).
2.  Connect your GitHub account.
3.  Click **"New app"**.
4.  Select your Repository, Branch (usually `main`), and Main file path (`app.py`).
5.  Click **"Advanced settings..."** (or go to Settings -> Secrets after deploying).
6.  Paste the contents of your JSON key file into the Secrets area, but format it like TOML.
    
    **Easier Method:**
    Streamlit secrets use TOML format. You can check [Streamlit Docs on GSheets](https://docs.streamlit.io/knowledge-base/tutorials/databases/private-gsheet) or simply format it like this:

    ```toml
    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "..."
    client_email = "..."
    client_id = "..."
    auth_uri = "..."
    token_uri = "..."
    auth_provider_x509_cert_url = "..."
    client_x509_cert_url = "..."
    universe_domain = "googleapis.com"
    
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
    ```

    *Note: Ensure `private_key` value is in quotes.*

7.  Click **"Save"**.
8.  Click **"Deploy"**.

## Troubleshooting

- **"Could not find Google Sheet"**: Ensure you shared the sheet with the Service Account email.
- **"App resets after reload"**: Ensure you are connected to Google Sheets. If the app says "Mode: Local CSV", your data will be lost on restart.
