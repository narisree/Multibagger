#!/usr/bin/env python3
"""
fetch_nse.py — refresh CMP, P/E, 52-week range and (best-effort) surveillance
flags from the OFFICIAL NSE India endpoints, via BennyThadikaran/NseIndiaApi.

This is an authoritative complement to tools/fetch_yahoo.js:
  - NSE  -> official last price, P/E, 52-week high/low, surveillance flag
  - Yahoo -> price history => 50/200-DMA, RSI, market ratios

Runs on GitHub Actions runners (full internet). It will NOT work inside a
restricted dev container where nseindia.com is blocked by the egress allowlist.

Install (CI):
    pip install "git+https://github.com/BennyThadikaran/NseIndiaApi.git" "httpx[http2]"

Usage:
    python tools/fetch_nse.py --candidates    # refresh data/candidates.json
    python tools/fetch_nse.py --portfolio     # refresh data/portfolio.json

No API key or login required. Records are keyed by their NSE 'ticker'
(e.g. MARKSANS). Not financial advice.
"""
import json
import sys
import time
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()
RATE_SLEEP = 0.4  # library caps ~3 req/s


def get_nse():
    """Instantiate the NSE client in server/cloud mode."""
    from nse import NSE  # imported lazily so --help / syntax-check works without the dep
    cache = ROOT / ".nse_cache"
    cache.mkdir(exist_ok=True)
    return NSE(download_folder=cache, server=True, timeout=20)


def dig(d, *keys, default=None):
    """Safe nested dict access."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
        if d is None:
            return default
    return d


def fetch_quote(nse, symbol):
    """Return a normalised dict of the fields we use, or None on failure."""
    try:
        q = nse.quote(symbol)
    except Exception as e:  # noqa: BLE001 — per-symbol resilience
        print(f"  ! {symbol}: quote failed ({e})")
        return None
    surv = dig(q, "securityInfo", "surveillance", "surveillance")
    if surv is None:
        surv = dig(q, "securityInfo", "surveillance", "surv")
    return {
        "price": dig(q, "priceInfo", "lastPrice"),
        "pchange": dig(q, "priceInfo", "pChange"),
        "wk_max": dig(q, "priceInfo", "weekHighLow", "max"),
        "wk_min": dig(q, "priceInfo", "weekHighLow", "min"),
        "pe": dig(q, "metadata", "pdSymbolPe"),
        "surveillance": surv,  # None/empty => clean; non-empty string => under a measure
    }


def add_source(rec, note):
    rec.setdefault("sources", [])
    rec["sources"] = [s for s in rec["sources"] if not str(s.get("label", "")).startswith("NSE official")]
    rec["sources"].append({
        "label": f"NSE official quote ({rec['ticker']})",
        "url": f"https://www.nseindia.com/get-quotes/equity?symbol={rec['ticker']}",
        "date": TODAY,
        "note": note,
    })


def update_candidates(nse):
    f = ROOT / "data" / "candidates.json"
    data = json.loads(f.read_text())
    n = 0
    for c in data.get("candidates", []):
        sym = c.get("ticker")
        if not sym:
            continue
        q = fetch_quote(nse, sym)
        time.sleep(RATE_SLEEP)
        if not q or q["price"] is None:
            print(f"- {sym}: no quote, left unchanged")
            continue
        c["cmp"] = q["price"]
        if q["pe"] is not None:
            c.setdefault("fundamentals", {})["pe"] = q["pe"]
        if q["wk_max"] is not None and q["wk_min"] is not None:
            c.setdefault("technicals", {})["weekHigh52"] = q["wk_max"]
            c["technicals"]["weekLow52"] = q["wk_min"]
        # surveillance: only flag when NSE actually reports a measure
        surv_active = bool(q["surveillance"]) and str(q["surveillance"]).lower() not in ("", "none", "false")
        c.setdefault("redFlags", {})["surveillance"] = surv_active
        add_source(c, "official CMP, P/E, 52-week range, surveillance"
                      + (f" [SURVEILLANCE: {q['surveillance']}]" if surv_active else " (clean)"))
        flag = "  ⚠ SURVEILLANCE" if surv_active else ""
        print(f"✓ {sym}: CMP ₹{q['price']} PE {q['pe']} 52w {q['wk_min']}-{q['wk_max']}{flag}")
        n += 1
    data.setdefault("meta", {})["screenDate"] = TODAY
    f.write_text(json.dumps(data, indent=2) + "\n")
    print(f"\nUpdated {n} candidate(s) from NSE -> data/candidates.json")


def update_portfolio(nse):
    f = ROOT / "data" / "portfolio.json"
    data = json.loads(f.read_text())
    n = 0
    for p in data.get("positions", []):
        sym = p.get("ticker")
        if not sym:
            continue
        q = fetch_quote(nse, sym)
        time.sleep(RATE_SLEEP)
        if not q or q["price"] is None:
            print(f"- {sym}: no quote, left unchanged")
            continue
        p["cmp"] = q["price"]
        if q["pchange"] is not None:
            p["dayChangePct"] = q["pchange"]
        surv_active = bool(q["surveillance"]) and str(q["surveillance"]).lower() not in ("", "none", "false")
        if surv_active:
            p.setdefault("alerts", []).append(f"NSE surveillance flag: {q['surveillance']} (as of {TODAY})")
        since = ((q["price"] - p["entryPrice"]) / p["entryPrice"] * 100) if p.get("entryPrice") else None
        print(f"✓ {sym}: CMP ₹{q['price']} ({q['pchange']}% today"
              + (f", {since:+.1f}% since entry" if since is not None else "") + ")")
        n += 1
    data.setdefault("meta", {})["lastUpdated"] = TODAY
    f.write_text(json.dumps(data, indent=2) + "\n")
    print(f"\nUpdated {n} position(s) from NSE -> data/portfolio.json")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("--candidates", "--portfolio"):
        sys.exit("Usage: python tools/fetch_nse.py [--candidates|--portfolio]")
    nse = get_nse()
    try:
        if mode == "--candidates":
            update_candidates(nse)
        else:
            update_portfolio(nse)
    finally:
        try:
            nse.exit()
        except Exception:  # noqa: BLE001
            pass
    print("Reminder: re-embed into the dashboards with  node tools/embed_data.js")


if __name__ == "__main__":
    main()
