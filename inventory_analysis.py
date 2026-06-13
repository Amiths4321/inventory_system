# inventory_analysis.py
import pandas as pd
import numpy  as np
from datetime import datetime


def predict_stockouts(inventory: pd.DataFrame) -> pd.DataFrame:
    """
    Predict which items will stock out and when.
    Returns filtered + enriched dataframe.
    """
    df = inventory.copy()

    # Ensure required columns
    if "Daily Sales" not in df.columns:
        if "Monthly Sales" in df.columns:
            df["Daily Sales"] = df["Monthly Sales"] / 30
        else:
            df["Daily Sales"] = 1

    if "Days Until Stockout" not in df.columns:
        df["Days Until Stockout"] = (
            df["Current Stock"] / df["Daily Sales"].clip(lower=0.1)
        ).round(0).astype(int)

    # Criticality classification
    def classify(row):
        days = row["Days Until Stockout"]
        if days <= 7:   return "🔴 Critical"
        if days <= 14:  return "🟡 Warning"
        if days <= 30:  return "🟠 Monitor"
        return          "🟢 OK"

    df["Risk Level"]    = df.apply(classify, axis=1)
    df["Needs Reorder"] = df["Current Stock"] <= df.get("Reorder Point", 0)

    return df.sort_values("Days Until Stockout")


def calculate_eoq(
    annual_demand:   float,
    order_cost:      float = 500,
    holding_cost_pct: float = 0.2,
    unit_cost:       float = 100
) -> float:
    """
    Economic Order Quantity formula.
    EOQ = sqrt(2 * D * S / H)
    D = annual demand
    S = order cost per order
    H = annual holding cost per unit
    """
    H = unit_cost * holding_cost_pct
    if H <= 0 or annual_demand <= 0:
        return annual_demand / 12  # fallback: order one month supply
    eoq = np.sqrt((2 * annual_demand * order_cost) / H)
    return round(eoq)


def generate_reorder_recommendations(inventory: pd.DataFrame) -> pd.DataFrame:
    """Generate reorder recommendations for items below reorder point."""
    df        = inventory.copy()
    reorder_needed = df[df.get("Needs Reorder", df["Current Stock"] <= df.get("Reorder Point", 0))]

    recommendations = []
    for _, row in reorder_needed.iterrows():
        annual_demand = row.get("Monthly Sales", 10) * 12
        unit_price    = row.get("Unit Price", 100)
        eoq           = calculate_eoq(annual_demand, unit_cost=unit_price)
        reorder_qty   = max(eoq, row.get("Monthly Sales", 10))   # at least 1 month supply

        recommendations.append({
            "SKU":              row.get("SKU", ""),
            "Product":          row.get("Product Name", ""),
            "Current Stock":    row.get("Current Stock", 0),
            "Reorder Point":    row.get("Reorder Point", 0),
            "Recommended Qty":  int(reorder_qty),
            "Unit Price":       unit_price,
            "Total Value":      round(reorder_qty * unit_price, 2),
            "Supplier":         row.get("Supplier ID", ""),
            "Lead Time":        row.get("Lead Time Days", 7),
            "Days Until Stockout": row.get("Days Until Stockout", 0)
        })

    return pd.DataFrame(recommendations)


def forecast_demand(sales_history: pd.DataFrame, days_ahead: int = 30) -> pd.DataFrame:
    """
    Simple demand forecast using moving average + trend.
    Returns forecast per SKU.
    """
    forecasts = []
    sales_history["Date"] = pd.to_datetime(sales_history["Date"])

    for sku in sales_history["SKU"].unique():
        sku_data = sales_history[sales_history["SKU"] == sku].sort_values("Date")

        if len(sku_data) < 7:
            continue

        qty = sku_data["Quantity"].values

        # 7-day moving average
        ma7    = np.mean(qty[-7:])
        ma30   = np.mean(qty[-30:]) if len(qty) >= 30 else ma7

        # Simple trend
        if len(qty) >= 14:
            trend = (np.mean(qty[-7:]) - np.mean(qty[-14:-7])) / 7
        else:
            trend = 0

        forecast     = max(0, ma7 + trend * (days_ahead / 2))
        total_30d    = round(forecast * days_ahead)
        confidence   = "High" if len(sku_data) >= 60 else "Medium" if len(sku_data) >= 30 else "Low"

        forecasts.append({
            "SKU":                sku,
            f"Forecast {days_ahead}d": total_30d,
            "Daily Average":      round(ma7, 1),
            "Trend":              "↑ Rising" if trend > 0.1 else "↓ Falling" if trend < -0.1 else "→ Stable",
            "Confidence":         confidence
        })

    return pd.DataFrame(forecasts)


