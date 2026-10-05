import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "ret_lag0",
    "ret_lag1",
    "ret_lag2",
    "ret_lag4",
    "ret_lag6",
    "ret_mean_7",
    "ret_mean_30",
    "ret_std_7",
    "ret_std_30",
    "sma7_gap",
    "sma30_gap",
    "volume_gap_7",
    "volume_gap_30",
]

MIN_HISTORY = 40


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    volume = df["volume"].clip(lower=1.0)
    ret = np.log(close).diff()

    feats = pd.DataFrame(index=df.index)
    feats["ret_lag0"] = ret
    feats["ret_lag1"] = ret.shift(1)
    feats["ret_lag2"] = ret.shift(2)
    feats["ret_lag4"] = ret.shift(4)
    feats["ret_lag6"] = ret.shift(6)
    feats["ret_mean_7"] = ret.rolling(7).mean()
    feats["ret_mean_30"] = ret.rolling(30).mean()
    feats["ret_std_7"] = ret.rolling(7).std()
    feats["ret_std_30"] = ret.rolling(30).std()
    feats["sma7_gap"] = close / close.rolling(7).mean() - 1
    feats["sma30_gap"] = close / close.rolling(30).mean() - 1
    feats["volume_gap_7"] = np.log(volume / volume.rolling(7).mean())
    feats["volume_gap_30"] = np.log(volume / volume.rolling(30).mean())
    return feats[FEATURE_NAMES]


def build_target(df: pd.DataFrame) -> pd.Series:
    return np.log(df["close"].shift(-1) / df["close"]).rename("target")


def training_set(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    data = pd.concat([build_features(df), build_target(df)], axis=1).dropna()
    return data[FEATURE_NAMES], data["target"]


def latest_features(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < MIN_HISTORY:
        raise ValueError(
            f"histórico insuficiente: {len(df)} dias, mínimo de {MIN_HISTORY}"
        )
    row = build_features(df).iloc[[-1]]
    if row.isna().any().any():
        raise ValueError("não foi possível calcular todos os atributos da última linha")
    return row
