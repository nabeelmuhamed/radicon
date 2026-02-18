import streamlit as st
import pandas as pd

# ----------------------------- SIDEBAR WIDTH -----------------------------
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 300px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ===================== ICD ANALYSIS FUNCTION =====================
def ICD(icd):

    st.title("ICD Analysis")

    # ----------------------------- CLEANING -----------------------------
    icd = icd.copy()
    icd['Date'] = pd.to_datetime(icd['Date'], errors='coerce')

    today = pd.Timestamp.today().normalize()

    # ----------------------------- PERIOD FILTER -----------------------------
    selected_period = st.radio(
        "Select Period",
        [
            "Today",
            "Yesterday",
            "This Month",
            "Previous Month",
            "Last 3 Months",
            "Last 6 Months",
            "This Year",
            "Custom"
        ],
        horizontal=True
    )

    # Default filter
    icd_filtered = icd.copy()

    if selected_period == "Today":
        icd_filtered = icd[icd['Date'] == today]

    elif selected_period == "Yesterday":
        icd_filtered = icd[icd['Date'] == today - pd.Timedelta(days=1)]

    elif selected_period == "This Month":
        icd_filtered = icd[
            (icd['Date'].dt.year == today.year) &
            (icd['Date'].dt.month == today.month)
        ]

    elif selected_period == "Previous Month":
        prev_month = today - pd.DateOffset(months=1)
        icd_filtered = icd[
            (icd['Date'].dt.year == prev_month.year) &
            (icd['Date'].dt.month == prev_month.month)
        ]

    elif selected_period == "Last 3 Months":
        icd_filtered = icd[
            icd['Date'] >= today - pd.DateOffset(months=3)
        ]

    elif selected_period == "Last 6 Months":
        icd_filtered = icd[
            icd['Date'] >= today - pd.DateOffset(months=6)
        ]

    elif selected_period == "This Year":
        icd_filtered = icd[
            icd['Date'].dt.year == today.year
        ]

    elif selected_period == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", today - pd.DateOffset(months=1))
        with col2:
            end_date = st.date_input("End Date", today)

        icd_filtered = icd[
            (icd['Date'] >= pd.to_datetime(start_date)) &
            (icd['Date'] <= pd.to_datetime(end_date))
        ]

    if icd_filtered.empty:
        st.info("No diagnosis data available for this period.")
        return

    # ---------------- DYNAMIC DEPARTMENT SPLIT ----------------
    if 'Department' not in icd_filtered.columns:
        st.error("Column 'Department' not found in ICD data.")
        return

    departments = sorted(icd_filtered['Department'].dropna().unique())

    for dept in departments:
        df_dept = icd_filtered[icd_filtered['Department'] == dept]

        if df_dept.empty:
            continue

        # ----------------------------- TOGGLE EXPANDER (collapsed by default) -----------------------------
        with st.expander(f"Department: {dept}", expanded=False):

            # ===================== BUILD DIAGNOSIS COUNT TABLE =====================
            diag_table = (
                df_dept.groupby(["Diagnosis Code",'Diagnosis', 'Insurance Status'])['CID']
                .nunique()
                .reset_index()
                .pivot(index=["Diagnosis Code",'Diagnosis'], columns='Insurance Status', values='CID')
                .fillna(0)
            )

            diag_table['Total'] = diag_table.sum(axis=1)
            diag_table['Total %'] = diag_table['Total'] / diag_table['Total'].sum() * 100

            diag_table = diag_table.reset_index().sort_values('Total %', ascending=False)

            count_cols = diag_table.columns.drop(["Diagnosis Code",'Diagnosis', 'Total %'])
            diag_table[count_cols] = diag_table[count_cols].astype(int).applymap(lambda x: f"{x:,}")
            diag_table['Total %'] = diag_table['Total %'].map(lambda x: f"{x:.2f}%")

            # ----------------------------- DISPLAY -----------------------------
            st.subheader("Diagnosis Count")
            st.dataframe(diag_table, use_container_width=True)
