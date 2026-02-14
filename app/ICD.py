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
def ICD(df, dfs, icd):

    st.title("ICD Analysis")

    # ----------------------------- CLEANING -----------------------------
    icd = icd.copy()
    icd['Date'] = pd.to_datetime(icd['Date'], errors='coerce')

    today = pd.Timestamp.today().normalize()

    # ----------------------------- PERIOD FILTER -----------------------------
    period_filters = {
        "Today": icd[icd['Date'] == today],
        "Yesterday": icd[icd['Date'] == today - pd.Timedelta(days=1)],
        "This Month": icd[
            (icd['Date'].dt.year == today.year) &
            (icd['Date'].dt.month == today.month)
        ],
        "Previous Month": icd[
            (icd['Date'].dt.year == (today - pd.DateOffset(months=1)).year) &
            (icd['Date'].dt.month == (today - pd.DateOffset(months=1)).month)
        ],
        "This Quarter": icd[
            ((icd['Date'].dt.month - 1)//3 + 1) ==
            ((today.month - 1)//3 + 1)
        ],
        "1 Year": icd[
            icd['Date'] >= today - pd.DateOffset(years=1)
        ],
        "Above 1 Year": icd[
            icd['Date'] < today - pd.DateOffset(years=1)
        ]
    }

    selected_period = st.radio(
        "Select Period",
        list(period_filters.keys()),
        horizontal=True
    )

    icd_filtered = period_filters[selected_period].copy()

    # ===================== BUILD DIAGNOSIS COUNT TABLE =====================
    if icd_filtered.empty:
        st.info("No diagnosis data available for this period.")
        return

    diag_table = (
        icd_filtered.groupby(['Diagnosis', 'Insurance Status'])['CID']
        .nunique()
        .reset_index()
        .pivot(index='Diagnosis', columns='Insurance Status', values='CID')
        .fillna(0)
    )

    diag_table['Total'] = diag_table.sum(axis=1)
    diag_table['Total %'] = (
        diag_table['Total'] / diag_table['Total'].sum() * 100
    )

    diag_table = diag_table.reset_index()
    diag_table = diag_table.sort_values('Total %', ascending=False)

    count_cols = diag_table.columns.drop(['Diagnosis', 'Total %'])

    diag_table[count_cols] = (
        diag_table[count_cols]
        .astype(int)
        .applymap(lambda x: f"{x:,}")
    )

    diag_table['Total %'] = diag_table['Total %'].map(lambda x: f"{x:.2f}%")

    # ----------------------------- DISPLAY -----------------------------
    st.subheader("Diagnosis Count")
    st.dataframe(diag_table, use_container_width=True)
