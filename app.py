"""
Customer Engagement and Product Utilization Analytics Dashboard
-----------------------------------------------------------------
This Streamlit application is the live, interactive companion to the
research paper and Jupyter notebook analysis. It reads the same
European_Bank.csv dataset and recreates the same engagement profiles,
product utilization findings, and KPIs, but lets the user filter and
explore the data live instead of only reading static charts.

To run this dashboard:
    1. Make sure European_Bank.csv is in the same folder as this file.
    2. Open a terminal in that folder.
    3. Run: pip install streamlit plotly pandas
    4. Run: streamlit run app.py
    5. A browser tab will open automatically at http://localhost:8501
"""

import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------
# Page configuration. This must be the first Streamlit command in the
# script. "wide" layout gives the dashboard the full browser width,
# which is more suitable for charts and tables than the default
# centered, narrow layout.
# -----------------------------------------------------------------------
st.set_page_config(
    page_title="Customer Retention Analytics",
    page_icon="\U0001F4CA",
    layout="wide",
)


# -----------------------------------------------------------------------
# Data loading and preparation
# -----------------------------------------------------------------------
# The @st.cache_data decorator tells Streamlit to run this function once
# and reuse the result on every rerun of the app, instead of reloading
# and reprocessing the CSV file every time the user moves a filter.
# Without this, the dashboard would feel slow because Streamlit reruns
# the entire script from top to bottom on every single interaction.
@st.cache_data
def load_data():
    df = pd.read_csv("European_Bank.csv")

    # Drop the Year column. It was found during data validation to hold
    # only a single constant value across every row, so it carries no
    # information and is not used anywhere in this dashboard.
    df = df.drop(columns=["Year"], errors="ignore")

    # Balance threshold used throughout the notebook and research paper.
    # Recalculating it here keeps the dashboard consistent with those
    # documents rather than inventing a new cutoff.
    balance_threshold = df["Balance"].median()
    salary_threshold = df["EstimatedSalary"].median()

    # Recreate the four engagement profiles from Phase 2 of the notebook.
    # Written as a function and applied row by row with axis=1, exactly
    # as in the notebook, so the logic matches the research paper exactly.
    def classify_engagement(row):
        if row["IsActiveMember"] == 1:
            if row["NumOfProducts"] >= 2:
                return "Active Engaged"
            else:
                return "Active Low-Product"
        else:
            if row["Balance"] > balance_threshold:
                return "Inactive High-Balance"
            else:
                return "Inactive Disengaged"

    df["EngagementProfile"] = df.apply(classify_engagement, axis=1)

    # Product group used in Phase 3: single-product vs multi-product.
    df["ProductGroup"] = df["NumOfProducts"].apply(
        lambda x: "Single-Product" if x == 1 else "Multi-Product"
    )

    # Relationship Strength Index from Phase 6: one point each for being
    # active, holding two or more products, and holding a credit card.
    df["RelationshipStrengthIndex"] = (
        df["IsActiveMember"]
        + (df["NumOfProducts"] >= 2).astype(int)
        + df["HasCrCard"]
    )

    # Sticky customer flag from Phase 5: Active Engaged AND has a credit card.
    df["Sticky"] = (
        (df["EngagementProfile"] == "Active Engaged") & (df["HasCrCard"] == 1)
    ).astype(int)

    return df, balance_threshold, salary_threshold


df, balance_threshold, salary_threshold = load_data()
overall_churn_rate = df["Exited"].mean() * 100


# -----------------------------------------------------------------------
# Sidebar filters
# -----------------------------------------------------------------------
# These filters apply to every tab in the dashboard, so the user can,
# for example, narrow the whole dashboard down to only Inactive
# High-Balance customers holding 2 or 3 products above a certain balance.
st.sidebar.header("Filters")
st.sidebar.markdown(
    "These filters apply across every tab. Use them to zoom into a "
    "specific customer segment."
)

