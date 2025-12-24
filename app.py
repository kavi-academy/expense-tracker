import streamlit as st
import pandas as pd
import plotly.express as px
import data_handler as dh
from datetime import datetime

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

    # Load Data
    df = dh.load_data()

    # Sidebar
    st.sidebar.header("Navigation")
    
    # Storage Status
    backend = dh.get_backend()
    if backend == "sheets":
        st.sidebar.success("🟢 Storage: Google Sheets")
    else:
        st.sidebar.warning("🟠 Storage: Local CSV")
        
        st.sidebar.warning("🟠 Storage: Local CSV")
        
    page = st.sidebar.radio("Go to", ["Dashboard", "Add Expenses", "Data View", "Settings"])

    if page == "Dashboard":
        show_dashboard(df)
    elif page == "Add Expenses":
        show_add_expenses()
    elif page == "Data View":
        show_data_view(df)
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
    date_filter = st.sidebar.date_input("Date Range", [])
    
    unique_categories = sorted(df["Category"].unique().tolist())
    category_filter = st.sidebar.multiselect("Category", unique_categories)
    
    unique_types = sorted(df["Type"].unique().tolist())
    type_filter = st.sidebar.multiselect("Transaction Type", unique_types)
    
    # Apply Filters
    filtered_df = df.copy()
    if date_filter and len(date_filter) == 2:
        start_date, end_date = date_filter
        filtered_df = filtered_df[
            (pd.to_datetime(filtered_df["Date"]).dt.date >= start_date) & 
            (pd.to_datetime(filtered_df["Date"]).dt.date <= end_date)
        ]
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
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Income", f"₹{total_income:,.2f}")
    with col2:
        st.metric("Total Expenses", f"₹{total_expenses:,.2f}")
    with col3:
        st.metric("Credit Card Usage", f"₹{cc_spending:,.2f}")
    with col4:
        savings = total_income - total_expenses
        st.metric("Net Savings", f"₹{savings:,.2f}", delta_color="normal" if savings > 0 else "inverse")

    st.markdown("---")

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Expenses by Category")
        if not expense_df.empty:
            cat_fig = px.pie(expense_df, values='Amount', names='Category', hole=0.4, title='')
            st.plotly_chart(cat_fig, use_container_width=True)

    with col2:
        st.subheader("Daily Spending Trend")
        if not expense_df.empty:
            # Aggregate by date
            daily_df = expense_df.groupby("Date")["Amount"].sum().reset_index()
            trend_fig = px.bar(daily_df, x='Date', y='Amount', title='')
            st.plotly_chart(trend_fig, use_container_width=True)
            
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
                # Allow custom categories via "Other" or just editable? 
                # Let's use a standard list + Medicine, but allow typing if we switched to a different input method.
                # For now, adding Medicine to the list.
                default_cats = ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Rent", "Salary", "Investment", "Medicine", "Other"]
                category = st.selectbox("Category", default_cats)
                if category == "Other":
                    category = st.text_input("Enter Custom Category")
                if category == "Other":
                    category = st.text_input("Enter Custom Category")
                description = st.text_input("Description")
                tags = st.text_input("Tags (comma separated, e.g. #vacation, #food)")
            
            submitted = st.form_submit_button("Add Transaction")
            if submitted:
                if amount > 0:
                    dh.add_entry(date, category, amount, description, type, payment_method, str(time), tags)
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

if __name__ == "__main__":
    main()
