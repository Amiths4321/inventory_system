# AI Inventory & Supply Chain Manager

A production-ready AI-powered inventory management system built as **Project 21** in the AI Solution Architecture learning series. Upload your inventory data and get stockout predictions, demand forecasts, anomaly alerts, automated purchase orders, and natural language Q&A — all powered by Qwen2.5-VL.

---

## Where this fits in the AI development lifecycle

```
1-20. All previous projects    ✅
21.   AI Inventory Manager     ← this project (supply chain AI)
22.   Docker + AWS             Upcoming
```

---

## Features

- **Stockout predictor** — calculates days until each item runs out, colour-coded by risk
- **Demand forecaster** — 30/60/90 day forecasts using moving average + trend analysis
- **Anomaly detector** — spots overstocking, stockouts, demand spikes, high-value alerts
- **Purchase order generator** — auto-calculates EOQ, generates formatted Word PO documents
- **Supplier analyser** — compares suppliers by rating, on-time %, lead time
- **Natural language Q&A** — ask any question about your inventory in plain English
- **AI executive briefing** — one-click narrative summary of inventory health
- **Sample data** — 15 products, 90 days sales history, 5 suppliers generated instantly

---

## New Skills vs Previous Projects

| Skill | Where it appears |
|---|---|
| EOQ formula | Calculates optimal reorder quantity per item |
| Sales velocity | Daily sales rate used to predict stockout date |
| Moving average forecast | 7-day MA + trend for demand prediction |
| Anomaly detection | Statistical outliers in stock and sales data |
| Purchase order generation | Structured Word document with supplier grouping |
| Pandas code execution | LLM writes pandas → executes → returns answer |

---

## Project Structure

```
inventory_system/
│
├── inventory_app.py        # Streamlit UI — main entry point
├── inventory_data.py       # data loading + sample data generator
├── inventory_analysis.py   # stockout, forecast, anomaly, EOQ
├── inventory_ai.py         # Qwen insights + natural language Q&A
├── po_generator.py         # purchase order Word documents
│
├── sample_data/            # auto-generated sample CSVs
│   ├── inventory.csv
│   ├── sales_history.csv
│   └── suppliers.csv
│
├── outputs/                # generated purchase orders saved here
│
└── requirements.txt
```

---

## Prerequisites

- Python 3.9+
- Virtual environment activated
- Ollama running on remote GPU at `http://10.22.39.192:11434`
- Model `qwen2.5vl:latest` pulled on the remote GPU

---

## Installation

```powershell
cd inventory_system

# Activate venv
C:\Dev\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### `requirements.txt`

```
pandas
numpy
matplotlib
streamlit
requests
python-docx
python-dotenv
openpyxl
```

---

## Running the App

```powershell
cd "C:\Users\amith\Desktop\Confidential\Misc Projects\P3\inventory_system"
C:\Dev\venv\Scripts\Activate.ps1
streamlit run inventory_app.py
```

Open `http://localhost:8501` in your browser.
Click **Use sample data** in the sidebar to get started immediately.

---

## CSV Format Requirements

### Inventory CSV (required)

| Column | Type | Description |
|---|---|---|
| SKU | text | Unique product code |
| Product Name | text | Product description |
| Category | text | Product category |
| Unit Price | number | Price per unit in Rs. |
| Current Stock | integer | Units currently in stock |
| Reorder Point | integer | Minimum stock before reorder |
| Monthly Sales | number | Average units sold per month |
| Supplier ID | text | Supplier reference code |
| Lead Time Days | integer | Days from order to delivery |

### Sales History CSV (optional — for forecasting)

| Column | Type | Description |
|---|---|---|
| Date | YYYY-MM-DD | Sale date |
| SKU | text | Product code matching inventory |
| Quantity | integer | Units sold on that date |

### Suppliers CSV (optional)

| Column | Type | Description |
|---|---|---|
| Supplier ID | text | Unique supplier code |
| Supplier Name | text | Company name |
| Category | text | Products they supply |
| On-Time % | number | Delivery reliability percentage |
| Avg Lead Days | integer | Average delivery days |
| Rating | number | Overall rating out of 5 |

---

## How the Analysis Works

### Stockout Prediction

```
Daily Sales = Monthly Sales / 30
Days Until Stockout = Current Stock / Daily Sales

Risk classification:
  ≤ 7 days  → 🔴 Critical
  ≤ 14 days → 🟡 Warning
  ≤ 30 days → 🟠 Monitor
  > 30 days → 🟢 OK
```

### Economic Order Quantity (EOQ)

The EOQ formula calculates the optimal order quantity that minimises total inventory cost (ordering cost + holding cost):

```
EOQ = √(2 × D × S / H)

Where:
  D = Annual demand (Monthly Sales × 12)
  S = Order cost per order (default Rs. 500)
  H = Annual holding cost per unit (Unit Price × 20%)
```

A higher unit price means higher holding cost, so EOQ orders less but more frequently. A lower unit price means EOQ orders more at once to save on order costs.

### Demand Forecasting

```
7-day moving average of recent sales
+ linear trend (last 7 days vs previous 7 days)
× forecast horizon days
= total forecast demand
```

Confidence levels:
- High: 60+ days of history
- Medium: 30-59 days
- Low: under 30 days

### Anomaly Detection

