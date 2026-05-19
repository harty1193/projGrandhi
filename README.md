# 💰 UPI Finance Coach

An AI-powered personal finance coach for India's UPI economy.
Upload your bank/UPI statement and get instant insights, anomaly alerts, and a conversational AI coach.

## Features
- 📄 Parse UPI/bank statements (CSV or PDF)
- 🏷️ Auto-categorize transactions (food, rent, subscriptions, etc.)
- 📊 Visual spending dashboard
- 🚨 Anomaly detection (unusual spends)
- 🔮 Month-end balance forecast
- 🤖 Chat with your finances using Claude AI

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY=your_key_here

# 3. Run the app
streamlit run app.py
```

## Supported Statement Formats
- Google Pay (CSV export)
- PhonePe (CSV export)
- HDFC Bank (PDF/CSV)
- Generic bank CSV (Date, Description, Amount columns)

## Sample Data
A sample CSV is included at `data/samples/sample_transactions.csv` to try without uploading real data.

## Project Structure
```
finance-coach/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── src/
│   ├── parser/
│   │   └── statement_parser.py    # CSV/PDF ingestion
│   ├── categorizer/
│   │   └── categorizer.py         # NLP-based categorization
│   ├── analytics/
│   │   └── insights.py            # Anomaly detection + forecasting
│   └── ui/
│       └── components.py          # Reusable Streamlit components
└── data/samples/
    └── sample_transactions.csv
```


sk-ijklmnopabcd5678ijklmnopabcd5678ijklmnop