def detect_anomalies(
    inventory:     pd.DataFrame,
    sales_history: pd.DataFrame = None
) -> list[dict]:
    """
    Detect anomalies in inventory and sales data.
    Returns list of anomaly dicts.
    """
    anomalies = []

    # Check inventory for anomalies
    for _, row in inventory.iterrows():
        name  = row.get("Product Name", row.get("SKU", "Unknown"))
        stock = row.get("Current Stock", 0)
        sales = row.get("Monthly Sales", 1)
        price = row.get("Unit Price", 0)

        # Overstocking — more than 6 months supply
        months_supply = stock / max(sales / 30, 0.1) / 30
        if months_supply > 6:
            anomalies.append({
                "type":        "Overstock",
                "severity":    "Medium",
                "product":     name,
                "description": f"{months_supply:.1f} months of stock — capital tied up: Rs. {stock * price:,.0f}",
                "action":      "Consider promotions or return to supplier"
            })

        # Zero or near-zero stock with active sales
        if stock == 0 and sales > 0:
            anomalies.append({
                "type":        "Stockout",
                "severity":    "Critical",
                "product":     name,
                "description": "Currently out of stock with active demand",
                "action":      "Emergency reorder required immediately"
            })

        # Very high value items with low stock
        if price > 10000 and stock <= row.get("Reorder Point", 2):
            anomalies.append({
                "type":        "High Value Alert",
                "severity":    "High",
                "product":     name,
                "description": f"High-value item (Rs. {price:,}) below reorder point",
                "action":      "Priority reorder — high revenue impact"
            })

    # Sales anomalies from history
    if sales_history is not None and not sales_history.empty:
        sales_history["Date"] = pd.to_datetime(sales_history["Date"])
        recent = sales_history[
            sales_history["Date"] >= sales_history["Date"].max() - pd.Timedelta(days=7)
        ]
        older  = sales_history[
            sales_history["Date"] < sales_history["Date"].max() - pd.Timedelta(days=7)
        ]

        for sku in sales_history["SKU"].unique():
            rec_sales = recent[recent["SKU"] == sku]["Quantity"].mean()
            old_sales = older[older["SKU"] == sku]["Quantity"].mean()

            if old_sales > 0:
                change = (rec_sales - old_sales) / old_sales

                if change > 0.5:
                    anomalies.append({
                        "type":        "Demand Spike",
                        "severity":    "Medium",
                        "product":     sku,
                        "description": f"Sales up {change*100:.0f}% vs prior period",
                        "action":      "Check stock levels — may need expedited reorder"
                    })
                elif change < -0.5:
                    anomalies.append({
                        "type":        "Demand Drop",
                        "severity":    "Low",
                        "product":     sku,
                        "description": f"Sales down {abs(change)*100:.0f}% vs prior period",
                        "action":      "Investigate cause — seasonal or product issue?"
                    })

    return anomalies


def get_inventory_summary(inventory: pd.DataFrame) -> dict:
    """Overall inventory health summary."""
    total_skus     = len(inventory)
    total_value    = (inventory["Current Stock"] * inventory.get("Unit Price", 1)).sum()
    critical_items = len(inventory[inventory.get("Days Until Stockout", 999) <= 7])
    out_of_stock   = len(inventory[inventory["Current Stock"] == 0])
    needs_reorder  = len(inventory[
        inventory["Current Stock"] <= inventory.get("Reorder Point", 0)
    ])

    return {
        "total_skus":     total_skus,
        "total_value":    round(total_value, 2),
        "critical_items": critical_items,
        "out_of_stock":   out_of_stock,
        "needs_reorder":  needs_reorder,
        "health_score":   max(0, 100 - (critical_items * 10) - (out_of_stock * 20))
    }