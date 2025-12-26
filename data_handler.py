import streamlit as st
import pandas as pd
import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuration
DATA_FILE = "expenses.csv"
COLUMNS = ["Date", "Time", "Type", "Category", "Amount", "Payment Method", "Account", "Description", "Source", "Tags"]
SHEET_URL_KEY = "spreadsheet_url"
RULES_FILE = "category_rules.json"
RECURRING_FILE = "recurring_expenses.json"
import json
import account_manager as am

from googleapiclient.discovery import build

import auth
DATA_DIR = "data"

def get_user_data_file():
    """Returns the static filename for local mode."""
    # Since we are using simple password auth for a single user (or shared admin),
    # we default to the main data file.
    return DATA_FILE

def get_backend():
    """Determines if we should use Google Sheets or CSV."""
    if "gcp_service_account" in st.secrets:
        return "service_account"
    return "csv"

def get_google_sheet_client():
    """Authenticates and returns the Google Sheet object."""
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # Key-based Service Account
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        if SHEET_URL_KEY in st.secrets:
             try:
                return client.open_by_url(st.secrets[SHEET_URL_KEY]).sheet1
             except:
                return None
        else:
            try:
                # Find/Create a sheet named 'ExpenseTracker_Data'
                # For service account, it only sees files it has access to.
                # Simplest is to open by name if user shared it, or create new.
                try:
                    return client.open("ExpenseTracker_Data").sheet1
                except gspread.exceptions.SpreadsheetNotFound:
                    # Create if allowed (Service accounts can create sheets)
                    sh = client.create("ExpenseTracker_Data")
                    # IMPORTANT: Service account email needs to share it with user?
                    # Actually, for personal use, user usually creates sheet and shares with SA email.
                    st.toast(f"Created new sheet. Share it with your personal email!")
                    return sh.sheet1
            except:
                return None
    return None

def migrate_data_for_accounts(df):
    """Migrates existing data to include Account column."""
    if "Account" not in df.columns:
        # Initialize accounts if needed
        am.initialize_accounts()
        default_account = am.get_default_account()
        default_name = default_account["name"] if default_account else "Main Account"
        df["Account"] = default_name
    return df

def load_data():
    """Loads expense data from CSV or Google Sheets."""
    backend = get_backend()
    
    if backend == "service_account":
        try:
            sheet = get_google_sheet_client()
            if not sheet: 
                # Fallback to local if sheet fails
                st.warning("⚠️ Could not connect to Google Sheet. Using local CSV temporarily.")
            else:
                data = sheet.get_all_records()
                if not data:
                    return pd.DataFrame(columns=COLUMNS)
                
                df = pd.DataFrame(data)
                if df.empty:
                    return pd.DataFrame(columns=COLUMNS)

                # Ensure proper columns
                for col in COLUMNS:
                    if col not in df.columns:
                        df[col] = ""

                # Ensure proper types
                df["Date"] = pd.to_datetime(df["Date"]).dt.date
                df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0.0)
                
                # Migrate for accounts
                df = migrate_data_for_accounts(df)
                
                return df[COLUMNS] 
                
        except Exception as e:
            st.error(f"Google Sheets Error: {e}")
            return pd.DataFrame(columns=COLUMNS)
    
    # Fallback/Default to CSV
    # (Existing CSV logic below)
    data_file = get_user_data_file()
    
    if data_file and os.path.exists(data_file):
        try:
            df = pd.read_csv(data_file)
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0.0)
            
            # Migrate for accounts
            df = migrate_data_for_accounts(df)
            
            for col in COLUMNS:
                 if col not in df.columns:
                    df[col] = ""
            return df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame(columns=COLUMNS)
    else:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    """Saves expense data to CSV or Google Sheets."""
    backend = get_backend()
    
    # Ensure Date is string for storage stability
    df_store = df.copy()
    df_store["Date"] = df_store["Date"].astype(str)

    if backend == "service_account":
        try:
            sheet = get_google_sheet_client()
            if sheet:
                sheet.clear()
                sheet.append_row(df_store.columns.tolist())
                sheet.append_rows(df_store.values.tolist())
                return
        except Exception as e:
            st.error(f"Failed to save to Google Sheets: {e}")
            # Fall through to local save as backup

    # Local Save
    data_file = get_user_data_file()
    if not data_file: 
        return # Should not happen if correctly configured

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    df_store.to_csv(data_file, index=False)

