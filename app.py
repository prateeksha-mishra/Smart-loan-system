import streamlit as st
import sqlite3
import pandas as pd
import hashlib


def init_db():
    conn=sqlite3.connect("loan_data.db")
    cursor=conn.cursor()
    cursor.execute(''' CREATE TABLE IF NOT EXISTS loans 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT,
                   age INTEGER,
                   income REAL,
                   loan_amt REAL,
                   loan_term INTEGER,
                   emi REAL,
                   total_interest REAL,
                   total_payment REAL,
                   risk TEXT)
                   ''')
    conn.commit()
    conn.close()
def save_to_sql (data):
    conn= sqlite3.connect ("loan_data.db")
    cursor= conn.cursor()
    cursor.execute ("""INSERT INTO loans 
        (name, age, income, loan_amt, loan_term, emi, total_interest, total_payment, risk)
        VALUES (?,?,?,?,?,?,?,?,?)""",data)
    conn.commit()
    conn.close()

init_db()

st.title("Smart Loan Eligibility System")
st.header("Applicant details")

name = st.text_input("Enter your name")
age = st.number_input("Enter your age", min_value=18, max_value=70)
income = st.number_input("Enter your monthly income (in Rs.)")
loan_amt = st.number_input("Enter loan amount requested (in Rs.)")
loan_term = st.number_input("Enter loan term (in years)", min_value=1, max_value=30)

interest_rate = 0.10   # 10% annual
def validate_inputs(name, age, income, loan_amt, loan_term):
    errors = []

    if not name.strip():
        errors.append("Name cannot be empty.")

    if age < 21:
        errors.append("Applicant must be at least 21 years old.")

    if income <= 0:
        errors.append("Monthly income must be greater than 0.")

    if loan_amt <= 0:
        errors.append("Loan amount must be greater than 0.")

    if loan_term <= 0:
        errors.append("Loan term must be at least 1 year.")

    if loan_amt > income * 12 * 2:
        errors.append("Requested loan amount is unrealistically high compared to income.")

    return errors

def eligibility_check(age, income):
    reasons = []

    if age < 21:
        reasons.append("Age must be 21 years or above.")

    if income < 25000:
        reasons.append("Monthly income must be at least ₹25,000.")

    if reasons:
        return False, reasons
    return True, []


def calc_emi(P,r,n):
    return (P*r*(1+r)**n)/((1+r)**n-1)
def calc_total_interest(emi,n,P):
    return emi*n-P

# Risk score is calculated using:
# 1. EMI-to-Income ratio (DTI)
# 2. Loan-to-Income ratio (LTI)
# 3. Applicant age (working years left)
# This is a simplified, explainable model inspired by real banking systems

