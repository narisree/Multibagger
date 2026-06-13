#!/usr/bin/env node
/*
 * embed_data.js — re-inject the JSON data files into each dashboard's embedded
 * data island(s), so the self-contained HTML keeps working offline (file://) with
 * the latest data. Run after the fetchers or any manual edit to data/*.json.
 *
 *   node tools/embed_data.js
 *
 * A dashboard can host MORE THAN ONE island, each addressed by its id:
 *   screener.html <- data/candidates.json            (island id="embedded-data")
 *   tracker.html  <- data/portfolio.json             (island id="embedded-data")
 *                 <- data/paper-trades.json          (island id="paper-data")
 */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const pairs = [
  { html: 'screener.html', json: 'data/candidates.json', islandId: 'embedded-data' },
  { html: 'tracker.html', json: 'data/portfolio.json', islandId: 'embedded-data' },
  { html: 'tracker.html', json: 'data/paper-trades.json', islandId: 'paper-data' }
];

function islandRE(id) {
  return new RegExp('(<script id="' + id + '" type="application/json">)([\\s\\S]*?)(</script>)');
}

for (const p of pairs) {
  const htmlPath = path.join(ROOT, p.html);
  const jsonPath = path.join(ROOT, p.json);
  const json = fs.readFileSync(jsonPath, 'utf8').trim();
  JSON.parse(json); // validate before embedding
  let html = fs.readFileSync(htmlPath, 'utf8');
  const RE = islandRE(p.islandId);
  if (!RE.test(html)) { console.error(`! ${p.html}: island id="${p.islandId}" not found, skipped`); continue; }
  html = html.replace(RE, `$1\n${json}\n$3`);
  fs.writeFileSync(htmlPath, html);
  console.log(`✓ embedded ${p.json} (${json.length} bytes) into ${p.html} [#${p.islandId}]`);
}
console.log('Done.');
