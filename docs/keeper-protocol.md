# Keeper protocol — out-of-band credential fill

The **Keeper** lets a user supply secrets (passwords, login codes, 2FA) to a
browser session **without the value ever reaching the AI model**. The agent asks
*which* field to fill; the user supplies the *value* via a desktop app; the
service types it into the page. The model only learns the *status*.

- **Goal:** credentials are never passed to the model.
- **Value path:** `user → Keeper app → service → form field`.
- **Model path:** `agent → request_fill → request_id → get_fill_status → "filled"`.
- Reference client: `remote-browser-keeper` — an Electron tray app implementing this protocol.

## 1. Keeper WebSocket — `wss://<host>/api/keeper/ws`

A user's Keeper app holds one persistent socket (auto-reconnect).

**Auth:** the token is **never** placed in the URL/query, so it can't leak into
proxy/access logs. Three accepted forms (checked in order):

1. `Authorization: Bearer <API_KEY>` header (desktop Keeper).
2. `X-API-Key: <API_KEY>` header.
3. WebSocket **subprotocol** `["bearer", "<API_KEY>"]` — for browser/WebView
   clients that can't set request headers. The server reads the token from
   `Sec-WebSocket-Protocol` and echoes `bearer` to complete the handshake. In JS:
   `new WebSocket(url, ["bearer", apiKey])`.

The user_id is derived from the token; a Keeper may only fill that user's sessions.

### Messages

Server → Keeper (`request_id` is a server-generated UUID; one or more fields, ≤ 50):

```json
{
  "type": "fill_request",
  "request_id": "1f3c…-uuid",
  "session_id": "telegram",
  "url": "https://web.telegram.org/k/",
  "message": "Logging into Telegram to read your unread chats",  // optional, from the agent
  "screenshot": "data:image/jpeg;base64,…",  // ONE proof image for the whole request
  "fields": [
    {
      "selector": "#password",
      "label": "Password",
      "field": "password",     // password|code|login|email|text|card-* (prompt hint; see keeper-fill-formats.md)
      "length": 20,            // optional: max input length
      "format": "numeric"      // optional: email | numeric/digits | a regex
    }
  ]
}
```
The single `screenshot` covers the requested fields (or the explicit
`screenshot_selector(s)` from the API call) plus a margin — the Keeper renders it
once, above the inputs.
Server → Keeper (liveness, optional): `{ "type": "ping" }`.

Keeper → Server (values keyed by selector; the Keeper shows one input per field):

```json
{ "type": "hello", "app": "remote-browser-keeper", "version": "0.1.0" }
{ "type": "fill_response", "request_id": "1f3c…", "values": [ { "selector": "#password", "value": "…" } ] }
{ "type": "fill_response", "request_id": "1f3c…", "cancelled": true }
{ "type": "pong" }
```

The Keeper SHOULD show the user the `label`, `url`, optional `message`, and the
`screenshot` before collecting the value, so they can verify what they're filling.

## 2. Agent API

### `POST /api/sessions/{session_id}/request-fill` — MCP tool `request_fill`

One field:
`{ selector | ref, label?, field?, length?, format?, message?, url? }` (no value).

Or several fields in one prompt (max **50**):
`{ fields: [ { selector, label?, field?, length?, format? }, … ], message?, url? }`.

- `selector`/`ref` (required per field) — the field to fill.
- `label` — short field name shown to the user (e.g. `"Password"`).
- `field` — prompt hint: `password` (default, masked) / `code` / `login` / `email` / `text`.
- `length` — optional max input length (caps the input).
- `format` — optional constraint/hint: `email`, `numeric`/`digits`, or a regex.
- `message` — plain-language reason shown to the user.
- `url` — optional; auto-detected from the page if omitted.
- `screenshot_selector` / `screenshot_selectors` — optional; selector(s) to
  capture for the single proof image. Defaults to the union of the field
  selectors (+ margin). **Prefer pointing this at the whole `<form>`/container**
  so the user sees the entire form in context, not just a crop around the inputs.

Returns immediately (asynchronous); `request_id` is a server-generated UUID:
```json
{ "request_id": "1f3c…", "session_id": "telegram", "status": "pending", "fields": 2 }
```
`status` is `pending`, or `no_keeper` if no Keeper app is connected for the user.
The service also captures a screenshot of the field area and pushes the
`fill_request` to the Keeper. **The value is never returned and never logged.**