def risk_assessment(age, income, loan_amt, loan_term, interest_rate=0.10):
    score = 100

    # 1 EMI-to-Income Ratio (MOST IMPORTANT)
    monthly_rate = interest_rate / 12
    months = loan_term * 12
    emi = (loan_amt * monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    dti = emi / income  # Debt-to-Income ratio

    if dti > 0.5:
        score -= 60
    elif dti > 0.4:
        score -= 40
    elif dti > 0.3:
        score -= 20

    # 2️ Loan-to-Income Ratio (LTI)
    yearly_income = income * 12
    lti = loan_amt / yearly_income

    if lti > 2:
        score -= 30
    elif lti > 1:
        score -= 15

    # 3️ Age (working years logic)
    if age < 21:
        score -= 40
    elif age < 25:
        score -= 10
    elif age > 60:
        score -= 20

    # Clamp score
    score = max(0, min(score, 100))

    # Final Risk Category
    if score >= 75:
        return "low risk ✅"
    elif score >= 50:
        return "medium risk ⚠️"
    else:
        return "high risk ❌"


if st.button("Check Eligibility"):  # check eligibility
    errors = validate_inputs(name, age, income, loan_amt, loan_term)

    if errors:
        for err in errors:
            st.error(err)
        st.stop()
    eligible, reasons = eligibility_check(age, income)

    if eligible:
        st.success("You are eligible for the loan ✅ ")
        # EMI Calculation
        monthly_rate = interest_rate/12
        months = loan_term * 12
        emi = round(calc_emi(loan_amt, monthly_rate, months),2)
        total_payment = round(emi*months,2)
        total_interest = round(calc_total_interest(emi,months,loan_amt),2)
        risk=risk_assessment(age,income,loan_amt,loan_term)

        st.info(f" 💰 Estimated Monthly EMI: Rs {emi:,.2f}")
        st.info(f" 📊 Total interest payable: Rs {total_interest:,.2f}")
        st.info(f" 📃 Total payment (Principal+Interest): Rs {total_payment:,.2f}")
        st.info(f" 🚩Risk Assessment: {risk}")
        data_to_save=(name,age,income,loan_amt,loan_term,emi,total_interest,total_payment,risk)
        save_to_sql(data_to_save)
        st.success(" User data saved to SQL database!")
        if st.session_state.get("admin_logged_in"):
            conn = sqlite3.connect("loan_data.db")
            df_new = pd.read_sql_query("SELECT rowid, * FROM loans", conn)
            df_new_display = df_new.copy()
            df_new_display.insert(0, "ID", range(1, len(df_new_display) + 1))
            st.session_state.df_display = df_new_display
            conn.close()
    else:
        st.error("You are not eligible for the loan ❌ ")
        st.warning("Reasons:")
        for r in reasons:
            st.write(f"• {r}") 

# Admin Panel   
# ------------------- Admin Panel -------------------
st.sidebar.title("🔐 Admin Panel")
stored_hash = st.secrets.get("ADMIN_PASSWORD_HASH")

# Initialize session_state
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# --- Login Form ---
if not st.session_state.admin_logged_in:
    if not stored_hash:
        st.sidebar.error("Admin password not configured.")
    else:
        admin_key = st.sidebar.text_input("Enter password", type="password")
        if st.sidebar.button("Login"):
            entered_hash = hashlib.sha256(admin_key.encode()).hexdigest()
            if entered_hash == stored_hash:
                st.session_state.admin_logged_in = True
                st.sidebar.success("Access Granted ✅")
            else:
                st.sidebar.error("Wrong password ❌")

# --- Logout Button ---
if st.session_state.admin_logged_in:
    if st.sidebar.button("Logout"):
        st.session_state.admin_logged_in = False
        st.sidebar.success("Logged out ✅")

# --- Admin Panel Content ---
if st.session_state.admin_logged_in:
    st.markdown("---")
    st.header("📄 Applicant Database")

    conn = sqlite3.connect("loan_data.db")
    cursor = conn.cursor()

    try:
        # Load data from DB
        df = pd.read_sql_query("SELECT rowid, * FROM loans", conn)

        # Placeholders to update table, metrics, chart
        table_placeholder = st.empty()
        metrics_placeholder = st.empty()
        chart_placeholder = st.empty()

        # Store table in session state to persist across reruns
        if "df_display" not in st.session_state:
            df_display = df.copy()
            df_display.insert(0, "ID", range(1, len(df_display)+1))
            st.session_state.df_display = df_display

        # Function to refresh table + metrics + chart
        def refresh_table():
            df_display = st.session_state.df_display
            table_placeholder.dataframe(df_display, width='stretch')
            # Metrics
            with metrics_placeholder.container():
                col1, col2, col3 = st.columns(3)
                col1.metric("👥 Total Applicants", len(df_display))
                col2.metric("💰 Total Loan Amount", f"₹{df_display['loan_amt'].sum():,.2f}" if len(df_display)>0 else "₹0.00")
                col3.metric("📊 Average Loan", f"₹{df_display['loan_amt'].mean():,.2f}" if len(df_display)>0 else "₹0.00")
            # Chart
            with chart_placeholder.container():
                st.markdown("---")
                st.subheader("📊 Loan Distribution by Applicant")
                if not df_display.empty:
                    st.bar_chart(df_display.set_index("name")["loan_amt"])
                else:
                    st.write("No data to display.")

        # Show initial table
        refresh_table()

        st.markdown("---")
        st.subheader("⛏️ Admin Tools: Data Management")
        col1, col2 = st.columns(2)

        # --- Delete Single Record ---
        with col1:
            df_display = st.session_state.df_display
            if not df_display.empty:
                rowid_options = df_display["rowid"].tolist()
                # Use a placeholder/default to force no selection initially
                rowid_to_del = st.selectbox(
                "Select RowID to delete",
                options=["-- Select a row --"] + rowid_options,
                format_func=lambda x: str(x) if x == "-- Select a row --" else
                f"RowID {x} - {df_display.loc[df_display['rowid'] == x, 'name'].values[0]}"
                )
                if st.button("🗑️ Delete Selected", key="delete_single"):
                    if rowid_to_del == "-- Select a row --":
                        st.warning("Please select a row to delete.")
                    else:
                        try:
                            cursor.execute("DELETE FROM loans WHERE rowid=?", (rowid_to_del,))
                            conn.commit()
                            # Reload table from DB
                            df_new = pd.read_sql_query("SELECT rowid, * FROM loans", conn)
                            df_new_display = df_new.copy()
                            df_new_display.insert(0, "ID", range(1, len(df_new_display)+1))
                            st.session_state.df_display = df_new_display

                            refresh_table()
                            st.success(f"Deleted row with RowID {rowid_to_del}")
                        except Exception as e:
                            st.error(f"Error deleting record: {e}")
            else:
                st.info("No records available to delete.")

        # --- Delete All Records ---
        with col2:
            confirm_all = st.checkbox("Confirm deletion of ALL records", key="confirm_all")
            if st.button("🚨 Emergency Reset", key="delete_all"):
                if confirm_all:
                    cursor.execute("DELETE FROM loans")
                    conn.commit()
                    # Reload empty table
                    df_new = pd.read_sql_query("SELECT rowid, * FROM loans", conn)
                    df_new_display = df_new.copy()
                    df_new_display.insert(0, "ID", range(1, len(df_new_display)+1))
                    st.session_state.df_display = df_new_display
                    refresh_table()
                    st.success("All data wiped out ✅")
                else:
                    st.warning("Please confirm before resetting.")

    except Exception as e:
        st.error(f"Error loading database: {e}")
    finally:
        conn.close()
