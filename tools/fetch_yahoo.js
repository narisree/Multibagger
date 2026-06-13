#!/usr/bin/env node
/*
 * fetch_yahoo.js — populate the screener's data files from the Yahoo Finance
 * public JSON API. Dependency-free (Node 18+ global fetch).
 *
 *   node tools/fetch_yahoo.js --candidates   # refresh data/candidates.json
 *   node tools/fetch_yahoo.js --portfolio    # refresh data/portfolio.json (daily PHASE 2)
 *
 * Each record must carry a Yahoo symbol, e.g.  "yahooSymbol": "NESCO.NS"
 *   - NSE tickers use the .NS suffix, BSE uses .BO
 *
 * What Yahoo CAN provide (filled automatically):
 *   CMP, day-change %, ~1y price series, 50/200-DMA flags, RSI(14), 52-week
 *   high/low, market cap, trailing P/E, P/B, ROE, debt/equity, margins,
 *   revenue growth.
 *
 * What Yahoo CANNOT provide (leave for manual sourcing — see docs/METHODOLOGY.md):
 *   AMFI cap classification, promoter holding & PLEDGE, ROCE, ASM/GSM/T2T
 *   surveillance flags, order book, governance — these are India-specific and
 *   must come from AMFI / NSE-BSE / company filings.
 *
 * Not financial advice.
 */
'use strict';
const fs = require('fs');
const path = require('path');

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36';
const ROOT = path.join(__dirname, '..');
const today = new Date().toISOString().slice(0, 10);

function die(msg) { console.error('\n' + msg + '\n'); process.exit(1); }

async function getJSON(url) {
  let res;
  try {
    res = await fetch(url, { headers: { 'User-Agent': UA, 'Accept': 'application/json' } });
  } catch (e) {
    if (/allowlist|ENOTFOUND|EAI_AGAIN|getaddrinfo/i.test(String(e))) {
      die('NETWORK BLOCKED: this environment\'s egress allowlist is blocking Yahoo.\n' +
          'Add these hosts to the environment network settings, then re-run:\n' +
          '  query1.finance.yahoo.com\n  query2.finance.yahoo.com\n' +
          'Docs: https://code.claude.com/docs/en/claude-code-on-the-web');
    }
    throw e;
  }
  if (res.status === 403) die('Yahoo returned 403 (egress IP likely rate-limited/blocked by Yahoo). Try query2 host or run from a different network.');
  if (!res.ok) throw new Error('HTTP ' + res.status + ' for ' + url);
  return res.json();
}

// ---- indicators -----------------------------------------------------------
function sma(arr, n) { if (arr.length < n) return null; const s = arr.slice(-n).reduce((a, b) => a + b, 0); return s / n; }
function rsi(closes, period = 14) {
  if (closes.length < period + 1) return null;
  let gain = 0, loss = 0;
  for (let i = closes.length - period; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    if (d >= 0) gain += d; else loss -= d;
  }
  const ag = gain / period, al = loss / period;
  if (al === 0) return 100;
  const rs = ag / al;
  return Math.round(100 - 100 / (1 + rs));
}
function round(x, d = 2) { return x == null ? null : Math.round(x * 10 ** d) / 10 ** d; }