### `GET /api/sessions/fill-status/{request_id}` — MCP tool `get_fill_status`

Poll until terminal:
```json
{ "request_id": "f3a9…", "session_id": "telegram", "status": "filled", "created_at": 1781… }
```

| status | meaning |
| --- | --- |
| `pending` | waiting on the user |
| `filled` | value received and typed into the field |
| `cancelled` | user dismissed the prompt |
| `timeout` | user did not respond in time (default 300s) |
| `no_keeper` | no Keeper app connected for this user |
| `error` | value received but typing it failed |

`404` if the `request_id` is unknown (or pruned ~10 min after completion).

## 3. Lifecycle

```
agent  POST request-fill ─────────────►  service
                                          ├─ screenshot field area
                                          ├─ start_request → request_id (pending)
agent  ◄── {request_id, "pending"} ──────┤
                                          └─ fill_request (WS) ──► Keeper
                                                                   user types value
                                          ◄── fill_response (WS) ─ Keeper
                                          └─ type value into field, status=filled
agent  GET fill-status/{id} ────────────►
agent  ◄── {"status":"filled"} ──────────┘   (never the value)
```

## 4. Security properties

- The value travels `Keeper → service` only; never in any agent-facing response,
  never logged (request-fill/fill-status return status only; the fill reuses the
  no-log `fill` path).
- Keeper auth token is header-only (never in the URL).
- The Keeper prompt masks the input, disables spellcheck/autocomplete/autocorrect,
  and clears it after send.
- Request state is in memory (process-local); finished requests are pruned ~10 min
  after completion.

### Injection / abuse hardening

- **No JS injection via `selector`/value.** Every selector and value reaches the
  page through a JSON-encoded `document.querySelector(...)` / `Input.insertText`;
  agent strings are data, never code.
- **Only the requested fields can be filled.** A `fill_response` is filtered to the
  selectors of the originating request; arbitrary selectors are dropped.
- **Responses are bound to the authenticated user.** A `fill_response` is honored
  only for a request owned by that Keeper socket's user; a leaked/guessed
  `request_id` from another user is ignored (atop the unguessable UUID).
- **Cross-user isolation.** `get_fill_status` only returns a request to its owner;
  the filler runs against the caller's own session.
- **Bounded agent input.** `request_fill` caps every agent-supplied string
  (`selector`/`label`/`format`/`message`/`url`), whitelists `field`, clamps
  `length`, and limits fields to 50 — a prompt-injected agent can't flood the UI.
- **Hardened Keeper window.** The prompt renderer runs sandboxed with
  `contextIsolation` (only a minimal preload bridge), a strict CSP
  (`default-src 'none'; img-src data:`), text-only rendering (no `innerHTML`), a
  proof image restricted to `data:image/`, and all navigation / new windows denied.
- **The user is the gate.** The agent picks *which* field and *why*; the user sees
  the real page URL and a screenshot of the field before typing, and supplies the
  value. The `message` is agent-influenced text — treat it as untrusted; the URL
  and screenshot are authoritative.

## 5. History (no values)

Every finished request is logged for auditing — **never the value**.

- **Service:** appended as JSONL to `rb/{user_id}/keeper-history.jsonl` in object
  storage. Each line: `{request_id, session_id, status, url, message, fields:[{selector,
  label, field, length, format}], created_at, completed_at}`. Eviction on write —
  the most recent **1000** entries are kept, and anything older than **~6 months**
  is dropped.
- **Keeper app:** appends to `history.jsonl` in its per-user app-data dir. Each
  line: `{request_id, session_id, url, requested_at, resolved_at, outcome
  ("submitted"|"cancelled"), fields:[{selector, label, field, length, format}]}`.
  Capped at the last 2000 lines.

Field metadata records *which* field was requested; values are not present in
either log.

## 6. Reliability notes

- `request_fill` is async — do not block; poll `get_fill_status`.
- One Keeper handles requests sequentially (it queues prompts); multiple Keepers
  for the same user all receive the request, first response wins.
- A service restart drops in-memory request state and Keeper sockets; the Keeper
  reconnects automatically, and in-flight requests should be re-issued.
