import streamlit as st
import pandas as pd
import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuration
DATA_FILE = "expenses.csv"
COLUMNS = ["Date", "Time", "Type", "Category", "Amount", "Payment Method", "Description", "Source", "Tags"]
COLUMNS = ["Date", "Time", "Type", "Category", "Amount", "Payment Method", "Description", "Source", "Tags"]
SHEET_URL_KEY = "spreadsheet_url"
RULES_FILE = "category_rules.json"
RECURRING_FILE = "recurring_expenses.json"
import json

def get_backend():
    """Determines if we should use Google Sheets or CSV."""
    try:
        # Check if secrets exist and have the key
        if "gcp_service_account" in st.secrets:
            return "sheets"
    except Exception:
        # Secrets file not found or key missing
        pass
    return "csv"

def get_google_sheet_client():
    """Authenticates and returns the Google Sheet object."""
    # Define the scope
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # Load credentials from Streamlit secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    
    client = gspread.authorize(credentials)
    
    # Open the spreadsheet
    # We expect a secret 'spreadsheet_url' or we can open by title if preferred, 
    # but URL is safer.
    if SHEET_URL_KEY in st.secrets:
        sheet = client.open_by_url(st.secrets[SHEET_URL_KEY]).sheet1
    else:
        # Fallback: try to find a sheet named 'ExpenseTracker' or create it?
        # For simplicity, let's assume if they went through the trouble of setting up
        # service account, they setup the sheet.
        try:
            sheet = client.open("ExpenseTracker").sheet1
        except:
            st.error("Could not find Google Sheet. Please add 'spreadsheet_url' to secrets or name your sheet 'ExpenseTracker'.")
            return None
    return sheet

def load_data():
    """Loads expense data from CSV or Google Sheets."""
    backend = get_backend()
    
    if backend == "sheets":
        try:
            sheet = get_google_sheet_client()
            if not sheet: 
                return pd.DataFrame(columns=COLUMNS)
                
            data = sheet.get_all_records()
            if not data:
                return pd.DataFrame(columns=COLUMNS)
                
            df = pd.DataFrame(data)
            
            # Ensure columns exist even if sheet is empty but has headers
            if df.empty:
                return pd.DataFrame(columns=COLUMNS)

            # Cleanup: Ensure all standard columns exist
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""

            # Ensure proper types
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0.0)
            return df[COLUMNS] # Reorder to standard
            
        except Exception as e:
            st.error(f"Google Sheets Error: {e}")
            return pd.DataFrame(columns=COLUMNS)
            
    else:
        # Fallback to CSV
        if os.path.exists(DATA_FILE):
            try:
                df = pd.read_csv(DATA_FILE)
                # Ensure proper types
                df["Date"] = pd.to_datetime(df["Date"]).dt.date
                df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0.0)
                
                # Verify columns
                for col in COLUMNS:
                     if col not in df.columns:
                        df[col] = ""
                        
                return df
            except Exception as e:
                print(f"Error loading data: {e}")
                return pd.DataFrame(columns=COLUMNS)
        else:
            return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    """Saves expense data to CSV or Google Sheets."""
    backend = get_backend()
    
    # Ensure Date is string for storage stability
    df_store = df.copy()
    df_store["Date"] = df_store["Date"].astype(str)
    
    if backend == "sheets":
        try:
            sheet = get_google_sheet_client()
            if sheet:
                # Clear and write all (simplest way to ensure consistency)
                # For very large datasets, this is bad, but for personal finance (<2000 rows), it's fine.
                sheet.clear()
                # Update headers
                sheet.append_row(df_store.columns.tolist())
                # Update values
                sheet.append_rows(df_store.values.tolist())
        except Exception as e:
            st.error(f"Failed to save to Google Sheets: {e}")
    else:
        df_store.to_csv(DATA_FILE, index=False)

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

def add_entry(date, category, amount, description, type, payment_method, time="00:00", tags="", source="Manual"):
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
