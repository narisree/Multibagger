/*
 * scoring.js — transparent scoring engine for the Multibagger screener.
 *
 * Pillar scores are COMPUTED from raw metrics (not hand-entered), so the
 * method is auditable and reproducible. Each pillar is a weighted sum of
 * sub-components, every sub-component mapped to 0-100.
 *
 * This file is the canonical source. The dashboards embed a copy inline so
 * each HTML file stays self-contained and works offline.
 *
 * Not financial advice.
 */
(function (global) {
  'use strict';

  // ---- small helpers ----------------------------------------------------
  function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

  // Linear ramp: value v mapped so that v<=lo -> 0, v>=hi -> 100 (or reversed).
  function ramp(v, lo, hi) {
    if (hi === lo) return v >= hi ? 100 : 0;
    return clamp(((v - lo) / (hi - lo)) * 100, 0, 100);
  }
  function rampDown(v, lo, hi) { // lower is better: v<=lo -> 100, v>=hi -> 0
    return 100 - ramp(v, lo, hi);
  }
  function bool(b, yes, no) { return b ? yes : (no === undefined ? 0 : no); }
  function num(x, d) { return (typeof x === 'number' && !isNaN(x)) ? x : (d || 0); }

  // ---- FUNDAMENTAL pillar (weights sum to 1.0) --------------------------
  var F_WEIGHTS = {
    growth: 0.20, profitability: 0.20, balanceSheet: 0.15, cashFlow: 0.15,
    ownership: 0.10, valuation: 0.10, structuralEdge: 0.05, governance: 0.05
  };

  function fundamentalComponents(f) {
    f = f || {};
    // Growth: blend of revenue and PAT CAGR (0% -> 0, 35%+ -> 100), adjust for quality.
    var growthRaw = (ramp(num(f.revCagr3y), 0, 35) * 0.5) + (ramp(num(f.patCagr3y), 0, 40) * 0.5);
    var growth = growthRaw * (0.6 + 0.4 * (num(f.growthQuality, 60) / 100));

    // Profitability: ROCE (15->60, 30->100 with floor), ROE, margin trend bonus.
    var roceScore = ramp(num(f.roce), 8, 30);
    var roeScore = ramp(num(f.roe), 8, 28);
    var marginBonus = f.marginTrend === 'rising' ? 100 : (f.marginTrend === 'falling' ? 40 : 70);
    var profitability = roceScore * 0.5 + roeScore * 0.3 + marginBonus * 0.2;

    // Balance sheet: debt/equity (lower better) + interest coverage + WC trend.
    var deScore = rampDown(num(f.debtEquity), 0.0, 1.5); // <=0 ->100, >=1.5 ->0
    var icScore = ramp(num(f.interestCoverage), 1, 10);
    var wcScore = f.workingCapitalTrend === 'rising' ? 45 : (f.workingCapitalTrend === 'falling' ? 90 : 70);
    var balanceSheet = deScore * 0.55 + icScore * 0.30 + wcScore * 0.15;

    // Cash flow: must be positive; OCF/PAT quality.
    var cashFlow = f.ocfPositive ? (40 + ramp(num(f.ocfToPat), 0.3, 1.0) * 0.6) : 10;

    // Ownership: promoter level, trend, pledge (penalty), institutional entry.
    var promLevel = ramp(num(f.promoterHolding), 25, 70);
    var trendBonus = f.promoterTrend === 'rising' ? 100 : (f.promoterTrend === 'falling' ? 30 : 65);
    var pledgePenalty = rampDown(num(f.pledge), 0, 25); // 0% ->100, >=25% ->0
    var instBonus = bool(f.instEntry, 100, 50);
    var ownership = promLevel * 0.35 + trendBonus * 0.25 + pledgePenalty * 0.25 + instBonus * 0.15;

    // Valuation: PEG primary (1.0 ~ fair), PE sanity.
    var pegScore = f.peg ? rampDown(num(f.peg), 0.5, 2.5) : 50; // <=0.5 ->100, >=2.5 ->0
    var peScore = rampDown(num(f.pe), 10, 60);
    var valuation = pegScore * 0.6 + peScore * 0.4;

    // Qualitative inputs (0-100 already).
    var structuralEdge = clamp(num(f.structuralEdgeScore, 50), 0, 100);
    var governance = clamp(num(f.governanceScore, 50), 0, 100);

    return {
      growth: clamp(growth, 0, 100),
      profitability: clamp(profitability, 0, 100),
      balanceSheet: clamp(balanceSheet, 0, 100),
      cashFlow: clamp(cashFlow, 0, 100),
      ownership: clamp(ownership, 0, 100),
      valuation: clamp(valuation, 0, 100),
      structuralEdge: structuralEdge,
      governance: governance
    };
  }

  function fundamentalScore(f) {
    var c = fundamentalComponents(f);
    var s = 0;
    for (var k in F_WEIGHTS) s += c[k] * F_WEIGHTS[k];
    return Math.round(s);
  }

  // ---- TECHNICAL pillar (weights sum to 1.0) ----------------------------
  var T_WEIGHTS = {
    trend: 0.25, relativeStrength: 0.20, structure: 0.20, volume: 0.15,
    momentum: 0.10, positioning: 0.10
  };

  function rsScore(v) {
    return v === 'outperform' ? 100 : (v === 'inline' ? 60 : 20);
  }

  function technicalComponents(t) {
    t = t || {};
    // Trend: above 50/200-DMA and higher-highs structure.
    var trend = bool(t.above50DMA, 40, 0) + bool(t.above200DMA, 40, 0) + bool(t.higherHighs, 20, 0);

    // Relative strength: vs smallcap index and vs sector.
    var relativeStrength = rsScore(t.rsVsSmallcap) * 0.6 + rsScore(t.rsVsSector) * 0.4;

    // Structure: proximity to breakout + cushion above support.
    var breakout = bool(t.nearBreakout, 70, 35);
    var supportCushion = (t.keySupport && t.cmp) ? ramp((t.cmp - t.keySupport) / t.cmp * 100, 0, 12) : 50;
    var structure = breakout * 0.6 + supportCushion * 0.4;

    // Volume: accumulation confirmation.
    var volume = bool(t.volumeAccumulation, 100, 45);

    // Momentum: RSI sweet spot (55-65 best, overbought >75 penalised) + MACD.
    var rsi = num(t.rsi, 50);
    var rsiScore;
    if (rsi >= 50 && rsi <= 68) rsiScore = 100;
    else if (rsi < 50) rsiScore = ramp(rsi, 30, 50);
    else rsiScore = rampDown(rsi, 68, 85); // overbought penalty
    var macdScore = t.macd === 'bullish' ? 100 : (t.macd === 'bearish' ? 25 : 60);
    var momentum = rsiScore * 0.6 + macdScore * 0.4;

    // 52-week positioning + base quality.
    var range = (t.weekHigh52 && t.weekLow52 && t.weekHigh52 > t.weekLow52)
      ? (t.cmp - t.weekLow52) / (t.weekHigh52 - t.weekLow52) * 100 : 50;
    // sweet spot: well off the lows but not stretched at the highs
    var posScore = range >= 35 && range <= 85 ? 100 : (range < 35 ? ramp(range, 0, 35) : rampDown(range, 85, 100));
    var positioning = posScore * 0.5 + clamp(num(t.basePatternScore, 50), 0, 100) * 0.5;

    return {
      trend: clamp(trend, 0, 100),
      relativeStrength: clamp(relativeStrength, 0, 100),
      structure: clamp(structure, 0, 100),
      volume: clamp(volume, 0, 100),
      momentum: clamp(momentum, 0, 100),
      positioning: clamp(positioning, 0, 100)
    };
  }

  function technicalScore(t) {
    var c = technicalComponents(t);
    var s = 0;
    for (var k in T_WEIGHTS) s += c[k] * T_WEIGHTS[k];
    return Math.round(s);
  }

  // ---- composite + tiers ------------------------------------------------
  function composite(fScore, tScore, weights) {
    weights = weights || { fundamental: 0.6, technical: 0.4 };
    return Math.round(fScore * weights.fundamental + tScore * weights.technical);
  }

  function tier(compositeScore, tiers) {
    tiers = tiers || { high: 75, medium: 60 };
    if (compositeScore >= tiers.high) return 'High';
    if (compositeScore >= tiers.medium) return 'Medium';
    return 'Watch';
  }

  // ---- hard filters & red flags ----------------------------------------
  function passesHardFilters(c, cfg) {
    cfg = cfg || { liquidityFloorCr: 1.0, cmpCeiling: 1000 };
    var h = c.hardFilters || {};
    var liq = (typeof c.avgDailyValueCr === 'number') ? c.avgDailyValueCr >= cfg.liquidityFloorCr : !!h.liquidityAboveFloor;
    var cmpOk = (typeof c.cmp === 'number') ? c.cmp < cfg.cmpCeiling : !!h.cmpBelow1000;
    return !!(h.listedNSEBSE && h.capSmallOrMicro && cmpOk && liq);
  }

  function redFlagList(c) {
    var r = c.redFlags || {};
    var flags = [];
    if (r.surveillance) flags.push('Under surveillance (ASM/GSM/T2T)');
    if (r.pledgeHigh) flags.push('Promoter pledge high/rising');
    if (r.circuitManipulation) flags.push('Circuit hits / possible manipulation');
    if (r.goingConcern) flags.push('Going-concern / auditor / SEBI issue');
    if (r.negativeOCF) flags.push('Persistently negative operating cash flow');
    return flags;
  }

  function evaluate(c, cfg) {
    cfg = cfg || {};
    var weights = cfg.weights || { fundamental: 0.6, technical: 0.4 };
    var tiers = cfg.tiers || { high: 75, medium: 60 };
    // attach cmp into technicals for support/positioning math
    var t = Object.assign({}, c.technicals, { cmp: c.cmp });
    var fScore = fundamentalScore(c.fundamentals);
    var tScore = technicalScore(t);
    var comp = composite(fScore, tScore, weights);
    return {
      fundamentalScore: fScore,
      technicalScore: tScore,
      fundamentalComponents: fundamentalComponents(c.fundamentals),
      technicalComponents: technicalComponents(t),
      composite: comp,
      tier: tier(comp, tiers),
      passesHardFilters: passesHardFilters(c, cfg),
      redFlags: redFlagList(c)
    };
  }

  var api = {
    F_WEIGHTS: F_WEIGHTS, T_WEIGHTS: T_WEIGHTS,
    fundamentalComponents: fundamentalComponents, fundamentalScore: fundamentalScore,
    technicalComponents: technicalComponents, technicalScore: technicalScore,
    composite: composite, tier: tier,
    passesHardFilters: passesHardFilters, redFlagList: redFlagList,
    evaluate: evaluate
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.MBScoring = api;
})(typeof window !== 'undefined' ? window : this);
