import pandas as pd
import numpy as np


def generate_time_features(df: pd.DataFrame, time_col: str = "timestamp_hour") -> pd.DataFrame:
    """
    Extracts cyclical and categorical time attributes.
    """
    df = df.copy()
    dt_series = pd.to_datetime(df[time_col], utc=True)
    df["hour"] = dt_series.dt.hour
    df["day_of_week"] = dt_series.dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_peak_hour"] = df["hour"].isin([11, 12, 13, 18, 19, 20, 21]).astype(int)
    return df


def generate_lag_and_rolling_features(df: pd.DataFrame, target_col: str = "quantity") -> pd.DataFrame:
    """
    Computes lag, rolling mean, and rolling volatility features for demand/sales forecasting.
    """
    df = df.copy()
    df = df.sort_values("timestamp_hour").reset_index(drop=True)

    # Lag features
    df["lag_1h"] = df[target_col].shift(1).fillna(0.0)
    df["lag_2h"] = df[target_col].shift(2).fillna(0.0)
    df["lag_24h"] = df[target_col].shift(24).fillna(0.0)

    # Rolling window aggregations
    df["rolling_mean_3h"] = df[target_col].shift(1).rolling(window=3, min_periods=1).mean().fillna(0.0)
    df["rolling_mean_6h"] = df[target_col].shift(1).rolling(window=6, min_periods=1).mean().fillna(0.0)
    df["rolling_mean_24h"] = df[target_col].shift(1).rolling(window=24, min_periods=1).mean().fillna(0.0)
    df["rolling_std_24h"] = df[target_col].shift(1).rolling(window=24, min_periods=1).std().fillna(0.0)

    return df


def prepare_forecasting_feature_matrix(df: pd.DataFrame, target_col: str = "quantity") -> tuple[pd.DataFrame, pd.Series]:
    """
    Prepares X (feature matrix) and y (target vector) for ML regression models.
    """
    df = generate_time_features(df)
    df = generate_lag_and_rolling_features(df, target_col=target_col)

    feature_cols = [
        "hour", "day_of_week", "is_weekend", "is_peak_hour",
        "lag_1h", "lag_2h", "lag_24h",
        "rolling_mean_3h", "rolling_mean_6h", "rolling_mean_24h", "rolling_std_24h"
    ]

    X = df[feature_cols].copy()
    y = df[target_col].copy()
    return X, y
