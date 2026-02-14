import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# Sidebar width + radio horizontal style
# =========================
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 300px !important;
        }
        div[data-baseweb="radio"] > div {
            flex-direction: row;
            gap: 15px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# DATE FILTER FUNCTION
# =========================
def apply_date_filter(df, period):
    today = pd.Timestamp.today().normalize()

    if period == "Today":
        return df[df["Date"] == today]
    if period == "Yesterday":
        return df[df["Date"] == today - pd.Timedelta(days=1)]
    if period == "This Month":
        return df[df["Date"].dt.to_period("M") == today.to_period("M")]
    if period == "Previous Month":
        prev = today.to_period("M") - 1
        return df[df["Date"].dt.to_period("M") == prev]
    if period == "This Quarter":
        return df[df["Date"].dt.to_period("Q") == today.to_period("Q")]
    if period == "This Year":
        return df[df["Date"].dt.year == today.year]
    if period == "Above 1 Year":
        return df[df["Date"] < today - pd.DateOffset(years=1)]
    return df

# =========================
# MAIN DASHBOARD FUNCTION
# =========================
def revenue(df, dfs):

    st.title("🏥 Clinic Revenue Dashboard")

    # =========================
    # DATA PREP
    # =========================
    df = df.copy()
    
    dfs = dfs.copy()

    Xray_codes = dfs["CPT Code"][dfs["CPT Code"].str.contains("RAY", na=False)].unique()
    Lab_codes = dfs["CPT Code"][dfs["CPT Code"].str.contains("LAB", na=False)].unique()
    USG_codes = dfs["CPT Code"][dfs["CPT Code"].str.contains("USG", na=False)].unique()

    dfs["Dept"] = dfs["Department"]
    dfs.loc[dfs["CPT Code"].isin(Xray_codes) | dfs["CPT Code"].isin(USG_codes), "Dept"] = "Xray / USG"
    dfs.loc[dfs["CPT Code"].isin(Lab_codes), "Dept"] = "LAB"
    

    df["Date"] = pd.to_datetime(df["Date"])
    #dfs["Date"] = pd.to_datetime(dfs["Date"])

    df_clean = df[~df["Visit Status"].str.contains("Cancelled", case=False, na=False)]
    dfs_clean = dfs[~dfs["Visit Status"].str.contains("Cancelled", case=False, na=False)]

    # =========================
    # TOP METRICS (NO DATE FILTER)
    # =========================
    avg_patient_revenue = df_clean.groupby("CID")["Receivable"].sum().mean()
    avg_doctor_revenue = df_clean.groupby("Doctor")["Receivable"].sum().mean()
    total_revenue = df_clean["Receivable"].sum()

    cash_revenue = df_clean.loc[df_clean["Cash/Ins"] == "Cash", "Receivable"].sum()
    ins_revenue = df_clean.loc[
        df_clean["Cash/Ins"].str.contains("Insurance", case=False, na=False),
        "Receivable",
    ].sum()

    cancelled_patients = df[df["Visit Status"] == "Cancelled"]["CID"].nunique()
    missed_revenue = cancelled_patients * avg_patient_revenue

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"Ɖ {total_revenue:,.0f}")
    col2.metric("Avg Revenue / Patient", f"Ɖ {avg_patient_revenue:,.0f}")
    col3.metric("Avg Revenue / Doctor", f"Ɖ {avg_doctor_revenue:,.0f}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Cash Revenue", f"Ɖ {cash_revenue:,.0f}")
    col2.metric("Insurance Revenue", f"Ɖ {ins_revenue:,.0f}")
    col3.metric("Missed Avg Revenue", f"Ɖ {missed_revenue:,.0f}")

    # =========================
    # TABLE 1: REVENUE BY DEPARTMENT
    # =========================
    st.subheader("📋 Revenue by Department")

    period_dept = st.radio(
        "Department Table Period",
        ["Today", "Yesterday", "This Month", "Previous Month", "This Quarter", "This Year", "Above 1 Year"],
        horizontal=True
    )
    table_dept_df = apply_date_filter(dfs_clean, period_dept)

    dept_summary = (
        table_dept_df
        .groupby("Department")
        .agg(
            patient_count=("CID", "nunique"),
            total_revenue=("Receivable", "sum"),
            cash_revenue=("Receivable", lambda x: x[table_dept_df.loc[x.index, "Cash/Ins"] == "Cash"].sum()),
            insurance_revenue=("Receivable", lambda x: x[table_dept_df.loc[x.index, "Cash/Ins"].str.contains("Insurance", case=False, na=False)].sum())
        )
        .reset_index()
    )
    dept_summary["total_%"] = dept_summary["total_revenue"] / dept_summary["total_revenue"].sum() * 100
    dept_summary = dept_summary[["Department", "patient_count", "cash_revenue", "insurance_revenue", "total_revenue", "total_%"]]


    st.dataframe(
        dept_summary.style.format({
            "cash_revenue": "Ɖ {:,.0f}",
            "insurance_revenue": "Ɖ {:,.0f}",
            "total_revenue": "Ɖ {:,.0f}",
            "total_%": "{:.1f}%"
        }),
        use_container_width=True
    )

    # =========================
    # TABLE 2: REVENUE BY CPT TYPE
    # =========================
    st.subheader("📋 Revenue by CPT Type")

    period_cpt = st.radio(
        "CPT Table Period",
        ["Today", "Yesterday", "This Month", "Previous Month", "This Quarter", "This Year", "Above 1 Year"],
        horizontal=True
    )
    table_cpt_df = apply_date_filter(dfs_clean, period_cpt)

    user_summary = (
        table_cpt_df
        .groupby("CPT Type")
        .agg(
            patient_count=("CID", "nunique"),
            total_revenue=("Receivable", "sum"),
            cash_revenue=("Receivable", lambda x: x[table_cpt_df.loc[x.index, "Cash/Ins"] == "Cash"].sum()),
            insurance_revenue=("Receivable", lambda x: x[table_cpt_df.loc[x.index, "Cash/Ins"].str.contains("Insurance", case=False, na=False)].sum())
        )
        .reset_index()
    )
    user_summary["average_patient_revenue"] = user_summary["total_revenue"] / user_summary["patient_count"]
    user_summary["total_%"] = user_summary["total_revenue"] / user_summary["total_revenue"].sum() * 100
    user_summary = user_summary[["CPT Type", "patient_count", "cash_revenue", "insurance_revenue", "total_revenue", "total_%"]]

    st.dataframe(
        user_summary.style.format({
            "average_patient_revenue": "Ɖ {:,.0f}",
            "cash_revenue": "Ɖ {:,.0f}",
            "insurance_revenue": "Ɖ {:,.0f}",
            "total_revenue": "Ɖ {:,.0f}",
            "total_%": "{:.1f}%"
        }),
        use_container_width=True
    )

    # =========================
    # VISUALS: TRENDS & BREAKDOWNS
    # =========================
    st.subheader("📈 Revenue Trends")

    # Monthly bar chart
    monthly = df_clean.groupby(pd.Grouper(key="Date", freq="M"))["Receivable"].sum().reset_index()
    fig_monthly = px.bar(monthly, x="Date", y="Receivable", text="Receivable", title="Monthly Revenue", color_discrete_sequence=px.colors.qualitative.Set2)
    fig_monthly.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='outside')
    fig_monthly.update_layout(margin=dict(l=40, r=40, t=50, b=40), yaxis_title="Revenue")
    st.plotly_chart(fig_monthly, use_container_width=True)

    # Weekly line chart
    weekly = df_clean.groupby(pd.Grouper(key="Date", freq="W"))["Receivable"].sum().reset_index()
    fig_weekly = px.line(weekly, x="Date", y="Receivable", markers=True, title="Weekly Revenue", color_discrete_sequence=px.colors.qualitative.Set1)
    fig_weekly.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='top center')
    fig_weekly.update_layout(margin=dict(l=40, r=40, t=50, b=40), yaxis_title="Revenue")
    st.plotly_chart(fig_weekly, use_container_width=True)

    # Daily line chart
    daily = df_clean.groupby(pd.Grouper(key="Date", freq="D"))["Receivable"].sum().reset_index()
    fig_daily = px.line(daily, x="Date", y="Receivable", markers=True, title="Daily Revenue", color_discrete_sequence=px.colors.qualitative.Set1)
    fig_daily.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='top center')
    fig_daily.update_layout(margin=dict(l=40, r=40, t=50, b=40), yaxis_title="Revenue")
    st.plotly_chart(fig_daily, use_container_width=True)

    # Cash vs Insurance
    cash_ins_summary = df_clean.groupby("Cash/Ins")["Receivable"].sum().reset_index()
    fig_cash_ins = px.bar(cash_ins_summary, x="Cash/Ins", y="Receivable", text="Receivable", color="Cash/Ins", title="Revenue by Payment Type", color_discrete_sequence=px.colors.qualitative.Set2)
    fig_cash_ins.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='outside')
    fig_cash_ins.update_layout(margin=dict(l=40, r=40, t=50, b=40), yaxis_title="Revenue", xaxis_title="Payment Type", showlegend=True)
    st.plotly_chart(fig_cash_ins, use_container_width=True)

    # Age & Nationality
    st.subheader("👥 Revenue by Age Group & Nationality")
    age_group_summary = df_clean.groupby("AgeGroup")["Receivable"].sum().reset_index()
    nationality_summary = df_clean.groupby("Nationality")["Receivable"].sum().reset_index()
    col1, col2 = st.columns(2)
    fig_age = px.bar(age_group_summary, x="AgeGroup", y="Receivable", text="Receivable", color="AgeGroup")
    fig_age.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='outside')
    fig_age.update_layout(margin=dict(l=40, r=40, t=40, b=40), showlegend=True)
    col1.plotly_chart(fig_age, use_container_width=True)

    fig_nat = px.bar(nationality_summary, x="Nationality", y="Receivable", text="Receivable", color="Nationality")
    fig_nat.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='outside')
    fig_nat.update_layout(margin=dict(l=40, r=40, t=40, b=40), showlegend=True)
    col2.plotly_chart(fig_nat, use_container_width=True)

    # Weekday
    if "Weekday" in df_clean.columns:
        st.subheader("📅 Revenue by Weekday")
        weekday_summary = df_clean.groupby("Weekday")["Receivable"].sum().reset_index()
        fig_weekday = px.bar(weekday_summary, x="Weekday", y="Receivable", text="Receivable", color="Weekday")
        fig_weekday.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='outside')
        fig_weekday.update_layout(margin=dict(l=40, r=40, t=40, b=40), showlegend=True)
        st.plotly_chart(fig_weekday, use_container_width=True)

    # Top CPT Codes
    if "CPT Code" in df_clean.columns:
        st.subheader("🧾 Top CPT Code by Revenue")
        top_cpt = df_clean.groupby("CPT Code").agg(revenue=("Receivable", "sum"), visits=("CID", "count")).sort_values("revenue", ascending=False).head(10).reset_index()
        fig_cpt = px.bar(top_cpt, x="CPT Code", y="revenue", text="revenue", color="CPT Code")
        fig_cpt.update_traces(texttemplate='Ɖ %{y:,.0f}', textposition='outside')
        fig_cpt.update_layout(margin=dict(l=40, r=40, t=40, b=40), showlegend=True)
        st.plotly_chart(fig_cpt, use_container_width=True)
