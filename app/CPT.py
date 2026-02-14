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
    # ===================== PAGE TITLE =====================
    st.title("CPT Analysis")

    # ----------------------------- BASIC CLEANING -----------------------------
    df = df.copy()
    icd = icd.copy()
    df['Visit Date'] = pd.to_datetime(df['Visit Date'], errors='coerce')
    icd['Date'] = pd.to_datetime(icd['Date'], errors='coerce')
    df['Receivable'] = pd.to_numeric(df['Receivable'], errors='coerce').fillna(0)

    # ===================== EXECUTIVE METRICS (FULL DATA) =====================
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.metric("Total Visits", f"{df['CID'].nunique():,}")
    with col2:
        st.metric("Unique Procedures", f"{df['CPT Desc.'].nunique():,}")
    with col3:
        st.metric("Total Revenue", f"{df['Receivable'].sum():,.0f}")

    st.divider()

    # ===================== TABLE BUILDER FUNCTION (PATIENT COUNT) =====================
    def build_tables(data):
        cpt_count_tbl = (
            data.groupby(['CPT Desc.', 'Insurance Status'])['CID']
            .nunique()
            .reset_index()
            .pivot(index='CPT Desc.', columns='Insurance Status', values='CID')
            .fillna(0)
        )
        if len(cpt_count_tbl) == 0:
            return pd.DataFrame(columns=['CPT Desc.', 'Cash', 'Insurance', 'Total', 'Total %'])

        cpt_count_tbl['Total'] = cpt_count_tbl.sum(axis=1)
        cpt_count_tbl['Total %'] = (cpt_count_tbl['Total'] / cpt_count_tbl['Total'].sum() * 100)
        cpt_count_tbl = cpt_count_tbl.reset_index()

        # Sort by Total % descending
        cpt_count_tbl = cpt_count_tbl.sort_values('Total %', ascending=False)

        count_cols = cpt_count_tbl.columns.drop(['CPT Desc.', 'Total %'])
        cpt_count_tbl[count_cols] = (
            cpt_count_tbl[count_cols]
            .astype(int)
            .applymap(lambda x: f"{x:,}")
        )
        cpt_count_tbl['Total %'] = cpt_count_tbl['Total %'].map(lambda x: f"{x:.2f}%")
        return cpt_count_tbl

    # ===================== TABLE BUILDER FUNCTION (REVENUE) =====================
    def build_revenue_table(data):
        if len(data) == 0:
            return pd.DataFrame(columns=['CPT Desc.', 'Cash', 'Insurance', 'Total', 'Total %'])

        revenue_tbl = (
            data.groupby(['CPT Desc.', 'Insurance Status'])['Receivable']
            .sum()
            .reset_index()
            .pivot(index='CPT Desc.', columns='Insurance Status', values='Receivable')
            .fillna(0)
        )
        revenue_tbl['Total'] = revenue_tbl.sum(axis=1)
        total_sum = revenue_tbl['Total'].sum()
        revenue_tbl['Total %'] = revenue_tbl['Total'] / total_sum * 100 if total_sum != 0 else 0
        revenue_tbl = revenue_tbl.reset_index()

        # Sort by Total % descending
        revenue_tbl = revenue_tbl.sort_values('Total %', ascending=False)

        value_cols = revenue_tbl.columns.drop(['CPT Desc.', 'Total %'])
        revenue_tbl[value_cols] = revenue_tbl[value_cols].applymap(lambda x: f"{x:,.0f}")
        revenue_tbl['Total %'] = revenue_tbl['Total %'].map(lambda x: f"{x:.2f}%")

        return revenue_tbl

    # ===================== MULTIPLE TABLES BY CPT TYPE WITH TOGGLES =====================
    if 'CPT Type' not in df.columns:
        st.error("Column 'CPT Type' not found in dataframe.")
        return

    cpt_types = sorted(df['CPT Type'].dropna().unique())
    today = pd.Timestamp.today().normalize()

    for cpt_type in cpt_types:
        st.header(f"{cpt_type}")
        df_type = df[df['CPT Type'] == cpt_type]

        # ----------------------------- PER-TABLE PERIOD FILTER -----------------------------
        period_filters = {
            "Today": df_type[df_type['Visit Date'] == today],
            "Yesterday": df_type[df_type['Visit Date'] == today - pd.Timedelta(days=1)],
            "This Month": df_type[
                (df_type['Visit Date'].dt.year == today.year) &
                (df_type['Visit Date'].dt.month == today.month)
            ],
            "Previous Month": df_type[
                (df_type['Visit Date'].dt.year == (today - pd.DateOffset(months=1)).year) &
                (df_type['Visit Date'].dt.month == (today - pd.DateOffset(months=1)).month)
            ],
            "This Quarter": df_type[
                ((df_type['Visit Date'].dt.month - 1) // 3 + 1) == ((today.month - 1) // 3 + 1)
            ],
            "1 Year": df_type[df_type['Visit Date'] >= today - pd.DateOffset(years=1)],
            "Above 1 Year": df_type[df_type['Visit Date'] < today - pd.DateOffset(years=1)]
        }

        # ---------- PER-TABLE RADIO TOGGLE ----------
        selected_period = st.radio(
            f"Select Period for {cpt_type}",
            list(period_filters.keys()),
            key=f"cpt_period_{cpt_type}",
            horizontal=True
        )

        df_filtered = period_filters[selected_period].copy()

        # ----------------------------- PATIENT COUNT TABLE -----------------------------
        patient_table = build_tables(df_filtered)
        if len(patient_table) == 0:
            st.info("No patient data available for this period.")
        else:
            st.subheader("Patient Count")
            st.dataframe(patient_table, use_container_width=True)

        # ----------------------------- REVENUE TABLE -----------------------------
        revenue_table = build_revenue_table(df_filtered)
        if len(revenue_table) == 0:
            st.info("No revenue data available for this period.")
        else:
            st.subheader("Revenue")
            st.dataframe(revenue_table, use_container_width=True)

        st.divider()