# Multiselect lets the user pick any combination of the four engagement
# profiles. Defaulting to all four means the dashboard shows the full
# customer base until the user chooses to narrow it down.
engagement_options = sorted(df["EngagementProfile"].unique())
selected_profiles = st.sidebar.multiselect(
    "Engagement Profile",
    options=engagement_options,
    default=engagement_options,
)

# A range slider for number of products, from the dataset minimum to
# maximum. (min, max) as the default selects the full range initially.
product_min, product_max = int(df["NumOfProducts"].min()), int(df["NumOfProducts"].max())
selected_products = st.sidebar.slider(
    "Number of Products",
    min_value=product_min,
    max_value=product_max,
    value=(product_min, product_max),
)

# A balance threshold slider. Rather than a range, this is a single
# "show customers with balance at or above this value" cutoff, which
# matches how the research paper defines high-balance and premium
# customer segments.
balance_min, balance_max = float(df["Balance"].min()), float(df["Balance"].max())
selected_balance_floor = st.sidebar.slider(
    "Minimum Balance",
    min_value=balance_min,
    max_value=balance_max,
    value=balance_min,
    step=1000.0,
    format="%.0f",
)

# A salary threshold slider, working the same way as the balance slider.
salary_min, salary_max = float(df["EstimatedSalary"].min()), float(df["EstimatedSalary"].max())
selected_salary_floor = st.sidebar.slider(
    "Minimum Estimated Salary",
    min_value=salary_min,
    max_value=salary_max,
    value=salary_min,
    step=1000.0,
    format="%.0f",
)

# Applying all four filters together with boolean masking. Each
# condition produces a column of True/False values, and combining them
# with "&" keeps only rows where every condition is True at once.
filtered_df = df[
    (df["EngagementProfile"].isin(selected_profiles))
    & (df["NumOfProducts"].between(selected_products[0], selected_products[1]))
    & (df["Balance"] >= selected_balance_floor)
    & (df["EstimatedSalary"] >= selected_salary_floor)
]

st.sidebar.markdown(f"**{len(filtered_df):,}** customers match the current filters "
                     f"(out of {len(df):,} total).")


# -----------------------------------------------------------------------
# Page header
# -----------------------------------------------------------------------
st.title("Customer Engagement & Product Utilization Analytics")
st.caption("Retention strategy dashboard for European Bank customer data")

if filtered_df.empty:
    st.warning("No customers match the current filter selection. Please widen the filters in the sidebar.")
    st.stop()


# -----------------------------------------------------------------------
# Tabs: one per core module requested in the project guidelines
# -----------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview: Engagement vs Churn",
    "Product Utilization Impact",
    "High-Value Disengaged Detector",
    "Retention Strength Scoring",
])


