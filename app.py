"""
app.py
UPI Finance Coach — Main Streamlit Application
Run: streamlit run app.py
"""

import os
import sys
import json
import pandas as pd
import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from src.parser.statement_parser import parse_statement, load_sample_data
from src.categorizer.categorizer import categorize_dataframe, get_category_totals
from src.analytics.insights import (
    detect_anomalies,
    get_category_anomalies,
    forecast_month_end,
    generate_nudges,
    get_summary_stats,
)
from src.ui.components import (
    metric_cards,
    spending_donut,
    monthly_bar,
    daily_spend_line,
    anomaly_table,
    forecast_card,
    nudge_cards,
    transaction_table,
)

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="💰 UPI Finance Coach",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .stMetric { background: #1e1e2e; border-radius: 10px; padding: 12px; }
    .stAlert { border-radius: 8px; }
    h1, h2, h3 { color: #e2e8f0; }
    .chat-message { padding: 10px 14px; border-radius: 8px; margin: 6px 0; }
    .chat-user { background: #1e3a5f; text-align: right; }
    .chat-ai { background: #1e2a1e; }
</style>
""", unsafe_allow_html=True)


# ── Session State ──────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💰 Finance Coach")
    st.markdown("---")

    # File upload
    st.subheader("📄 Upload Statement")
    uploaded = st.file_uploader(
        "Drop your bank/UPI statement",
        type=["csv", "pdf", "txt"],
        help="Supports: Google Pay, PhonePe, HDFC, any bank CSV"
    )

    if st.button("🧪 Use Sample Data", use_container_width=True):
        with st.spinner("Loading sample data..."):
            df = load_sample_data()
            df = categorize_dataframe(df)
            df = detect_anomalies(df)
            st.session_state.df = df
            st.session_state.chat_history = []
        st.success("Sample data loaded!")

    if uploaded:
        with st.spinner("Parsing statement..."):
            try:
                df = parse_statement(uploaded)
                df = categorize_dataframe(df)
                df = detect_anomalies(df)
                st.session_state.df = df
                st.session_state.chat_history = []
                st.success(f"✅ Loaded {len(df)} transactions")
            except Exception as e:
                st.error(f"Parse error: {e}")

    st.markdown("---")
    st.caption("🔒 All data processed locally. Nothing is stored.")
    st.caption("Built with Python + Claude AI")


# ── Main Content ───────────────────────────────────────────────────────────────
st.title("💰 UPI Finance Coach")

if st.session_state.df is None:
    # Landing state
    st.markdown("""
    ### Welcome! 👋
    Upload your bank statement or use the sample data to get started.

    **What you'll get:**
    - 📊 Instant spending breakdown by category
    - 🚨 Anomaly alerts for unusual transactions
    - 🔮 Month-end balance forecast
    - 💡 Personalized saving tips
    - 🤖 Chat with your finances using AI

    ← Use the sidebar to upload or load sample data.
    """)
    st.stop()

df = st.session_state.df

# ── KPI Strip ──────────────────────────────────────────────────────────────────
stats = get_summary_stats(df)
metric_cards(stats)
st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🚨 Anomalies & Tips", "📋 Transactions", "🤖 AI Coach"])

# ── Tab 1: Dashboard ──────────────────────────────────────────────────────────
with tab1:
    col_left, col_right = st.columns([1, 1])

    with col_left:
        cat_totals = get_category_totals(df)
        spending_donut(cat_totals)

    with col_right:
        monthly_bar(df)

    daily_spend_line(df)

    # Forecast
    forecast = forecast_month_end(df)
    if forecast:
        forecast_card(forecast)


# ── Tab 2: Anomalies & Tips ───────────────────────────────────────────────────
with tab2:
    st.subheader("🚨 Unusual Transactions")
    anomaly_table(df)

    st.markdown("---")
    st.subheader("📈 Category Spend Alerts")
    cat_alerts = get_category_anomalies(df)
    if cat_alerts:
        for alert in cat_alerts:
            st.warning(f"⚠️ {alert['message']}")
    else:
        st.success("✅ Your spending patterns look consistent this month.")

    st.markdown("---")
    nudges = generate_nudges(df)
    nudge_cards(nudges)


# ── Tab 3: Transactions ────────────────────────────────────────────────────────
with tab3:
    transaction_table(df)


# ── Tab 4: AI Coach ───────────────────────────────────────────────────────────
with tab4:
    st.subheader("🤖 Chat with Your Finances")
    st.caption("Ask anything: 'Why am I broke?', 'How can I save ₹5000?', 'Analyze my food spending'")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Enter Anthropic API Key to enable AI chat",
                                type="password", placeholder="sk-ant-...")
        if not api_key:
            st.info("Add your Anthropic API key to enable the AI coach.")
            st.stop()

    # Build context summary for Claude
    def build_finance_context(df: pd.DataFrame) -> str:
        stats = get_summary_stats(df)
        cat_totals = get_category_totals(df)
        top_cats = cat_totals.head(5).to_dict("records")
        alerts = get_category_anomalies(df)
        forecast = forecast_month_end(df)

        context = f"""
You are a personal finance coach for an Indian user. Here is their financial data:

SUMMARY:
- Total Income: ₹{stats['total_income']:,.0f}
- Total Spend: ₹{stats['total_spend']:,.0f}
- Net Balance: ₹{stats['net']:,.0f}
- Savings Rate: {stats['savings_rate']:.1f}%
- Total Transactions: {stats['n_transactions']}
- Biggest spend category: {stats['top_category']}

TOP SPENDING CATEGORIES:
{json.dumps(top_cats, indent=2)}

ANOMALY ALERTS:
{json.dumps([a['message'] for a in alerts], indent=2) if alerts else 'None'}

FORECAST:
{json.dumps(forecast, indent=2) if forecast else 'Not enough data'}

Provide specific, actionable advice in a friendly tone. Use ₹ for amounts.
Keep responses concise (3-5 sentences max unless asked for more detail).
        """.strip()
        return context

    # Render chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-message chat-user">👤 {msg["content"]}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message chat-ai">🤖 {msg["content"]}</div>',
                        unsafe_allow_html=True)

    # Quick prompts
    st.markdown("**Quick questions:**")
    qcols = st.columns(3)
    quick_prompts = [
        "Where did most of my money go?",
        "How can I save ₹5000 next month?",
        "Am I spending too much on food?",
    ]
    for i, prompt in enumerate(quick_prompts):
        if qcols[i].button(prompt, use_container_width=True):
            st.session_state._quick_prompt = prompt

    # Chat input
    user_input = st.chat_input("Ask your finance coach...")
    if hasattr(st.session_state, "_quick_prompt"):
        user_input = st.session_state._quick_prompt
        del st.session_state._quick_prompt

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.spinner("Thinking..."):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)

                system_prompt = build_finance_context(df)
                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history
                ]

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=600,
                    system=system_prompt,
                    messages=messages,
                )
                reply = response.content[0].text
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

            except Exception as e:
                st.error(f"AI error: {e}")

    if st.button("🗑️ Clear chat"):
        st.session_state.chat_history = []
        st.rerun()
