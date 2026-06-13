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

## Paper Portfolio — ₹50,000 (started 2026-06-13, review 2026-12-13)
Conviction-weighted across the fresh-5 screen. Realized mark-to-market; not a forecast. Lives in
`../data/paper-trades.json`, shown in `../tracker.html`. Buy prices are June-2026 snapshots,
re-executed at real prices on the first live fetch.

| Pick | Conviction | Composite | Weight | Buy ₹ (prov.) | Shares | Invested ₹ |
|---|---|---|---|---|---|---|
| SKYGOLD | High | 78 | 24.2% | 513.05 | 23 | 11,800 |
| SKIPPER | Medium | 73 | 22.7% | 572.70 | 19 | 10,881 |
| ELECON | Medium | 66 | 20.5% | 510.00 | 20 | 10,200 |
| CYIENTDLM | Watch | 54 | 16.8% | 452.00 | 18 | 8,136 |
| TIMETECHNO | Watch | 51 | 15.8% | 167.00 | 47 | 7,849 |

Invested ₹48,866 · Cash ₹1,134 · Capital ₹50,000. Benchmark: Nifty Smallcap 250 (set on first fetch).

## Fresh-5 screen (2026-06-13)
The current screener shortlist is the five above. Excluded by guardrails: TRITURBINE (ASM),
ZENTEC & AETHER (CMP > ₹1,000), DCXINDIA (loss-making), TARIL (pledge), INOXWIND (promoters selling).

## Archived prior screen (2026-06-13, original 6)
MARKSANS (tracked, above) · HBLENGINE · MAHSEAMLES · CONTROLPR · GOLDIAM · IONEXCHANG.
Saved at `../data/archive/candidates-2026-06-13-original6.json`.

---

## Methodology-review log

| Date | Hit rate (up / down / broken) | What worked | What misled | Proposed change (pending approval) |
|---|---|---|---|---|
| — | — | — | — | — |
