from pathlib import Path

import yfinance as yf

INICIO = "2017-01-01"
SAIDA = Path(__file__).parent / "btc_usd.csv"


def main() -> None:
    df = yf.download("BTC-USD", start=INICIO, interval="1d", auto_adjust=False, progress=False)
    if df.empty:
        raise SystemExit("O Yahoo Finance não devolveu dados.")

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    df = df[["Close", "Volume"]].dropna()
    df.index.name = "date"
    df.columns = ["close", "volume"]
    df.index = df.index.strftime("%Y-%m-%d")
    df.to_csv(SAIDA)
    print(f"{len(df)} linhas de {df.index[0]} a {df.index[-1]} salvas em {SAIDA}")


if __name__ == "__main__":
    main()
