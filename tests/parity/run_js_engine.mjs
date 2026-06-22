/**
 * tests/parity/run_js_engine.mjs — run the JS offline-fallback engine
 * against the shared parity fixtures and emit a JSON report.
 *
 *   node tests/parity/run_js_engine.mjs
 *     → prints per-case results, writes tests/parity/js_results.json
 *
 *   node tests/parity/run_js_engine.mjs --compare
 *     → also reads tests/parity/python_results.json and asserts the
 *       under-triage parity rule. Exit code 1 on parity failure.
 *
 * The parity rule:
 *   JS may produce a more acute (lower numerical) level than Python, but it
 *   must NEVER produce a less acute one on a critical case. ESI v5: 1 is the
 *   most acute, 5 is the least acute, so the rule is:
 *
 *       js_level <= python_level + tolerance
 *
 *   A case with `expected_max_level` is also independently asserted on both
 *   engines (both must produce <= expected_max_level).
 */

import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';

import { runOfflineFallbackTriage } from '../../frontend/src/lib/triageEngineOfflineFallback.js';

const here = path.dirname(url.fileURLToPath(import.meta.url));
const fixturePath = path.join(here, 'critical_cases.json');
const jsReportPath = path.join(here, 'js_results.json');
const pyReportPath = path.join(here, 'python_results.json');

const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
const tolerance = Number(fixture.tolerance ?? 0);

const jsResults = fixture.cases.map((c) => {
    const r = runOfflineFallbackTriage(c.input);
    return {
        name: c.name,
        level: r.level,
        category: r.category,
        engine_source: r.engine_source,
        expected_max_level: c.expected_max_level ?? null,
    };
});

fs.writeFileSync(jsReportPath, JSON.stringify({ tolerance, results: jsResults }, null, 2));

const compareMode = process.argv.includes('--compare');
let exitCode = 0;

console.log('JS offline-fallback engine results:');
for (const r of jsResults) {
    console.log(`  · ${r.name.padEnd(40)} → L${r.level}  (${r.category})`);
    if (r.expected_max_level != null && r.level > r.expected_max_level) {
        console.log(`     ✗ exceeds expected_max_level ${r.expected_max_level}`);
        exitCode = 1;
    }
}

if (compareMode) {
    if (!fs.existsSync(pyReportPath)) {
        console.error(`\n[compare] python_results.json not found at ${pyReportPath}.\nRun the Python runner first:  python tests/parity/run_python_engine.py`);
        process.exit(2);
    }
    const py = JSON.parse(fs.readFileSync(pyReportPath, 'utf8'));
    const pyByName = new Map(py.results.map((r) => [r.name, r]));
    const pyTolerance = Number(py.tolerance ?? tolerance);

    console.log('\nParity (JS vs Python) — under-triage check:');
    let parityFailures = 0;
    for (const r of jsResults) {
        const p = pyByName.get(r.name);
        if (!p) {
            console.log(`  ? ${r.name} — no Python result; skipping`);
            continue;
        }
        const diff = r.level - p.level;            // > 0 ⇒ JS less acute = bad
        const ok = diff <= pyTolerance;
        const tag = ok ? '✓' : '✗ UNDER-TRIAGE';
        console.log(`  ${tag}  ${r.name.padEnd(40)} python=L${p.level}  js=L${r.level}  Δ=${diff > 0 ? '+' : ''}${diff}`);
        if (!ok) { parityFailures++; exitCode = 1; }
    }
    if (parityFailures > 0) {
        console.log(`\n${parityFailures} parity failure(s).`);
    } else {
        console.log(`\nAll parity checks passed (tolerance=${pyTolerance}).`);
    }
}

process.exit(exitCode);
