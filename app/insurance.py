import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# Sidebar width (consistent UI)
# =========================
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

# =========================
# Insurance Dashboard
# =========================
def insurance(df):

    st.title("🛡️ Insurance Analytics Dashboard")

    DEFAULT_HEIGHT = 380
    DEFAULT_MARGIN = dict(l=40, r=40, t=50, b=40)

    # =========================
    # DATA PREP
    # =========================
    df_ins = df[df['Cash/Ins'].str.contains("Insurance", case=False, na=False)].copy()
    df_clean = df_ins[~df_ins['Visit Status'].str.contains('Cancelled', case=False, na=False)]

    total_ins_patients = df_ins['CID'].nunique()
    total_ins_revenue = df_clean['Receivable'].sum()
    avg_revenue_per_patient = (
        df_clean.groupby('CID')['Receivable'].sum().mean()
    )

    total_companies = df_ins['I.Company'].nunique()
    total_plans = df_ins['I.Plan'].nunique()

    cancelled_ins_patients = df_ins[df_ins['Visit Status'] == 'Cancelled']['CID'].nunique()
    cancellation_rate = (
        (cancelled_ins_patients / total_ins_patients) * 100
        if total_ins_patients > 0 else 0
    )

    # =========================
    # KPI METRICS
    # =========================
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Insured Patients", f"{total_ins_patients:,}")
    col2.metric("Insurance Revenue", f"Ɖ {total_ins_revenue:,.0f}")
    col3.metric("Avg Revenue / Patient", f"Ɖ {avg_revenue_per_patient:,.0f}")
    col4.metric("Cancellation Rate", f"{cancellation_rate:.1f}%")

    col1, col2 = st.columns(2)
    col1.metric("Insurance Companies", total_companies)
    col2.metric("Insurance Plans", total_plans)

    # =========================
    # TOP INSURANCE COMPANIES
    # =========================
    st.subheader("Top Insurance Companies by Patients")

    company_summary = (
        df_ins.groupby('I.Company')['CID']
        .nunique()
        .reset_index(name='Patients')
        .sort_values('Patients', ascending=False)
        .head(10)
    )

    fig_company = px.bar(
        company_summary,
        x='Patients',
        y='I.Company',
        text='Patients',
        orientation='h'
    )
    fig_company.update_traces(textposition='outside')
    fig_company.update_layout(
        height=DEFAULT_HEIGHT,
        margin=dict(l=120, r=40, t=40, b=30),
        xaxis_title="Patients",
        yaxis_title=None
    )

    st.plotly_chart(fig_company, use_container_width=True)

    # =========================
    # TOP INSURANCE PLANS
    # =========================
    st.subheader("Top Insurance Plans")

    plan_summary = (
        df_ins.groupby(['I.Company', 'I.Plan'])['CID']
        .nunique()
        .reset_index(name='Patients')
        .sort_values('Patients', ascending=False)
        .head(10)
    )

    fig_plan = px.bar(
        plan_summary,
        x='Patients',
        y='I.Plan',
        color='I.Company',
        text='Patients',
        orientation='h'
    )

    fig_plan.update_traces(textposition='outside')
    fig_plan.update_layout(
        height=450,
        margin=dict(l=150, r=40, t=40, b=30),
        xaxis_title="Patients",
        yaxis_title=None
    )

    st.plotly_chart(fig_plan, use_container_width=True)

    # =========================
    # INSURANCE REVENUE SHARE
    # =========================
    st.subheader("Insurance Revenue Contribution")

    revenue_by_company = (
        df_clean.groupby('I.Company')['Receivable']
        .sum()
        .reset_index()
        .sort_values('Receivable', ascending=False)
        .head(10)
    )

    fig_rev = px.bar(
        revenue_by_company,
        x='I.Company',
        y='Receivable',
        text='Receivable',
        color='I.Company'
    )

    fig_rev.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='outside')
    fig_rev.update_layout(
        height=DEFAULT_HEIGHT,
        margin=DEFAULT_MARGIN,
        yaxis_title="Revenue",
        xaxis_title=None,
        showlegend=False
    )

    st.plotly_chart(fig_rev, use_container_width=True)

    # =========================
    # INSURANCE TREND
    # =========================
    st.subheader("Insurance Revenue Trend")

    trend = (
        df_clean.groupby('Date')['Receivable']
        .sum()
        .reset_index()
    )

    fig_trend = px.line(
        trend,
        x='Date',
        y='Receivable',
        markers=True
    )

    fig_trend.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='top center')
    fig_trend.update_layout(
        height=DEFAULT_HEIGHT,
        margin=DEFAULT_MARGIN,
        yaxis_title="Revenue"
    )

    st.plotly_chart(fig_trend, use_container_width=True)

    