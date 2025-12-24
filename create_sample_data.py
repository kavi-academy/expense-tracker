import pandas as pd
from datetime import datetime

data = [
    {"Date": "2024-01-15", "Amount": 50.00, "Description": "Grocery Store"},
    {"Date": "2024-01-16", "Amount": 120.50, "Description": "Electric Bill"},
    {"Date": "2024-01-20", "Amount": 15.00, "Description": "Coffee Shop"},
    {"Date": "2024-01-22", "Amount": 200.00, "Description": "Weekly Shopping"},
    {"Date": "2024-01-25", "Amount": 45.00, "Description": "Gas Station"}
]

df = pd.DataFrame(data)
df.to_excel("sample_expenses.xlsx", index=False)
print("sample_expenses.xlsx created.")
