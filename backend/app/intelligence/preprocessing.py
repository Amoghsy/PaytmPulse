import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.models.base import utc_now


def resample_hourly_series(df: pd.DataFrame, time_col: str = "timestamp_hour", fill_value: float = 0.0, days: int = 30) -> pd.DataFrame:
    """
    Ensures complete, continuous hourly intervals by filling missing hours with zero values.
    """
    if df.empty:
        end_time = utc_now().replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=days)
        full_index = pd.date_range(start=start_time, end=end_time, freq="h", tz="UTC")
        return pd.DataFrame({
            time_col: full_index,
            "quantity": fill_value,
            "revenue": fill_value,
            "order_count": 0,
            "aov": fill_value
        })

    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], utc=True)
    df = df.set_index(time_col)

    start_time = df.index.min()
    end_time = max(df.index.max(), utc_now().replace(minute=0, second=0, microsecond=0))
    full_index = pd.date_range(start=start_time, end=end_time, freq="h", tz="UTC")

    resampled = df.reindex(full_index)
    resampled.index.name = time_col

    for col in resampled.columns:
        if col in ["quantity", "revenue", "order_count", "aov"]:
            resampled[col] = resampled[col].fillna(fill_value)
        else:
            resampled[col] = resampled[col].ffill().bfill()

    return resampled.reset_index()


def remove_extreme_outliers(df: pd.DataFrame, col: str = "quantity", upper_quantile: float = 0.999) -> pd.DataFrame:
    """
    Clips extreme outliers above upper quantile to prevent distortion.
    """
    if df.empty or len(df) < 10:
        return df

    df = df.copy()
    threshold = df[col].quantile(upper_quantile)
    df[col] = np.clip(df[col], a_min=0, a_max=threshold)
    return df