| Anomaly type | Trigger condition |
|---|---|
| Overstock | Current stock > 6 months supply |
| Stockout | Current stock = 0 with active sales |
| High Value Alert | Price > Rs. 10,000 and below reorder point |
| Demand Spike | Recent 7-day sales > 50% above prior 7-day |
| Demand Drop | Recent 7-day sales < 50% below prior 7-day |

---

## The 6 Tabs

### Tab 1 — 🚨 Stockouts
- Colour-coded table of all items sorted by days until stockout
- Filter by risk level
- Horizontal bar chart showing top 10 most at-risk items
- AI executive briefing button

### Tab 2 — 📈 Forecast
- Demand forecast table for 30/60/90 days ahead
- Line chart showing historical sales trend per SKU
- Trend direction: Rising / Falling / Stable

### Tab 3 — ⚠️ Anomalies
- All detected anomalies sorted by severity
- Each anomaly shows: type, severity, description, recommended action

### Tab 4 — 🛒 Purchase Orders
- List of all items needing reorder with recommended quantities
- Total PO value summary
- One-click Word document generation grouped by supplier

### Tab 5 — 🏭 Suppliers
- Supplier performance table
- Rating bar chart
- Best supplier recommendation

### Tab 6 — 💬 Ask AI
- Natural language questions answered using pandas code execution
- Quick example questions
- Shows the pandas code used for transparency

---

## Sample Output

Using the built-in sample data (15 products):

```
Health Score: 70/100
Total Inventory Value: Rs. 18,45,200
Critical Items: 2
Out of Stock: 1

Stockouts:
  🔴 USB-C Hub    — 4 days  (Daily sales: 2.3 units)
  🔴 Laptop       — 6 days  (Daily sales: 4.0 units)
  🟡 Webcam       — 12 days (Daily sales: 0.8 units)

Anomalies:
  🔴 Stockout     — Network Switch: out of stock with active demand
  🟡 Overstock    — Office Chair: 4.2 months stock (Rs. 34,000 tied up)
  🟡 Demand Spike — Notebook: sales up 65% vs prior week

Purchase Order generated:
  USB-C Hub  × 240 units — Rs. 2,88,000
  Laptop     × 52 units  — Rs. 23,40,000
  Total PO: Rs. 26,28,000

AI Answer to "Which products will run out in 7 days?":
  USB-C Hub (4 days) and Laptop (6 days)
```

---

## Natural Language Q&A Examples

```
"Which products will run out in the next 7 days?"
"What is the total value of Electronics inventory?"
"Which category has the most items needing reorder?"
"What are our top 5 most valuable products by stock value?"
"Which supplier has the best on-time delivery record?"
"Show me all items where current stock is below reorder point"
"What is the average lead time across all suppliers?"
"Which items have zero stock?"
```

---

## Purchase Order Document

The generated PO Word document includes:
- Auto-generated PO number (PO-YYYYMMDDHHSS)
- Issue date and required-by date
- Items grouped by supplier
- Unit prices and total values per line
- Subtotal per supplier
- Grand total
- Standard T&C
- Signature block

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `KeyError: 'Days Until Stockout'` | Column missing from CSV | Ensure Monthly Sales column exists |
| `ModuleNotFoundError: openpyxl` | Package missing | `pip install openpyxl` |
| `Empty forecast` | No sales history loaded | Load sales_history.csv or use sample data |
| `PO generation fails` | python-docx not installed | `pip install python-docx` |
| `Ollama connection error` | Remote GPU not reachable | Check `curl http://10.22.39.192:11434/api/tags` |
| Chart not showing | matplotlib backend issue | Already fixed with `matplotlib.use("Agg")` |

---

## Extending the Project

### Connect to a real database

```python
import psycopg2
import pandas as pd

def load_from_postgres(connection_string: str) -> pd.DataFrame:
    conn = psycopg2.connect(connection_string)
    df   = pd.read_sql("SELECT * FROM inventory", conn)
    conn.close()
    return df
```

### Add email alerts for critical items

```python
import smtplib
from email.mime.text import MIMEText

def send_stockout_alert(critical_items: pd.DataFrame, to_email: str):
    items_text = critical_items[["Product Name", "Days Until Stockout"]].to_string()
    msg        = MIMEText(f"Critical stockout alert:\n\n{items_text}")
    msg["Subject"] = f"⚠️ {len(critical_items)} items running out soon"
    msg["From"]    = "inventory@yourcompany.com"
    msg["To"]      = to_email
    # send via SMTP
```

### Add scheduled daily report

```python
import schedule
import time

def daily_report():
    data      = load_data(None, None, None)
    inventory = predict_stockouts(data["inventory"])
    critical  = inventory[inventory["Risk Level"] == "🔴 Critical"]
    if not critical.empty:
        send_stockout_alert(critical, "manager@yourcompany.com")

schedule.every().day.at("08:00").do(daily_report)
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Part of a Larger Project Series

| # | Project | Core skill learned |
|---|---|---|
| 1 | Problem Definition Validator | Define before building |
| 5 | AI Data Analyst | Code execution, pandas, charts |
| 10 | Knowledge Graph AI | Entity relationships |
| 16 | Document Generator | Structured document output |
| 17 | AI SQL Agent | Database queries |
| 21 | **AI Inventory Manager** | **EOQ, forecasting, anomaly detection, PO generation** |
| 22 | Docker + AWS | Containers, cloud deployment |

---

## Author

Built as part of an AI Solution Architecture learning project.
Model: `qwen2.5vl:latest` via Ollama on remote GPU `10.22.39.192:11434`
No OpenAI · No Anthropic · Fully open source
