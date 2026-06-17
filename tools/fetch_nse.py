#!/usr/bin/env python3
"""
fetch_nse.py — comprehensive scoring/validation data from OFFICIAL NSE India
endpoints, via BennyThadikaran/NseIndiaApi. Authoritative complement to the
Yahoo fetcher (which runs first as a fallback; NSE then overwrites).

What this populates per stock (each enricher is independently guarded — partial
success is fine; failures are logged, not fatal):

  VALIDATION / HARD FILTERS
    - cmp, marketCapCr -> capCategory + hardFilters.capSmallOrMicro
    - hardFilters.cmpBelow1000, hardFilters.liquidityAboveFloor (from traded value)
    - avgDailyValueCr (single-session traded value, proxy for the liquidity floor)
    - deliveryPct (delivery-to-traded quantity; quality of volume)
  RED FLAGS
    - redFlags.surveillance (ASM/GSM), redFlags.pledgeHigh (pledge > 25%)
  FUNDAMENTALS / OWNERSHIP
    - pe, sectorPe, promoterHolding, pledge, instEntry (FII/DII present)
  TECHNICALS (computed from ~1y history)
    - weekHigh52/weekLow52, above50DMA, above200DMA, rsi, macd, higherHighs,
      nearBreakout, keySupport, keyResistance, volumeAccumulation, basePatternScore
  NEWS (portfolio only)
    - recent corporate actions / board meetings appended to a position's notes

STILL MANUAL (no reliable API source — research/judgment): revCagr3y, patCagr3y,
growthQuality, ROCE, OCF, interestCoverage, workingCapitalTrend, marginTrend,
structuralEdgeScore, governanceScore. (Yahoo fills roe/debtEquity/margins/pb.)

Runs on GitHub Actions (full internet); NOT inside a GitHub-only dev container.
Install (CI): pip install "git+https://github.com/BennyThadikaran/NseIndiaApi.git" "httpx[http2]"
Usage: python tools/fetch_nse.py [--candidates|--portfolio]
No API key. Not financial advice.

NOTE: exact NSE JSON shapes vary by endpoint version, so every field is read
through defensive multi-key lookups. The first GitHub Actions run is the
validation step — check its logs and tighten any field that comes back empty.
"""
import json
import sys
import time
from pathlib import Path
from datetime import date, datetime, timedelta

ROOT = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()
RATE_SLEEP = 0.4              # library caps ~3 req/s
MID_CAP_FLOOR_CR = 34700     # AMFI ref (Jan 2026): small/micro sits below the mid floor
LIQUIDITY_FLOOR_CR = 1.0


# ----------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------
def get_nse():
    from nse import NSE
    cache = ROOT / ".nse_cache"
    cache.mkdir(exist_ok=True)
    return NSE(download_folder=cache, server=True, timeout=20)


def dig(d, *keys, default=None):
    for k in keys:
        if isinstance(d, list) and isinstance(k, int):
            d = d[k] if -len(d) <= k < len(d) else None
        elif isinstance(d, dict):
            d = d.get(k)
        else:
            return default
        if d is None:
            return default
    return d


def first_num(d, *paths):
    """Try several key-paths (each a tuple), return the first numeric value."""
    for p in paths:
        v = dig(d, *p)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.replace(",", ""))
            except ValueError:
                pass
    return None


def rnd(x, n=2):
    return None if x is None else round(float(x), n)


# ----------------------------------------------------------------------------
# technical indicators (pure python)
# ----------------------------------------------------------------------------
def sma(a, n):
    return sum(a[-n:]) / n if len(a) >= n else None


