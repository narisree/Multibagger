#!/usr/bin/env python3
"""
fetch_bhavcopy.py — mark prices to market from NSE's official end-of-day
**Bhavcopy** (a static archive on nsearchives.nseindia.com). No API key, covers
every NSE equity. EOD close granularity (one update per trading day), which is
the right resolution for a daily paper book.

Why: live-quote APIs are blocked for GitHub-Actions IPs — Yahoo 429s them and
NSE's quote endpoint strips lastPrice for datacenter IPs. The Bhavcopy archive
is a plain file download and usually is NOT blocked, so it's the reliable
free/automated source for NSE prices on CI.

Updates cmp / currentPrice across:
  data/candidates.json   -> candidate.cmp
  data/portfolio.json    -> position.cmp
  data/paper-trades.json -> holding.currentPrice   (drives the paper P&L)

The Nifty Smallcap benchmark stays sourced from tools/fetch_nse.py. Reuses the
already-installed `nse` library (no new dependency). Not financial advice.
"""
import csv
import json
from pathlib import Path
from datetime import date, datetime, timedelta

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".nse_cache"
CACHE.mkdir(exist_ok=True)


def get_nse():
    from nse import NSE
    return NSE(download_folder=CACHE, server=True, timeout=30)


def latest_bhavcopy(nse, lookback=7):
    """(csv_path, trade_date) for the most recent available equity bhavcopy, or (None, None)."""
    for i in range(lookback):
        d = date.today() - timedelta(days=i)
        if d.weekday() >= 5:            # Sat/Sun — no trading
            continue
        try:
            p = nse.equityBhavcopy(datetime(d.year, d.month, d.day))
            return Path(p), d
        except Exception as e:           # not published yet / holiday / not found
            print(f"  · bhavcopy {d}: unavailable ({e})")
    return None, None


def parse_closes(csv_path):
    """Parse a bhavcopy CSV -> {SYMBOL: close}. Handles new UDiFF + legacy headers."""
    closes = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        cols = {(c or "").strip(): c for c in (reader.fieldnames or [])}

        def pick(*names):
            for n in names:
                if n in cols:
                    return cols[n]
            return None

        sym_c = pick("TckrSymb", "SYMBOL", "Symbol")
        srs_c = pick("SctySrs", "SERIES", "Series")
        cls_c = pick("ClsPric", "CLOSE", "Close", "LastPric", "LAST", "Last")
        if not (sym_c and cls_c):
            print(f"  ! unrecognised bhavcopy columns: {reader.fieldnames}")
            return closes
        for row in reader:
            if srs_c:
                series = str(row.get(srs_c, "")).strip().upper()
                if series not in ("EQ", "BE", "BZ", ""):
                    continue
            sym = str(row.get(sym_c, "")).strip().upper()
            try:
                px = float(str(row.get(cls_c, "")).replace(",", ""))
            except (TypeError, ValueError):
                continue
            if sym and px > 0:
                closes[sym] = round(px, 2)
    return closes


def main():
    try:
        nse = get_nse()
    except Exception as e:  # noqa: BLE001
        print(f"NSE init failed ({e}); skipping bhavcopy price fetch.")
        return
    try:
        csv_path, tdate = latest_bhavcopy(nse)
    finally:
        try:
            nse.exit()
        except Exception:  # noqa: BLE001
            pass

    if not csv_path:
        print("No bhavcopy available in the lookback window; files left unchanged.")
        return
    closes = parse_closes(csv_path)
    print(f"Bhavcopy {tdate}: parsed {len(closes)} EQ close(s).")
    if not closes:
        return

    iso = tdate.isoformat()
    plan = [
        (ROOT / "data" / "candidates.json", "candidates", "cmp", "screenDate"),
        (ROOT / "data" / "portfolio.json", "positions", "cmp", "lastUpdated"),
        (ROOT / "data" / "paper-trades.json", "holdings", "currentPrice", "lastUpdated"),
    ]
    for fp, key, field, meta_key in plan:
        if not fp.exists():
            continue
        data = json.loads(fp.read_text())
        priced, missing = 0, []
        for rec in data.get(key, []):
            sym = (rec.get("ticker") or "").upper()
            if sym in closes:
                rec[field] = closes[sym]
                priced += 1
            elif sym:
                missing.append(sym)
        data.setdefault("meta", {})[meta_key] = iso
        fp.write_text(json.dumps(data, indent=2) + "\n")
        msg = f"  ✓ {fp.name}: priced {priced} record(s) from bhavcopy {iso}"
        if missing:
            msg += f"  (not in bhavcopy: {', '.join(missing)})"
        print(msg)

    paper = json.loads((ROOT / "data" / "paper-trades.json").read_text())
    cap = paper.get("meta", {}).get("startingCapital", 50000)
    cash = paper.get("cash", 0)
    val = sum((h.get("currentPrice") or h.get("buyPrice", 0)) * h.get("shares", 0)
              for h in paper.get("holdings", []))
    total = val + cash
    print(f"\nPaper book: value Rs {total:,.0f} vs Rs {cap:,} start "
          f"-> P&L Rs {total - cap:,.0f} ({(total - cap) / cap * 100:+.1f}%)")
    print("Reminder: re-embed with  node tools/embed_data.js")


if __name__ == "__main__":
    main()
