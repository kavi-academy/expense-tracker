import streamlit as st
import pandas as pd
import plotly.express as px
import data_handler as dh
from datetime import datetime
import auth
import account_manager as am

# Page Configuration
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="wide"
)

# Custom CSS for aesthetics
st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .st-emotion-cache-1y4p8pa {
        padding: 2rem;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("💰 Personal Expense Tracker")
    st.markdown("---")
    
    # 🔒 Authentication Flow
    if not auth.check_password():
        st.stop()  # Stop execution if not authenticated

    # User Profile & Logout
    if st.sidebar.button("🚪 Logout"):
        auth.logout()
    st.sidebar.divider()

    # Load Data
    with st.spinner("📂 Loading your expense data..."):
        df = dh.load_data()

    # Sidebar
    st.sidebar.header("Navigation")
    
    # Storage Status
    backend = dh.get_backend()
    if backend == "service_account":
        st.sidebar.success("🟢 Storage: Google Sheets (Cloud)")
    else:
        st.sidebar.warning("🟠 Storage: Local CSV (Temporary)")
        
    page = st.sidebar.radio("Go to", ["Dashboard", "Add Expenses", "Data View", "Accounts", "Settings"])

    if page == "Dashboard":
        show_dashboard(df)
    elif page == "Add Expenses":
        show_add_expenses()
    elif page == "Data View":
        show_data_view(df)
    elif page == "Accounts":
        show_accounts()
    elif page == "Settings":
        show_settings()

def show_dashboard(df):
    if df.empty:
        st.info("No data available. Go to 'Add Expenses' to get started!")
        return

    # Key Metrics
    display_pending_recurring(df)
    
    # --- Filters ---
    st.sidebar.subheader("🔍 Filters")
    
    # Time Period Selector
    time_period = st.sidebar.radio(
        "Time Period",
        ["Monthly", "Yearly", "All-time"],
        index=0,  # Default to Monthly
        horizontal=True
    )
    
    # Apply time period filter
    filtered_df = df.copy()
    
    if time_period == "Monthly":
        # Get current month or allow selection
        current_date = datetime.now()
        available_months = sorted(pd.to_datetime(df["Date"]).dt.to_period('M').unique(), reverse=True)
        
        if len(available_months) > 0:
            month_options = [str(m) for m in available_months]
            current_month_str = f"{current_date.year}-{current_date.month:02d}"
            default_idx = month_options.index(current_month_str) if current_month_str in month_options else 0
            
            selected_month = st.sidebar.selectbox(
                "Select Month",
                month_options,
                index=default_idx
            )
            
            # Filter by selected month
            filtered_df["Date_Period"] = pd.to_datetime(filtered_df["Date"]).dt.to_period('M')
            filtered_df = filtered_df[filtered_df["Date_Period"] == selected_month]
            filtered_df = filtered_df.drop(columns=["Date_Period"])
    
    elif time_period == "Yearly":
        # Get current year or allow selection
        current_year = datetime.now().year
        available_years = pd.to_datetime(df["Date"]).dt.year.unique()
        available_years = sorted(available_years, reverse=True)
        
        if len(available_years) > 0:
            default_idx = list(available_years).index(current_year) if current_year in available_years else 0
            selected_year = st.sidebar.selectbox(
                "Select Year",
                available_years,
                index=default_idx
            )
            
            # Filter by selected year
            filtered_df = filtered_df[pd.to_datetime(filtered_df["Date"]).dt.year == selected_year]
    
    # All-time: no additional filtering needed
    
    # Additional filters
    date_filter = st.sidebar.date_input("Custom Date Range (Optional)", [])
    
    # Account Filter
    if "Account" in filtered_df.columns:
        unique_accounts = sorted(filtered_df["Account"].unique().tolist())
        account_filter = st.sidebar.multiselect("Account", unique_accounts)
    
    unique_categories = sorted(df["Category"].unique().tolist())
    category_filter = st.sidebar.multiselect("Category", unique_categories)
    
    unique_types = sorted(df["Type"].unique().tolist())
    type_filter = st.sidebar.multiselect("Transaction Type", unique_types)
    
    # Apply Filters
    if date_filter and len(date_filter) == 2:
        start_date, end_date = date_filter
        filtered_df = filtered_df[
            (pd.to_datetime(filtered_df["Date"]).dt.date >= start_date) & 
            (pd.to_datetime(filtered_df["Date"]).dt.date <= end_date)
        ]
    if account_filter:
        filtered_df = filtered_df[filtered_df["Account"].isin(account_filter)]
    if category_filter:
        filtered_df = filtered_df[filtered_df["Category"].isin(category_filter)]
    if type_filter:
        filtered_df = filtered_df[filtered_df["Type"].isin(type_filter)]
        
    # --- Metrics based on Filtered Data ---
    # Filter by Type
    expense_df = filtered_df[filtered_df["Type"] == "Expense"]
    income_df = filtered_df[filtered_df["Type"] == "Income"]
    
    total_expenses = expense_df["Amount"].sum()
    total_income = income_df["Amount"].sum()
    
    # Credit Card Spending (subset of expenses)
    cc_spending = expense_df[expense_df["Payment Method"] == "Credit Card"]["Amount"].sum()
    
    # Current Month Calculations (Keep these absolute or relative to filter? Usually Dashboard metrics are better as 'Visible' vs 'Total')
    # Let's show metrics for the FILTERED range primarily
    
    # But for "This Month" delta, we need global context or just relative to something?
    # Let's keep the metrics simple: Show totals for the selected period
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Income", f"₹{total_income:,.2f}")
    with col2:
        st.metric("Total Expenses", f"₹{total_expenses:,.2f}")
    with col3:
        st.metric("Credit Card Usage", f"₹{cc_spending:,.2f}")
    with col4:
        savings = total_income - total_expenses
        st.metric("Net Savings", f"₹{savings:,.2f}", delta_color="normal" if savings > 0 else "inverse")
    with col5:
        # Account count
        active_accounts = len(am.get_active_accounts())
        st.metric("Active Accounts", active_accounts)

    st.markdown("---")

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Expenses by Category")
        if not expense_df.empty:
            cat_fig = px.pie(expense_df, values='Amount', names='Category', hole=0.4, title='')
            st.plotly_chart(cat_fig, use_container_width=True)

    with col2:
        st.subheader("Spending by Account")
        if not expense_df.empty and "Account" in expense_df.columns:
            account_fig = px.bar(expense_df.groupby("Account")["Amount"].sum().reset_index(), 
                               x='Account', y='Amount', title='')
            st.plotly_chart(account_fig, use_container_width=True)
        else:
            st.info("No account data available")
            
    st.markdown("---")
    
    # --- Recent Transactions ---
    st.subheader("🕒 Recent Transactions")
    if not filtered_df.empty:
        # Sort by date descending
        recent_df = filtered_df.sort_values(by="Date", ascending=False).head(10)
        
        for index, row in recent_df.iterrows():
            # Create a nice card-like row
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            with c1:
                st.markdown(f"**{row['Description']}**")
                st.caption(f"{row['Date']} | {row['Time']}")
            with c2:
                st.write(f"{row['Category']}")
                tags = row.get('Tags', '')
                if tags and isinstance(tags, str) and tags.strip():
                     st.caption(f"🏷️ {tags}")
            with c3:
                color = "red" if row['Type'] == "Expense" else "green"
                prefix = "-" if row['Type'] == "Expense" else "+"
                st.markdown(f":{color}[**{prefix}₹{row['Amount']:,.2f}**]")
                st.caption(f"{row['Payment Method']}")
            with c4:
                 st.write(f"_{row['Source']}_")
            st.divider()  
    else:
         st.info("No transactions match your filters.")

def display_pending_recurring(df):
    pending = dh.get_pending_recurring(df)
    if pending:
        st.warning(f"🔔 You have {len(pending)} pending recurring payments for this month.")
        with st.expander("View Pending Payments", expanded=True):
            for p in pending:
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(f"**{p['name']}**")
                with col2:
                    st.write(f"₹{p['amount']}")
                with col3:
                    if st.button("Mark as Paid", key=f"pay_{p['name']}"):
                        dh.add_entry(
                            date=datetime.now(),
                            category=p['category'],
                            amount=p['amount'],
                            description=p['name'],
                            type=p['type'],
                            payment_method="Bank Transfer", # Default
                            tags="#recurring",
                            source="Recurring Auto"
                        )
                        st.success(f"Recorded {p['name']}!")
                        st.rerun()

def show_add_expenses():
    st.header("Add New Expenses")
    
    tab1, tab2 = st.tabs(["📝 Manual Entry", "📂 Upload Excel"])
    
    with tab1:
        with st.form("manual_entry_form"):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date", datetime.now())
                time = st.time_input("Time", datetime.now())
                type = st.selectbox("Type", ["Expense", "Income", "Transfer"])
                amount = st.number_input("Amount", min_value=0.0, step=0.01)
            with col2:
                payment_method = st.selectbox("Payment Method", ["UPI", "Cash", "Credit Card", "Transfer"])
                
                # Account Selection
                active_accounts = am.get_active_accounts()
                account_names = [acc["name"] for acc in active_accounts]
                default_account = am.get_default_account()
                default_idx = 0
                if default_account and default_account["name"] in account_names:
                    default_idx = account_names.index(default_account["name"])
                
                account = st.selectbox("Account", account_names, index=default_idx)
                
                # Allow custom categories via "Other" or just editable? 
                # Let's use a standard list + Medicine, but allow typing if we switched to a different input method.
                # For now, adding Medicine to the list.
                default_cats = ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Rent", "Salary", "Investment", "Medicine", "Other"]
                category = st.selectbox("Category", default_cats)
                if category == "Other":
                    category = st.text_input("Enter Custom Category")
                description = st.text_input("Description")
                tags = st.text_input("Tags (comma separated, e.g. #vacation, #food)")
            
            submitted = st.form_submit_button("Add Transaction")
            if submitted:
                if amount > 0:
                    dh.add_entry(date, category, amount, description, type, payment_method, account, str(time), tags)
                    st.success("Expense added successfully!")
                    st.rerun() # Refresh to update data
                else:
                    st.error("Please enter a valid amount.")

    with tab2:
        st.info("Upload your bank statement or expense sheet (Excel format).")
        st.markdown("**Expected Columns:** Date, Amount, Description/Narration")
        
        uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            if st.button("Process Initial Upload"):
                count, error = dh.process_upload(uploaded_file)
                if error:
                    st.error(f"Error: {error}")
                else:
                    if count > 0:
                        st.success(f"Successfully added {count} new transaction(s)!")
                        st.balloons()
                    else:
                        st.warning("No new unique transactions found (duplicates skipped).")

def show_data_view(df):
    st.header("All Transactions")
    st.header("All Transactions")
    st.info("📝 You can edit, delete, or add rows directly in the table below. Click 'Save Changes' to update.")
    
    if not df.empty:
        # Use data_editor for interactivity
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key="data_editor"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
             if st.button("💾 Save Changes", type="primary"):
                try:
                    dh.save_data(edited_df)
                    st.success("✅ Changes saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving data: {e}")
        
        with col2:
            # Download button
            csv = edited_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download CSV",
                csv,
                "expenses.csv",
                "text/csv",
                key='download-csv'
            )
    else:
        st.info("No records found.")

