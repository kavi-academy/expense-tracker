import streamlit as st

def check_password():
    """Returns `True` if the user had the correct password."""

    # 1. Check if secrets are configured
    try:
        # Try to access the password
        # This will raise FileNotFoundError (StreamlitSecretNotFoundError) if no file exists
        # or KeyError if the file exists but key is missing
        correct_password = st.secrets["app_password"]
    except Exception:
        # Secrets not found or configured
        st.warning("⚠️ Login Setup Required")
        st.info("To protect your app with a password, you must create a configuration file.")
        st.markdown("### How to fix:")
        st.markdown("1. Create a folder named `.streamlit`")
        st.markdown("2. Inside it, create a file named `secrets.toml`")
        st.markdown("3. Add this line:")
        st.code('app_password = "admin"', language="toml")
        return False

    # Security: Check for lockout
    if "auth_lockout" in st.session_state:
        import time
        remaining = st.session_state["auth_lockout"] - time.time()
        if remaining > 0:
             col1, col2, col3 = st.columns([1, 2, 1])
             with col2:
                 st.error(f"⛔ Too many failed attempts. Try again in {int(remaining)} seconds.")
             return False
        else:
            del st.session_state["auth_lockout"]
            st.session_state["auth_attempts"] = 0

    # helper to check state
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            st.session_state["auth_attempts"] = 0 # Reset on success
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
            # Increment failures
            attempts = st.session_state.get("auth_attempts", 0) + 1
            st.session_state["auth_attempts"] = attempts
            
            if attempts >= 3:
                import time
                st.session_state["auth_lockout"] = time.time() + 30 # 30 sec lockout
                
    # Return True if we already validated
    if st.session_state.get("password_correct", False):
        return True

    # Show input if not validated
    st.markdown(
        """
        <style>
            .auth-container {
                max-width: 400px;
                margin: auto;
                padding: 30px;
                border-radius: 10px;
                background-color: white;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
            }
        </style>
        """, unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Login Required")
        st.text_input(
            "Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            attempts = st.session_state.get("auth_attempts", 0)
            st.error(f"😕 Password incorrect. Attempt {attempts}/3")

    return False

def logout():
    st.session_state["password_correct"] = False
    st.rerun()

def get_current_user():
    """Returns a dummy user object for compatibility."""
    if st.session_state.get("password_correct", False):
        return {"name": "Admin"}
    return None
