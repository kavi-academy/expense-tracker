import json
import os
from typing import List, Dict, Optional

ACCOUNTS_FILE = "accounts.json"

def initialize_accounts():
    """Creates default accounts file if it doesn't exist."""
    if not os.path.exists(ACCOUNTS_FILE):
        default_accounts = [
            {
                "id": "main_account",
                "name": "Main Account",
                "type": "Bank Account",
                "description": "Default account",
                "status": "Active",
                "is_default": True
            }
        ]
        save_accounts(default_accounts)
        return default_accounts
    return load_accounts()

def load_accounts() -> List[Dict]:
    """Loads all accounts from JSON file."""
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_accounts(accounts: List[Dict]):
    """Saves accounts to JSON file."""
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4)

def get_all_accounts() -> List[Dict]:
    """Returns all accounts."""
    accounts = load_accounts()
    if not accounts:
        accounts = initialize_accounts()
    return accounts

def get_active_accounts() -> List[Dict]:
    """Returns only active accounts."""
    return [acc for acc in get_all_accounts() if acc.get("status") == "Active"]

def get_account_by_name(name: str) -> Optional[Dict]:
    """Finds an account by name."""
    accounts = get_all_accounts()
    for acc in accounts:
        if acc["name"] == name:
            return acc
    return None

def get_default_account() -> Optional[Dict]:
    """Returns the default account."""
    accounts = get_all_accounts()
    for acc in accounts:
        if acc.get("is_default", False):
            return acc
    # If no default found, return first active account
    active = get_active_accounts()
    return active[0] if active else None

def create_account(name: str, account_type: str, description: str = "", is_default: bool = False) -> bool:
    """Creates a new account."""
    accounts = get_all_accounts()
    
    # Check if account with same name exists
    if any(acc["name"] == name for acc in accounts):
        return False
    
    # Generate ID from name
    account_id = name.lower().replace(" ", "_")
    
    # If setting as default, unset other defaults
    if is_default:
        for acc in accounts:
            acc["is_default"] = False
    
    new_account = {
        "id": account_id,
        "name": name,
        "type": account_type,
        "description": description,
        "status": "Active",
        "is_default": is_default
    }
    
    accounts.append(new_account)
    save_accounts(accounts)
    return True

def update_account(name: str, new_name: str = None, account_type: str = None, 
                  description: str = None, status: str = None, is_default: bool = None) -> bool:
    """Updates an existing account."""
    accounts = get_all_accounts()
    
    for acc in accounts:
        if acc["name"] == name:
            if new_name:
                acc["name"] = new_name
                acc["id"] = new_name.lower().replace(" ", "_")
            if account_type:
                acc["type"] = account_type
            if description is not None:
                acc["description"] = description
            if status:
                acc["status"] = status
            if is_default is not None:
                if is_default:
                    # Unset other defaults
                    for other_acc in accounts:
                        other_acc["is_default"] = False
                acc["is_default"] = is_default
            
            save_accounts(accounts)
            return True
    
    return False

def delete_account(name: str) -> bool:
    """Deletes an account. Cannot delete default account."""
    accounts = get_all_accounts()
    
    for i, acc in enumerate(accounts):
        if acc["name"] == name:
            # Prevent deleting default account
            if acc.get("is_default", False):
                return False
            
            accounts.pop(i)
            save_accounts(accounts)
            return True
    
    return False

def get_account_types() -> List[str]:
    """Returns list of supported account types."""
    return [
        "Bank Account",
        "Credit Card",
        "Cash",
        "Digital Wallet",
        "Other"
    ]

def get_accounts_by_type(account_type: str) -> List[Dict]:
    """Returns all accounts of a specific type."""
    return [acc for acc in get_all_accounts() if acc["type"] == account_type]

def set_default_account(name: str) -> bool:
    """Sets an account as the default."""
    return update_account(name, is_default=True)
