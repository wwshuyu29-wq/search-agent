#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch a compact Yahoo Finance snapshot through yfinance.

This script is intentionally small: SourceHunterExecutor needs a stable JSON
surface, while yfinance itself can be slow, rate-limited, or absent locally.
"""

import argparse
import json
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Fetch yfinance market snapshot")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. AAPL")
    args = parser.parse_args()

    try:
        import yfinance as yf
    except ImportError:
        print("YFINANCE_NOT_INSTALLED", file=sys.stderr)
        return 3

    ticker_symbol = args.ticker.upper().strip()
    try:
        ticker = yf.Ticker(ticker_symbol)
        fast_info = {}
        try:
            fast_info = dict(ticker.fast_info or {})
        except Exception:
            fast_info = {}

        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        currency = fast_info.get("currency") or info.get("currency") or ""
        last_price = fast_info.get("last_price") or fast_info.get("lastPrice") or info.get("currentPrice")
        market_cap = fast_info.get("market_cap") or fast_info.get("marketCap") or info.get("marketCap")
        previous_close = fast_info.get("previous_close") or fast_info.get("previousClose")
        try:
            history = ticker.history(period="5d")
            if not history.empty and "Close" in history:
                closes = history["Close"].dropna()
                if not closes.empty and last_price is None:
                    last_price = round(float(closes.iloc[-1]), 4)
                if len(closes) > 1 and previous_close is None:
                    previous_close = round(float(closes.iloc[-2]), 4)
        except Exception:
            pass
        exchange = fast_info.get("exchange") or info.get("exchange") or ""
        short_name = info.get("shortName") or info.get("longName") or ticker_symbol

        facts = []
        if last_price is not None:
            facts.append(f"last price {last_price} {currency}".strip())
        if market_cap is not None:
            facts.append(f"market cap {market_cap} {currency}".strip())
        if previous_close is not None:
            facts.append(f"previous close {previous_close} {currency}".strip())
        if exchange:
            facts.append(f"exchange {exchange}")
        description = f"{ticker_symbol} " + "; ".join(facts) if facts else f"{ticker_symbol} snapshot fetched"

        print(
            json.dumps(
                [
                    {
                        "title": f"{ticker_symbol} Yahoo Finance market snapshot",
                        "url": f"https://finance.yahoo.com/quote/{ticker_symbol}",
                        "description": description,
                        "publish_date": datetime.now(timezone.utc).date().isoformat(),
                        "source": "Yahoo Finance via yfinance",
                        "confidence": "high" if facts else "medium",
                        "full_text_fetched": True,
                        "metrics": {
                            "ticker": ticker_symbol,
                            "name": short_name,
                            "currency": currency,
                            "last_price": last_price,
                            "market_cap": market_cap,
                            "previous_close": previous_close,
                            "exchange": exchange,
                        },
                    }
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(f"YFINANCE_FETCH_FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
