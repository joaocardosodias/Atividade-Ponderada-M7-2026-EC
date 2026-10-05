from datetime import datetime, timezone

import pandas as pd


def frame_from_records(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)
    missing = {"date", "close", "volume"} - set(df.columns)
    if missing:
        raise ValueError(f"colunas ausentes: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.drop_duplicates("date", keep="last").set_index("date").sort_index()
    return df[["close", "volume"]].astype(float)


def drop_incomplete_day(df: pd.DataFrame, today: str | None = None) -> pd.DataFrame:
    if today is None:
        limit = pd.Timestamp(datetime.now(timezone.utc).date())
    else:
        limit = pd.Timestamp(today)
    return df[df.index < limit]
