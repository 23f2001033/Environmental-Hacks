# Frontend build space

This folder belongs to the product UI. Build it with whatever stack the frontend lead chooses (React, Svelte, Astro, plain HTML…). The backend will not change under you as long as you follow the contract below.

## The contract

| Rule | Why |
|---|---|
| Your production build goes to **`frontend/dist/`**, with `index.html` at its root | CDK deploys `frontend/dist` to `/` when it exists; otherwise it deploys `frontend/placeholder` |
| Call the API only at **`/api/v1/...`** (same origin) | CloudFront routes `/api/*` to the backend, so there's no CORS and no hard-coded URLs |
| Use only the endpoints and fields in **[docs/API.md](../docs/API.md)** | The `/api/v1` contract is versioned; breaking changes get a new version, never silent edits |
| Keep `/?v=<village key>` opening that village | Telegram alerts and printed posters link to it |
| Don't write to `/test/` | The test console lives there and is deployed separately |
| Audio and media come from `audio_url` (`/media/...`) | Served by CloudFront from S3 |
| Hindi first, English toggle; works on a low-end Android phone | PRD.md, section 8 |

## Local development

1. Point your dev server's proxy at the deployed API so `/api/v1` works locally. For Vite:
   ```js
   // vite.config.js
   export default { server: { proxy: { "/api": { target: "https://<SiteUrl domain>", changeOrigin: true } } } }
   ```
   Get the domain from the stack outputs (`SiteUrl`) or from `state.md`.
2. `npm run build` must write to `frontend/dist`.
3. Deploy: `python scripts/build.py` then `npx -y aws-cdk@2 deploy` from the repo root (Aman runs deploys).

## Routing note

CloudFront rewrites `/path/` and `/path` (no file extension) to `/path/index.html`. For a single-page app, prefer query-string or hash routing (`/?v=412558`, `/#/block/5037`), or ask for a CloudFront change so every unknown path serves `/index.html`.

## What the screens need

See PRD.md section 7 (FR-11 village page, FR-12 block view) and the poster requirement (FR-11). The test console at `/test/` shows every field in use and is a working reference.