def ema_series(a, n):
    if len(a) < n:
        return []
    k = 2 / (n + 1)
    out = [sum(a[:n]) / n]
    for v in a[n:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gain = loss = 0.0
    for i in range(len(closes) - period, len(closes)):
        d = closes[i] - closes[i - 1]
        gain += max(d, 0)
        loss += max(-d, 0)
    if loss == 0:
        return 100
    rs = (gain / period) / (loss / period)
    return round(100 - 100 / (1 + rs))


def macd_state(closes):
    if len(closes) < 35:
        return None
    ema12 = ema_series(closes, 12)
    ema26 = ema_series(closes, 26)
    n = min(len(ema12), len(ema26))
    macd_line = [ema12[-n + i] - ema26[-n + i] for i in range(n)]
    signal = ema_series(macd_line, 9)
    if not signal:
        return "neutral"
    hist = macd_line[-1] - signal[-1]
    return "bullish" if hist > 0 else ("bearish" if hist < 0 else "neutral")


def technicals_from_history(closes, vols, cmp_):
    """Return a dict of technical fields computed from closing prices/volumes."""
    if not closes or len(closes) < 30:
        return {}
    s50, s200 = sma(closes, 50), sma(closes, 200)
    hi52, lo52 = max(closes[-252:]), min(closes[-252:])
    recent = closes[-60:]
    # higher-highs: last third's max above the prior third's max
    third = len(recent) // 3
    higher_highs = third > 0 and max(recent[-third:]) > max(recent[:third])
    near_breakout = cmp_ >= hi52 * 0.95
    key_resistance = round(hi52, 2)
    key_support = round(max(lo52, s200) if s200 else lo52, 2)
    out = {
        "above50DMA": bool(s50 and cmp_ > s50),
        "above200DMA": bool(s200 and cmp_ > s200),
        "higherHighs": bool(higher_highs),
        "rsi": rsi(closes),
        "macd": macd_state(closes),
        "nearBreakout": bool(near_breakout),
        "keySupport": key_support,
        "keyResistance": key_resistance,
        "weekHigh52": round(hi52, 2),
        "weekLow52": round(lo52, 2),
    }
    if vols and len(vols) >= 20:
        up = [vols[i] for i in range(1, len(vols)) if closes[i] >= closes[i - 1]][-20:]
        dn = [vols[i] for i in range(1, len(vols)) if closes[i] < closes[i - 1]][-20:]
        if up and dn:
            out["volumeAccumulation"] = (sum(up) / len(up)) > (sum(dn) / len(dn))
    # base pattern: tighter recent range scores higher
    rng = (max(recent) - min(recent)) / (sum(recent) / len(recent)) if recent else 1
    out["basePatternScore"] = max(0, min(100, round(100 - rng * 120)))
    return out


# ----------------------------------------------------------------------------
# NSE enrichers (each guarded)
# ----------------------------------------------------------------------------
def nse_equity_quote(nse, sym):
    """Best-effort equity quote: try the typed call first, fall back to the bare call,
    with a light retry. Different nse-lib versions accept/return slightly different shapes."""
    last_err = None
    for call in (
        lambda: nse.quote(sym, type="equity"),
        lambda: nse.quote(sym),
    ):
        for _ in range(2):
            try:
                q = call()
                if q:
                    return q
            except TypeError:
                break  # this call form's signature isn't supported; try the next form
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(0.6)
    if last_err:
        raise last_err
    return None


def enrich_quote(nse, sym, rec):
    """cmp, day change, 52w, P/E, sector P/E, market cap, traded value, delivery, surveillance."""
    try:
        q = nse_equity_quote(nse, sym)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {sym}: quote failed ({e})")
        return False
    if not q:
        print(f"  ! {sym}: empty quote response")
        return False
    price = first_num(q,
                      ("priceInfo", "lastPrice"), ("lastPrice",),
                      ("priceInfo", "close"), ("priceInfo", "previousClose"),
                      ("data", 0, "lastPrice"), ("data", 0, "closePrice"),
                      ("price",))
    if price is None:
        # One-time diagnostic so the real JSON shape surfaces in the Actions log
        # (the first run is the validation step — see module docstring).
        try:
            top = sorted(q.keys()) if isinstance(q, dict) else type(q).__name__
            pinfo = q.get("priceInfo") if isinstance(q, dict) else None
            pkeys = sorted(pinfo.keys()) if isinstance(pinfo, dict) else pinfo
            print(f"  ! {sym}: no lastPrice in quote | top-keys={top} | priceInfo={pkeys}")
        except Exception:  # noqa: BLE001
            print(f"  ! {sym}: no lastPrice in quote (could not introspect response)")
        return False
    rec["cmp"] = rnd(price)
    pch = first_num(q, ("priceInfo", "pChange"), ("pChange",), ("priceInfo", "change"))

    wk_max = first_num(q, ("priceInfo", "weekHighLow", "max"))
    wk_min = first_num(q, ("priceInfo", "weekHighLow", "min"))
    pe = first_num(q, ("metadata", "pdSymbolPe"), ("metadata", "symbolPe"))
    sector_pe = first_num(q, ("metadata", "pdSectorPe"))
    issued = first_num(q, ("securityInfo", "issuedSize"))
    mcap = first_num(q,
                     ("marketDeptOrderBook", "tradeInfo", "totalMarketCap"),
                     ("tradeInfo", "totalMarketCap"))
    if mcap is None and issued:
        mcap = issued * price        # shares x price (INR)
    traded_val = first_num(q,
                           ("marketDeptOrderBook", "tradeInfo", "totalTradedValue"),
                           ("tradeInfo", "totalTradedValue"))
    delivery = first_num(q,
                         ("securityWiseDP", "deliveryToTradedQuantity"),
                         ("marketDeptOrderBook", "tradeInfo", "deliveryToTradedQuantity"))
    surv = dig(q, "securityInfo", "surveillance", "surveillance") \
        or dig(q, "securityInfo", "surveillance", "surv")

    tech = rec.setdefault("technicals", {})
    fund = rec.setdefault("fundamentals", {})
    if wk_max is not None and wk_min is not None:
        tech["weekHigh52"], tech["weekLow52"] = rnd(wk_max), rnd(wk_min)
    if pe is not None:
        fund["pe"] = rnd(pe, 1)
    if sector_pe is not None:
        fund["sectorPe"] = rnd(sector_pe, 1)
    if mcap is not None:
        rec["marketCapCr"] = round(mcap / 1e7)
    if traded_val is not None:
        rec["avgDailyValueCr"] = rnd(traded_val / 1e7, 1)   # single-session proxy
    if delivery is not None:
        rec["deliveryPct"] = rnd(delivery, 1)
    surv_active = bool(surv) and str(surv).lower() not in ("", "none", "false")
    rec.setdefault("redFlags", {})["surveillance"] = surv_active

    # derive hard filters / category from fresh values
    hf = rec.setdefault("hardFilters", {})
    hf["listedNSEBSE"] = True
    hf["cmpBelow1000"] = rec["cmp"] < 1000
    if rec.get("marketCapCr") is not None:
        hf["capSmallOrMicro"] = rec["marketCapCr"] < MID_CAP_FLOOR_CR
        rec["capCategory"] = "Micro Cap" if rec["marketCapCr"] < 500 else "Small Cap"
    if rec.get("avgDailyValueCr") is not None:
        hf["liquidityAboveFloor"] = rec["avgDailyValueCr"] >= LIQUIDITY_FLOOR_CR

    rec["_dayChangePct"] = rnd(pch, 2) if pch is not None else None
    flag = "  ⚠SURV" if surv_active else ""
    print(f"  · quote: CMP ₹{rec['cmp']} PE {pe} mcap {rec.get('marketCapCr')}cr "
          f"liq {rec.get('avgDailyValueCr')}cr deliv {rec.get('deliveryPct')}%{flag}")
    return True


def enrich_shareholding(nse, sym, rec):
    """promoter holding %, pledge %, institutional presence -> ownership + pledge red flag."""
    try:
        sh = nse.shareholding(sym)
    except Exception as e:  # noqa: BLE001
        print(f"  · shareholding unavailable ({e})")
        return
    prom = first_num(sh, ("promoter",), ("promoterHolding",), ("promoters",))
    pledge = first_num(sh, ("pledge",), ("promoterPledge",), ("pledgePercentage",))
    fii = first_num(sh, ("fii",), ("foreignInstitution",)) or 0
    dii = first_num(sh, ("dii",), ("domesticInstitution",)) or 0
    fund = rec.setdefault("fundamentals", {})
    if prom is not None:
        fund["promoterHolding"] = rnd(prom, 2)
    if pledge is not None:
        fund["pledge"] = rnd(pledge, 2)
        rec.setdefault("redFlags", {})["pledgeHigh"] = pledge > 25
    if (fii + dii) > 0:
        fund["instEntry"] = True
    print(f"  · shareholding: promoter {prom}% pledge {pledge}% inst {round(fii+dii,1)}%")


def enrich_history(nse, sym, rec):
    """~1y OHLC -> DMA/RSI/MACD/structure technicals."""
    closes, vols = get_history(nse, sym)
    if not closes:
        print("  · history unavailable (keeping Yahoo/manual technicals)")
        return
    tech = technicals_from_history(closes, vols, rec.get("cmp") or closes[-1])
    rec.setdefault("technicals", {}).update({k: v for k, v in tech.items() if v is not None})
    if len(closes) >= 30:
        rec["priceSeries"] = [round(c, 2) for c in closes[-30:]]
    print(f"  · history: {len(closes)} closes -> "
          f">50DMA {tech.get('above50DMA')} >200DMA {tech.get('above200DMA')} "
          f"RSI {tech.get('rsi')} MACD {tech.get('macd')}")


def get_history(nse, sym):
    """Best-effort OHLC history -> (closes, volumes) oldest..newest, or ([],[])."""
    to_d, from_d = datetime.now(), datetime.now() - timedelta(days=400)
    raw = None
    for call in (
        lambda: nse.fetch_equity_historical_data(sym, from_date=from_d, to_date=to_d),
        lambda: nse.fetch_equity_historical_data(sym),
    ):
        try:
            raw = call()
            if raw:
                break
        except Exception:  # noqa: BLE001
            continue
    if not raw:
        return [], []
    rows = raw.get("data") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return [], []
    closes, vols = [], []
    for r in rows:
        c = first_num(r, ("CH_CLOSING_PRICE",), ("close",), ("lastPrice",), ("CLOSE",))
        v = first_num(r, ("CH_TOT_TRADED_QTY",), ("volume",), ("TOTTRDQTY",))
        if c is not None:
            closes.append(c)
            vols.append(v or 0)
    # NSE history is usually newest-first; normalise to oldest..newest
    if len(closes) > 2 and closes[0] and closes[-1]:
        ts0 = dig(rows[0], "CH_TIMESTAMP") or dig(rows[0], "mTIMESTAMP")
        tsn = dig(rows[-1], "CH_TIMESTAMP") or dig(rows[-1], "mTIMESTAMP")
        if ts0 and tsn and str(ts0) > str(tsn):
            closes.reverse(); vols.reverse()
    return closes, vols


def enrich_news(nse, sym, rec):
    """Recent corporate actions + board meetings -> a short notes string (portfolio use)."""
    items = []
    for fn, label in ((lambda: nse.actions(symbol=sym), "action"),
                      (lambda: nse.boardMeetings(sym), "board")):
        try:
            data = fn() or []
            for it in (data[:2] if isinstance(data, list) else []):
                txt = dig(it, "subject") or dig(it, "purpose") or dig(it, "comp") or str(it)[:80]
                items.append(f"[{label}] {txt}")
        except Exception:  # noqa: BLE001
            pass
    if items:
        rec["lastNote"] = " | ".join(items)[:240]
        print(f"  · news: {len(items)} item(s)")


def add_source(rec, note):
    rec.setdefault("sources", [])
    rec["sources"] = [s for s in rec["sources"] if not str(s.get("label", "")).startswith("NSE official")]
    rec["sources"].append({
        "label": f"NSE official ({rec['ticker']})",
        "url": f"https://www.nseindia.com/get-quotes/equity?symbol={rec['ticker']}",
        "date": TODAY, "note": note,
    })


# ----------------------------------------------------------------------------
# drivers
# ----------------------------------------------------------------------------
def run_candidates(nse):
    f = ROOT / "data" / "candidates.json"
    data = json.loads(f.read_text())
    n = 0
    for c in data.get("candidates", []):
        sym = c.get("ticker")
        if not sym:
            continue
        print(f"\n{sym}")
        if not enrich_quote(nse, sym, c):
            continue
        time.sleep(RATE_SLEEP)
        enrich_shareholding(nse, sym, c); time.sleep(RATE_SLEEP)
        enrich_history(nse, sym, c); time.sleep(RATE_SLEEP)
        c.pop("_dayChangePct", None)
        c["illustrative"] = False
        add_source(c, "official CMP, P/E, market cap, liquidity, delivery, surveillance, "
                      "ownership/pledge, and history-derived technicals")
        n += 1
    data.setdefault("meta", {})["screenDate"] = TODAY
    data["meta"]["liquidityFloorCr"] = LIQUIDITY_FLOOR_CR
    f.write_text(json.dumps(data, indent=2) + "\n")
    print(f"\nUpdated {n} candidate(s) from NSE -> data/candidates.json")


def run_portfolio(nse):
    f = ROOT / "data" / "portfolio.json"
    data = json.loads(f.read_text())
    n = 0
    for p in data.get("positions", []):
        sym = p.get("ticker")
        if not sym:
            continue
        print(f"\n{sym}")
        if not enrich_quote(nse, sym, p):
            continue
        p["dayChangePct"] = p.pop("_dayChangePct", None)
        time.sleep(RATE_SLEEP)
        enrich_history(nse, sym, p); time.sleep(RATE_SLEEP)
        enrich_news(nse, sym, p); time.sleep(RATE_SLEEP)
        if dig(p, "redFlags", "surveillance"):
            p.setdefault("alerts", []).append(f"NSE surveillance flag active (as of {TODAY})")
        n += 1
    data.setdefault("meta", {})["lastUpdated"] = TODAY
    f.write_text(json.dumps(data, indent=2) + "\n")
    print(f"\nUpdated {n} position(s) from NSE -> data/portfolio.json")


def benchmark_level(nse, name):
    """Best-effort current level of a named NSE index (e.g. 'NIFTY SMALLCAP 250')."""
    try:
        data = nse.listIndices()
    except Exception as e:  # noqa: BLE001
        print(f"  · index list unavailable ({e})")
        return None
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return None
    target = (name or "").upper().replace(" ", "")
    best = None
    for r in rows:
        idx = str(dig(r, "index") or dig(r, "indexSymbol") or "").upper().replace(" ", "")
        if not idx:
            continue
        if idx == target or (target and target in idx):
            lvl = first_num(r, ("last",), ("lastPrice",), ("indexValue",))
            if lvl is not None:
                # exact match wins immediately; otherwise keep the first contains-match
                if idx == target:
                    return lvl
                if best is None:
                    best = lvl
    return best


def run_paper(nse):
    f = ROOT / "data" / "paper-trades.json"
    data = json.loads(f.read_text())
    n = 0
    for h in data.get("holdings", []):
        sym = h.get("ticker")
        if not sym:
            continue
        print(f"\n{sym}")
        rec = {"ticker": sym}
        if not enrich_quote(nse, sym, rec):
            continue
        if rec.get("cmp") is not None:
            h["currentPrice"] = rec["cmp"]
            val = rec["cmp"] * (h.get("shares") or 0)
            pl = val - (h.get("invested") or 0)
            print(f"  · paper: value ₹{val:.0f} P&L {'+' if pl >= 0 else ''}{pl:.0f}")
            n += 1
        rec.pop("_dayChangePct", None)
        time.sleep(RATE_SLEEP)
    bm = data.get("benchmark") or {}
    if bm.get("name"):
        lvl = benchmark_level(nse, bm["name"])
        if lvl is not None:
            bm["currentLevel"] = rnd(lvl)
            if bm.get("startProvisional"):
                bm["startLevel"] = rnd(lvl)
                bm["startProvisional"] = False
                bm["startDate"] = TODAY
            print(f"\nbenchmark {bm['name']}: level {bm['currentLevel']}")
        else:
            print(f"\nbenchmark {bm['name']}: level unavailable (keeping prior)")
    data.setdefault("meta", {})["lastUpdated"] = TODAY
    f.write_text(json.dumps(data, indent=2) + "\n")
    print(f"\nUpdated {n} holding(s) from NSE -> data/paper-trades.json")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("--candidates", "--portfolio", "--paper"):
        sys.exit("Usage: python tools/fetch_nse.py [--candidates|--portfolio|--paper]")
    nse = get_nse()
    try:
        if mode == "--candidates":
            run_candidates(nse)
        elif mode == "--portfolio":
            run_portfolio(nse)
        else:
            run_paper(nse)
    finally:
        try:
            nse.exit()
        except Exception:  # noqa: BLE001
            pass
    print("Reminder: re-embed into the dashboards with  node tools/embed_data.js")


if __name__ == "__main__":
    main()
