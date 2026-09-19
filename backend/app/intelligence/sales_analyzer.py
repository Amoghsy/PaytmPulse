import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.intelligence.data_loader import load_merchant_sales, load_product_sales
from app.models.base import utc_now

logger = logging.getLogger("paytm_pulse.intelligence.sales_analyzer")


def analyze_merchant_sales(session: Session, merchant_id: str, days: int = 30) -> dict:
    """
    Performs comprehensive deterministic multi-horizon sales analytics for a merchant.
    """
    now = utc_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)
    thirty_days_ago = now - timedelta(days=days)

    df = load_product_sales(session, merchant_id, days=days)

    if df.empty:
        return {
            "merchant_id": merchant_id,
            "sales": {
                "today": 0.0,
                "yesterday": 0.0,
                "last_7_days": 0.0,
                "last_30_days": 0.0,
                "average_daily_sales": 0.0,
                "growth_percentage": 0.0,
                "transaction_count": 0,
                "average_transaction_value": 0.0
            },
            "top_products": [],
            "slow_products": [],
            "sales_by_hour": {str(h): 0.0 for h in range(24)},
            "sales_by_day": {day: 0.0 for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
            "peak_sales_period": {"peak_hour": 12, "peak_day": "Sat"}
        }

    # Time filters
    df["tx_time"] = pd.to_datetime(df["transaction_timestamp"], utc=True)
    df_today = df[df["tx_time"] >= today_start]
    df_yesterday = df[(df["tx_time"] >= yesterday_start) & (df["tx_time"] < today_start)]
    df_last_7d = df[df["tx_time"] >= seven_days_ago]
    df_prev_7d = df[(df["tx_time"] >= fourteen_days_ago) & (df["tx_time"] < seven_days_ago)]
    df_30d = df[df["tx_time"] >= thirty_days_ago]

    # Sales sums
    sales_today = float(df_today["amount"].sum())
    sales_yesterday = float(df_yesterday["amount"].sum())
    sales_7d = float(df_last_7d["amount"].sum())
    sales_prev_7d = float(df_prev_7d["amount"].sum())
    sales_30d = float(df_30d["amount"].sum())

    # Growth percentage (last 7d vs prior 7d)
    growth_pct = 0.0
    if sales_prev_7d > 0:
        growth_pct = round(((sales_7d - sales_prev_7d) / sales_prev_7d) * 100.0, 2)
    elif sales_7d > 0:
        growth_pct = 100.0

    avg_daily_sales = round(sales_30d / max(days, 1), 2)
    total_tx_count = len(df)
    aov = round(sales_30d / max(total_tx_count, 1), 2)

    # Product Performance Breakdown
    prod_group = df.groupby(["product_id", "product_name", "category"]).agg(
        units_sold=("quantity", "sum"),
        revenue=("amount", "sum")
    ).reset_index()

    prod_group = prod_group.sort_values("revenue", ascending=False)
    top_products = prod_group.head(5).to_dict(orient="records")
    slow_products = prod_group.tail(5).sort_values("revenue", ascending=True).to_dict(orient="records")

    # Sales by Hour (0-23)
    df["hour"] = df["tx_time"].dt.hour
    hourly_sales = df.groupby("hour")["amount"].sum().to_dict()
    full_hourly = {str(h): round(float(hourly_sales.get(h, 0.0)), 2) for h in range(24)}

    # Sales by Day of Week
    day_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    df["day_name"] = df["tx_time"].dt.dayofweek.map(day_map)
    daily_sales = df.groupby("day_name")["amount"].sum().to_dict()
    full_daily = {d: round(float(daily_sales.get(d, 0.0)), 2) for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}

    # Peak Periods
    peak_hour = int(max(hourly_sales, key=hourly_sales.get)) if hourly_sales else 19
    peak_day = str(max(daily_sales, key=daily_sales.get)) if daily_sales else "Sat"

    return {
        "merchant_id": merchant_id,
        "sales": {
            "today": round(sales_today, 2),
            "yesterday": round(sales_yesterday, 2),
            "last_7_days": round(sales_7d, 2),
            "last_30_days": round(sales_30d, 2),
            "average_daily_sales": avg_daily_sales,
            "growth_percentage": growth_pct,
            "transaction_count": total_tx_count,
            "average_transaction_value": aov
        },
        "top_products": top_products,
        "slow_products": slow_products,
        "sales_by_hour": full_hourly,
        "sales_by_day": full_daily,
        "peak_sales_period": {
            "peak_hour": peak_hour,
            "peak_day": peak_day,
            "peak_time_window": f"{peak_hour:02d}:00 - {(peak_hour + 1) % 24:02d}:00"
        }
    }


def analyze_product_demand(session: Session, merchant_id: str, product_id: str, days: int = 30) -> dict:
    """
    Calculates detailed demand analytics for a specific product.
    """
    df = load_product_sales(session, merchant_id, product_id=product_id, days=days)

    if df.empty:
        return {
            "product_id": product_id,
            "merchant_id": merchant_id,
            "units_sold": 0,
            "revenue": 0.0,
            "average_daily_demand": 0.0,
            "recent_7d_demand": 0,
            "historical_30d_demand": 0,
            "demand_growth_percentage": 0.0
        }

    now = utc_now()
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)

    df["tx_time"] = pd.to_datetime(df["transaction_timestamp"], utc=True)
    df_recent_7d = df[df["tx_time"] >= seven_days_ago]
    df_prev_7d = df[(df["tx_time"] >= fourteen_days_ago) & (df["tx_time"] < seven_days_ago)]

    total_units = int(df["quantity"].sum())
    total_revenue = float(df["amount"].sum())
    recent_7d_units = int(df_recent_7d["quantity"].sum())
    prev_7d_units = int(df_prev_7d["quantity"].sum())

    growth_pct = 0.0
    if prev_7d_units > 0:
        growth_pct = round(((recent_7d_units - prev_7d_units) / prev_7d_units) * 100.0, 2)
    elif recent_7d_units > 0:
        growth_pct = 100.0

    avg_daily_demand = round(total_units / max(days, 1), 2)

    return {
        "product_id": product_id,
        "product_name": df["product_name"].iloc[0] if "product_name" in df.columns else "Unknown",
        "merchant_id": merchant_id,
        "units_sold": total_units,
        "revenue": round(total_revenue, 2),
        "average_daily_demand": avg_daily_demand,
        "recent_7d_demand": recent_7d_units,
        "historical_30d_demand": total_units,
        "demand_growth_percentage": growth_pct
    }
