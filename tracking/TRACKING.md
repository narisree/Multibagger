# Tracked Portfolio — Persistent Log

> **Not financial advice.** High-risk segment. Flag bad news loudly; surface invalidation triggers.
> This file is the human-readable source of truth; `../data/portfolio.json` drives `../tracker.html`.
> Keep them in sync.

**Last updated:** 2026-06-13 (illustrative)

---

## Positions

### DEMO-1 — Illustrative Forgings Ltd  *(illustrative placeholder — replace)*
| Field | Value |
|---|---|
| Entry date | 2026-06-13 |
| Entry price | ₹412.50 |
| Scores at entry (F / T / Composite) | 78 / 72 / 76 |
| Conviction tier at entry | High |
| Thesis (summary) | Import-substitution + EV content growth in precision forgings; capacity doubling against a >2x revenue order book. |
| Invalidation triggers | Two quarters of OPM contraction >300bps · order book < 1x revenue · promoter pledge appears · close below 200-DMA on rising volume. |

**Daily log**
| Date | CMP | Today % | Since entry | Notes (dated source) | Technicals | Thesis | Reco |
|---|---|---|---|---|---|---|---|
| 2026-06-13 | ₹418.00 | +1.3% | +1.3% | Demo entry — no real news. | Above 50/200-DMA; RSI 61 | Intact | HOLD |

---

## How to use this file

1. **On accepting a stock from PHASE 1**, add a position block: entry date, entry price, the three
   scores, tier, thesis summary, and the explicit invalidation triggers.
2. **Each tracking run**, append a dated row to that stock's daily log and update the mirror entry in
   `../data/portfolio.json` (CMP, `dayChangePct`, `thesisStatus`, `recommendation`, `alerts`,
   `priceSeries`).
3. **When an invalidation trigger fires**, add it to that position's `alerts` array in the JSON so it
   shows in the dashboard's alerts panel, and set `thesisStatus: "Broken"` with
   `recommendation: "EXIT-thesis-broken"`.
4. **Periodic review** (monthly): record hit-rate, factor attribution, and any *proposed* (not yet
   applied) methodology changes in the section below.

---

## Methodology-review log

| Date | Hit rate (up / down / broken) | What worked | What misled | Proposed change (pending approval) |
|---|---|---|---|---|
| — | — | — | — | — |
