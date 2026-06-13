#!/usr/bin/env node
/*
 * embed_data.js — re-inject the JSON data files into each dashboard's embedded
 * data island, so the self-contained HTML keeps working offline (file://) with
 * the latest data. Run after fetch_yahoo.js or any manual edit to data/*.json.
 *
 *   node tools/embed_data.js
 *
 * Pairs: screener.html <- data/candidates.json ; tracker.html <- data/portfolio.json
 */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const pairs = [
  { html: 'screener.html', json: 'data/candidates.json' },
  { html: 'tracker.html', json: 'data/portfolio.json' }
];

const RE = /(<script id="embedded-data" type="application\/json">)([\s\S]*?)(<\/script>)/;

for (const p of pairs) {
  const htmlPath = path.join(ROOT, p.html);
  const jsonPath = path.join(ROOT, p.json);
  const json = fs.readFileSync(jsonPath, 'utf8').trim();
  JSON.parse(json); // validate before embedding
  let html = fs.readFileSync(htmlPath, 'utf8');
  if (!RE.test(html)) { console.error(`! ${p.html}: embedded-data island not found, skipped`); continue; }
  html = html.replace(RE, `$1\n${json}\n$3`);
  fs.writeFileSync(htmlPath, html);
  console.log(`✓ embedded ${p.json} (${json.length} bytes) into ${p.html}`);
}
console.log('Done.');
