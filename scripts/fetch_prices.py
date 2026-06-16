from __future__ import annotations

import requests
import yfinance as yf


def fetch_yfinance_price(ticker: str) -> float | None:
    """
    Fetch the latest tradable price from Yahoo Finance.
    Tries 1m intraday first, then falls back to daily close.
    """
    try:
        tk = yf.Ticker(ticker)

        # Prefer intraday last price if available
        hist = tk.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])

        # Fallback to daily close
        hist = tk.history(period="5d", interval="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])

        # Another fallback
        info = getattr(tk, "fast_info", None)
        if info and "lastPrice" in info:
            return float(info["lastPrice"])

    except Exception:
        pass

    return None


def fetch_mfapi_nav(scheme_code: str) -> float | None:
    """
    Fetch mutual fund NAV from MFAPI.
    scheme_code must be the AMFI/MFAPI numeric code.
    """
    try:
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        nav = data["data"][0]["nav"]
        return float(nav)
    except Exception:
        return None


def fetch_coingecko_price(coin_id: str, vs_currency: str = "inr") -> float | None:
    """
    Fetch crypto price from CoinGecko.
    Example coin_id: bitcoin, ethereum
    """
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": vs_currency}
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return float(data[coin_id][vs_currency])
    except Exception:
        return None


def fetch_price_for_holding(row: dict) -> float | None:
    """
    row expects:
      price_source: yfinance | mfapi | crypto | manual
      source_id: ticker / scheme code / coin id
      avg_price: fallback if manual
    """
    source = (row.get("price_source") or "").strip().lower()
    source_id = (row.get("source_id") or "").strip()

    if source == "manual":
        try:
            return float(row.get("avg_price"))
        except Exception:
            return None

    if source == "yfinance" and source_id:
        return fetch_yfinance_price(source_id)

    if source == "mfapi" and source_id:
        return fetch_mfapi_nav(source_id)

    if source == "crypto" and source_id:
        return fetch_coingecko_price(source_id)

    # Generic fallback: if it's a listed Indian instrument, try yfinance
    if source_id:
        p = fetch_yfinance_price(source_id)
        if p is not None:
            return p

    return None