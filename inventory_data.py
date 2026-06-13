# inventory_data.py
import pandas as pd
import numpy  as np
from pathlib import Path
from datetime import datetime, timedelta

SAMPLE_DIR = Path("sample_data")
SAMPLE_DIR.mkdir(exist_ok=True)


def generate_sample_inventory() -> pd.DataFrame:
    """Generate realistic sample inventory data."""
    products = [
        ("P001", "Laptop",           "Electronics",  45000, 120, 20,  50, "SUP001"),
        ("P002", "Wireless Mouse",   "Electronics",   800,   8,   5, 100, "SUP001"),
        ("P003", "USB-C Hub",        "Electronics",  1200,  15,   8,  80, "SUP002"),
        ("P004", "Office Chair",     "Furniture",    8500,   3,   1,  15, "SUP003"),
        ("P005", "Standing Desk",    "Furniture",   22000,   2,   1,  10, "SUP003"),
        ("P006", "Notebook",         "Stationery",    120,  200,  50, 500, "SUP004"),
        ("P007", "Ballpoint Pen",    "Stationery",     15,  500, 100,1000, "SUP004"),
        ("P008", "Printer Paper",    "Stationery",    450,   50,  20, 200, "SUP004"),
        ("P009", "Webcam",           "Electronics",  3500,  25,   5,  40, "SUP001"),
        ("P010", "Headphones",       "Electronics",  5500,  18,   5,  30, "SUP002"),
        ("P011", "Desk Lamp",        "Furniture",    1800,  30,   8,  50, "SUP003"),
        ("P012", "Whiteboard",       "Office",       4500,   5,   2,  15, "SUP005"),
        ("P013", "Marker Set",       "Stationery",    350,  80,  20, 150, "SUP004"),
        ("P014", "File Cabinet",     "Furniture",   12000,   4,   1,  10, "SUP003"),
        ("P015", "Network Switch",   "Electronics", 15000,   8,   3,  20, "SUP002"),
    ]

    rows = []
    for sku, name, cat, price, stock, reorder, monthly_sales, supplier in products:
        rows.append({
            "SKU":              sku,
            "Product Name":     name,
            "Category":         cat,
            "Unit Price":       price,
            "Current Stock":    stock,
            "Reorder Point":    reorder,
            "Monthly Sales":    monthly_sales,
            "Supplier ID":      supplier,
            "Lead Time Days":   np.random.randint(3, 14),
            "Last Restock":     (datetime.now() - timedelta(days=np.random.randint(5, 60))).strftime("%Y-%m-%d"),
            "Location":         f"Warehouse-{np.random.choice(['A', 'B', 'C'])}",
        })

    df = pd.DataFrame(rows)
    df["Daily Sales"] = (df["Monthly Sales"] / 30).round(2)
    df["Days Until Stockout"] = (df["Current Stock"] / df["Daily Sales"].clip(lower=0.1)).round(0).astype(int)
    df["Stock Value"] = df["Current Stock"] * df["Unit Price"]
    df["Needs Reorder"] = df["Current Stock"] <= df["Reorder Point"]

    return df


def generate_sample_sales_history() -> pd.DataFrame:
    """Generate 90 days of sales history per product."""
    products = ["P001","P002","P003","P004","P005",
                "P006","P007","P008","P009","P010"]
    base_sales = {"P001":4,"P002":8,"P003":7,"P004":3,"P005":2,
                  "P006":200,"P007":500,"P008":50,"P009":6,"P010":5}

    rows = []
    for sku, base in base_sales.items():
        for day in range(90):
            date  = datetime.now() - timedelta(days=90-day)
            # Add seasonality and noise
            trend   = 1 + (day / 90) * 0.2   # slight upward trend
            season  = 1 + 0.3 * np.sin(2 * np.pi * day / 30)   # monthly cycle
            sales   = max(0, int(base * trend * season + np.random.normal(0, base * 0.2)))
            rows.append({
                "Date":     date.strftime("%Y-%m-%d"),
                "SKU":      sku,
                "Quantity": sales,
            })

    return pd.DataFrame(rows)


def generate_sample_suppliers() -> pd.DataFrame:
    """Generate supplier data."""
    suppliers = [
        ("SUP001", "TechDist India",      "Electronics", 92, 7,  4.5, "Mumbai"),
        ("SUP002", "DigiParts Ltd",       "Electronics", 87, 10, 4.2, "Bangalore"),
        ("SUP003", "OfficeFurnish Co",    "Furniture",   95, 14, 4.8, "Delhi"),
        ("SUP004", "StatSupply India",    "Stationery",  98, 3,  4.7, "Chennai"),
        ("SUP005", "WorkspaceEquip Ltd",  "Office",      90, 7,  4.3, "Hyderabad"),
    ]
    return pd.DataFrame(suppliers, columns=[
        "Supplier ID", "Supplier Name", "Category",
        "On-Time %", "Avg Lead Days", "Rating", "City"
    ])


def create_sample_files():
    """Save sample CSVs to disk."""
    generate_sample_inventory().to_csv(SAMPLE_DIR / "inventory.csv",     index=False)
    generate_sample_sales_history().to_csv(SAMPLE_DIR / "sales_history.csv", index=False)
    generate_sample_suppliers().to_csv(SAMPLE_DIR / "suppliers.csv",     index=False)
    print("Sample data created in sample_data/")


def load_data(
    inventory_file,
    sales_file    = None,
    supplier_file = None
) -> dict:
    """Load data from uploaded files or use sample data."""
    data = {}

    # Inventory
    if inventory_file is not None:
        data["inventory"] = pd.read_csv(inventory_file)
    elif (SAMPLE_DIR / "inventory.csv").exists():
        data["inventory"] = pd.read_csv(SAMPLE_DIR / "inventory.csv")
    else:
        create_sample_files()
        data["inventory"] = pd.read_csv(SAMPLE_DIR / "inventory.csv")

    # Sales history
    if sales_file is not None:
        data["sales"] = pd.read_csv(sales_file)
    elif (SAMPLE_DIR / "sales_history.csv").exists():
        data["sales"] = pd.read_csv(SAMPLE_DIR / "sales_history.csv")

    # Suppliers
    if supplier_file is not None:
        data["suppliers"] = pd.read_csv(supplier_file)
    elif (SAMPLE_DIR / "suppliers.csv").exists():
        data["suppliers"] = pd.read_csv(SAMPLE_DIR / "suppliers.csv")

    return data