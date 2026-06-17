#!/usr/bin/env python3
"""
fetch_twelvedata.py — fill LIVE equity prices from Twelve Data (https://twelvedata.com).

Why this exists: Yahoo rate-limits GitHub-Actions IPs (HTTP 429) and NSE serves a
price-stripped quote to datacenter IPs (no lastPrice). Twelve Data *does* serve quotes
to CI IPs. Free tier is enough here (a handful of symbols, once a day).

Setup (one-time):
  1. Get a free API key at https://twelvedata.com (Sign up -> API key).
  2. Add it to the repo as a GitHub Actions secret named TWELVEDATA_API_KEY
     (Settings -> Secrets and variables -> Actions -> New repository secret).
The workflow passes it in as the TWELVEDATA_API_KEY env var.

In ONE batched request it refreshes the last price across all three data files:
  data/candidates.json   -> candidate.cmp
  data/portfolio.json    -> position.cmp, position.dayChangePct
  data/paper-trades.json -> holding.currentPrice   (this is what drives paper P&L)

The Nifty Smallcap benchmark stays sourced from tools/fetch_nse.py (NSE's index
endpoint is not IP-stripped). Dependency-free (stdlib urllib). Not financial advice.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()
QUOTE_URL = "https://api.twelvedata.com/quote"
KEY = os.environ.get("TWELVEDATA_API_KEY", "").strip()
EXCHANGE = "NSE"
CREDITS_PER_MIN = 8   # free-tier rate limit; we chunk requests to stay under it


def fetch_quotes(symbols):
    """Batched quote for NSE tickers -> {ticker: {'price': float, 'pct': float|None}}."""
    if not symbols:
        return {}
    qs = urllib.parse.urlencode({
        "symbol": ",".join(symbols),
        "exchange": EXCHANGE,
        "apikey": KEY,
    })
    req = urllib.request.Request(f"{QUOTE_URL}?{qs}", headers={"User-Agent": "multibagger/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)

    if isinstance(data, dict) and data.get("status") == "error":
        print(f"  ! Twelve Data API error: {data.get('message')}")
        return {}
    if isinstance(data, dict) and "symbol" in data:          # single-symbol response
        recs = {str(data.get("symbol")): data}
    elif isinstance(data, dict):                             # batched {symbol: rec}
        recs = data
    else:
        recs = {}

    out = {}
    for sym in symbols:
        rec = recs.get(sym) or recs.get(sym.upper())
        if not isinstance(rec, dict):
            print(f"  - {sym}: not returned (symbol may be outside free-tier coverage)")
            continue
        if rec.get("status") == "error" or rec.get("close") is None:
            print(f"  - {sym}: {rec.get('message', 'no close in quote')}")
            continue
        try:
            price = round(float(rec["close"]), 2)
        except (TypeError, ValueError):
            print(f"  - {sym}: bad close value {rec.get('close')!r}")
            continue
        pct = None
        try:
            pct = round(float(rec.get("percent_change")), 2)
        except (TypeError, ValueError):
            pct = None
        out[sym] = {"price": price, "pct": pct}
        print(f"  ✓ {sym}: ₹{price:.2f}" + (f" ({pct:+.2f}% today)" if pct is not None else ""))
    return out


def main():
    if not KEY:
        print("TWELVEDATA_API_KEY not set — skipping live price fetch.\n"
              "Create a free key at https://twelvedata.com and add it as the GitHub "
              "secret TWELVEDATA_API_KEY, then re-run 'Update market data'.")
        return  # exit 0 so the rest of the pipeline still runs

    cand_f = ROOT / "data" / "candidates.json"
    port_f = ROOT / "data" / "portfolio.json"
    paper_f = ROOT / "data" / "paper-trades.json"
    cand = json.loads(cand_f.read_text())
    port = json.loads(port_f.read_text())
    paper = json.loads(paper_f.read_text())

    syms = []
    for c in cand.get("candidates", []):
        if c.get("ticker"):
            syms.append(c["ticker"])
    for p in port.get("positions", []):
        if p.get("ticker"):
            syms.append(p["ticker"])
    for h in paper.get("holdings", []):
        if h.get("ticker"):
            syms.append(h["ticker"])
    syms = sorted(set(syms))
    if not syms:
        print("No tickers found in the data files; nothing to fetch.")
        return
    print(f"Fetching {len(syms)} symbol(s) from Twelve Data ({EXCHANGE}): {', '.join(syms)}")

    quotes = {}
    for i in range(0, len(syms), CREDITS_PER_MIN):
        chunk = syms[i:i + CREDITS_PER_MIN]
        try:
            quotes.update(fetch_quotes(chunk))
        except Exception as e:  # noqa: BLE001
            print(f"  ! batch {chunk} failed: {e}")
        if i + CREDITS_PER_MIN < len(syms):
            print("  · pausing 61s for the free-tier rate limit…")
            time.sleep(61)

    if not quotes:
        print("No prices returned — check the API key and symbol coverage. Files left unchanged.")
        return

    for c in cand.get("candidates", []):
        qd = quotes.get(c.get("ticker"))
        if qd:
            c["cmp"] = qd["price"]
    for p in port.get("positions", []):
        qd = quotes.get(p.get("ticker"))
        if qd:
            p["cmp"] = qd["price"]
            if qd["pct"] is not None:
                p["dayChangePct"] = qd["pct"]
    for h in paper.get("holdings", []):
        qd = quotes.get(h.get("ticker"))
        if qd:
            h["currentPrice"] = qd["price"]

    cand.setdefault("meta", {})["screenDate"] = TODAY
    port.setdefault("meta", {})["lastUpdated"] = TODAY
    paper.setdefault("meta", {})["lastUpdated"] = TODAY
    cand_f.write_text(json.dumps(cand, indent=2) + "\n")
    port_f.write_text(json.dumps(port, indent=2) + "\n")
    paper_f.write_text(json.dumps(paper, indent=2) + "\n")

    cap = paper.get("meta", {}).get("startingCapital", 50000)
    inv = sum(h.get("invested", 0) for h in paper.get("holdings", []))
    val = sum((h.get("currentPrice") or h.get("buyPrice", 0)) * h.get("shares", 0)
              for h in paper.get("holdings", []))
    cash = paper.get("cash", 0)
    total = val + cash
    print(f"\nPaper book marked to market: holdings ₹{val:,.0f} + cash ₹{cash:,.0f} "
          f"= ₹{total:,.0f} vs ₹{cap:,} start -> P&L ₹{total - cap:,.0f} "
          f"({(total - cap) / cap * 100:+.1f}%)  [{len(quotes)}/{len(syms)} priced]")
    print("Reminder: re-embed with  node tools/embed_data.js")


if __name__ == "__main__":
    main()
