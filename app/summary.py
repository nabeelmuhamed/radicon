import streamlit as st
import pandas as pd
import plotly.express as px

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


def summary(df):
       
    DEFAULT_HEIGHT = 350
    DEFAULT_MARGIN = dict(l=40, r=40, t=40, b=30)

    # =========================
    # DATA PREP
    # =========================
    total_patients = df['CID'].nunique()
    doctor_count = df['Doctor'].nunique()
    total_revenue = (df['Receivable']).sum()
    cash_revenue = df.loc[df['Cash/Ins'] == 'Cash', 'Receivable'].sum()
    ins_revenue = df.loc[df['Cash/Ins'] == 'Insurance', 'Receivable'].sum()
    

    df_clean = df[~df['Visit Status'].str.contains('Cancelled', case=False, na=False)]

    patients_per_doctor = df.groupby('Doctor')['CID'].nunique()
    avg_patients_per_doctor = patients_per_doctor.mean()

    avg_patient_revenue = (
        df_clean.groupby('CID')
        .apply(lambda x: (x['Receivable']).sum())
        .mean()
    )

    avg_doctor_revenue = (
        df_clean.groupby('Doctor')
        .apply(lambda x: (x['Receivable']).sum())
        .mean()
    )

    insurance_count = df[df['Insurance Status'] == 'Insured']['CID'].nunique()
    cash_count = df[df['Insurance Status'] == 'Cash']['CID'].nunique()

    hour_counts = df.groupby('Time Slot')['CID'].nunique().reset_index(name='Visits')
    busiest_hour = hour_counts.loc[hour_counts['Visits'].idxmax(), 'Time Slot']

    cancelled_patients = df[df['Visit Status'] == 'Cancelled']['CID'].nunique()
    new_patients = df[df['Visit Status'] == 'New']['CID'].nunique()

    cancellation_rate = (cancelled_patients / total_patients) * 100
    new_rate = (new_patients / total_patients) * 100

    # =========================
    # KPI METRICS
    # =========================
    col1, col2, col3, col4= st.columns([1,1,1,2])
    col1.metric("Total Patients", f"{total_patients:,}")
    
    col2.metric("Doctor Count", f"{doctor_count}")
    col3.metric("Avg Patients / Doctor", f"{avg_patients_per_doctor:.1f}")
    col4.metric("Busiest Hour", busiest_hour)

    col1, col2, col3 = st.columns(3)
    col1.metric("Cash | Insurance", f"{cash_count:,} | {insurance_count:,}")
    col2.metric("New Patients Rate", f"{new_rate:.1f}%",delta=f"New Patient Count: {new_patients}")
    col3.metric("Oppurtunity Missed Rate", f"{cancellation_rate:.1f}%",delta=f"Missed Patient Count: {cancelled_patients}")

    # =========================
    # PATIENT VOLUME TREND
    # =========================
    st.subheader("Patient Volume Trend")

    patient_growth = df.groupby('Date')['CID'].nunique().reset_index()

    fig_growth = px.line(
        patient_growth,
        x='Date',
        y='CID',
        markers=True,
        text='CID'
    )

    fig_growth.update_traces(textposition="top center")
    fig_growth.update_layout(
        height=DEFAULT_HEIGHT,
        margin=DEFAULT_MARGIN,
        yaxis=dict(rangemode='tozero', title="Patients")
    )

    st.plotly_chart(fig_growth, use_container_width=True)

    # =========================
    # FINANCIAL HEALTH
    # =========================
    st.subheader("Financial Health & Productivity")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"Ɖ {total_revenue:,.0f}")
    col2.metric("Avg Revenue / Patient", f"Ɖ {avg_patient_revenue:,.0f}")
    col3.metric("Avg Revenue / Doctor", f"Ɖ {avg_doctor_revenue:,.0f}")

    col1, col2 , col3 = st.columns([2,2,1])
    col1.metric("Cash Revenue", f"Ɖ {cash_revenue:,.0f}")
    col2.metric("Insurance Revenue", f"Ɖ {ins_revenue:,.0f}")

    # =========================
    # CLINIC PATIENTS COUNT
    # =========================
    st.subheader("Clinics Patients Count")

    clinic_summary = (
        df.groupby('Clinic')
        .size()
        .reset_index(name='Visits')
        .sort_values('Visits', ascending=False)
    )

    fig_clinics = px.bar(
        clinic_summary.head(10),
        x='Clinic',
        y='Visits',
        text='Visits'
    )

    fig_clinics.update_traces(textposition='outside')
    fig_clinics.update_layout(
        height=DEFAULT_HEIGHT,
        margin=DEFAULT_MARGIN,
        yaxis=dict(rangemode='tozero', title="Visits"),
        xaxis_title=None
    )

    st.plotly_chart(fig_clinics, use_container_width=True)

    # =========================
    # TOP 3 DOCTORS
    # =========================
    st.subheader("Top 3 Doctor Summary")

    df['Total Amount'] = df['Receivable']

    doctor_summary = df.groupby('Doctor').agg(
        patients_count=('CID', 'nunique'),
        total_revenue=('Total Amount', 'sum')
    )

    doctor_summary['avg_revenue_per_patient'] = (
        doctor_summary['total_revenue'] / doctor_summary['patients_count']
    )

    top_doctors_summary = (
        doctor_summary
        .sort_values('total_revenue', ascending=False)
        .head(3)
    )

    st.table(
        top_doctors_summary.style.format({
            'total_revenue': 'Ɖ {:,.0f}',
            'avg_revenue_per_patient': 'Ɖ {:,.0f}'
        })
    )

    # =========================
    # INSURANCE
    # =========================
    st.subheader("Top Insurance Company & Its Plan")

    df_insurance = df[~df['I.Plan'].str.contains("cash", case=False, na=False)]

    insurance_summary = (
        df_insurance
        .groupby(['I.Company', 'I.Plan'])['CID']
        .nunique()
        .reset_index(name='Patients')
        .sort_values('Patients', ascending=False)
        .head(10)
    )

    fig_insurance = px.bar(
        insurance_summary,
        x='Patients',
        y='I.Company',
        color='I.Plan',
        text='Patients',
        orientation='h'
    )

    fig_insurance.update_traces(textposition='outside')
    fig_insurance.update_layout(
        height=450,
        margin=dict(l=100, r=40, t=40, b=30),
        xaxis=dict(rangemode='tozero', title="Patients")
    )

    st.plotly_chart(fig_insurance, use_container_width=True)

    # =========================
    # CPT CODES
    # =========================
    if 'CPT Type' in df.columns:
        st.subheader("Top 5 CPT Type")
        top_cpt = df['CPT Type'].value_counts().head(5)
        st.bar_chart(top_cpt)


    
