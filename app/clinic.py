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

# -----------------------------
# Common layout for all charts
# -----------------------------
COMMON_LAYOUT = dict(
    margin=dict(l=60, r=40, t=80, b=80),
    xaxis=dict(automargin=True),
    yaxis=dict(automargin=True),
    uniformtext_minsize=8,
    uniformtext_mode="hide"
)

# -----------------------------
# Precompute metrics for speed
# -----------------------------
@st.cache_data(show_spinner=False)
def prepare_clinic_metrics(df):
    metrics = {}
    metrics['clinic_count'] = df["Clinic"].nunique()
    metrics['doctor_count'] = df["Doctor"].nunique()
    metrics['dept_count'] = df["Department"].nunique()
    metrics['user_count'] = df["User"].nunique()
    metrics['patient_count'] = df["CID"].nunique()
    metrics['unique_patient'] = df["MRN"].nunique()

    # Time columns
    df['Day'] = df['Date'].dt.date
    df['Week'] = df['Date'].dt.to_period('W').apply(lambda r: r.start_time)
    df['Month'] = df['Date'].dt.to_period('M').apply(lambda r: r.start_time)
    df['Month-Year'] = df['Date'].dt.to_period('M').astype(str)
    df['Visit Status'] = df['Visit Status'].fillna('Unknown')

    metrics['df'] = df
    return metrics


# -----------------------------
# Main clinic dashboard
# -----------------------------
def clinic(df):
    metrics = prepare_clinic_metrics(df)
    df = metrics['df']

    # -----------------------------
    # KPI Metrics
    # -----------------------------
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Patient Count", f"{metrics['patient_count']:,}")
    col2.metric("Unique Patients", f"{metrics['unique_patient']:,}")
    col3.metric("Clinic Count", metrics['clinic_count'])
    col4.metric("Doctor Count", metrics['doctor_count'])
    col5.metric("Department Count", metrics['dept_count'])
    col6.metric("Receptionist Count", metrics['user_count'])

    # -----------------------------
    # Patient Count Summary
    # -----------------------------
    st.subheader("📊 Patient Count Summary")

    # Radio buttons instead of selectbox
    view_option = st.radio(
        "Select View By:",
        options=["Doctor", "Department", "User"],
        horizontal=True
    )

    if view_option == "Doctor":
        group_cols = ["Doctor"]
    elif view_option == "Department":
        group_cols = ["Department"]
    else:
        group_cols = ["User"]

    patient_summary = (
        df.groupby(group_cols)['CID']
        .nunique()
        .reset_index(name='Patient Count')
        .sort_values('Patient Count', ascending=False)
    )

    st.dataframe(patient_summary)

    # -----------------------------
    # Patient Volume by Clinic
    # -----------------------------
    clinic_counts = df.groupby("Clinic")["CID"].nunique().reset_index(name="Patients")
    fig = px.bar(
        clinic_counts, x="Clinic", y="Patients",
        color="Clinic", text="Patients",
        title="Patient Volume by Clinic"
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Insurance Usage
    # -----------------------------
    insurance_usage = df.groupby(['Clinic', 'Insurance Status'])['CID'].nunique().reset_index(name="Count")
    fig = px.bar(
        insurance_usage, x="Clinic", y="Count",
        color="Insurance Status", barmode="group",
        title="Insured vs Non-Insured Patients by Clinic"
    )
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Hourly Visits
    # -----------------------------
    hourly_visits = df.groupby('Time Slot')['CID'].nunique().reset_index(name='Visits').sort_values('Time Slot')

    fig = px.bar(
        hourly_visits,
        x="Time Slot",
        y="Visits",
        text="Visits",
        title="Unique Patient Visits by Time Slot"
    )

    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(**COMMON_LAYOUT)

    st.plotly_chart(fig, use_container_width=True)


    # -----------------------------
    # Weekday vs Time Slot Heatmap
    # -----------------------------

    # Make sure Date column is datetime
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Extract weekday name
    df['Weekday'] = df['Date'].dt.day_name()

    # Optional: Set weekday order properly
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df['Weekday'] = pd.Categorical(df['Weekday'], categories=weekday_order, ordered=True)

    # Create pivot table
    heatmap_data = (
        df.groupby(['Weekday', 'Time Slot'])['CID']
        .nunique()
        .reset_index()
        .pivot(index='Weekday', columns='Time Slot', values='CID')
        .fillna(0)
    )

    # Sort columns if needed
    heatmap_data = heatmap_data.sort_index()

    # Create heatmap
    fig = px.imshow(
        heatmap_data,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Turbo",
        title="Unique Patient Visits by Weekday and Time Slot"
    )

    fig.update_layout(**COMMON_LAYOUT)

    st.plotly_chart(fig, use_container_width=True)


    # -----------------------------
    # Department Distribution
    # -----------------------------
    dept_clinic = df.groupby(['Clinic', 'Department'])['CID'].nunique().reset_index(name="Count")
    fig = px.bar(
        dept_clinic, x="Clinic", y="Count",
        color="Department", barmode="stack",
        title="Department Volume by Clinic"
    )
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.35))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Daily Visits
    # -----------------------------
    daily_trend = df.groupby(['Day', 'Clinic'])['CID'].nunique().reset_index(name="Visits")
    fig = px.bar(
        daily_trend, x="Day", y="Visits",
        color="Clinic", barmode="group",
        title="Daily Visits by Clinic"
    )
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Weekly Visits
    # -----------------------------
    weekly_trend = df.groupby(['Week', 'Clinic'])['CID'].nunique().reset_index(name="Visits")
    fig = px.bar(
        weekly_trend, x="Week", y="Visits",
        color="Clinic", barmode="group",
        title="Weekly Visits by Clinic"
    )
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Monthly Visits
    # -----------------------------
    monthly_trend = df.groupby(['Month', 'Clinic'])['CID'].nunique().reset_index(name="Visits")
    fig = px.bar(
        monthly_trend, x="Month", y="Visits",
        color="Clinic", barmode="group",
        title="Monthly Visits by Clinic"
    )
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Age Demographics by Department
    # -----------------------------
    age_dept_dist = df.groupby(['Department', 'AgeGroup'])['CID'].nunique().reset_index(name="Count")
    fig = px.bar(
        age_dept_dist, x="Department", y="Count",
        color="AgeGroup", barmode="stack",
        title="Age Group Distribution per Department"
    )
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.35))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Nationality Distribution by Department (Top 7)
    # -----------------------------
    top_nationalities = df['Nationality'].value_counts().nlargest(7).index.tolist()
    df_top_nationalities = df[df['Nationality'].isin(top_nationalities)]
    nationality_dept = df_top_nationalities.groupby(['Department', 'Nationality'])['CID'].nunique().reset_index(name="Count")
    fig = px.bar(
        nationality_dept, x="Department", y="Count",
        color="Nationality", barmode="stack",
        title="Top 7 Nationalities per Department"
    )
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.35))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Visit Status Trend
    # -----------------------------
    visit_status_monthly = df.groupby(['Month-Year', 'Visit Status'])['CID'].nunique().reset_index(name="Patient Count")
    fig = px.line(
        visit_status_monthly,
        x="Month-Year", y="Patient Count",
        color="Visit Status",
        markers=True, text="Patient Count",
        title="Monthly Patient Count by Visit Status"
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(**COMMON_LAYOUT, legend=dict(orientation="h", y=-0.35))
    st.plotly_chart(fig, use_container_width=True)
