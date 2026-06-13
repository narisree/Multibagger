# Tracked Portfolio — Persistent Log

> **Not financial advice.** High-risk segment. Flag bad news loudly; surface invalidation triggers.
> This file is the human-readable source of truth; `../data/portfolio.json` drives `../tracker.html`.

**Last updated:** 2026-06-13

---

## Positions

_None accepted yet._ The PHASE 1 screen (2026-06-13) produced the shortlist below. When you accept a
name, add a position block here (entry date, entry price, the three scores, tier, thesis summary,
invalidation triggers) and a mirror entry in `../data/portfolio.json`.

### PHASE 1 shortlist awaiting your decision (screen date 2026-06-13)
| Ticker | Name | CMP | Composite | Tier |
|---|---|---|---|---|
| MARKSANS | Marksans Pharma | ₹253.86 | 79 | High |
| HBLENGINE | HBL Engineering | ₹784.05 | 67 | Medium |
| MAHSEAMLES | Maharashtra Seamless | ₹609.80 | 67 | Medium |
| CONTROLPR | Control Print | ₹636.80 | 64 | Medium |
| GOLDIAM | Goldiam International | ₹391.30 | 56 | Watch |
| IONEXCHANG | Ion Exchange (India) | ₹336.60 | 43 | Watch |

Excluded by guardrails: **GENUSPOWER** (promoter pledge ~69%), **NESCO** & **POCL** (CMP > ₹1,000).

---

## How to use this file

1. **On accepting a stock**, add a position block: entry date, entry price, scores at entry, tier,
   thesis summary, and explicit invalidation triggers.
2. **Each tracking run**, append a dated row to that stock's daily log and update the mirror entry in
   `../data/portfolio.json` (CMP, `dayChangePct`, `thesisStatus`, `recommendation`, `alerts`,
   `priceSeries`). The GitHub Actions pipeline auto-refreshes prices if a `yahooSymbol` is set.
3. **When an invalidation trigger fires**, add it to that position's `alerts` array and set
   `thesisStatus: "Broken"` with `recommendation: "EXIT-thesis-broken"`.
4. **Monthly review**: record hit-rate, factor attribution, and proposed (not yet applied)
   methodology changes below.

---

## Methodology-review log

| Date | Hit rate (up / down / broken) | What worked | What misled | Proposed change (pending approval) |
|---|---|---|---|---|
| — | — | — | — | — |