def show_settings():
    st.header("⚙️ Settings")
    
    st.subheader("Auto-Categorization Rules")
    st.markdown("Define rules to automatically categorize transactions based on keywords in the description.")
    
    rules = dh.load_rules()
    
    # Add New Rule
    with st.form("add_rule_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_keyword = st.text_input("If Description contains (Keyword)")
        with col2:
            # Changed to text_input to allow adding future categories dynamically
            new_category = st.text_input("Assign Category", placeholder="e.g. Medicine, Gym...")
            
        if st.form_submit_button("Add Rule"):
            if new_keyword:
                rules[new_keyword] = new_category
                dh.save_rules(rules)
                st.success(f"Rule added: '{new_keyword}' -> '{new_category}'")
                st.rerun()
            else:
                st.error("Please enter a keyword.")

    st.divider()
    
    # Display Existing Rules
    if rules:
        st.write("### Existing Rules")
        
        # Convert to dataframe for nicer display
        rules_data = [{"Keyword": k, "Category": v} for k, v in rules.items()]
        st.table(rules_data)
        
        # Delete Rule Interaction
        rule_to_delete = st.selectbox("Select Rule to Delete", list(rules.keys()))
        if st.button("Delete Selected Rule"):
            if rule_to_delete in rules:
                del rules[rule_to_delete]
                dh.save_rules(rules)
                st.success(f"Deleted rule for '{rule_to_delete}'")
                st.rerun()
    else:
        st.info("No rules defined yet.")

    st.divider()
    st.subheader("🔁 Recurring Expenses (SIPs)")
    st.markdown("Set up monthly recurring payments like Rent, SIP, etc.")
    
    rec_profiles = dh.load_recurring()
    
    with st.form("add_recurring"):
        c1, c2, c3 = st.columns(3)
        with c1:
            r_name = st.text_input("Name (e.g. SIP Fund)")
            r_amount = st.number_input("Amount", min_value=0.0)
        with c2:
            r_cat = st.selectbox("Category", ["Investment", "Rent", "Utilities", "Other"], key="rec_cat")
            r_type = st.selectbox("Type", ["Expense", "Income", "Transfer"], key="rec_type")
        with c3:
            r_day = st.number_input("Day of Month Due", 1, 31, 1)
            
        if st.form_submit_button("Add Recurring Profile"):
            new_profile = {
                "name": r_name,
                "amount": r_amount,
                "category": r_cat,
                "type": r_type,
                "day": r_day
            }
            rec_profiles.append(new_profile)
            dh.save_recurring(rec_profiles)
            st.success("Recurring profile added!")
            st.rerun()

    if rec_profiles:
        st.write("#### Active Recurring Profiles")
        for i, p in enumerate(rec_profiles):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1: st.write(f"**{p['name']}** ({p['category']})")
            with c2: st.write(f"₹{p['amount']} (Due Day: {p['day']})")
            with c3:
                if st.button("🗑️", key=f"del_rec_{i}"):
                    rec_profiles.pop(i)
                    dh.save_recurring(rec_profiles)
                    st.rerun()

def show_accounts():
    st.header("💳 Account Management")
    st.markdown("Manage your payment accounts (bank accounts, credit cards, cash, digital wallets)")
    
    # Initialize accounts
    am.initialize_accounts()
    accounts = am.get_all_accounts()
    
    # Add New Account
    st.subheader("➕ Add New Account")
    with st.form("add_account_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            acc_name = st.text_input("Account Name", placeholder="e.g. HDFC Credit Card")
        with col2:
            acc_type = st.selectbox("Account Type", am.get_account_types())
        with col3:
            acc_desc = st.text_input("Description (Optional)", placeholder="e.g. Primary card")
        
        is_default = st.checkbox("Set as default account")
        
        if st.form_submit_button("Add Account", type="primary"):
            if acc_name:
                success = am.create_account(acc_name, acc_type, acc_desc, is_default)
                if success:
                    st.success(f"✅ Account '{acc_name}' created successfully!")
                    st.rerun()
                else:
                    st.error("❌ Account with this name already exists.")
            else:
                st.error("Please enter an account name.")
    
    st.divider()
    
    # Display Existing Accounts
    st.subheader("📋 Your Accounts")
    
    if accounts:
        for acc in accounts:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    default_badge = "⭐ " if acc.get("is_default", False) else ""
                    st.markdown(f"### {default_badge}{acc['name']}")
                    st.caption(f"Type: {acc['type']}")
                
                with col2:
                    status_color = "🟢" if acc['status'] == "Active" else "🔴"
                    st.write(f"{status_color} {acc['status']}")
                    if acc.get('description'):
                        st.caption(acc['description'])
                
                with col3:
                    # Show transaction count for this account
                    df = dh.load_data()
                    if not df.empty and "Account" in df.columns:
                        acc_transactions = df[df["Account"] == acc["name"]]
                        st.metric("Transactions", len(acc_transactions))
                
                with col4:
                    # Action buttons
                    if not acc.get("is_default", False):
                        if st.button("Set Default", key=f"default_{acc['id']}"):
                            am.set_default_account(acc['name'])
                            st.success(f"Set {acc['name']} as default")
                            st.rerun()
                    
                    if not acc.get("is_default", False):
                        if st.button("🗑️ Delete", key=f"del_{acc['id']}"):
                            success = am.delete_account(acc['name'])
                            if success:
                                st.success(f"Deleted {acc['name']}")
                                st.rerun()
                            else:
                                st.error("Cannot delete default account")
                
                st.divider()
    else:
        st.info("No accounts found. Add your first account above!")

if __name__ == "__main__":
    main()