// ---- fetchers -------------------------------------------------------------
async function fetchChart(symbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=1y`;
  const j = await getJSON(url);
  const r = j.chart && j.chart.result && j.chart.result[0];
  if (!r) throw new Error('no chart data for ' + symbol);
  const closesRaw = (r.indicators.quote[0].close || []);
  const closes = closesRaw.filter(v => typeof v === 'number');
  const cmp = closes[closes.length - 1];
  const prev = closes[closes.length - 2];
  const hi = Math.max(...closes), lo = Math.min(...closes);
  const s50 = sma(closes, 50), s200 = sma(closes, 200);
  // ~30-point series for the sparkline (evenly sampled)
  const step = Math.max(1, Math.floor(closes.length / 30));
  const series = closes.filter((_, i) => i % step === 0).slice(-30).map(v => round(v, 2));
  return {
    cmp: round(cmp, 2),
    dayChangePct: prev ? round((cmp - prev) / prev * 100, 2) : null,
    weekHigh52: round(hi, 2), weekLow52: round(lo, 2),
    above50DMA: s50 != null ? cmp > s50 : null,
    above200DMA: s200 != null ? cmp > s200 : null,
    rsi: rsi(closes), priceSeries: series,
    currency: r.meta && r.meta.currency
  };
}

async function fetchFundamentals(symbol) {
  const mods = 'summaryDetail,defaultKeyStatistics,financialData';
  const url = `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(symbol)}?modules=${mods}`;
  let j;
  try { j = await getJSON(url); } catch (e) { return null; } // fundamentals optional
  const r = j.quoteSummary && j.quoteSummary.result && j.quoteSummary.result[0];
  if (!r) return null;
  const sd = r.summaryDetail || {}, ks = r.defaultKeyStatistics || {}, fd = r.financialData || {};
  const raw = o => (o && typeof o.raw === 'number') ? o.raw : null;
  const mc = raw(sd.marketCap) || raw(ks.enterpriseValue);
  return {
    marketCapCr: mc != null ? round(mc / 1e7, 0) : null, // INR -> crore
    pe: round(raw(sd.trailingPE), 1),
    pb: round(raw(ks.priceToBook), 2),
    roe: raw(fd.returnOnEquity) != null ? round(raw(fd.returnOnEquity) * 100, 1) : null,
    debtEquity: raw(fd.debtToEquity) != null ? round(raw(fd.debtToEquity) / 100, 2) : null,
    npm: raw(fd.profitMargins) != null ? round(raw(fd.profitMargins) * 100, 1) : null,
    opm: raw(fd.operatingMargins) != null ? round(raw(fd.operatingMargins) * 100, 1) : null,
    revCagr3y: raw(fd.revenueGrowth) != null ? round(raw(fd.revenueGrowth) * 100, 1) : null // proxy: latest YoY, not 3y
  };
}

// ---- updaters -------------------------------------------------------------
function addSource(rec, note) {
  rec.sources = rec.sources || [];
  const label = 'Yahoo Finance (' + (rec.yahooSymbol || '') + ')';
  rec.sources = rec.sources.filter(s => !String(s.label).startsWith('Yahoo Finance'));
  rec.sources.push({ label, url: 'https://finance.yahoo.com/quote/' + rec.yahooSymbol, date: today, note });
}

async function updateCandidates() {
  const file = path.join(ROOT, 'data', 'candidates.json');
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  let n = 0;
  for (const c of data.candidates || []) {
    if (!c.yahooSymbol) { console.log(`- ${c.ticker}: no yahooSymbol, skipped`); continue; }
    const ch = await fetchChart(c.yahooSymbol);
    c.cmp = ch.cmp;
    c.technicals = Object.assign({}, c.technicals, {
      above50DMA: ch.above50DMA, above200DMA: ch.above200DMA, rsi: ch.rsi,
      weekHigh52: ch.weekHigh52, weekLow52: ch.weekLow52
    });
    c.priceSeries = ch.priceSeries;
    const f = await fetchFundamentals(c.yahooSymbol);
    if (f) {
      c.fundamentals = Object.assign({}, c.fundamentals);
      for (const k of ['marketCapCr', 'pe', 'pb', 'roe', 'debtEquity', 'npm', 'opm']) if (f[k] != null) {
        if (k === 'marketCapCr') c.marketCapCr = f[k]; else c.fundamentals[k] = f[k];
      }
    }
    c.illustrative = false;
    addSource(c, 'CMP, technicals & market ratios (auto). India-specific fields still need manual sourcing.');
    console.log(`✓ ${c.ticker} (${c.yahooSymbol}): CMP ₹${ch.cmp}, RSI ${ch.rsi}, >50DMA ${ch.above50DMA}, >200DMA ${ch.above200DMA}`);
    n++;
  }
  data.meta = data.meta || {};
  data.meta.screenDate = today;
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
  console.log(`\nUpdated ${n} candidate(s) -> data/candidates.json`);
  console.log('Reminder: re-embed into index.html with  node tools/embed_data.js');
}

async function updatePortfolio() {
  const file = path.join(ROOT, 'data', 'portfolio.json');
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  let n = 0;
  for (const p of data.positions || []) {
    if (!p.yahooSymbol) { console.log(`- ${p.ticker}: no yahooSymbol, skipped`); continue; }
    const ch = await fetchChart(p.yahooSymbol);
    p.cmp = ch.cmp; p.dayChangePct = ch.dayChangePct; p.priceSeries = ch.priceSeries;
    p.illustrative = false;
    const since = p.entryPrice ? ((ch.cmp - p.entryPrice) / p.entryPrice * 100) : null;
    console.log(`✓ ${p.ticker}: CMP ₹${ch.cmp} (${ch.dayChangePct >= 0 ? '+' : ''}${ch.dayChangePct}% today, ${since != null ? (since >= 0 ? '+' : '') + since.toFixed(1) + '% since entry' : '—'})`);
    n++;
  }
  data.meta = data.meta || {};
  data.meta.lastUpdated = today;
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n');
  console.log(`\nUpdated ${n} position(s) -> data/portfolio.json`);
  console.log('Reminder: re-embed into tracker.html with  node tools/embed_data.js');
}

(async () => {
  const mode = process.argv[2];
  if (mode === '--candidates') await updateCandidates();
  else if (mode === '--portfolio') await updatePortfolio();
  else die('Usage: node tools/fetch_yahoo.js [--candidates|--portfolio]');
})().catch(e => die('ERROR: ' + (e && e.message || e)));
