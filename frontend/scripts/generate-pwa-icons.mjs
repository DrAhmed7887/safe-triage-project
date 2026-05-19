// Generate PWA icons from public/app-icon.svg.
//
// Outputs (PNG, into public/icons/pwa/):
//   - icon-192.png, icon-512.png            (Android / generic PWA)
//   - icon-512-maskable.png                 (maskable; safe-area padded)
//   - apple-touch-icon-180.png              (iOS home screen)
//   - apple-touch-icon-precomposed-180.png  (older iOS)
//
// Run:  node scripts/generate-pwa-icons.mjs

import sharp from 'sharp';
import { readFileSync, mkdirSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const srcSvg = readFileSync(resolve(root, 'public/app-icon.svg'));
const outDir = resolve(root, 'public/icons/pwa');
mkdirSync(outDir, { recursive: true });

async function render(size, name, { background = null } = {}) {
    let pipe = sharp(srcSvg, { density: 384 }).resize(size, size);
    if (background) {
        pipe = pipe.flatten({ background });
    }
    await pipe.png().toFile(resolve(outDir, name));
    console.log(`  wrote ${name} (${size}x${size})`);
}

// iOS doesn't honour transparency for apple-touch-icon — flatten to teal.
const teal = '#0d9488';

await render(192, 'icon-192.png');
await render(512, 'icon-512.png');
// Maskable variant — same artwork; the icon already has ~20% inner padding via
// the rounded rectangle, which is within the safe-zone for maskable.
await render(512, 'icon-512-maskable.png', { background: teal });
await render(180, 'apple-touch-icon-180.png', { background: teal });
await render(180, 'apple-touch-icon-precomposed-180.png', { background: teal });
await render(167, 'apple-touch-icon-167.png', { background: teal }); // iPad Pro
await render(152, 'apple-touch-icon-152.png', { background: teal }); // iPad
await render(120, 'apple-touch-icon-120.png', { background: teal }); // iPhone

console.log('done.');