def load_rules():
    """Loads categorization rules from JSON."""
    if os.path.exists(RULES_FILE):
        try:
            with open(RULES_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_rules(rules):
    """Saves categorization rules to JSON."""
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, indent=4)

def apply_categorization(df):
    """Applies rules to the dataframe to guess categories."""
    rules = load_rules()
    # Iterate over rules and apply
    for keyword, category in rules.items():
        # Case insensitive contains check
        mask = df["Description"].str.contains(keyword, case=False, na=False)
        # Apply only if Category is Uncategorized or empty (optional, but safer to always apply or user preference?)
        # User request implies "if description contains X, it IS Y". So let's overwrite for now, 
        # but maybe only on the 'new' data during upload is safer.
        df.loc[mask, "Category"] = category
    return df

    return df

def load_recurring():
    """Loads recurring profiles."""
    if os.path.exists(RECURRING_FILE):
        try:
            with open(RECURRING_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_recurring(profiles):
    """Saves recurring profiles."""
    with open(RECURRING_FILE, "w") as f:
        json.dump(profiles, f, indent=4)

def get_pending_recurring(df):
    """Checks which recurring expenses are missing for the current month."""
    profiles = load_recurring()
    pending = []
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    if df.empty:
        return profiles
        
    df["Date_dt"] = pd.to_datetime(df["Date"])
    current_month_data = df[
        (df["Date_dt"].dt.month == current_month) & 
        (df["Date_dt"].dt.year == current_year)
    ]
    
    for p in profiles:
        # Check if already exists (fuzzy match on Description and Amount)
        # We assume if Description matches, it's paid.
        is_paid = not current_month_data[
            current_month_data["Description"] == p["name"]
        ].empty
        
        if not is_paid:
            pending.append(p)
            
    return pending

def add_entry(date, category, amount, description, type, payment_method, account="Main Account", time="00:00", tags="", source="Manual"):
    """Adds a single expense entry."""
    # We load, append, and save. 
    # This might seem inefficient for Sheets (vs just append_row), 
    # but it ensures our local 'load_data' logic regarding duplicates/types stays consistent
    # and keeps the function signature simple.
    
    df = load_data()
    new_entry = pd.DataFrame([{
        "Date": date,
        "Time": time,
        "Type": type,
        "Category": category,
        "Amount": float(amount),
        "Payment Method": payment_method,
        "Account": account,
        "Description": description,
        "Source": source,
        "Tags": tags
    }])
    
    df = pd.concat([df, new_entry], ignore_index=True)
    save_data(df)
    return True

def process_upload(uploaded_file):
    """
    Processes an uploaded Excel file.
    Assumes simple columns: Date, Amount, Description.
    Category might need to be auto-defaulted or mapped.
    """
    try:
        # Load existing data
        existing_df = load_data()
        
        # Load new data
        new_df = pd.read_excel(uploaded_file)
        
        # Normalize columns based on user provided image
        # User Image Cols: Date, Narration, Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance
        
        column_map = {}
        # We need to handle the specific case where we have separate Withdrawal and Deposit columns
        # If we find these specific keys, we handle them specially
        
        df_cols = [c.strip() for c in new_df.columns]
        new_df.columns = df_cols # Clean whitespace
        
        if "Withdrawal Amt." in df_cols and "Deposit Amt." in df_cols:
            # Special handling for this specific format
            new_df["Date"] = pd.to_datetime(new_df["Date"], dayfirst=True).dt.date
            new_df["Description"] = new_df["Narration"]
            
            # Calculate Amount: Withdrawal is Expense (Positive), Deposit is Income (Negative or ignored?)
            # For an expense tracker, let's treat Withdrawal as positive Expense. 
            # We can treat Deposit as negative Expense (Income) if desired, or skip.
            # Let's simple use: Amount = Withdrawal - Deposit
            # So if I spend 100, Withdrawal=100, Deposit=0 -> Amount=100
            # If I get 50 refund, Withdrawal=0, Deposit=50 -> Amount=-50
            # Determine Type based on which column has value
            # We want Amount to be positive, and Type to be Income or Expense
            new_df["Withdrawal Amt."] = pd.to_numeric(new_df["Withdrawal Amt."], errors='coerce').fillna(0.0)
            new_df["Deposit Amt."] = pd.to_numeric(new_df["Deposit Amt."], errors='coerce').fillna(0.0)
            
            # Vectorized condition: If Withdrawal > 0 -> Expense, else Income (if Deposit > 0)
            # Safe default: Expense
            new_df["Type"] = "Expense" 
            new_df.loc[new_df["Deposit Amt."] > 0, "Type"] = "Income"
            
            # Calculate absolute Amount
            new_df["Amount"] = new_df["Withdrawal Amt."] + new_df["Deposit Amt."]
            
        else:
            # Fallback to generic mapping
            for col in new_df.columns:
                col_lower = col.lower()
                if "date" in col_lower and "value" not in col_lower: # Avoid Value Dt if Date exists
                    column_map[col] = "Date"
                elif "amount" in col_lower or "debit" in col_lower or "cost" in col_lower:
                    column_map[col] = "Amount"
                elif "desc" in col_lower or "particulars" in col_lower or "narration" in col_lower:
                    column_map[col] = "Description"
            new_df = new_df.rename(columns=column_map)

        # Standardize types
        if "Date" in new_df.columns:
            new_df["Date"] = pd.to_datetime(new_df["Date"], dayfirst=True).dt.date
        
        if "Amount" in new_df.columns:
            new_df["Amount"] = pd.to_numeric(new_df["Amount"], errors='coerce').fillna(0.0)

        # Fill missing columns
        if "Type" not in new_df.columns:
             # Default if we couldn't determine it earlier (e.g. generic upload)
             new_df["Type"] = "Expense"
        
        if "Payment Method" not in new_df.columns:
            new_df["Payment Method"] = "Transfer" # Default for bank uploads
            
        if "Category" not in new_df.columns:
            new_df["Category"] = "Uncategorized"
        if "Description" not in new_df.columns:
            new_df["Description"] = "Imported Transaction"
        if "Source" not in new_df.columns:
            new_df["Source"] = "Upload"
        if "Tags" not in new_df.columns:
            new_df["Tags"] = ""
        if "Time" not in new_df.columns:
            new_df["Time"] = "00:00"
        if "Account" not in new_df.columns:
            # Use default account for uploads
            default_account = am.get_default_account()
            new_df["Account"] = default_account["name"] if default_account else "Main Account"
            
        # Apply Auto-Categorization Rules
        new_df = apply_categorization(new_df)

        # Basic Deduplication Logic
        # We create a 'signature' for each transaction
        # Signature = Date + Amount + Description (approx)
        
        # Filter Only New Rows
        # This is a naive check; for robust checking we might hash rows
        # But pandas merge can handle this
        
        # Let's use Source column specifically to track uploads
        
        # Select only relevant columns
        new_df = new_df[COLUMNS]
        
        # Concatenate and drop duplicates across all columns
        combined_df = pd.concat([existing_df, new_df])
        
        # Check specific duplicates based on Date and Amount and Description
        # subset checks for exact match on these fields
        before_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=["Date", "Amount", "Description"], keep='first')
        after_count = len(combined_df)
        
        added_count = len(combined_df) - len(existing_df)
        
        if added_count > 0:
            save_data(combined_df)
            
        return added_count, None
        
    except Exception as e:
        return 0, str(e)
