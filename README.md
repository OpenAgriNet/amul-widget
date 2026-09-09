# Amul AI Widget

Embeddable Amul AI advisory widget and its backend-for-frontend security boundary.

The repository contains two independently deployable services:

```text
apps/widget-web/        React/Vite iframe UI and partner-page loader
services/widget-bff/    FastAPI host policy, sessions and upstream proxy
packages/contracts/     Shared TypeScript and OpenAPI contracts
deploy/                 Local and Kubernetes deployment resources
```

See [the architecture document](docs/architecture.md) for the security model and phased API design.

## Run locally

Requirements: Node 22+, npm 10+, Python 3.10+ and `uv`.

```bash
npm install
cd services/widget-bff && uv sync --dev
```

Start the BFF:

```bash
cd services/widget-bff
uv run uvicorn widget_bff.main:app --app-dir src --reload --port 8000
```

Start the web application in another terminal:

```bash
npm run dev:web
```

To exercise the floating launcher on a representative partner page:

```bash
python3 -m http.server 9000 --directory examples
```

Then open `http://127.0.0.1:9000/partner.html`.

Or run the production-shaped local stack and open the expanded embed directly:

```bash
docker compose up --build
open http://127.0.0.1:8080/embed/AMULAI-HOST-6c48b031
```

Open the Vite development URL at:

```text
/embed/AMULAI-HOST-6c48b031
```

The Vite development server proxies `/api` to the BFF. Set `WIDGET_AMUL_API_BASE_URL` to enable the existing Amul advisory upstream. Without it, the BFF intentionally returns a typed `503` from the chat endpoint.

The initial slice implements anonymous advisory text chat end to end. Voice capture,
OTP elevation, persistent rate limiting and audit export are deliberately tracked as
the next security-sensitive milestones rather than mocked in the public contract.

## Partner installation

The intended integration is one loader script:

```html
<script
  async
  src="https://widget.amulai.in/widget.js"
  data-host-id="AMULAI-HOST-6c48b031">
</script>
```

The loader renders a small floating launcher and opens the sandboxed iframe only when requested. The direct `/embed/:hostId` URL remains the expanded panel.

A partner with a restrictive Content Security Policy must allow `https://widget.amulai.in` in `script-src`, `style-src` and `frame-src`. The embed response independently restricts `frame-ancestors` to the exact origins registered for its host ID.

## Verification

```bash
npm run lint:web
npm run test:web
npm run build:web

cd services/widget-bff
uv run pytest
```
