import json
import os
from typing import List, Dict, Optional

CATEGORIES_FILE = "categories.json"  # Fallback only

def initialize_categories():
    """Creates default categories if they don't exist."""
    categories = load_categories()
    if not categories:
        # Default categories based on user's list
        default_categories = [
            {"id": "food", "name": "Food", "type": "Expense", "is_default": False},
            {"id": "transport", "name": "Transport", "type": "Expense", "is_default": False},
            {"id": "entertainment", "name": "Entertainment", "type": "Expense", "is_default": False},
            {"id": "medicals", "name": "MEDICALS", "type": "Expense", "is_default": False},
            {"id": "groceries", "name": "Groceries", "type": "Expense", "is_default": False},
            {"id": "others", "name": "Others", "type": "Expense", "is_default": True},  # Default for uploads
            {"id": "shopping", "name": "Shopping", "type": "Expense", "is_default": False},
            {"id": "bills_utilities", "name": "Bills and Utilities", "type": "Expense", "is_default": False},
            {"id": "education", "name": "Education", "type": "Expense", "is_default": False},
            {"id": "rent", "name": "Rent", "type": "Expense", "is_default": False},
            {"id": "home", "name": "Home", "type": "Expense", "is_default": False},
            {"id": "chit", "name": "Chit", "type": "Expense", "is_default": False},
            {"id": "insurance", "name": "Insurance", "type": "Expense", "is_default": False},
            # Income categories
            {"id": "salary", "name": "Salary", "type": "Income", "is_default": False},
            {"id": "investment", "name": "Investment", "type": "Income", "is_default": False},
        ]
        save_categories(default_categories)
        return default_categories
    return categories

def load_categories() -> List[Dict]:
    """Loads all categories from Excel/Google Sheets or JSON fallback."""
    try:
        # Try to load from Excel/Sheets first
        from data_handler import read_sheet_as_dict, get_backend
        
        if get_backend() == "service_account":
            categories = read_sheet_as_dict("Categories")
            if categories:
                # Normalize boolean values from Sheet
                for cat in categories:
                    is_def = cat.get("is_default", False)
                    if isinstance(is_def, str):
                        cat["is_default"] = is_def.lower() in ("true", "1", "yes", "y", "checked")
                    else:
                        cat["is_default"] = bool(is_def)
                return categories
    except:
        pass
    
    # Fallback to JSON
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_categories(categories: List[Dict]):
    """Saves categories to Excel/Google Sheets and JSON fallback."""
    # Ensure only ONE default per type (Expense/Income)
    expense_default_found = False
    income_default_found = False
    
    # Process from the end to keep the latest marked as true
    for cat in reversed(categories):
        if cat.get("is_default", False):
            if cat.get("type") == "Expense" and not expense_default_found:
                expense_default_found = True
            elif cat.get("type") == "Income" and not income_default_found:
                income_default_found = True
            else:
                cat["is_default"] = False
    
    # If no expense default found, set "Others" if it exists
    if not expense_default_found:
        for cat in categories:
            if cat["name"] == "Others":
                cat["is_default"] = True
                break
    
    # Save to Excel/Sheets
    try:
        from data_handler import write_dict_to_sheet, get_backend
        
        if get_backend() == "service_account":
            write_dict_to_sheet("Categories", categories)
    except:
        pass
    
    # Also save to JSON as fallback
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(categories, f, indent=4)

def get_all_categories() -> List[Dict]:
    """Returns all categories."""
    categories = load_categories()
    if not categories:
        categories = initialize_categories()
    return categories

def get_category_names(category_type: str = None) -> List[str]:
    """Returns list of category names, optionally filtered by type."""
    categories = get_all_categories()
    if category_type:
        categories = [cat for cat in categories if cat.get("type") == category_type]
    return [cat["name"] for cat in categories]

def get_expense_categories() -> List[str]:
    """Returns only expense category names."""
    return get_category_names("Expense")

def get_income_categories() -> List[str]:
    """Returns only income category names."""
    return get_category_names("Income")

def get_category_by_name(name: str) -> Optional[Dict]:
    """Finds a category by name."""
    categories = get_all_categories()
    for cat in categories:
        if cat["name"] == name:
            return cat
    return None

def get_default_category() -> Optional[Dict]:
    """Returns the default category for uploads."""
    categories = get_all_categories()
    for cat in categories:
        if cat.get("is_default", False):
            return cat
    # If no default found, return "Others"
    return get_category_by_name("Others")

def create_category(name: str, category_type: str = "Expense", is_default: bool = False) -> bool:
    """Creates a new category."""
    categories = get_all_categories()
    
    # Check if category with same name exists
    if any(cat["name"].lower() == name.lower() for cat in categories):
        return False
    
    # Generate ID from name
    category_id = name.lower().replace(" ", "_").replace("and", "")
    
    # If setting as default, unset other defaults of same type
    if is_default:
        for cat in categories:
            if cat.get("type") == category_type:
                cat["is_default"] = False
    
    new_category = {
        "id": category_id,
        "name": name,
        "type": category_type,
        "is_default": is_default
    }
    
    categories.append(new_category)
    save_categories(categories)
    return True

def update_category(old_name: str, new_name: str = None, category_type: str = None, is_default: bool = None) -> bool:
    """Updates an existing category."""
    categories = get_all_categories()
    
    for cat in categories:
        if cat["name"] == old_name:
            if new_name:
                cat["name"] = new_name
                cat["id"] = new_name.lower().replace(" ", "_").replace("and", "")
            if category_type:
                cat["type"] = category_type
            if is_default is not None:
                if is_default:
                    # Unset other defaults of same type
                    for other_cat in categories:
                        if other_cat.get("type") == cat["type"]:
                            other_cat["is_default"] = False
                cat["is_default"] = is_default
            
            save_categories(categories)
            return True
    
    return False

def delete_category(name: str) -> bool:
    """Deletes a category."""
    categories = get_all_categories()
    
    for i, cat in enumerate(categories):
        if cat["name"] == name:
            categories.pop(i)
            save_categories(categories)
            return True
    
    return False

def set_default_category(name: str) -> bool:
    """Sets a category as the default for uploads."""
    return update_category(name, is_default=True)
