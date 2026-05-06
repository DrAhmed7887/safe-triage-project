# SAFE-Triage UI Kits

Static, dependency-free design previews of the SAFE-Triage product surfaces. Each
kit is a self-contained HTML page that renders a specific surface using React UMD
+ Babel-standalone from CDN, sharing the brand tokens in
[`colors_and_type.css`](./colors_and_type.css).

These are **design surfaces, not the live app.** They have no backend, no auth,
no analytics. Buttons update local component state. The live React + Vite app
lives in [`../frontend/`](../frontend/).

## Kits

| Kit | Surface | Entry |
|---|---|---|
| `clinical-app/` | In-product clinician dashboard (sign-in + queue + triage form + ESI result + workup) | [`clinical-app/index.html`](./clinical-app/index.html) |

## Running locally

The kits load `.jsx` files via `<script type="text/babel" src="…">`. Most browsers
block this on the `file://` protocol, so serve over HTTP:

```bash
# from the repo root
python3 -m http.server 8080 --directory ui_kits
# then open http://localhost:8080/clinical-app/
```

Any tiny static server works (`npx serve ui_kits`, `caddy file-server`, etc.).

## Design system source

`colors_and_type.css` and the component shapes mirror the production tokens used
by `frontend/src/pages/Dashboard.jsx` and `frontend/tailwind.config.js`. Update
the CSS variables here if and only if the production tokens change.

## Why babel-standalone instead of Vite

These kits are intended as **stable, self-contained design references** that
survive frontend dependency churn. A reviewer can open a single HTML file and
see the surface — no `npm install`, no build step, no node version pin.
