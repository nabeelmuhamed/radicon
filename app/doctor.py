import streamlit as st
import pandas as pd
import plotly.express as px

def doctor(df, dfs):
    st.title("Doctor Dashboard")

    # ===================== CLEAN df (filtered data) =====================
    df = df.copy()
    df['Doctor'] = df['Doctor'].astype(str).str.strip()
    df['Department'] = df['Department'].astype(str).str.strip()
    df['Clinic'] = df['Clinic'].astype(str).str.strip()
    df['Nationality'] = df['Nationality'].astype(str).str.strip()
    df['Insurance Status'] = df['Insurance Status'].astype(str).str.strip()
    df['Visit Date'] = pd.to_datetime(df['Visit Date'], errors='coerce')
    df['Receivable'] = pd.to_numeric(df['Receivable'], errors='coerce').fillna(0)

    # ===================== CLEAN dfs (FULL DATA – NO FILTERS) =====================
    dfs = dfs.copy()
    dfs['Doctor'] = dfs['Doctor'].astype(str).str.strip()
    dfs['Insurance Status'] = dfs['Insurance Status'].astype(str).str.strip()
    dfs['Visit Date'] = pd.to_datetime(dfs['Visit Date'], errors='coerce')
    dfs['Receivable'] = pd.to_numeric(dfs['Receivable'], errors='coerce').fillna(0)

    # ===================== TOP METRICS =====================
    total_doctors = df['Doctor'].nunique()
    total_patients = df['CID'].nunique()
    total_departments = df['Department'].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Patients", total_patients)
    col2.metric("Total Doctors", total_doctors)
    col3.metric("Total Departments", total_departments)

    # ===================== PERIOD FILTERS =====================
    today = pd.Timestamp.today().normalize()

    period_filters = {
        "Today": dfs[dfs['Visit Date'] == today],
        "Yesterday": dfs[dfs['Visit Date'] == today - pd.Timedelta(days=1)],
        "This Month": dfs[
            (dfs['Visit Date'].dt.year == today.year) &
            (dfs['Visit Date'].dt.month == today.month)
        ],
        "Previous Month": dfs[
            (dfs['Visit Date'].dt.year == (today - pd.DateOffset(months=1)).year) &
            (dfs['Visit Date'].dt.month == (today - pd.DateOffset(months=1)).month)
        ],
        "This Quarter": dfs[
            ((dfs['Visit Date'].dt.month - 1) // 3 + 1) ==
            ((today.month - 1) // 3 + 1)
        ],
        "1 Year": dfs[dfs['Visit Date'] >= today - pd.DateOffset(years=1)],
        "Above 1 Year": dfs[dfs['Visit Date'] < today - pd.DateOffset(years=1)]
    }

    # ===================== FUNCTION TO BUILD TABLES =====================
    def build_tables(data):
        # ---------- Patient table ----------
        patient_tbl = (
            data.groupby(['Doctor', 'Insurance Status'])['CID']
            .nunique()
            .reset_index()
            .pivot(index='Doctor', columns='Insurance Status', values='CID')
            .fillna(0)
        )
        patient_tbl['Total'] = patient_tbl.sum(axis=1)
        patient_tbl['Total %'] = patient_tbl['Total'] / patient_tbl['Total'].sum() * 100
        patient_tbl = patient_tbl.reset_index()
        count_cols = patient_tbl.columns.drop(['Doctor', 'Total %'])
        patient_tbl[count_cols] = patient_tbl[count_cols].astype(int).applymap(lambda x: f"{x:,}")
        patient_tbl['Total %'] = patient_tbl['Total %'].map(lambda x: f"{x:.2f}%")

        # ---------- Revenue table ----------
        revenue_tbl = (
            data.groupby(['Doctor', 'Insurance Status'])['Receivable']
            .sum()
            .reset_index()
            .pivot(index='Doctor', columns='Insurance Status', values='Receivable')
            .fillna(0)
        )
        revenue_tbl['Total'] = revenue_tbl.sum(axis=1)
        revenue_tbl['Total %'] = revenue_tbl['Total'] / revenue_tbl['Total'].sum() * 100
        revenue_tbl = revenue_tbl.reset_index()
        revenue_cols = revenue_tbl.columns.drop(['Doctor', 'Total %'])
        revenue_tbl[revenue_cols] = revenue_tbl[revenue_cols].applymap(lambda x: f"Ɖ{x:,.2f}")
        revenue_tbl['Total %'] = revenue_tbl['Total %'].map(lambda x: f"{x:.2f}%")

        return patient_tbl, revenue_tbl

    # ===================== BUILD ALL TABLES =====================
    patient_tables = {}
    revenue_tables = {}
    for period, pdf in period_filters.items():
        patient_tables[period], revenue_tables[period] = build_tables(pdf)

    # ===================== RADIO FOR PATIENT TABLE =====================
    selected_patient_period = st.radio(
        "Select Period for Patient Table",
        options=list(period_filters.keys()),
        horizontal=True,
        index=list(period_filters.keys()).index("This Month")
    )
    st.markdown("### Patient Count by Doctor")
    st.dataframe(patient_tables[selected_patient_period], use_container_width=True)

    # ===================== RADIO FOR REVENUE TABLE =====================
    selected_revenue_period = st.radio(
        "Select Period for Revenue Table",
        options=list(period_filters.keys()),
        horizontal=True,
        index=list(period_filters.keys()).index("This Month")
    )
    st.markdown("### Revenue by Doctor")
    st.dataframe(revenue_tables[selected_revenue_period], use_container_width=True)

    # ===================== REMAINING VISUALS =====================
    # --- Patients by Insurance Status ---
    st.subheader("Patients by Doctor and Insurance Status")
    insurance_df = df.groupby(['Doctor', 'Insurance Status'])['CID'].nunique().reset_index()
    insurance_df = insurance_df.rename(columns={'CID': 'Number of Patients'})
    fig4 = px.bar(
        insurance_df,
        x='Doctor',
        y='Number of Patients',
        color='Insurance Status',
        text='Number of Patients'
    )
    fig4.update_traces(textposition='inside')
    st.plotly_chart(fig4, use_container_width=True)

    # --- Monthly Patients per Doctor ---
    df['Month-Year'] = df['Visit Date'].dt.to_period('M').astype(str)
    monthly_patients = df.groupby(['Doctor', 'Month-Year'])['CID'].nunique().reset_index()
    monthly_patients = monthly_patients.rename(columns={'CID': 'Patients'})
    st.subheader("Monthly Patients per Doctor")
    fig5 = px.line(
        monthly_patients,
        x='Month-Year',
        y='Patients',
        color='Doctor',
        markers=True
    )
    st.plotly_chart(fig5, use_container_width=True)

    # --- Average Patients per Month ---
    avg_patients = monthly_patients.groupby('Doctor')['Patients'].mean().reset_index()
    avg_patients['Patients'] = avg_patients['Patients'].round(1)
    avg_patients = avg_patients.rename(columns={'Patients': 'Average Patients per Month'})
    st.subheader("Average Patients per Month per Doctor")
    st.dataframe(avg_patients, use_container_width=True)

    # --- Department Distribution ---
    st.subheader("Department Distribution per Doctor")
    dept_dist = df.groupby(['Doctor', 'Department'])['CID'].nunique().reset_index()
    dept_dist = dept_dist.rename(columns={'CID': 'Number of Patients'})
    fig6 = px.bar(
        dept_dist,
        x='Doctor',
        y='Number of Patients',
        color='Department',
        text='Number of Patients'
    )
    fig6.update_traces(textposition='inside')
    st.plotly_chart(fig6, use_container_width=True)
