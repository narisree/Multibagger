# Indian Small/Micro-Cap Multibagger Screener

A disciplined, transparent research tool for surfacing potential "next big thing" candidates from
the Indian small- and micro-cap universe, scoring them on fundamentals + technicals, articulating a
multibagger thesis with explicit invalidation triggers, and then tracking the calls daily while
refining the method over time.

> ⚠️ **Not financial advice.** Small/micro-caps are high-risk, illiquid and volatile — a bad pick can
> go to near-zero and an illiquid one can't even be exited. This is a research aid; final decisions
> and capital risk are the user's own.

---

## What this is (and what it isn't)

This repo is the **screener tool** — a self-contained, dependency-free dashboard plus a transparent,
auditable scoring engine and a documented daily-tracking process. It is **not** a list of live stock
picks.

It ships with **illustrative placeholder data** (fictional `DEMO-*` tickers, invented numbers) so the
dashboards render and every feature is visible. Replace that data with real, sourced entries before
any use.

**Why placeholders and not live picks?** A rigorous screen requires dated, per-stock data from
authorised sources (AMFI, NSE/BSE, company filings, Screener/Trendlyne). Those aggregators block
automated fetching (HTTP 403), so live numbers must be populated by a human or a licensed data feed —
the tool deliberately will not invent them. See
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for the exact source for each field.

---

## Quick start

Open the two dashboards directly in a browser — no build step, no server, no dependencies:

| File | Purpose |
|---|---|
| [`index.html`](index.html) | Landing page linking both dashboards (the GitHub Pages entry point) |
| [`screener.html`](screener.html) | **PHASE 1** — selection, scoring & thesis dashboard |
| [`tracker.html`](tracker.html) | **PHASE 2** — daily monitoring dashboard |

Each dashboard is self-contained and works offline (`file://`). When served over `http(s)` it reads
the editable JSON in `data/`; offline it falls back to an embedded copy of that data baked into the
file. To serve locally so edits to `data/*.json` are picked up live:

```bash
python3 -m http.server 8000   # then open http://localhost:8000/
```

**GitHub Pages:** enable via *Settings → Pages → Deploy from branch →
`claude/india-smallcap-screener-b6byat` / `(root)`*. The site then lives at
`https://narisree.github.io/Multibagger/` (landing), with the screener and tracker one click away.

---

## Project layout

```
.
├── index.html              # Landing page (links both dashboards; Pages entry point)
├── screener.html           # PHASE 1 selection dashboard (self-contained)
├── tracker.html            # PHASE 2 monitoring dashboard (self-contained)
├── assets/
│   └── scoring.js          # transparent scoring engine (canonical; also embedded in the HTML)
├── data/
│   ├── candidates.json     # PHASE 1 candidate data  ← populate from authorised sources
│   ├── portfolio.json      # PHASE 2 tracked positions ← the stocks you accept
│   ├── paper-trades.json   # ₹50k conviction-weighted paper book (drives the tracker's top panel)
│   └── archive/            # superseded data snapshots (e.g. the prior shortlist)
├── tracking/
│   └── TRACKING.md         # human-readable persistent tracking log
└── docs/
    └── METHODOLOGY.md      # filters, red flags, scoring rubric, sources, tracking process
```

---

## How the scoring works (transparent by design)

Pillar scores are **computed from raw metrics** by `assets/scoring.js`, not typed in by hand — so the
method is reproducible and auditable.

- **Fundamental (0–100):** growth, profitability, balance sheet, cash flow, ownership, valuation,
  structural edge, governance.
- **Technical (0–100):** trend, relative strength, structure/breakout, volume, momentum, 52-wk/base.
- **Composite** = `Fundamental × 0.60 + Technical × 0.40` (weights adjustable live via slider).
- **Conviction:** High ≥ 75 · Medium 60–74 · Watch < 60.

Full rubric and sub-weights: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

You can verify the engine without a browser:
```bash
node -e 'const S=require("./assets/scoring.js"),d=require("./data/candidates.json");
d.candidates.forEach(c=>{const e=S.evaluate(c,d.meta);
console.log(c.ticker,e.fundamentalScore,e.technicalScore,e.composite,e.tier);});'
```

---

## ₹50,000 paper-trading test (conviction-weighted)

The tracker opens with a **₹50,000 paper book** of 5 freshly-screened multibaggers
(`data/paper-trades.json`). It's a measurement tool, not a forecast: it **books the trades now** at
the screen-date price and **marks them to market** as months pass, reporting **realized P&L vs a
Nifty Smallcap benchmark** with a live countdown to a **6-month review (13 Dec 2026)**.

Capital is split by conviction, using the same scoring engine as the screener:

```
weight_i = composite_i / Σ composite        # higher composite → bigger slice
shares_i = floor(50000 · weight_i / buyPrice_i)   # whole shares only
cash     = 50000 − Σ invested_i             # residual stays as cash
```

The current 5 (composite in brackets): **ELECON** (79) · **SKYGOLD** (78) · **SKIPPER** (76) ·
**TIMETECHNO** (65) · **CYIENTDLM** (62). The prior shortlist is archived under
`data/archive/` — nothing is lost. P&L is **realized-not-predicted**: it only becomes meaningful as
the GitHub Actions pipeline fills in real, dated prices. Full method:
[`docs/METHODOLOGY.md §7`](docs/METHODOLOGY.md#7-paper-trading-test-50000-conviction-weighted).

> Not financial advice. Whole-share, no-cost, no-slippage assumptions make the book an approximation
> of a real account.

---

## Live data via Yahoo Finance (optional auto-fill)

`tools/fetch_yahoo.js` populates the data files from Yahoo's public JSON API (no dependencies,
Node 18+). Add a `yahooSymbol` to each record — NSE uses the `.NS` suffix, BSE uses `.BO`
(e.g. `"yahooSymbol": "NESCO.NS"`) — then:

```bash
node tools/fetch_yahoo.js --candidates   # refresh CMP, technicals, ratios in data/candidates.json
node tools/fetch_yahoo.js --portfolio    # daily PHASE 2 update of data/portfolio.json
node tools/fetch_yahoo.js --paper        # mark the ₹50k paper book to market + benchmark level
node tools/embed_data.js                 # re-embed JSON into the HTML offline fallback
```

**Yahoo fills automatically:** CMP, day-change %, ~1y price series, 50/200-DMA flags, RSI(14),
52-week high/low, market cap, P/E, P/B, ROE, debt/equity, margins.

**Yahoo cannot provide (still manual, from AMFI/NSE-BSE/filings):** AMFI cap classification,
promoter holding & **pledge**, ROCE, ASM/GSM/T2T surveillance flags, order book, governance.

> **Environment note:** a restricted dev container (e.g. Claude Code on the web with a GitHub-only
> network policy) blocks every market-data host. The fetcher still runs anywhere with normal
> internet — your laptop, or **GitHub Actions** (below), which is the recommended automated path.

### Official NSE data (tools/fetch_nse.py)

`tools/fetch_nse.py` pulls **official** figures from NSE India via
[BennyThadikaran/NseIndiaApi](https://github.com/BennyThadikaran/NseIndiaApi) (no API key): last
price, P/E, 52-week high/low, and a best-effort **surveillance flag** (ASM/GSM) that feeds the
red-flag check. It keys off each record's NSE `ticker` (e.g. `MARKSANS`). It needs `nseindia.com`
reachable, so it runs in **GitHub Actions** (below), not inside a GitHub-only dev container.

```bash
pip install "git+https://github.com/BennyThadikaran/NseIndiaApi.git" "httpx[http2]"
python tools/fetch_nse.py --candidates
python tools/fetch_nse.py --portfolio
```

The two fetchers are complementary: **Yahoo** gives price history → 50/200-DMA, RSI and ratios;
**NSE** then overwrites CMP / P/E / 52-week / surveillance with the authoritative values.

### Live equity prices via Twelve Data (required for live P&L on GitHub Actions)

Yahoo rate-limits GitHub-Actions IPs (HTTP 429) and NSE serves a **price-stripped** quote to
datacenter IPs (no `lastPrice`), so neither can mark the holdings to market from CI — only the
Nifty Smallcap **benchmark** (NSE index endpoint) comes through. `tools/fetch_twelvedata.py`
fixes this by pulling last prices from [Twelve Data](https://twelvedata.com), which does serve
CI IPs. **One-time setup:**

1. Create a free API key at [twelvedata.com](https://twelvedata.com) (Sign up → API key).
2. Add it to the repo: **Settings → Secrets and variables → Actions → New repository secret**,
   name it **`TWELVEDATA_API_KEY`**, paste the key.
3. Re-run **Update market data** — holdings now mark to market and the paper book shows real P&L.

It refreshes `cmp`/`currentPrice` across `candidates.json`, `portfolio.json` and
`paper-trades.json` in one batched request (free tier is ample for this handful of symbols).
Locally you can run it the same way: `TWELVEDATA_API_KEY=xxxx python tools/fetch_twelvedata.py`.

### Automated daily refresh (GitHub Actions)

`.github/workflows/update-data.yml` runs both fetchers on GitHub-hosted runners — which have full
internet access, so Yahoo and NSE are reachable there even when your local environment is locked
down. It:

1. runs on a weekday schedule (after NSE close) and on manual dispatch (Actions tab → *Run workflow*),
2. refreshes `data/candidates.json`, `data/portfolio.json` and `data/paper-trades.json` (Yahoo
   technicals/prices, then official NSE prices + benchmark level), re-embeds them into the dashboards,
3. commits the changes back to the branch.

With GitHub Pages enabled, your dashboards then update themselves daily with no machine of your own
running. Each record just needs a `yahooSymbol`; records without one are skipped.

## Workflow

### PHASE 1 — build the shortlist
1. Pull the current AMFI classification and the NSE/BSE surveillance lists.
2. For each candidate, fill a record in `data/candidates.json` from the
   [authorised sources](docs/METHODOLOGY.md#0-data-sourcing-reality-read-first) — every numeric value
   carries a `sources` entry with a date.
3. Open `screener.html`. Candidates failing a hard filter or hitting a red flag go in the `excluded`
   list (and show in the "Excluded & why" panel).
4. Review the ranked, tiered table and the per-stock thesis + invalidation triggers.

### PHASE 2 — track daily
1. Move accepted stocks into `data/portfolio.json` and add a position block in
   [`tracking/TRACKING.md`](tracking/TRACKING.md).
2. Each run: update CMP / day-change / since-entry, log dated news, re-check technicals, re-evaluate
   the thesis (Intact/Strengthening/Weakening/Broken), and set a recommendation
   (HOLD / ADD / REDUCE / EXIT). Fired invalidation triggers go in `alerts` and surface loudly in the
   dashboard.
3. **Monthly:** run the methodology review (hit rate, factor attribution, proposed weight/threshold
   changes) — proposed, never silently applied.

---

## Guardrails baked in

- Hard filters: NSE/BSE listed · small/micro only (live AMFI) · CMP < ₹1,000 · ≥ ₹1 cr/day liquidity.
- Red-flag auto-exclusion: ASM/GSM/T2T surveillance · pledge > 25% · manipulation signs · going-concern · chronic negative OCF.
- Sources restricted to authorised/dated origins — never tips, Telegram/WhatsApp, or anonymous forums.
- Persistent "not financial advice" caveat on every view.
