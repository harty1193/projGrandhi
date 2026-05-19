"""
insights.py
Analytics engine: anomaly detection, forecasting, and smart nudges.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


# ── Anomaly Detection ─────────────────────────────────────────────────────────

def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    """
    Flags statistically unusual transactions using Isolation Forest.
    Returns the DataFrame with an 'is_anomaly' column added.
    """
    df = df.copy()
    df["is_anomaly"] = False

    # Only run on expense transactions
    expenses = df[df["is_debit"]].copy()
    if len(expenses) < 10:
        return df  # Not enough data

    features = expenses[["abs_amount"]].values
    clf = IsolationForest(contamination=contamination, random_state=42)
    preds = clf.fit_predict(features)  # -1 = anomaly, 1 = normal

    anomaly_idx = expenses.index[preds == -1]
    df.loc[anomaly_idx, "is_anomaly"] = True
    return df


def get_category_anomalies(df: pd.DataFrame) -> list[dict]:
    """
    Detects categories where this month's spend is significantly higher
    than the historical average. Returns a list of alert dicts.
    """
    if "month" not in df.columns:
        df = df.copy()
        df["month"] = df["date"].dt.to_period("M").astype(str)

    expenses = df[df["is_debit"]].copy()
    if expenses.empty:
        return []

    current_month = expenses["month"].max()
    history = expenses[expenses["month"] != current_month]

    if history.empty:
        return []

    alerts = []
    hist_avg = (history.groupby("category")["abs_amount"]
                .mean()
                .rename("hist_avg"))
    curr_spend = (expenses[expenses["month"] == current_month]
                  .groupby("category")["abs_amount"]
                  .sum()
                  .rename("curr_spend"))

    merged = pd.DataFrame({"hist_avg": hist_avg, "curr_spend": curr_spend}).dropna()

    for cat, row in merged.iterrows():
        if row["hist_avg"] > 0:
            ratio = row["curr_spend"] / row["hist_avg"]
            if ratio >= 1.5:  # 50% higher than average
                alerts.append({
                    "category": cat,
                    "current": row["curr_spend"],
                    "average": row["hist_avg"],
                    "ratio": ratio,
                    "message": (
                        f"You spent ₹{row['curr_spend']:,.0f} on {cat} this month — "
                        f"{ratio:.1f}x your usual ₹{row['hist_avg']:,.0f}."
                    )
                })

    return sorted(alerts, key=lambda x: x["ratio"], reverse=True)


# ── Forecasting ───────────────────────────────────────────────────────────────

def forecast_month_end(df: pd.DataFrame) -> dict:
    """
    Forecasts remaining spend and end-of-month balance.
    Uses daily average spend rate extrapolated to month end.
    """
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)

    today = df["date"].max()
    current_month_str = today.to_period("M").astype(str)

    current = df[df["month"] == current_month_str]
    if current.empty:
        return {}

    current_income = current[~current["is_debit"]]["amount"].sum()
    current_spend = current[current["is_debit"]]["abs_amount"].sum()

    day_of_month = today.day
    days_in_month = today.days_in_month
    days_remaining = days_in_month - day_of_month

    if day_of_month == 0:
        return {}

    daily_spend_rate = current_spend / day_of_month
    projected_remaining_spend = daily_spend_rate * days_remaining
    projected_total_spend = current_spend + projected_remaining_spend
    projected_balance = current_income - projected_total_spend

    return {
        "current_income": current_income,
        "current_spend": current_spend,
        "days_elapsed": day_of_month,
        "days_remaining": days_remaining,
        "daily_rate": daily_spend_rate,
        "projected_spend": projected_total_spend,
        "projected_balance": projected_balance,
    }


# ── Smart Nudges ──────────────────────────────────────────────────────────────

def generate_nudges(df: pd.DataFrame) -> list[str]:
    """
    Rule-based spending nudges. Returns a list of tip strings.
    """
    nudges = []
    expenses = df[df["is_debit"]].copy()

    if expenses.empty:
        return nudges

    totals = expenses.groupby("category")["abs_amount"].sum()

    # Food nudge
    food_spend = totals.get("Food & Dining", 0)
    if food_spend > 5000:
        savings = food_spend * 0.3
        nudges.append(
            f"🍔 You spent ₹{food_spend:,.0f} on food. "
            f"Cooking at home 30% more often could save you ~₹{savings:,.0f}/month."
        )

    # Subscriptions nudge
    sub_spend = totals.get("Subscriptions", 0)
    if sub_spend > 1500:
        nudges.append(
            f"📺 ₹{sub_spend:,.0f}/month on subscriptions. "
            "Review which ones you actually use — most people forget 2-3 active ones."
        )

    # Transport nudge
    transport = totals.get("Transport", 0)
    if transport > 3000:
        nudges.append(
            f"🚗 ₹{transport:,.0f} on transport. "
            "Weekly metro/bus passes often beat per-ride costs significantly."
        )

    # ATM nudge
    atm_spend = totals.get("ATM / Cash", 0)
    if atm_spend > 0:
        nudges.append(
            f"🏧 You withdrew ₹{atm_spend:,.0f} in cash. "
            "Cash spending is hard to track — UPI is your friend!"
        )

    return nudges


# ── Summary Stats ─────────────────────────────────────────────────────────────

def get_summary_stats(df: pd.DataFrame) -> dict:
    """Top-level KPIs for the dashboard header."""
    total_income = df[~df["is_debit"]]["amount"].sum()
    total_spend = df[df["is_debit"]]["abs_amount"].sum()
    net = total_income - total_spend
    top_category = (df[df["is_debit"]]
                    .groupby("category")["abs_amount"].sum()
                    .idxmax() if not df[df["is_debit"]].empty else "N/A")
    n_transactions = len(df)

    return {
        "total_income": total_income,
        "total_spend": total_spend,
        "net": net,
        "top_category": top_category,
        "n_transactions": n_transactions,
        "savings_rate": (net / total_income * 100) if total_income > 0 else 0,
    }
