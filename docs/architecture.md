# Amul AI Widget BFF Design

Status: proposed architecture  
Saved: 2026-09-09

## Decision

Create one repository named `amul-widget` containing two independently deployable services. They share contracts and a release boundary, but they do not run in the same process or container.

```text
amul-widget/
  apps/widget-web/        # compact React/Vite iframe UI
  services/widget-bff/    # host policy, sessions, OTP and chat proxy
  packages/contracts/     # OpenAPI schemas and generated client types
  deploy/                 # Docker and Kubernetes resources
```

The existing OAN-UI widget route is the temporary integration surface. Its UI can be extracted into `apps/widget-web` once the new repository is created.

## Public routing

Keep the browser surface same-origin:

```text
GET  widget.amulai.in/embed/:hostId  -> widget BFF embed shell
GET  widget.amulai.in/assets/*       -> widget web static assets
ANY  widget.amulai.in/api/v1/*       -> widget BFF
```

The BFF serves the initial embed HTML after resolving the host and emits a host-specific `Content-Security-Policy: frame-ancestors ...` response. Same-origin API routing avoids browser CORS between the widget and its BFF.

For streaming endpoints, ingress must disable proxy buffering and use a suitable read timeout.

## Host registration

Host IDs are public installation identifiers, not secrets and not proof of partner identity. A partner can own multiple host registrations for different domains or environments.

```json
{
	"partner_id": "internal-uuid",
	"host_id": "AMULAI-HOST-6c48b031",
	"status": "active",
	"allowed_frame_origins": ["https://sarlaben.ai"],
	"features": ["advisory_chat", "voice_input"],
	"locales": ["gu", "hi", "en"],
	"rate_limit_tier": "standard"
}
```

Allowed origins must be normalized exact HTTPS origins. Do not accept paths, wildcards, substring matches, or arbitrary ports.

## MVP API

The visible advisory widget initially requires only:

```text
GET  /api/v1/hosts/:hostId/config
POST /api/v1/sessions/anonymous
POST /api/v1/chat/stream
GET  /api/v1/health
```

### Get host configuration

`GET /api/v1/hosts/AMULAI-HOST-6c48b031/config`

```json
{
	"host_id": "AMULAI-HOST-6c48b031",
	"partner_name": "Sarlaben",
	"features": ["advisory_chat", "voice_input"],
	"locales": ["gu", "hi", "en"],
	"default_locale": "gu"
}
```

Return only public presentation and capability data. The origin allowlist and internal partner ID remain server-side.

### Start an anonymous session

`POST /api/v1/sessions/anonymous`

```json
{
	"host_id": "AMULAI-HOST-6c48b031",
	"locale": "gu"
}
```

```json
{
	"session_id": "uuid",
	"access_token": "short-lived-token",
	"expires_in": 900,
	"features": ["advisory_chat", "voice_input"]
}
```

Keep anonymous tokens in memory, not `localStorage`. The widget can create a new anonymous session after the 15-minute expiry.

### Stream a chat response

```http
POST /api/v1/chat/stream
Authorization: Bearer <access-token>
Idempotency-Key: <uuid>
Accept: text/event-stream
Content-Type: application/json
```

```json
{
	"conversation_id": null,
	"message_id": "uuid",
	"text": "How do I prevent mastitis?",
	"locale": "en"
}
```

Use fetch-based server-sent events with these event names:

```text
turn.started
message.delta
message.completed
error
```

Limit message size and permit only one active generation per session.

## Later OTP-authenticated farmer reads

These endpoints are outside the visible-widget MVP:

```text
POST /api/v1/auth/otp/challenges
POST /api/v1/auth/otp/exchange
GET  /api/v1/farmers/me/profile
GET  /api/v1/farmers/me/milk-sales
GET  /api/v1/farmers/me/revenue-summary
```

OTP challenge creation always returns a generic response so it does not disclose whether a farmer exists. Successful verification exchanges the challenge for a new short-lived scoped token; it does not upgrade the anonymous token in place.

Suggested authenticated claims:

```json
{
	"iss": "https://widget.amulai.in",
	"aud": "amul-widget-bff",
	"sub": "farmer:<opaque-id>",
	"sid": "<session-id>",
	"jti": "<unique-id>",
	"partner_id": "<internal-uuid>",
	"host_id": "AMULAI-HOST-6c48b031",
	"scopes": ["farmer.milk_sales:read", "farmer.revenue:read"],
	"amr": ["otp"],
	"auth_time": 1780000000,
	"iat": 1780000000,
	"nbf": 1780000000,
	"exp": 1780000300
}
```

Use approximately five-minute authenticated access tokens and require fresh OTP verification after a short maximum authenticated session, initially 15 minutes. Never put phone numbers, farmer numbers, milk-sale values, or revenue values in JWTs.

## Security boundary

The BFF owns:

- host and partner policy;
- exact embedding-origin registration and dynamic `frame-ancestors`;
- anonymous and authenticated sessions;
- OTP challenge and exchange;
- authorization scopes and upstream credentials;
- rate limiting, audit events and upstream Amul API calls.

The web application owns rendering, microphone capture, text input and response presentation.

Browser origin checks control where the UI can be framed but do not cryptographically authenticate a partner. Non-browser callers can forge an `Origin` header. This is sufficient for generic advisory traffic and can coexist with farmer-authenticated read-only data because OTP authenticates the farmer. If partner authentication becomes necessary, add a single-use signed launch ticket issued by the partner backend.

The partner iframe must include `allow="microphone"` to delegate microphone access to the cross-origin widget.

## Initial limits and audit

- Advisory chat: 10 turns per minute per session, one concurrent generation.
- OTP sends: 3 per destination per 15 minutes and 5 per day, plus IP and host limits.
- OTP verification: no more than 5 attempts per challenge.
- Farmer reads: 30 per minute per authenticated session.

Audit the host, partner, pseudonymous farmer ID, session ID, granted scope, outcome, timestamp and request ID. Never log OTP values, JWTs or unredacted farmer data.

## Error contract

Use `application/problem+json` for HTTP errors:

```json
{
	"type": "https://widget.amulai.in/problems/rate-limited",
	"title": "Too many requests",
	"status": 429,
	"code": "rate_limited",
	"request_id": "uuid",
	"retry_after": 30
}
```

For a streaming request, send the same structure in an `error` SSE event.
