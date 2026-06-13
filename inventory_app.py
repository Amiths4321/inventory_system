# inventory_app.py
# streamlit run inventory_app.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas    as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from inventory_data     import load_data, create_sample_files
from inventory_analysis import (
    predict_stockouts, generate_reorder_recommendations,
    forecast_demand, detect_anomalies, get_inventory_summary
)
from inventory_ai    import answer_inventory_question, generate_inventory_insights
from po_generator    import build_po_docx

st.set_page_config(
    page_title="AI Inventory Manager",
    page_icon="📦",
    layout="wide"
)

Path("outputs").mkdir(exist_ok=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "data"    not in st.session_state: st.session_state.data    = None
if "summary" not in st.session_state: st.session_state.summary = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📦 AI Inventory Manager")
    st.caption("Stockout prediction · Forecasting · PO generation")

    st.divider()
    st.markdown("**Load data**")

    inv_file  = st.file_uploader("Inventory CSV",     type=["csv"])
    sales_file = st.file_uploader("Sales history CSV", type=["csv"])
    sup_file  = st.file_uploader("Suppliers CSV",      type=["csv"])

    if st.button("Load uploaded data", type="primary", use_container_width=True):
        with st.spinner("Loading..."):
            st.session_state.data = load_data(inv_file, sales_file, sup_file)
        st.success("Data loaded!")
        st.rerun()

    st.divider()
    if st.button("Use sample data", use_container_width=True):
        with st.spinner("Generating sample data..."):
            create_sample_files()
            st.session_state.data = load_data(None, None, None)
        st.success("Sample data loaded!")
        st.rerun()

    if st.session_state.data:
        inv = st.session_state.data.get("inventory")
        if inv is not None:
            st.metric("SKUs",       len(inv))
            st.metric("Categories", inv["Category"].nunique() if "Category" in inv.columns else "—")

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("📦 AI Inventory & Supply Chain Manager")

if st.session_state.data is None:
    st.info("Load your inventory data or click **Use sample data** in the sidebar.")
    st.markdown("""
**Required CSV columns for inventory:**
`SKU, Product Name, Category, Unit Price, Current Stock, Reorder Point, Monthly Sales, Supplier ID, Lead Time Days`

**Optional: Sales history CSV:** `Date, SKU, Quantity`

**Optional: Suppliers CSV:** `Supplier ID, Supplier Name, Category, On-Time %, Avg Lead Days, Rating`
    """)
    st.stop()

data      = st.session_state.data
inventory = data["inventory"]
sales     = data.get("sales")
suppliers = data.get("suppliers")

# Compute summary once
if st.session_state.summary is None:
    inventory_with_stockout = predict_stockouts(inventory)
    st.session_state.summary = get_inventory_summary(inventory_with_stockout)
    data["inventory"]        = inventory_with_stockout
    inventory                = inventory_with_stockout

summary = st.session_state.summary

# ── Top metrics ───────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total SKUs",      summary["total_skus"])
col2.metric("Inventory Value", f"Rs. {summary['total_value']:,.0f}")
col3.metric("Critical Items",  summary["critical_items"],  delta_color="inverse")
col4.metric("Out of Stock",    summary["out_of_stock"],     delta_color="inverse")
col5.metric("Health Score",    f"{summary['health_score']}/100")

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🚨 Stockouts",
    "📈 Forecast",
    "⚠️ Anomalies",
    "🛒 Purchase Orders",
    "🏭 Suppliers",
    "💬 Ask AI"
])

# ── Tab 1: Stockouts ──────────────────────────────────────────────────────────
with tab1:
    st.subheader("Stockout predictions")

    df_stock = predict_stockouts(inventory)

    # AI insights
    if st.button("Generate AI briefing", type="primary"):
        anomalies = detect_anomalies(inventory, sales)
        with st.spinner("Generating executive briefing..."):
            briefing = generate_inventory_insights(df_stock, anomalies, summary)
        st.info(f"**AI Briefing:** {briefing}")

    st.divider()

    # Risk filter
    risk_filter = st.selectbox(
        "Show:", ["All", "🔴 Critical", "🟡 Warning", "🟠 Monitor", "🟢 OK"]
    )

    display = df_stock.copy()
    if risk_filter != "All":
        display = display[display["Risk Level"] == risk_filter]

    # Show table
    cols_to_show = [c for c in [
        "SKU", "Product Name", "Category", "Current Stock",
        "Reorder Point", "Daily Sales", "Days Until Stockout",
        "Risk Level", "Needs Reorder"
    ] if c in display.columns]

    st.dataframe(
        display[cols_to_show].style.apply(
            lambda row: [
                "background-color: #E24B4A22" if row.get("Risk Level", "") == "🔴 Critical"
                else "background-color: #EF9F2722" if row.get("Risk Level", "") == "🟡 Warning"
                else ""
                for _ in row
            ], axis=1
        ),
        use_container_width=True
    )

    # Chart
    if "Days Until Stockout" in display.columns and len(display) > 0:
        fig, ax = plt.subplots(figsize=(10, 4))
        top10   = display.head(10)
        colors  = [
            "#E24B4A" if r == "🔴 Critical" else
            "#EF9F27" if r == "🟡 Warning"  else
            "#1D9E75"
            for r in top10.get("Risk Level", ["🟢 OK"] * len(top10))
        ]
        ax.barh(top10.get("Product Name", top10.index), top10["Days Until Stockout"], color=colors)
        ax.set_xlabel("Days until stockout")
        ax.set_title("Top 10 items by stockout risk")
        ax.axvline(x=7,  color="#E24B4A", linestyle="--", alpha=0.5, label="Critical (7 days)")
        ax.axvline(x=14, color="#EF9F27", linestyle="--", alpha=0.5, label="Warning (14 days)")
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

