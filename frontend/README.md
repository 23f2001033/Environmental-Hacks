# JalSaathi public frontend

Hindi-first village reports, a searchable directory, scoped block queues, case
progress, Hindi audio and printable posters. Built with Vite and JavaScript modules.

## Run locally

Node.js 22 or newer is recommended (the map dependency declares Node 22).
The core build was also checked on the workstation's Node 20.18.

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:4173/?demo=1&v=412558** for the village preview.
Open **http://127.0.0.1:4173/?demo=1** for the directory (13 fixture villages).

Preview measurements come from the repository fixtures and advice comes directly
from `content/advice.json`. Workflow events are simulated and visibly labelled.
Preview has no audio recording or map connection. Clicking a Telegram link opens
the existing bot; the frontend itself sends no messages.

For the deployed public API, set a development proxy before starting Vite:

```powershell
$env:JALSAATHI_API_ORIGIN = 'https://d2735023v3xj6.cloudfront.net'
npm run dev
```

Open http://127.0.0.1:4173/?v=412558 without `demo=1`. Requests to `/api` and
`/media` are proxied. Public GETs need no credentials. Failed requests show a retry
screen and never silently substitute mock results.

## Routes and architecture

| Route             | Screen                                                     |
| ----------------- | ---------------------------------------------------------- |
| `/`               | Searchable village directory; optional Amazon Location map |
| `/?v=<key>`       | Village status, advice, audio, history and poster          |
| `/?b=<block_key>` | That block's cases, ordered by severity and age            |
| Add `demo=1`      | Explicit fixture preview, preserved across navigation      |

Query routing preserves the CloudFront and Telegram contracts. Hindi is the initial
language; subsequent choices persist locally.

- `src/app.js`: routing, cancellation, loading/error state, interaction binding.
- `src/components.js`: shared shell, village page, six-stage timeline, expandable
  history/test details, directory and block dashboard.
- `src/api.js`: same-origin requests with a 15-second timeout.
- `src/mock.js`: API-shaped fixture adapter, loaded only for preview.
- `src/model.js`: sorting, status, escaping and route helpers.
- `src/i18n.js`: bilingual interface copy. Safety advice comes from the API.
- `src/poster.js`: preview dialog, local QR generation and A4 print styling.
- `src/map.js`: optional MapLibre integration, loaded on demand.
- `src/styles.css`: responsive layout, focus, reduced-motion and print styles.

The map uses `/api/v1/config`. Hollow points indicate approximate block/district
centres. All villages remain available in the list without the map.

## Build and verification

```powershell
npm test
npm run build
npm run preview
```

Vite writes **frontend/dist/**, including self-hosted fonts. Generated files are
ignored by Git; commit source and the lockfile. Build the frontend before running
the repository's Lambda build and CDK deploy commands, which require its AWS setup.
The original test console at `/test/` is unchanged.

Tests cover routing, reopening, sorting, safe/provisional/unknown status, escaping,
unsafe URL schemes, chemical advice, closed cases and private timeline actors.

Browser checks: desktop and 390px village layouts, block language switching,
directory search, nitrate advice, expandable history, poster preview/QR, and live
API failure without mock fallback. Live Polly playback, map tiles and physical
printer output still need deployed-system validation. Hindi needs native review.

## Credits

JJM-WQMIS for test data; the repository's sourced advice library for advice.
Noto Sans Devanagari and DM Sans (SIL OFL) via Fontsource; MapLibre GL JS
(BSD-3-Clause); node-qrcode and Vite (MIT). Illustrations are project-local SVG.

See [DESIGN.md](DESIGN.md) and [the API contract](../docs/API.md).
