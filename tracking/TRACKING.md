# Tracked Portfolio — Persistent Log

> **Not financial advice.** High-risk segment. Flag bad news loudly; surface invalidation triggers.
> This file is the human-readable source of truth; `../data/portfolio.json` drives `../tracker.html`.

**Last updated:** 2026-06-13 · **Positions:** 1

---

## Positions

### MARKSANS — Marksans Pharma Ltd  ·  Pharmaceuticals (Generics / CMO)
| Field | Value |
|---|---|
| Entry date | 2026-06-13 |
| Entry price | ₹253.86 |
| Scores at entry (F / T / Composite) | 73 / 89 / 79 |
| Conviction tier at entry | High |
| Thesis (summary) | Debt-free, vertically integrated generics maker (US/UK/Australia OTC + Rx) with in-house CMO; ROCE ~22.5%, PAT +64% YoY (Q4 FY26), confirmed uptrend (golden cross). USFDA approvals widening the basket. |
| Invalidation triggers | Adverse USFDA action (warning letter/import alert) · OPM contraction >300bps for two quarters · debt-funded M&A pushing D/E > 0.5 · decisive close below the 200-DMA. |

**Daily log**
| Date | CMP | Today % | Since entry | Notes (dated source) | Technicals | Thesis | Reco |
|---|---|---|---|---|---|---|---|
| 2026-06-13 | ₹257.25 | +2.9%* | +1.3% | Latest available 11 Jun: +2.9% on a **block deal**; USFDA final approval for Benzonatate ANDA (positive, in-thesis). *=11 Jun session. (Web aggregators, 11 Jun 2026) | >50-DMA (206) & >200-DMA (235); RSI ~60; golden cross intact | Intact | HOLD |
| 2026-06-13 | ₹253.86 | — | 0.0% | Entry. No new filings/flags. (NSE/Screener, 10 Jun 2026 data) | >50-DMA (206) & >200-DMA (235); RSI ~60; golden cross | Intact | HOLD |

---

## Paper-trading ledger — ₹50,000 conviction-weighted (booked 2026-06-13)

> A measurement experiment, not advice. Trades are **booked now** at the screen-date price and
> **marked to market** as months pass. P&L is **realized-not-predicted**. Benchmark: Nifty Smallcap
> 250. **6-month review: 2026-12-13.** Drives the top panel of `../tracker.html` via
> `../data/paper-trades.json`. Weights = composite ÷ Σcomposite (Σ = 360); shares = floor(50000·w/buy).

| # | Ticker | Conviction | Composite | Weight | Buy ₹ | Shares | Invested ₹ |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | ELECON | High | 79 | 21.9% | 510.00 | 21 | 10,710.00 |
| 2 | SKYGOLD | High | 78 | 21.7% | 490.00 | 22 | 10,780.00 |
| 3 | SKIPPER | High | 76 | 21.1% | 572.70 | 18 | 10,308.60 |
| 4 | TIMETECHNO | Medium | 65 | 18.1% | 175.00 | 51 | 8,925.00 |
| 5 | CYIENTDLM | Medium | 62 | 17.2% | 452.00 | 19 | 8,588.00 |
| | **Total invested** | | | | | | **49,311.60** |
| | **Cash (residual)** | | | | | | **688.40** |
| | **Starting capital** | | | | | | **50,000.00** |

Buy prices are provisional CMP at 13 Jun 2026; the GitHub Actions pipeline overwrites `currentPrice`
and the benchmark level so the book becomes live. At the 6-month review, record realized P&L vs the
benchmark per name and in aggregate in the methodology-review log below.

**Paper-book review log**
| Date | Portfolio value | Total P&L (₹ / %) | Benchmark return | Notes |
|---|---|---|---|---|
| 2026-06-13 | ₹50,000 (entry) | ₹0 / 0.0% | 0.0% (baseline) | Book opened; awaiting first live mark from the Actions pipeline. |

---

## How to use this file

1. **On accepting a stock**, add a position block (entry date, price, scores, tier, thesis,
   invalidation triggers) and a mirror entry in `../data/portfolio.json`.
2. **Each tracking run**, append a dated row to the daily log and update the JSON (CMP,
   `dayChangePct`, `thesisStatus`, `recommendation`, `alerts`, `priceSeries`). The GitHub Actions
   pipeline auto-refreshes prices/technicals from Yahoo + official NSE.
3. **When an invalidation trigger fires**, add it to that position's `alerts` array and set
   `thesisStatus: "Broken"` with `recommendation: "EXIT-thesis-broken"`.
4. **Monthly review**: record hit-rate, factor attribution, and proposed (not yet applied)
   methodology changes below.

---

## Fresh screen (2026-06-13) — the paper book's 5 picks
ELECON (High 79) · SKYGOLD (High 78) · SKIPPER (High 76) · TIMETECHNO (Medium 65) · CYIENTDLM (Medium 62).
All 5 pass the hard filters with no red flags and seed the ₹50,000 paper book above.
Excluded by guardrails: TRITURBINE (ASM surveillance), ZENTEC & AETHER (CMP > ₹1,000),
DCXINDIA (FY26 net loss), TARIL (pledge > 25%), INOXWIND (promoter stake cut / WC stress),
BORORENEW (elevated debt / rights issue). See `../screener.html` → "Excluded & why".

> **Prior shortlist archived.** The earlier screen (MARKSANS, HBLENGINE, CONTROLPR, GOLDIAM,
> MAHSEAMLES, IONEXCHANG) is preserved at `../data/archive/candidates-2026-06-13.json` — nothing
> lost. **MARKSANS** remains independently tracked as an accepted position above.

---

## Methodology-review log

| Date | Hit rate (up / down / broken) | What worked | What misled | Proposed change (pending approval) |
|---|---|---|---|---|
| — | — | — | — | — |