# ── Tab 2: Forecast ───────────────────────────────────────────────────────────
with tab2:
    st.subheader("Demand forecasting")

    if sales is None:
        st.info("Load sales history CSV for demand forecasting.")
    else:
        days = st.selectbox("Forecast horizon:", [30, 60, 90], index=0)

        with st.spinner("Forecasting demand..."):
            forecast_df = forecast_demand(sales, days)

        if not forecast_df.empty:
            st.dataframe(forecast_df, use_container_width=True)

            # Sales trend chart for selected SKU
            sku_options = sales["SKU"].unique().tolist()
            selected_sku = st.selectbox("View trend for:", sku_options)

            sku_sales = sales[sales["SKU"] == selected_sku].sort_values("Date")
            fig, ax   = plt.subplots(figsize=(10, 4))
            ax.plot(sku_sales["Date"], sku_sales["Quantity"],
                    color="#1D9E75", linewidth=2)
            ax.fill_between(sku_sales["Date"], sku_sales["Quantity"],
                            alpha=0.2, color="#1D9E75")
            ax.set_title(f"Sales trend — {selected_sku}")
            ax.set_xlabel("Date")
            ax.set_ylabel("Units sold")
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

# ── Tab 3: Anomalies ──────────────────────────────────────────────────────────
with tab3:
    st.subheader("Anomaly detection")

    with st.spinner("Detecting anomalies..."):
        anomalies = detect_anomalies(inventory, sales)

    if not anomalies:
        st.success("No anomalies detected — inventory looks healthy!")
    else:
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        anomalies.sort(key=lambda x: severity_order.get(x["severity"], 4))

        for a in anomalies:
            icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(a["severity"], "⚪")
            with st.expander(f"{icon} {a['type']} — {a['product']}"):
                st.markdown(f"**Severity:** {a['severity']}")
                st.markdown(f"**Description:** {a['description']}")
                st.markdown(f"**Recommended action:** {a['action']}")

# ── Tab 4: Purchase Orders ────────────────────────────────────────────────────
with tab4:
    st.subheader("Auto-generate purchase orders")

    recommendations = generate_reorder_recommendations(inventory)

    if recommendations.empty:
        st.success("No items need reordering right now!")
    else:
        st.metric("Items needing reorder", len(recommendations))
        st.metric("Total PO value",
                  f"Rs. {recommendations['Total Value'].sum():,.0f}")

        st.dataframe(recommendations, use_container_width=True)

        company = st.text_input("Company name:", value="TechCorp India Pvt Ltd")

        if st.button("Generate Purchase Order", type="primary"):
            with st.spinner("Generating PO document..."):
                po_path = build_po_docx(recommendations, suppliers, company)

            with open(po_path, "rb") as f:
                st.download_button(
                    "📥 Download Purchase Order (.docx)",
                    f.read(),
                    file_name           = Path(po_path).name,
                    mime                = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width = True
                )
            st.success(f"PO generated: {Path(po_path).name}")

# ── Tab 5: Suppliers ──────────────────────────────────────────────────────────
with tab5:
    st.subheader("Supplier performance")

    if suppliers is None:
        st.info("Load suppliers CSV to see supplier analysis.")
    else:
        st.dataframe(suppliers, use_container_width=True)

        # Supplier rating chart
        if "Rating" in suppliers.columns:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.barh(
                suppliers["Supplier Name"] if "Supplier Name" in suppliers.columns else suppliers["Supplier ID"],
                suppliers["Rating"],
                color="#1D9E75"
            )
            ax.set_xlabel("Rating")
            ax.set_title("Supplier ratings")
            ax.set_xlim(0, 5)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

        # Best supplier recommendation
        if st.button("Get supplier recommendation"):
            best = suppliers.sort_values("Rating", ascending=False).iloc[0]
            st.success(
                f"Best overall supplier: **{best.get('Supplier Name', best['Supplier ID'])}** "
                f"(Rating: {best.get('Rating', 'N/A')}, "
                f"On-time: {best.get('On-Time %', 'N/A')}%, "
                f"Lead time: {best.get('Avg Lead Days', 'N/A')} days)"
            )

# ── Tab 6: Ask AI ─────────────────────────────────────────────────────────────
with tab6:
    st.subheader("Ask anything about your inventory")

    examples = [
        "Which products will run out in the next 7 days?",
        "What is the total value of Electronics inventory?",
        "Which category has the most items needing reorder?",
        "What are our top 5 most valuable products?",
        "Which items have been out of stock?",
    ]

    for i, ex in enumerate(examples):
        if st.button(ex, key=f"inv_q_{i}", use_container_width=True):
            st.session_state["inv_question"] = ex

    question = st.text_input(
        "Your question:",
        value       = st.session_state.pop("inv_question", ""),
        placeholder = "e.g. Which products need immediate reorder?"
    )

    if st.button("Ask", type="primary") and question:
        with st.spinner("Analysing..."):
            result = answer_inventory_question(
                question, inventory, sales, suppliers
            )
        st.markdown(f"**Answer:** {result['answer']}")
        with st.expander("Code used"):
            st.code(result["code_used"], language="python")