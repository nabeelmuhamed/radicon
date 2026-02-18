import streamlit as st
import pandas as pd
import mysql.connector
import hashlib

from summary import summary
from doctor import doctor
from clinic import clinic
from CPT import CPT
from insurance import insurance
from revenue import revenue
from ICD import ICD

# =====================================================
# PAGE CONFIG (MUST BE FIRST STREAMLIT COMMAND)
# =====================================================
st.set_page_config(
    page_title="Radicon Dashboard",
    page_icon="radicon-logo.png",
    layout="wide"
)

# =====================================================
# DATABASE CONNECTION
# =====================================================
conn = mysql.connector.connect(
    host='192.168.0.132',
    user='radicon_user',
    password='Central!1@2#3',
    database='RadiconDB'
)
cursor = conn.cursor()

# =====================================================
# AUTH FUNCTIONS
# =====================================================
def check_credentials(username, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute(
        "SELECT username FROM users WHERE username=%s AND password_hash=%s",
        (username, password_hash)
    )
    return cursor.fetchone() is not None


def login_page():
    st.markdown("## 🔐 Radicon Dashboard Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_credentials(username, password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Invalid username or password")


# =====================================================
# SESSION AUTH
# =====================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_page()
    st.stop()

# =====================================================
# CUSTOM CSS
# =====================================================
st.markdown("""
<style>
.js-plotly-plot .legend {
    max-height: 150px !important;
    overflow-y: auto !important;
}

.reportview-container, .main {
    background-color: #f5f5f5 !important;
    color: #1B365D !important;
}

.stMetric, .stDataFrame, .stPlotlyChart {
    background-color: #ffffff !important;
    color: #1B365D !important;
    padding: 15px;
    border-radius: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

h1, h2, h3, h4, h5, h6 {
    color: #1B365D !important;
}

.stDataFrame table {
    background-color: #ffffff !important;
    color: #1B365D !important;
}

.js-plotly-plot .main-svg text,
.js-plotly-plot .main-svg tspan {
    fill: #1B365D !important;
}

[data-testid="stSegmentedControl"] {
    display: flex !important;
    gap: 6px !important;
    margin-bottom: 20px !important;
}

[data-testid="stSegmentedControl"] button {
    border-radius: 50px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
    border: 1px solid #154080 !important;
    color: #154080 !important;
    background-color: #ffffff !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    transition: all 0.2s ease-in-out;
}

[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
    background-color: #154080 !important;
    color: #ffffff !important;
    box-shadow: 0 6px 12px rgba(21,64,128,0.4);
}

[data-testid="stSegmentedControl"] button:hover {
    background-color: #e6f0ff !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.2);
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR LOGOUT
# =====================================================
if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.rerun()

# =====================================================
# DATA LOADING
# =====================================================
@st.cache_data(show_spinner="Loading data...")
def load_data():
    return {
        "main": pd.read_parquet("billwise.parquet"),
        "dfs": pd.read_parquet("billwise.parquet"),
        "icd": pd.read_parquet("icd.parquet"),
        #"appo": pd.read_parquet("appof.parquet"),
    }

data = load_data()
df = data["main"]

# =====================================================
# INIT FILTER STATE
# =====================================================
if "initialized" not in st.session_state:
    st.session_state.start_date = df["Date"].min().date()
    st.session_state.end_date = df["Date"].max().date()

    for col in [
        "Cash/Ins", "Clinic", "Department", "Doctor",
        "CPT Type", "I.Company", "AgeGroup", "Nationality"
    ]:
        st.session_state[col] = []

    st.session_state.initialized = True

# =====================================================
# GLOBAL FILTERS
# =====================================================
def global_filters(df):
    st.sidebar.header("Filters")

    c1, c2 = st.sidebar.columns(2)
    start = c1.date_input("Start Date", key="start_date")
    end = c2.date_input("End Date", key="end_date")

    filtered = df[
        (df["Date"] >= pd.to_datetime(start)) &
        (df["Date"] <= pd.to_datetime(end))
    ]

    def multi(col, label):
        opts = sorted(filtered[col].dropna().unique())
        sel = st.sidebar.multiselect(label, opts, key=col)
        return filtered[filtered[col].isin(sel)] if sel else filtered

    for col, label in [
        ("Cash/Ins", "Cash / Insurance"),
        ("Clinic", "Clinic"),
        ("Department", "Department"),
        ("Doctor", "Doctor"),
        ("CPT Type", "CPT Type"),
        ("I.Company", "Insurance Company"),
        ("AgeGroup", "Age Group"),
        ("Nationality", "Nationality"),
    ]:
        filtered = multi(col, label)

    if st.sidebar.button("Reset Filters"):
        st.session_state.start_date = df["Date"].min().date()
        st.session_state.end_date = df["Date"].max().date()

        for key in [
            "Cash/Ins", "Clinic", "Department", "Doctor",
            "CPT Type", "I.Company", "AgeGroup", "Nationality"
        ]:
            st.session_state[key] = []

        st.rerun()

    return filtered, start, end

filtered_df, start_date, end_date = global_filters(df)

# =====================================================
# FILTER dfs (NO DATE)
# =====================================================
def apply_filters_no_date(df):
    filtered = df.copy()
    for col in [
        "Cash/Ins", "Clinic", "Department", "Doctor",
        "CPT Type", "I.Company", "AgeGroup", "Nationality"
    ]:
        sel = st.session_state.get(col, [])
        if sel:
            filtered = filtered[filtered[col].isin(sel)]
    return filtered

dfs_filtered = apply_filters_no_date(data["dfs"])


# =====================================================
# FILTER ICD
# =====================================================
def filter_icd(df):
    filtered = df.copy()

    for col in [
        "Doctor", "Clinic", "I.Company",
        "AgeGroup", "Nationality",
        "Department", "Insurance Status"
    ]:
        if col in filtered.columns:
            sel = st.session_state.get(col, [])
            if sel:
                filtered = filtered[filtered[col].isin(sel)]

    return filtered

icd_filtered = filter_icd(data["icd"])

# =====================================================
# NAVIGATION
# =====================================================
st.title("Radicon Healthcare Dashboard")

pages = [
    ("Summary", "summary"),
    ("Clinic Overview", "clinic"),
    ("Revenue Overview", "revenue"),
    ("Doctor Overview", "doctor"),
    ("Insurance Demographics", "insurance"),
    ("Treatment/Procedure View", "cpt"),
    ("Diagnosis View", "icd")
]

selected_label = st.segmented_control(
    "Navigate:",
    options=[label for label, _ in pages],
    default="Summary"
)

current_page = dict(pages)[selected_label]

# =====================================================
# PAGE CONTENT
# =====================================================
if current_page == "summary":
    summary(filtered_df)

elif current_page == "clinic":
    clinic(filtered_df)

elif current_page == "revenue":
    revenue(filtered_df, dfs_filtered)

elif current_page == "doctor":
    doctor(filtered_df, dfs_filtered)

elif current_page == "insurance":
    insurance(filtered_df)

elif current_page == "cpt":
    CPT(filtered_df, dfs_filtered, data["icd"])

elif current_page == "icd":
    ICD(icd_filtered)
