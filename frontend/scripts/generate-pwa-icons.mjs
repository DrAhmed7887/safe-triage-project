// Generate PWA + iOS icons from the SAFE-Triage brand source.
//
// This wrapper intentionally avoids a Node-native image dependency. It calls
// the adjacent Pillow script, which also generates the iOS AppIcon and splash
// image so all surfaces share one mark.
//
// Run:  node scripts/generate-pwa-icons.mjs

import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { spawnSync } from 'child_process';

const here = dirname(fileURLToPath(import.meta.url));
const script = resolve(here, 'generate-brand-assets.py');

const result = spawnSync('python3', [script], { stdio: 'inherit' });
if (result.error) {
    throw result.error;
}
process.exit(result.status ?? 0);
