# web/

Decoupled browser SPA for CameraCommander2. Svelte 4 + Vite + TypeScript +
Tailwind. Talks to the host application exclusively over the public REST +
WebSocket API documented in
[`specs/001-core-system/contracts/host-api.openapi.yaml`](../specs/001-core-system/contracts/host-api.openapi.yaml)
and
[`specs/001-core-system/contracts/host-events.asyncapi.yaml`](../specs/001-core-system/contracts/host-events.asyncapi.yaml).

The bundle is **always built off-device** (laptop or CI) and the produced
`dist/` directory is served by the Pi-side host as static files.

## Quick start

```bash
cd web
npm ci
npm run dev          # Vite dev server, proxies /api and /ws to localhost:8000
npm run build        # produces dist/
npm test             # vitest
```

## Off-Device Build And Deploy

The Pi does not run Node, Vite, SSR, or a dev server. Build on a laptop or CI:

```bash
cd web
npm ci
npm run build
```

Deploy the resulting `web/dist/` next to the host checkout. The FastAPI app
serves that directory with `StaticFiles`; if it is missing, `serve` logs a
single warning and exposes only the API.

## Views

| View | Source | Spec |
|---|---|---|
| Live Control | `src/views/LiveControl.svelte` | FR-030 |
| Planner | `src/views/Planner.svelte` | FR-031 |
| Monitor | `src/views/Monitor.svelte` | FR-032 |
| Library | `src/views/Library.svelte` | FR-033 |
