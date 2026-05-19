"""
categorizer.py
Categorizes transaction descriptions into spending buckets.
Uses keyword matching with regex — no ML model needed for MVP.
"""

import re
import pandas as pd

# ── Category rules: (regex_pattern, category, emoji) ──────────────────────────
CATEGORY_RULES = [
    # Food & Dining
    (r"zomato|swiggy|dunzo|blinkit|zepto|bigbasket|grofer|instamart|"
     r"dineout|eazydiner|pizza|burger|kfc|mcdonald|subway|domino|cafe|"
     r"restaurant|dhaba|food|tiffin|biryani|sweets|bakery", "Food & Dining", "🍔"),

    # Transport
    (r"uber|ola|rapido|namma yatri|yulu|bounce|metro|irctc|redbus|"
     r"makemytrip|goibibo|cleartrip|indigo|spicejet|airindia|flight|"
     r"railway|petrol|diesel|fuel|parking|toll|fastag", "Transport", "🚗"),

    # Shopping
    (r"amazon|flipkart|myntra|ajio|meesho|nykaa|snapdeal|shopsy|"
     r"reliance|dmart|big bazaar|more stores|spencer|lifestyle|"
     r"westside|zara|h&m|decathlon|croma|vijay sales", "Shopping", "🛍️"),

    # Utilities & Bills
    (r"bescom|bescom|tata power|adani|bses|electricity|water board|"
     r"airtel|jio|vi |vodafone|bsnl|act broadband|hathway|"
     r"gas|lpg|cylinder|pipeline|municipal|bbmp|property tax|"
     r"recharge|prepaid|postpaid|mobile bill|broadband", "Utilities & Bills", "💡"),

    # Subscriptions
    (r"netflix|prime video|hotstar|disney|zee5|sonyliv|jiocinema|"
     r"spotify|gaana|wynk|youtube premium|apple|google one|"
     r"linkedin|coursera|udemy|unacademy|byju|"
     r"subscription|renewal|annual plan", "Subscriptions", "📺"),

    # Health & Wellness
    (r"apollo|fortis|manipal|columbia asia|narayana|medplus|"
     r"1mg|pharmeasy|netmeds|healthkart|cult.fit|cure.fit|"
     r"gym|yoga|doctor|hospital|clinic|pharmacy|medical|"
     r"insurance|star health|care health|niva bupa", "Health & Wellness", "🏥"),

    # Investments & Finance
    (r"zerodha|groww|upstox|paytm money|coin|kuvera|scripbox|"
     r"mutual fund|mf|sip|nps|ppf|fd |fixed deposit|"
     r"lic|hdfc life|sbi life|icici prudential|bajaj allianz|"
     r"emi|loan repayment|credit card bill|loan emi", "Investments & Finance", "📈"),

    # Rent & Housing
    (r"rent|house rent|society|maintenance|flat|apartment|"
     r"housing society|nobroker|nestaway|stanza|paying guest|pg |"
     r"landlord|owner", "Rent & Housing", "🏠"),

    # Education
    (r"school fee|college fee|tuition|coaching|institute|"
     r"books|stationery|education|university|iit|nit|"
     r"exam fee|certification", "Education", "📚"),

    # Entertainment & Leisure
    (r"bookmyshow|paytm insider|pvr|inox|cinepolis|carnival|"
     r"gaming|steam|playstation|xbox|esports|"
     r"travel|holiday|hotel|oyo|treebo|fabhotel|airbnb|"
     r"clubbing|pub|bar|alcohol|beer|wine", "Entertainment", "🎬"),

    # Salary & Income (credits)
    (r"salary|sal cr|payroll|neft cr|imps cr|credited by|"
     r"refund|cashback|reward|interest credit|dividend", "Income / Refund", "💰"),

    # ATM / Cash
    (r"atm|cash withdrawal|cdm", "ATM / Cash", "🏧"),

    # Transfers
    (r"upi|neft|rtgs|imps|transfer|send money|pay to|"
     r"phonepe|gpay|google pay|paytm|bhim|razorpay", "UPI Transfer", "🔄"),
]

# Compile patterns once at module load
COMPILED_RULES = [
    (re.compile(pattern, re.IGNORECASE), category, emoji)
    for pattern, category, emoji in CATEGORY_RULES
]

DEFAULT_CATEGORY = ("Other", "❓")


def categorize_transaction(description: str) -> tuple[str, str]:
    """Return (category, emoji) for a single transaction description."""
    for pattern, category, emoji in COMPILED_RULES:
        if pattern.search(description):
            return category, emoji
    return DEFAULT_CATEGORY


def categorize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 'category' and 'emoji' columns to the transactions DataFrame.
    Also adds 'is_debit' boolean for filtering.
    """
    df = df.copy()
    results = df["description"].apply(categorize_transaction)
    df["category"] = results.apply(lambda x: x[0])
    df["emoji"] = results.apply(lambda x: x[1])
    df["is_debit"] = df["amount"] < 0
    df["abs_amount"] = df["amount"].abs()
    return df


def get_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a pivot of monthly spending per category.
    Includes only debit (expense) transactions.
    """
    expenses = df[df["is_debit"]].copy()
    expenses["month"] = expenses["date"].dt.to_period("M").astype(str)
    pivot = (expenses.groupby(["month", "category"])["abs_amount"]
             .sum()
             .unstack(fill_value=0))
    return pivot


def get_category_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Total spending per category across all time (debits only)."""
    expenses = df[df["is_debit"]].copy()
    totals = (expenses.groupby(["category", "emoji"])["abs_amount"]
              .sum()
              .reset_index()
              .sort_values("abs_amount", ascending=False))
    totals.columns = ["Category", "Emoji", "Total Spent (₹)"]
    return totals
