"""
statement_parser.py
Parses UPI/bank statements from CSV or PDF into a clean DataFrame.
Supports: Google Pay CSV, PhonePe CSV, HDFC CSV/PDF, Generic CSV
"""

import io
import re
import pandas as pd
import pdfplumber
from dateutil import parser as dateparser


COLUMN_ALIASES = {
    "date": ["date", "transaction date", "txn date", "value date", "time"],
    "description": ["description", "narration", "particulars", "remarks",
                    "merchant", "to/from", "transaction details", "details"],
    "amount": ["amount", "transaction amount", "debit", "credit",
               "withdrawal", "deposit", "inr"],
    "type": ["type", "transaction type", "cr/dr", "dr/cr"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map whatever column names the bank uses → standard names."""
    rename = {}
    lower_cols = {c.lower().strip(): c for c in df.columns}

    for standard, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_cols and standard not in rename.values():
                rename[lower_cols[alias]] = standard
                break

    df = df.rename(columns=rename)

    # If separate Debit/Credit columns, merge into signed Amount
    if "amount" not in df.columns:
        if "debit" in df.columns and "credit" in df.columns:
            df["debit"] = pd.to_numeric(df["debit"].astype(str)
                                        .str.replace(",", "").str.strip(), errors="coerce").fillna(0)
            df["credit"] = pd.to_numeric(df["credit"].astype(str)
                                         .str.replace(",", "").str.strip(), errors="coerce").fillna(0)
            df["amount"] = df["credit"] - df["debit"]

    return df


def _clean_amount(series: pd.Series) -> pd.Series:
    """Convert amount strings like '₹1,234.56 Dr' → signed float."""
    def parse_amount(val):
        if pd.isna(val):
            return 0.0
        s = str(val).replace("₹", "").replace(",", "").strip()
        # Check for explicit Dr/Cr suffix (common in bank PDFs)
        is_debit_suffix = bool(re.search(r"\b(dr|debit)\b", s, re.I))
        is_credit_suffix = bool(re.search(r"\b(cr|credit)\b", s, re.I))
        # Check for leading negative sign
        has_negative = s.lstrip().startswith("-")
        # Strip everything except digits, dots, minus
        clean = re.sub(r"[^\d.\-]", "", s)
        try:
            amount = float(clean)
            # If already signed, trust it
            if has_negative:
                return amount  # already negative
            # Otherwise apply Dr/Cr suffix logic
            if is_debit_suffix:
                return -abs(amount)
            return abs(amount)
        except ValueError:
            return 0.0

    return series.apply(parse_amount)


def _clean_dates(series: pd.Series) -> pd.Series:
    """Parse varied date formats robustly."""
    def parse_date(val):
        try:
            return dateparser.parse(str(val), dayfirst=True)
        except Exception:
            return pd.NaT

    return series.apply(parse_date)


def parse_csv(file) -> pd.DataFrame:
    """Parse a CSV/Excel bank statement from a file-like object."""
    try:
        df = pd.read_csv(file, encoding="utf-8", skip_blank_lines=True)
    except Exception:
        file.seek(0)
        df = pd.read_csv(file, encoding="latin-1", skip_blank_lines=True)

    # Drop fully empty rows/cols
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = df.columns.str.strip()

    df = _normalize_columns(df)
    _validate_required_columns(df)

    df["date"] = _clean_dates(df["date"])
    df["amount"] = _clean_amount(df["amount"])
    df = df.dropna(subset=["date"])
    df = df[df["amount"] != 0]
    df["description"] = df["description"].astype(str).str.strip()
    df = df.sort_values("date").reset_index(drop=True)

    return df[["date", "description", "amount"]]


def parse_pdf(file) -> pd.DataFrame:
    """Extract transaction table from a bank statement PDF."""
    rows = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and any(cell for cell in row if cell):
                        rows.append([str(c).strip() if c else "" for c in row])

    if not rows:
        raise ValueError("No tables found in PDF. Try exporting as CSV instead.")

    # Use first row as header if it looks like one
    header = rows[0]
    data = rows[1:]
    df = pd.DataFrame(data, columns=header)
    df = df.dropna(how="all").dropna(axis=1, how="all")

    df = _normalize_columns(df)
    _validate_required_columns(df)

    df["date"] = _clean_dates(df["date"])
    df["amount"] = _clean_amount(df["amount"])
    df = df.dropna(subset=["date"])
    df = df[df["amount"] != 0]
    df["description"] = df["description"].astype(str).str.strip()
    df = df.sort_values("date").reset_index(drop=True)

    return df[["date", "description", "amount"]]


def _validate_required_columns(df: pd.DataFrame):
    missing = [c for c in ["date", "description", "amount"] if c not in df.columns]
    if missing:
        raise ValueError(
            f"Could not find required columns: {missing}.\n"
            f"Found columns: {list(df.columns)}\n"
            "Please ensure your file has Date, Description, and Amount columns."
        )


def load_sample_data() -> pd.DataFrame:
    """Return built-in sample transactions for demo purposes."""
    import os
    sample_path = os.path.join(os.path.dirname(__file__),
                               "../../data/samples/sample_transactions.csv")
    with open(sample_path, "r") as f:
        return parse_csv(f)


def parse_statement(uploaded_file) -> pd.DataFrame:
    """
    Main entry point. Auto-detects CSV vs PDF from the uploaded Streamlit file.
    Returns a clean DataFrame with columns: date, description, amount
    """
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return parse_pdf(io.BytesIO(uploaded_file.read()))
    elif name.endswith((".csv", ".txt", ".xlsx", ".xls")):
        return parse_csv(io.StringIO(uploaded_file.read().decode("utf-8", errors="replace")))
    else:
        raise ValueError(f"Unsupported file type: {uploaded_file.name}")
