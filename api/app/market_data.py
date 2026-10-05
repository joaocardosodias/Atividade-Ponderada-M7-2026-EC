import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from backend.config import settings
from btc_common.series import frame_from_records

logger = logging.getLogger("api.market_data")

SYMBOL = "BTC-USD"
FULL_HISTORY_START = "2017-01-01"
RECENT_DAYS = 120
YAHOO_TIMEOUT = 20


class DataUnavailable(Exception):
    pass


def _from_yahoo(start: str) -> pd.DataFrame:
    df = yf.download(
        SYMBOL,
        start=start,
        interval="1d",
        auto_adjust=False,
        progress=False,
        timeout=YAHOO_TIMEOUT,
    )
    if df is None or df.empty:
        raise DataUnavailable("o Yahoo Finance não devolveu dados")
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    df = df[["Close", "Volume"]].dropna()
    df.index.name = "date"
    df.columns = ["close", "volume"]
    records = df.reset_index().to_dict("records")
    return frame_from_records(records)


def _from_csv() -> pd.DataFrame:
    try:
        raw = pd.read_csv(settings.fallback_csv)
    except OSError as exc:
        raise DataUnavailable("cópia de reserva dos dados indisponível") from exc
    return frame_from_records(raw.to_dict("records"))


def load(start: str) -> tuple[pd.DataFrame, str]:
    try:
        return _from_yahoo(start), "yahoo"
    except Exception:
        logger.exception("falha ao buscar dados no Yahoo Finance, usando o CSV de reserva")
    frame = _from_csv()
    return frame[frame.index >= pd.Timestamp(start)], "csv"


def recent() -> tuple[pd.DataFrame, str]:
    start = (date.today() - timedelta(days=RECENT_DAYS)).isoformat()
    return load(start)


def full_history() -> tuple[pd.DataFrame, str]:
    return load(FULL_HISTORY_START)
