"""
components.py
Reusable Streamlit UI components for the Finance Coach dashboard.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ── Color palette ─────────────────────────────────────────────────────────────
COLORS = px.colors.qualitative.Set3
DEBIT_COLOR = "#FF6B6B"
CREDIT_COLOR = "#51CF66"
ACCENT = "#845EF7"


def metric_cards(stats: dict):
    """4-column KPI strip at the top of the dashboard."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💸 Total Spent", f"₹{stats['total_spend']:,.0f}")
    with col2:
        st.metric("💰 Total Income", f"₹{stats['total_income']:,.0f}")
    with col3:
        delta_color = "normal" if stats["net"] >= 0 else "inverse"
        st.metric("📊 Net Balance", f"₹{stats['net']:,.0f}")
    with col4:
        rate = stats["savings_rate"]
        st.metric("🎯 Savings Rate", f"{rate:.1f}%",
                  delta=f"{'Good' if rate > 20 else 'Low'}",
                  delta_color="normal" if rate > 20 else "inverse")


def spending_donut(category_totals: pd.DataFrame):
    """Donut chart of spending by category."""
    fig = px.pie(
        category_totals,
        names="Category",
        values="Total Spent (₹)",
        hole=0.45,
        color_discrete_sequence=COLORS,
        title="Spending by Category",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", x=1.0, y=0.5),
        margin=dict(t=40, b=10, l=10, r=10),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)


def monthly_bar(df: pd.DataFrame):
    """Grouped bar chart: monthly income vs spend."""
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)

    monthly = df.groupby("month").apply(lambda g: pd.Series({
        "Income": g[~g["is_debit"]]["amount"].sum(),
        "Spend": g[g["is_debit"]]["abs_amount"].sum(),
    })).reset_index()

    fig = go.Figure()
    fig.add_bar(x=monthly["month"], y=monthly["Income"],
                name="Income", marker_color=CREDIT_COLOR)
    fig.add_bar(x=monthly["month"], y=monthly["Spend"],
                name="Spend", marker_color=DEBIT_COLOR)
    fig.update_layout(
        title="Monthly Income vs Spend",
        barmode="group",
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
        height=350,
        margin=dict(t=40, b=30, l=20, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def daily_spend_line(df: pd.DataFrame):
    """Cumulative daily spend line chart for current month."""
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    current_month = df["month"].max()
    curr = df[(df["month"] == current_month) & df["is_debit"]].copy()
    curr["day"] = curr["date"].dt.day
    daily = curr.groupby("day")["abs_amount"].sum().reset_index()
    daily["cumulative"] = daily["abs_amount"].cumsum()

    fig = px.area(daily, x="day", y="cumulative",
                  title=f"Cumulative Spend — {current_month}",
                  labels={"day": "Day of Month", "cumulative": "₹ Spent"},
                  color_discrete_sequence=[ACCENT])
    fig.update_layout(height=300, margin=dict(t=40, b=30, l=20, r=10))
    st.plotly_chart(fig, use_container_width=True)


def anomaly_table(df: pd.DataFrame):
    """Shows flagged anomalous transactions."""
    anomalies = df[df.get("is_anomaly", pd.Series(False, index=df.index))].copy()
    if anomalies.empty:
        st.info("✅ No unusual transactions detected.")
        return

    st.warning(f"⚠️ {len(anomalies)} unusual transaction(s) flagged")
    display = anomalies[["date", "description", "abs_amount", "category"]].copy()
    display.columns = ["Date", "Description", "Amount (₹)", "Category"]
    display["Amount (₹)"] = display["Amount (₹)"].map("₹{:,.2f}".format)
    display["Date"] = display["Date"].dt.strftime("%d %b %Y")
    st.dataframe(display, use_container_width=True, hide_index=True)


def forecast_card(forecast: dict):
    """Displays end-of-month forecast."""
    if not forecast:
        return

    st.subheader("🔮 Month-End Forecast")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Burn Rate", f"₹{forecast['daily_rate']:,.0f}/day")
    with col2:
        st.metric("Projected Total Spend", f"₹{forecast['projected_spend']:,.0f}")
    with col3:
        balance = forecast["projected_balance"]
        st.metric("Projected Balance", f"₹{balance:,.0f}",
                  delta="On track" if balance > 0 else "Overspend risk",
                  delta_color="normal" if balance > 0 else "inverse")


def nudge_cards(nudges: list[str]):
    """Renders savings nudge tips."""
    if not nudges:
        return
    st.subheader("💡 Smart Tips")
    for nudge in nudges:
        st.info(nudge)


def transaction_table(df: pd.DataFrame):
    """Paginated, searchable transaction list."""
    st.subheader("📋 Transactions")
    search = st.text_input("🔍 Search transactions", placeholder="e.g. Swiggy, rent...")

    display = df.copy()
    if search:
        display = display[display["description"].str.contains(search, case=False, na=False)]

    display = display.sort_values("date", ascending=False).head(200)
    out = display[["date", "description", "category", "amount"]].copy()
    out["date"] = out["date"].dt.strftime("%d %b %Y")
    out["amount"] = out["amount"].apply(
        lambda x: f"{'🔴 -₹' if x < 0 else '🟢 +₹'}{abs(x):,.2f}"
    )
    out.columns = ["Date", "Description", "Category", "Amount"]
    st.dataframe(out, use_container_width=True, hide_index=True, height=400)
