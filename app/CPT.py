import streamlit as st
import pandas as pd
import plotly.express as px

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

# ===================== CPT ANALYSIS FUNCTION =====================
def CPT(df, dfs, icd):

    st.title("CPT Analysis")

    # ---------------- BASIC CLEANING ----------------
    dfs = dfs.copy()  # <-- use global filtered dfs
    dfs['Visit Date'] = pd.to_datetime(dfs['Visit Date'], errors='coerce')
    dfs['Receivable'] = pd.to_numeric(dfs['Receivable'], errors='coerce').fillna(0)

    # ---------------- REQUIRED COLUMNS CHECK ----------------
    required_columns = [
        'CPT Type', 'Category Level', 'Visit Date', 'CID',
        'CPT Desc.', 'Receivable', 'Insurance Status',
        'CPT Code', 'Department'
    ]

    for col in required_columns:
        if col not in dfs.columns:
            st.error(f"Column '{col}' not found in dataframe.")
            return

    # ---------------- EXECUTIVE METRICS ----------------
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.metric("Total Visits", f"{df['CID'].nunique():,}")
    with col2:
        st.metric("Unique Procedures", f"{df['CPT Desc.'].nunique():,}")
    with col3:
        st.metric("Total Revenue", f"{df['Receivable'].sum():,.0f}")

    st.divider()

    # ===================== CPT TYPE DROPDOWN =====================
    cpt_types = sorted(dfs['CPT Type'].dropna().unique())

    if not cpt_types:
        st.info("No CPT Types found.")
        return

    selected_cpt_type = st.selectbox("Select CPT Type", cpt_types)

    df_type = dfs[dfs['CPT Type'] == selected_cpt_type]  # <-- filtered from dfs

    if df_type.empty:
        st.info("No data available for selected CPT Type.")
        return

    # ---------------- PERIOD FILTER ----------------
    today = pd.Timestamp.today().normalize()

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

    df_filtered = df_type.copy()

    if selected_period == "Today":
        df_filtered = df_type[df_type['Visit Date'] == today]

    elif selected_period == "Yesterday":
        df_filtered = df_type[df_type['Visit Date'] == today - pd.Timedelta(days=1)]

    elif selected_period == "This Month":
        df_filtered = df_type[
            (df_type['Visit Date'].dt.year == today.year) &
            (df_type['Visit Date'].dt.month == today.month)
        ]

    elif selected_period == "Previous Month":
        prev_month = today - pd.DateOffset(months=1)
        df_filtered = df_type[
            (df_type['Visit Date'].dt.year == prev_month.year) &
            (df_type['Visit Date'].dt.month == prev_month.month)
        ]

    elif selected_period == "Last 3 Months":
        df_filtered = df_type[df_type['Visit Date'] >= today - pd.DateOffset(months=3)]

    elif selected_period == "Last 6 Months":
        df_filtered = df_type[df_type['Visit Date'] >= today - pd.DateOffset(months=6)]

    elif selected_period == "This Year":
        df_filtered = df_type[df_type['Visit Date'].dt.year == today.year]

    elif selected_period == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", today - pd.DateOffset(months=1))
        with col2:
            end_date = st.date_input("End Date", today)
        df_filtered = df_type[
            (df_type['Visit Date'] >= pd.to_datetime(start_date)) &
            (df_type['Visit Date'] <= pd.to_datetime(end_date))
        ]

    if df_filtered.empty:
        st.info("No data available for selected period.")
        return

    st.divider()

    # ===================== TABLE BUILDERS =====================
    def build_patient_table(data):
        if data.empty:
            return pd.DataFrame()
        tbl = (
            data.groupby([
                'CPT Code', 'CPT Description', 'Department', 'Insurance Status'
            ])['CID']
            .nunique()
            .reset_index()
            .pivot(
                index=['CPT Code', 'CPT Description', 'Department'],
                columns='Insurance Status',
                values='CID'
            )
            .fillna(0)
        )
        tbl['Total'] = tbl.sum(axis=1)
        tbl['Total %'] = tbl['Total'] / tbl['Total'].sum() * 100
        tbl = tbl.reset_index().sort_values('Total %', ascending=False)
        count_cols = tbl.columns.drop(['CPT Code', 'CPT Description', 'Department', 'Total %'])
        tbl[count_cols] = tbl[count_cols].astype(int).applymap(lambda x: f"{x:,}")
        tbl['Total %'] = tbl['Total %'].map(lambda x: f"{x:.2f}%")
        return tbl

    def build_revenue_table(data):
        if data.empty:
            return pd.DataFrame()
        tbl = (
            data.groupby([
                'CPT Code', 'CPT Description', 'Department', 'Insurance Status'
            ])['Receivable']
            .sum()
            .reset_index()
            .pivot(
                index=['CPT Code', 'CPT Description', 'Department'],
                columns='Insurance Status',
                values='Receivable'
            )
            .fillna(0)
        )
        tbl['Total'] = tbl.sum(axis=1)
        total_sum = tbl['Total'].sum()
        tbl['Total %'] = (tbl['Total'] / total_sum * 100) if total_sum != 0 else 0
        tbl = tbl.reset_index().sort_values('Total %', ascending=False)
        value_cols = tbl.columns.drop(['CPT Code', 'CPT Description', 'Department', 'Total %'])
        tbl[value_cols] = tbl[value_cols].applymap(lambda x: f"{x:,.0f}")
        tbl['Total %'] = tbl['Total %'].map(lambda x: f"{x:.2f}%")
        return tbl

    # ===================== CATEGORY TOGGLES =====================
    category_levels = sorted(df_filtered['Category Level'].dropna().unique())

    for category in category_levels:
        df_category = df_filtered[df_filtered['Category Level'] == category]
        if df_category.empty:
            continue
        with st.expander(f"Category Level: {category}", expanded=False):
            patient_table = build_patient_table(df_category)
            if patient_table.empty:
                st.info("No patient data available.")
            else:
                st.subheader("Patient Count")
                st.dataframe(patient_table, use_container_width=True, hide_index=True)

            revenue_table = build_revenue_table(df_category)
            if revenue_table.empty:
                st.info("No revenue data available.")
            else:
                st.subheader("Revenue")
                st.dataframe(revenue_table, use_container_width=True, hide_index=True)
