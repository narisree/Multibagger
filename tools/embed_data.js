#!/usr/bin/env node
/*
 * embed_data.js — re-inject JSON data files into each dashboard's embedded
 * data island(s), so the self-contained HTML keeps working offline (file://)
 * with the latest data. Run after the fetchers or any manual edit to data/*.json.
 *
 *   node tools/embed_data.js
 *
 * A file may hold multiple islands, each keyed by a unique id:
 *   screener.html <- candidates.json            (id="embedded-data")
 *   tracker.html  <- portfolio.json             (id="embedded-data")
 *                 <- paper-trades.json          (id="paper-data")
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

function islandRegex(id) {
  return new RegExp(`(<script id="${id}" type="application/json">)([\\s\\S]*?)(</script>)`);
}

for (const p of pairs) {
  const htmlPath = path.join(ROOT, p.html);
  const json = fs.readFileSync(path.join(ROOT, p.json), 'utf8').trim();
  JSON.parse(json); // validate before embedding
  let html = fs.readFileSync(htmlPath, 'utf8');
  const re = islandRegex(p.islandId);
  if (!re.test(html)) { console.error(`! ${p.html}: island id="${p.islandId}" not found, skipped`); continue; }
  // Replacement function (not a string) so `$` sequences in the JSON (e.g. "$145bn") aren't
  // interpreted as capture-group references.
  html = html.replace(re, (_m, open, _body, close) => `${open}\n${json}\n${close}`);
  fs.writeFileSync(htmlPath, html);
  console.log(`✓ embedded ${p.json} (${json.length} bytes) into ${p.html} [#${p.islandId}]`);
}
console.log('Done.');