# ========================= TAB 1: OVERVIEW ==============================
with tab1:
    st.subheader("Engagement vs Churn Overview")

    # st.metric displays a single number as a large "KPI card", commonly
    # used at the top of dashboards. st.columns splits the row into four
    # equal-width sections so the four cards sit side by side.
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Customers (filtered)", f"{len(filtered_df):,}")
    col2.metric("Churn Rate (filtered)", f"{filtered_df['Exited'].mean() * 100:.2f}%")
    col3.metric("Overall Churn Rate (all customers)", f"{overall_churn_rate:.2f}%")

    active_rate = filtered_df["IsActiveMember"].mean() * 100
    col4.metric("Active Members (filtered)", f"{active_rate:.1f}%")

    st.markdown("---")

    # Bar chart: churn rate by engagement profile, built from the
    # currently filtered data so it updates live as filters change.
    profile_churn = (
        filtered_df.groupby("EngagementProfile")["Exited"].mean() * 100
    ).round(2).reset_index()
    profile_churn.columns = ["EngagementProfile", "ChurnRate"]
    profile_churn = profile_churn.sort_values("ChurnRate", ascending=False)

    fig1 = px.bar(
        profile_churn,
        x="EngagementProfile",
        y="ChurnRate",
        color="ChurnRate",
        color_continuous_scale="Reds",
        text="ChurnRate",
        labels={"ChurnRate": "Churn Rate (%)", "EngagementProfile": "Engagement Profile"},
        title="Churn Rate by Engagement Profile",
    )
    fig1.update_traces(texttemplate="%{text}%", textposition="outside")
    fig1.add_hline(
        y=overall_churn_rate,
        line_dash="dash",
        line_color="black",
        annotation_text=f"Overall churn rate: {overall_churn_rate:.2f}%",
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown(
        "**Key finding:** Inactive High-Balance customers churn at more than "
        "three times the rate of Active Engaged customers. Engagement, not "
        "balance, is the dominant signal of retention risk."
    )


# ================= TAB 2: PRODUCT UTILIZATION IMPACT ====================
with tab2:
    st.subheader("Product Utilization Impact Analysis")

    product_churn = (
        filtered_df.groupby("NumOfProducts")["Exited"].agg(["count", "mean"])
    ).reset_index()
    product_churn["mean"] = (product_churn["mean"] * 100).round(2)
    product_churn.columns = ["NumOfProducts", "CustomerCount", "ChurnRate"]

    col_a, col_b = st.columns([2, 1])

    with col_a:
        fig2 = px.bar(
            product_churn,
            x="NumOfProducts",
            y="ChurnRate",
            text="ChurnRate",
            color="ChurnRate",
            color_continuous_scale="Blues",
            labels={"ChurnRate": "Churn Rate (%)", "NumOfProducts": "Number of Products"},
            title="Churn Rate by Number of Products Held",
        )
        fig2.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.markdown("**Customers per product count**")
        st.dataframe(product_churn.set_index("NumOfProducts"), use_container_width=True)

    st.markdown("---")

    # Single-product vs multi-product comparison, shown as two metric cards.
    single_multi = (filtered_df.groupby("ProductGroup")["Exited"].mean() * 100).round(2)
    m1, m2 = st.columns(2)
    m1.metric("Single-Product Churn Rate", f"{single_multi.get('Single-Product', 0):.2f}%")
    m2.metric("Multi-Product Churn Rate", f"{single_multi.get('Multi-Product', 0):.2f}%")

    st.markdown(
        "**Key finding:** Two products is the genuine retention sweet spot. "
        "Customers holding three or four products behave as a distinct, "
        "extremely high-risk segment rather than showing deeper loyalty."
    )


# ============= TAB 3: HIGH-VALUE DISENGAGED DETECTOR =====================
with tab3:
    st.subheader("High-Value Disengaged Customer Detector")
    st.markdown(
        "This tool identifies customers who look financially valuable but "
        "show signs of disengagement, the group most likely to represent "
        "'silent churn' the bank is not currently watching for."
    )

    # Premium threshold is recalculated on the full dataset (not the
    # filtered one) so the definition of "premium" stays fixed at the
    # top 25 percent of all customers, regardless of which segment the
    # user is currently viewing in the sidebar filters.
    premium_threshold = df["Balance"].quantile(0.75)

    at_risk = filtered_df[
        (filtered_df["Balance"] > premium_threshold)
        & (filtered_df["IsActiveMember"] == 0)
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric("Premium Balance Threshold", f"{premium_threshold:,.0f}")
    col2.metric("At-Risk Premium Customers (filtered view)", f"{len(at_risk):,}")
    col3.metric(
        "Churn Rate in This Group",
        f"{at_risk['Exited'].mean() * 100:.2f}%" if len(at_risk) > 0 else "N/A",
    )

    st.markdown("---")

    # Scatter plot: Balance vs EstimatedSalary, colored by churn, so the
    # user can visually spot where at-risk premium customers cluster.
    scatter_df = filtered_df.copy()
    scatter_df["Churn Status"] = scatter_df["Exited"].map({0: "Retained", 1: "Churned"})

    fig3 = px.scatter(
        scatter_df,
        x="Balance",
        y="EstimatedSalary",
        color="Churn Status",
        symbol="IsActiveMember",
        opacity=0.6,
        color_discrete_map={"Retained": "#2ca02c", "Churned": "#d62728"},
        labels={"EstimatedSalary": "Estimated Salary", "Balance": "Balance"},
        title="Balance vs Estimated Salary, Colored by Churn Status",
    )
    fig3.add_vline(x=premium_threshold, line_dash="dash", line_color="gray",
                    annotation_text="Premium threshold (75th percentile)")
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("**At-risk premium customer records (filtered):**")
    display_cols = [
        "CustomerId", "Surname", "Geography", "Balance", "EstimatedSalary",
        "NumOfProducts", "IsActiveMember", "EngagementProfile", "Exited",
    ]
    st.dataframe(at_risk[display_cols].reset_index(drop=True), use_container_width=True)


# ================ TAB 4: RETENTION STRENGTH SCORING =======================
with tab4:
    st.subheader("Retention Strength Scoring Panel")

    rsi_summary = (
        filtered_df.groupby("RelationshipStrengthIndex")["Exited"].agg(["count", "mean"])
    ).reset_index()
    rsi_summary["mean"] = (rsi_summary["mean"] * 100).round(2)
    rsi_summary.columns = ["RelationshipStrengthIndex", "CustomerCount", "ChurnRate"]

    col_a, col_b = st.columns([2, 1])

    with col_a:
        fig4 = px.bar(
            rsi_summary,
            x="RelationshipStrengthIndex",
            y="ChurnRate",
            text="ChurnRate",
            color="ChurnRate",
            color_continuous_scale="Greens_r",
            labels={
                "ChurnRate": "Churn Rate (%)",
                "RelationshipStrengthIndex": "Relationship Strength Index (0 = weakest, 3 = strongest)",
            },
            title="Churn Rate by Relationship Strength Index",
        )
        fig4.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig4, use_container_width=True)

    with col_b:
        sticky_summary = (filtered_df.groupby("Sticky")["Exited"].mean() * 100).round(2)
        st.markdown("**Sticky Customer Segment**")
        st.metric("Sticky Customers Churn Rate", f"{sticky_summary.get(1, 0):.2f}%")
        st.metric("Everyone Else Churn Rate", f"{sticky_summary.get(0, 0):.2f}%")
        sticky_count = int(filtered_df["Sticky"].sum())
        st.caption(
            f"{sticky_count:,} customers in the current filtered view are "
            f"'sticky': Active Engaged and a credit card holder."
        )

    st.markdown("---")
    st.markdown("**Key KPI summary (calculated on the currently filtered data):**")

    active_churn = filtered_df[filtered_df["IsActiveMember"] == 1]["Exited"].mean()
    inactive_churn = filtered_df[filtered_df["IsActiveMember"] == 0]["Exited"].mean()
    engagement_retention_ratio = (
        inactive_churn / active_churn if active_churn > 0 else float("nan")
    )

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    kpi_col1.metric("Engagement Retention Ratio", f"{engagement_retention_ratio:.2f}x")

    high_balance_filtered = filtered_df[filtered_df["Balance"] > balance_threshold]
    hbdr = (
        (high_balance_filtered["IsActiveMember"] == 0).mean() * 100
        if len(high_balance_filtered) > 0 else float("nan")
    )
    kpi_col2.metric("High-Balance Disengagement Rate", f"{hbdr:.2f}%")

    cc_churn = filtered_df[filtered_df["HasCrCard"] == 1]["Exited"].mean()
    nocc_churn = filtered_df[filtered_df["HasCrCard"] == 0]["Exited"].mean()
    ccss = (
        ((nocc_churn - cc_churn) / nocc_churn * 100) if nocc_churn > 0 else float("nan")
    )
    kpi_col3.metric("Credit Card Stickiness Score", f"{ccss:.2f}%")


# -----------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Customer Engagement & Product Utilization Analytics for Retention Strategy | "
    "Unified Mentor Internship Project"
)
