# Methodology — Small/Micro-Cap Multibagger Screener

> **Not financial advice.** Small- and micro-caps are the highest-risk segment of the Indian
> market: illiquid, volatile, and capable of going to near-zero. This is a research aid. Capital
> risk and all decisions are the user's own.

This document is the single source of truth for *how* the screen works: the filters, the scoring
rubric, the data fields, and the daily/periodic tracking process. The dashboards
(`screener.html`, `tracker.html`) implement exactly what is described here, and the scoring engine in
`assets/scoring.js` computes the pillar scores from the raw inputs (so scores are reproducible and
auditable, not hand-typed).

---

## 0. Data-sourcing reality (read first)

This repository ships with **illustrative placeholder data** (fictional `DEMO-*` tickers) so the
dashboards render and every feature is visible. Those numbers are invented and are **not** real
analysis of any real company.

When this screen was built, automated fetching of the authorised live-data aggregators
(Screener.in, Tickertape, Moneycontrol) returned **HTTP 403 / blocked** — they do not allow
programmatic scraping. A rigorous screen therefore requires a human (or a data feed/API you are
licensed to use) to populate `data/candidates.json` from the authorised sources below. Do **not**
let the dashboard invent numbers; every value must trace to a cited, dated source.

### Authorised sources (cite each, with the date pulled)
| Field group | Where to get it |
|---|---|
| Market-cap **classification** (large/mid/small) | [AMFI half-yearly list](https://www.amfiindia.com/research-information/other-data/categorization-of-stocks) — top 100 = large, 101–250 = mid, 251+ = small/micro |
| CMP, market cap, 52-week range, delivery/volume | [NSE](https://www.nseindia.com/) / [BSE](https://www.bseindia.com/) official quote pages |
| **Surveillance** flags (ASM/GSM/T2T) | [NSE ASM report](https://www.nseindia.com/reports/asm), [NSE GSM](https://www.nseindia.com/reports/gsm), BSE surveillance |
| Fundamentals, ratios, shareholding, pledge | Company **annual reports & investor presentations**, [Screener.in](https://www.screener.in/), Trendlyne, Tijori |
| Credit / leverage view | CRISIL / ICRA / CARE rating rationales |
| Macro / sector tailwind | RBI, government / ministry data, SEBI filings |

**Never** use stock tips, Telegram/WhatsApp calls, anonymous forums, or unverifiable sources.
If data is stale or conflicting, say so in the `sources` note rather than guessing. If data quality
is insufficient for a stock, **drop it** and record why in the `excluded` list.

---

## 1. Universe & hard filters (all must hold)

A candidate is only eligible if **every** filter passes:

1. **Listed** on NSE and/or BSE.
2. **Cap category = small or micro only.** Exclude large- and mid-cap. Use the *current* AMFI
   classification (rank 251+). Do not hardcode an old market-cap cutoff — refetch each screen.
3. **CMP < ₹1,000** (default ceiling, adjustable in the dashboard config).
4. **Liquidity floor:** 30-session average daily traded value **> ₹1 crore/day** (default,
   adjustable). This is the single biggest practical risk in micro-caps — a winner you cannot exit
   is worthless. Raise the floor to be safer.

## 2. Red-flag exclusions (drop if ANY are true)

- Under exchange **surveillance**: ASM, GSM, or Trade-to-Trade (T2T).
- **Promoter pledging high** (> 25% of promoter holding, default) or rising sharply.
- Frequent **circuit hits** / signs of manipulation / unexplained volume spikes with no
  fundamental basis.
- **Going-concern** doubts, auditor qualifications/resignations, or pending SEBI action.
- **Persistently negative operating cash flow** with no credible path to positive.

The dashboard's "Excluded & why" panel exists to prove the guardrails fired.

---

## 3. Scoring rubric

Each pillar is scored 0–100 as a **weighted sum of sub-components**, each sub-component mapped to
0–100 by the functions in `assets/scoring.js`. The exact weights:

### Fundamental pillar (default sub-weights)
| Component | Weight | Driven by |
|---|---:|---|
| Growth | 20% | 3-yr revenue & PAT CAGR, adjusted for growth quality (organic vs one-off) |
| Profitability | 20% | ROCE (anchor), ROE, margin trend |
| Balance sheet | 15% | Debt/Equity (lower better), interest coverage, working-capital trend |
| Cash flow | 15% | OCF positive?, OCF/PAT (earnings quality) |
| Ownership | 10% | Promoter holding & trend, pledge (penalty), institutional entry |
| Valuation | 10% | PEG (primary), P/E sanity vs growth |
| Structural edge | 5% | Qualitative 0–100: moat / TAM / order book / policy tailwind |
| Governance | 5% | Qualitative 0–100: track record, related-party, capital allocation |

### Technical pillar (default sub-weights)
| Component | Weight | Driven by |
|---|---:|---|
| Trend | 25% | Price vs 50-DMA & 200-DMA, higher-highs structure |
| Relative strength | 20% | vs Nifty Smallcap index and vs sector |
| Structure | 20% | Proximity to a clean breakout; cushion above key support |
| Volume | 15% | Accumulation / volume confirming the move |
| Momentum | 10% | RSI (sweet spot ~50–68, overbought penalised), MACD |
| 52-week / base | 10% | Position in 52-wk range, base-formation quality |

### Composite & conviction tiers
```
Composite = Fundamental × wF + Technical × wT     (default wF = 0.60, wT = 0.40)
```
- **High** conviction: composite ≥ 75 (actionable)
- **Medium**: 60–74 (actionable, smaller size)
- **Watch**: < 60 (list but flag as *not actionable*)

Weights are adjustable live via the slider in `screener.html`; the defaults and tier cutoffs live in
`data/candidates.json → meta`.

### Adjustable knobs (and the trade-off when you move them)
- **Pillar weights** — momentum traders raise technical weight; long-term compounders raise
  fundamental weight.
- **Liquidity floor** — raise it to reduce exit risk (the dominant micro-cap hazard).
- **ROCE / Debt thresholds** — the rubric prefers ROCE > 15% and D/E < 1. Relax for genuine
  early-stage high-growth names, but the score will (correctly) dock them — flag the trade-off in
  the thesis when you do.

---

## 4. Multibagger thesis (required per stock)

Every shortlisted stock must carry:
- **Core "why now"** — the structural reason it could re-rate multi-fold.
- **Catalysts + horizon** — specific events and a rough timeframe.
- **What must go right** — the assumptions the thesis depends on.
- **Key risks.**
- **Invalidation triggers** — the explicit, pre-committed conditions that mean *exit / abandon
  thesis*. These are surfaced loudly in the PHASE 2 alerts panel.

No invalidation triggers → the stock is not done and should not enter the tracked book.

---

## 5. PHASE 2 — daily tracking & periodic review

**Tracking files:** `tracking/TRACKING.md` (human-readable log, source of truth) and
`data/portfolio.json` (drives `tracker.html`). Keep them in sync.

### Daily update (per tracked stock)
1. Update CMP, day-change %, and % move since entry.
2. Note any news / results / filings / rating actions / promoter or pledge changes / new
   surveillance flags since the last check (with dated sources).
3. Re-check technicals: trend vs 50/200-DMA, RSI, volume.
4. Re-evaluate the thesis: **Intact / Strengthening / Weakening / Broken**, and whether any
   invalidation trigger has fired.
5. Recommend: **HOLD / ADD-on-strength / REDUCE / EXIT-thesis-broken** (with the reason).
6. Surface fired triggers and red flags in the **alerts panel** — flag, don't bury, bad news.

### Periodic methodology review (monthly is more honest than daily for judging the *method*)
- **Hit rate:** how many calls are up vs down vs thesis-broken.
- **Factor attribution:** which factors actually predicted winners vs which were noise.
- **Scoring errors:** where a pillar was over/under-weighted or a signal misled.
- **Proposed changes:** concrete, evidence-backed adjustments to filters / weights / thresholds for
  the *next* selection round.
- **Do not silently change the method** — present proposed changes for approval first.

---

## 6. Data schema (per candidate)

See `data/candidates.json` for the full shape. Key objects: `hardFilters`, `redFlags`,
`fundamentals` (raw metrics → scored), `technicals` (raw signals → scored), `thesis`, `sources`,
plus `priceSeries` for the sparkline. The top-level `excluded` array records guardrail rejections.
The scoring engine reads the raw metrics and computes `fundamentalScore`, `technicalScore`,
`composite`, and `tier` — you do not type the scores by hand.

---

## 7. Paper-trading test (₹50,000, conviction-weighted)

`data/paper-trades.json` drives a small **paper-trading experiment** shown at the top of
`tracker.html`. It exists to answer, honestly, *"how would these picks have done?"* — not to
predict a number.

**What it is — and what it is not.** The book **books the trades now** (at the screen-date CMP) and
**marks them to market** as the months pass. It reports **realized P&L vs a Nifty Smallcap
benchmark** and a live countdown to a **6-month review date (2026-12-13)**. It does **not** forecast a
future value; the headline figure only becomes meaningful as real, dated prices arrive via the
GitHub Actions pipeline.

**Conviction weighting (computed, not hand-set).** Capital is allocated in proportion to each pick's
composite score from the same `assets/scoring.js` engine used by the screener:

```
weight_i  = composite_i / Σ composite
shares_i  = floor(startingCapital · weight_i / buyPrice_i)   # whole shares only
cash      = startingCapital − Σ invested_i                    # residual, uninvested
```

Higher-composite (higher-conviction) names get a larger slice; the leftover that doesn't buy a whole
share stays as cash. Because the composites cluster, the weights come out *roughly* even — which is
the point: a transparent, reproducible rule, not a discretionary bet size.

**Marking to market.** `tools/fetch_yahoo.js --paper` (then `tools/fetch_nse.py --paper` as the
authoritative overwrite) refreshes each holding's `currentPrice` and the benchmark index level on the
same schedule as the rest of the data. Per-holding value, P&L (₹ and %), the portfolio total, and the
benchmark return are all computed in the dashboard from those marks. The benchmark's `startLevel` is
re-baselined to the first live fetch (while `startProvisional` is true) so the comparison starts from
a real, dated level.

**At the 6-month review (2026-12-13):** record realized P&L vs the benchmark per name and in
aggregate, attribute winners/losers to factors, and fold the lessons into the methodology-review log —
the same *propose-don't-silently-apply* discipline as the rest of the method.

> The paper book is a measurement tool, not advice. Whole-share, no-cost, no-slippage assumptions
> mean it is an approximation of a real account.
