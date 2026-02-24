# Remote Browser Service API Documentation

HTTP REST and WebSocket API for managing remote browser sessions.

## Base URL

The API is available at:
- Production: `https://<host>` (replace with your service URL)
- Local development: `http://localhost:8080` (or `PORT` env)

## Authentication

All API endpoints (except `/health`) require authentication. The service supports:

1. **Auth0 Authentication**:
   - Provide Auth0 JWT token in Authorization header:
     ```
     Authorization: Bearer <auth0-token>
     ```
   - The `user_id` in path must match the authenticated user's user_id from the token

2. **API Key Authentication**:
   - API key is a JWT containing `user_id`. Get it from the UI (API Token in sidebar) or `PUT /api/users/me/api-key`
   - Provide API key using one of:
     - Authorization Header: `Authorization: Bearer <api-key>`
     - X-API-Key Header: `X-API-Key: <api-key>`
     - Query Parameter: `?api_key=<api-key>` or `?access_token=<api-key>` or `?token=<api-key>`

**User-scoped paths** (`/api/users/{user_id}/...`): Path `user_id` must match the authenticated user. With API key, `user_id` is encoded in the JWT.

**Token-scoped paths** (`/api/sessions/...`, `/api/stored-sessions`): `user_id` is derived from the token only (no `user_id` in path).

---

## Endpoints

### API Endpoints Index

#### System Endpoints
- [`GET /health`](#health-check) - Health check endpoint

#### User Metadata (Auth0 required)
- [`GET /api/users/me/api-key`](#get-api-key) - Get user metadata (user_id, ac_api_key)
- [`PUT /api/users/me/api-key`](#generate-api-token) - Generate new API token
- [`PUT /api/users/me/user_id`](#set-user-id) - Set user_id (UserIdSetup, once)

#### Session Management
- [`GET /api/users/{user_id}/sessions`](#list-sessions) or [`GET /api/sessions`](#list-sessions) - List active sessions
- [`POST /api/users/{user_id}/sessions`](#create-session) or [`POST /api/sessions`](#create-session) - Start session via HTTP
- [`GET /api/users/{user_id}/sessions/{session_id}`](#get-session) or [`GET /api/sessions/{session_id}`](#get-session) - Get session details
- [`POST /api/users/{user_id}/sessions/{session_id}/ping`](#ping-session) or [`POST /api/sessions/{session_id}/ping`](#ping-session) - Keep session alive
- [`DELETE /api/users/{user_id}/sessions/{session_id}`](#terminate-session) or [`DELETE /api/sessions/{session_id}`](#terminate-session) - Terminate session

#### Browser Control
- [`POST /api/sessions/{session_id}/navigate`](#navigate) - Navigate to URL
- [`POST /api/sessions/{session_id}/location`](#set-location) - Set page geolocation
- [`GET /api/sessions/{session_id}/html`](#html-snapshot) - HTML snapshot (DOM + inlined CSS)
- [`GET /api/sessions/{session_id}/json`](#accessibility-tree) - Accessibility tree (Pinchtab format)
- [`GET /api/sessions/{session_id}/text`](#extract-text) - Readable page text
- [`GET /api/sessions/{session_id}/screenshot`](#screenshot) - JPEG screenshot
- [`GET /api/sessions/{session_id}/page-size`](#page-size) - Page content dimensions
- [`GET /api/sessions/{session_id}/image`](#image) - Screenshot of element by selector
- [`POST /api/sessions/{session_id}/action`](#browser-action) - Browser action (click, type, fill, etc.)

#### Stored Sessions
- [`GET /api/users/{user_id}/stored-sessions`](#list-stored-sessions) or [`GET /api/stored-sessions`](#list-stored-sessions) - List stored session IDs
- [`GET /api/users/{user_id}/stored-sessions/{session_id}`](#get-stored-session-metadata) or [`GET /api/stored-sessions/{session_id}`](#get-stored-session-metadata) - Get stored session metadata
- [`PUT /api/users/{user_id}/stored-sessions/{session_id}`](#put-stored-session-metadata) or [`PUT /api/stored-sessions/{session_id}`](#put-stored-session-metadata) - Update stored session metadata
- [`DELETE /api/users/{user_id}/stored-sessions/{session_id}`](#delete-stored-session) or [`DELETE /api/stored-sessions/{session_id}`](#delete-stored-session) - Delete stored session

#### WebSocket
- [`GET /users/{user_id}/ws/{session_id}`](#websocket-devtools) - DevTools CDP WebSocket (user_id in path)
- [`GET /ws/{session_id}`](#websocket-devtools) - DevTools CDP WebSocket (user_id from token)

#### VNC
- [`GET /users/{user_id}/vnc/{session_id}`](#vnc-page) - noVNC client page
- WebSocket `/users/{user_id}/vnc/ws/{session_id}` - VNC WebSocket proxy

---

### Health Check

#### `GET /health`

Health check endpoint. Does not require authentication.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "remote-browser-service",
  "active_sessions": 2
}
```

---

### List Sessions

#### `GET /api/users/{user_id}/sessions` or `GET /api/sessions`

List active sessions for the authenticated user.

**Path Parameters:** (user-scoped only)
- `user_id` (string, required) - User ID (must match authenticated user)

**Response (200 OK):**
```json
{
  "sessions": [
    {
      "session_id": "session-123",
      "created_at": "2026-02-12T10:00:00",
      "active_ws_connections": 1
    }
  ],
  "count": 1
}
```

**Example using curl:**
```bash
curl "https://<host>/api/sessions" \
  -H "Authorization: Bearer <token>"
```

---

### Create Session

#### `POST /api/users/{user_id}/sessions` or `POST /api/sessions`

Start a session via HTTP (without WebSocket). Creates a browser instance. Sessions idle for 5 minutes are closed automatically; use `POST .../ping` to keep alive.

**Path Parameters:** (user-scoped only)
- `user_id` (string, required) - User ID (must match authenticated user)

**Request Body (JSON):**
```json
{}
```
or
```json
{"session_id": "my-session", "url": "https://example.com"}
```
or fork from stored session:
```json
{"session_id": "my-fork", "from": "original-session"}
```
or start from metadata but do not save (ephemeral):
```json
{"session_id": "temp-session", "from": "stored-session", "ephemeral": true}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | No | Custom session ID. If omitted, a unique ID is generated. |
| `url` | string | No | Navigate to this URL immediately after session start. If omitted and session has stored metadata (e.g. from a previous run), the saved URL is used. |
| `from` | string | No | Fork from this stored session ID. Restores cookies, localStorage, sessionStorage from the source; saves the new session under `session_id`. |
| `ephemeral` | boolean | No | If `true`, do not save session and metadata when the session terminates. Use when starting from metadata or forking but you do not want to persist the new session. |

**Response (200 OK):**
```json
{
  "session_id": "session-abc123",
  "created_at": "2026-02-12T10:00:00",
  "active_ws_connections": 0
}
```

**Error Responses:**
- `403 Forbidden` - Session exists and belongs to another user
- `500 Internal Server Error` - Failed to create session

**Example using curl:**
```bash
curl -X POST "https://<host>/api/sessions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'

# With initial URL
curl -X POST "https://<host>/api/sessions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

---

### Get Session

#### `GET /api/users/{user_id}/sessions/{session_id}` or `GET /api/sessions/{session_id}`

Get session details.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Response (200 OK):**
```json
{
  "session_id": "session-123",
  "created_at": "2026-02-12T10:00:00",
  "active_ws_connections": 1
}
```

**Error Responses:**
- `404 Not Found` - Session not found

---

### Ping Session

#### `POST /api/users/{user_id}/sessions/{session_id}/ping` or `POST /api/sessions/{session_id}/ping`

Keep session alive; resets the 5-minute idle timeout.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Response (200 OK):**
```json
{
  "session_id": "session-123",
  "ok": true
}
```

**Error Responses:**
- `404 Not Found` - Session not found

---

### Terminate Session

#### `DELETE /api/users/{user_id}/sessions/{session_id}` or `DELETE /api/sessions/{session_id}`

Terminate an active session. Saves state to storage if configured.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Response (200 OK):**
```json
{
  "session_id": "session-123",
  "deleted": true
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `500 Internal Server Error` - Failed to terminate session

---

### Navigate

#### `POST /api/users/{user_id}/sessions/{session_id}/navigate` or `POST /api/sessions/{session_id}/navigate`

Navigate the browser to a URL.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Request Body (JSON):**
```json
{
  "url": "https://example.com",
  "timeout": 30,
  "blockImages": false,
  "newTab": false
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | URL to navigate to |
| `timeout` | integer | No | Timeout in seconds (default: 30) |
| `blockImages` | boolean | No | Block images during load |
| `newTab` | boolean | No | Open in new tab |

**Response (200 OK):**
```json
{
  "url": "https://example.com",
  "frameId": "..."
}
```

**Error Responses:**
- `400 Bad Request` - Missing `url`
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Navigate failed

---

### Set Location

#### `POST /api/users/{user_id}/sessions/{session_id}/location` or `POST /api/sessions/{session_id}/location`

Set geolocation for the page. Overrides `navigator.geolocation` for pages that request location.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Request Body (JSON):**
```json
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "accuracy": 100
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `latitude` | number | Yes | Latitude (-90 to 90) |
| `longitude` | number | Yes | Longitude (-180 to 180) |
| `accuracy` | number | No | Accuracy in meters (default: 100) |

**Response (200 OK):**
```json
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "accuracy": 100
}
```

**Error Responses:**
- `400 Bad Request` - Missing latitude or longitude
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Set location failed

---

### HTML Snapshot

#### `GET /api/users/{user_id}/sessions/{session_id}/html` or `GET /api/sessions/{session_id}/html`

Return a snapshot of the page's DOM with inlined CSS.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Response (200 OK):** HTML content with `Content-Disposition: inline`

**Error Responses:**
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Snapshot failed

---

### Accessibility Tree

#### `GET /api/users/{user_id}/sessions/{session_id}/json` or `GET /api/sessions/{session_id}/json`

Return the accessibility tree in Pinchtab format. Use refs (`e0`, `e1`, …) with `/action` via `selector` or `ref`.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `filter` | string | `interactive` — only buttons, links, inputs (~75% fewer nodes) |
| `depth` | integer | Max tree depth (-1 = unlimited) |

**Response (200 OK):**
```json
{
  "nodes": [
    {"ref": "e0", "role": "button", "name": "Submit", "depth": 2},
    {"ref": "e1", "role": "textbox", "name": "Email", "depth": 2, "value": ""}
  ],
  "count": 2
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Snapshot failed

---

### Extract Text

#### `GET /api/users/{user_id}/sessions/{session_id}/text` or `GET /api/sessions/{session_id}/text`

Return readable page text (readability extraction or raw innerText).

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `mode` | string | `raw` — return raw `innerText` instead of readability extraction |

**Response (200 OK):**
```json
{
  "url": "https://example.com/page",
  "title": "Page Title",
  "text": "Extracted readable text..."
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Text extraction failed

---

### Screenshot

#### `GET /api/users/{user_id}/sessions/{session_id}/screenshot` or `GET /api/sessions/{session_id}/screenshot`

Return JPEG screenshot of the page. Optional clip region for partial capture.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `quality` | integer | JPEG quality 1-100 (default: 80) |
| `raw` | boolean | `true` — return binary JPEG instead of JSON with base64 |
| `x` | integer | Clip offset X in CSS pixels (use with width/height) |
| `y` | integer | Clip offset Y in CSS pixels (use with width/height) |
| `width` | integer | Clip width in CSS pixels (requires height for clip) |
| `height` | integer | Clip height in CSS pixels (requires width for clip) |

When `width` and `height` are provided, captures a rectangular region. Use `x` and `y` (default 0) for offset. Get full page size via [`GET /api/sessions/{session_id}/page-size`](#page-size).

**Response (200 OK):** With `raw=true`: binary `image/jpeg`. Otherwise:
```json
{
  "format": "jpeg",
  "base64": "/9j/4AAQSkZJRg..."
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Screenshot failed

---

### Page Size

#### `GET /api/users/{user_id}/sessions/{session_id}/page-size` or `GET /api/sessions/{session_id}/page-size`

Return page content dimensions in CSS pixels. Use with screenshot `x`, `y`, `width`, `height` for region capture.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Response (200 OK):**
```json
{
  "width": 1920,
  "height": 3840
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Page size failed

---

### Image

#### `GET /api/users/{user_id}/sessions/{session_id}/image` or `GET /api/sessions/{session_id}/image`

Capture a screenshot of a single element by CSS selector or ref. Scrolls the element into view, then captures its bounding box. Use to download images or any visible element.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `selector` | string | One of selector/ref | CSS selector (e.g. `img.hero`, `#banner`) |
| `ref` | string | One of selector/ref | Ref from accessibility snapshot (e.g. `e5`) |
| `quality` | integer | No | JPEG quality 1-100 (default: 80) |
| `raw` | boolean | No | `true` — return binary JPEG instead of JSON with base64 |

**Response (200 OK):** With `raw=true`: binary `image/jpeg`. Otherwise:
```json
{
  "format": "jpeg",
  "base64": "/9j/4AAQSkZJRg..."
}
```

**Error Responses:**
- `400 Bad Request` - Missing selector or ref
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Element not found or capture failed

---

### Browser Action

#### `POST /api/users/{user_id}/sessions/{session_id}/action` or `POST /api/sessions/{session_id}/action`

Perform a browser action: click, type, fill, press, focus, hover, select, scroll.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Request Body (JSON):**
```json
{
  "kind": "click",
  "selector": "button.submit"
}
```
Or click by coordinates (viewport-relative):
```json
{
  "kind": "click",
  "x": 100,
  "y": 200
}
```
Or press a key (e.g. Enter) on the page or on a specific element:
```json
{"kind": "press", "key": "Enter"}
{"kind": "press", "key": "Enter", "selector": "input#search"}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `kind` | string | Yes | One of: `click`, `type`, `fill`, `press`, `focus`, `hover`, `select`, `scroll` |
| `selector` | string | For most kinds | CSS selector or ref (e.g. `"e5"`) |
| `ref` | string | Alternative to selector | Ref from accessibility snapshot |
| `x` | number | For `click` by coordinates | X coordinate in viewport (use with `y`) |
| `y` | number | For `click` by coordinates | Y coordinate in viewport (use with `x`) |
| `text` | string | For `type`, `fill` | Text to type or fill |
| `key` | string | For `press` | Key name: `Enter`, `Tab`, `Escape`, `Backspace`, `Space`, `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, `Home`, `End`, `PageUp`, `PageDown`, `Delete`, or any single character |
| `value` | string | For `select` | Value to select |
| `scrollY` | integer | For `scroll` | Pixels to scroll (when no selector) |

For `press`: `key` is required. Optional `selector` or `ref` focuses that element first, then dispatches the key (useful for pressing Enter in an input).

**Response (200 OK):**
```json
{
  "kind": "click",
  "ok": true
}
```

**Error Responses:**
- `400 Bad Request` - Invalid kind or missing selector/ref
- `404 Not Found` - Session not found
- `502 Bad Gateway` - Action failed

---

### List Stored Sessions

#### `GET /api/users/{user_id}/stored-sessions` or `GET /api/stored-sessions`

List stored session IDs. Stored state includes cookies, localStorage, sessionStorage, and metadata (e.g. last page URL used for redirect on resume).

**Response (200 OK):**
```json
{
  "sessions": ["session-abc", "session-xyz"],
  "count": 2
}
```

---

### Get Stored Session Metadata

#### `GET /api/users/{user_id}/stored-sessions/{session_id}` or `GET /api/stored-sessions/{session_id}`

Get stored session metadata (e.g. redirect URL).

**Response (200 OK):**
```json
{
  "session_id": "session-abc",
  "metadata": {"url": "https://example.com"}
}
```

---

### Put Stored Session Metadata

#### `PUT /api/users/{user_id}/stored-sessions/{session_id}` or `PUT /api/stored-sessions/{session_id}`

Update stored session metadata. Merges with existing. Body: `{url?}`.

**Request Body (JSON):**
```json
{"url": "https://example.com"}
```

**Response (200 OK):**
```json
{
  "session_id": "session-abc",
  "metadata": {"url": "https://example.com"}
}
```

---

### Delete Stored Session

#### `DELETE /api/users/{user_id}/stored-sessions/{session_id}` or `DELETE /api/stored-sessions/{session_id}`

Remove persisted session state.

**Path Parameters:**
- `session_id` (string, required) - Session identifier

**Response (200 OK):**
```json
{
  "session_id": "session-abc",
  "deleted": true
}
```

**Error Responses:**
- `404 Not Found` - Session not found
- `503 Service Unavailable` - Storage not configured

---

### WebSocket DevTools

#### `GET /users/{user_id}/ws/{session_id}` or `GET /ws/{session_id}`

DevTools CDP WebSocket. Connects to the browser's DevTools protocol (e.g. for Playwright).

**Path Parameters:**
- `session_id` (string, required) - Session identifier
- `user_id` (string, user-scoped path only) - User ID (must match token)

**Query Parameters:**
| Parameter | Description |
|-----------|-------------|
| `mode=browser` | Use browser-level CDP (recommended for Playwright) |
| `access_token` or `token` | Auth token (required for `/ws/...`, optional for `/users/...`) |
| `url` | Navigate to this URL immediately after session start (optional). If omitted and session has stored metadata from a previous run, the saved URL is used. |
| `from` | Fork from this stored session ID. Restores cookies, localStorage, sessionStorage from the source; saves the new session under the path `session_id`. |
| `ephemeral` | If `true`, do not save session and metadata when the session terminates. Use when starting from metadata or forking but you do not want to persist the new session. |

**Examples:**
```
wss://<host>/users/YOUR_USER_ID/ws/my-session?mode=browser&access_token=<token>
wss://<host>/ws/my-session?mode=browser&access_token=<token>
wss://<host>/ws/my-session?mode=browser&url=https://example.com&access_token=<token>
wss://<host>/ws/my-fork?mode=browser&from=original-session&access_token=<token>
wss://<host>/ws/ephemeral?mode=browser&ephemeral=true&access_token=<token>
```

**Note:** Creates session on first connection if it does not exist. Closing the last WebSocket connection terminates the session.

---

### VNC Page

#### `GET /users/{user_id}/vnc/{session_id}`

Serve noVNC client page (connects to VNC WebSocket at `/users/{user_id}/vnc/ws/{session_id}`).

**Path Parameters:**
- `user_id` (string, required) - User ID
- `session_id` (string, required) - Session identifier

---

## Session Lifecycle

1. **Start session** — `POST /api/sessions` (HTTP) or connect to `GET /ws/{session_id}` (WebSocket). WebSocket creates session on first connection.
2. **Keep alive** — Sessions idle for **5 minutes** are closed automatically. Use `POST .../ping` or any session-using call (navigate, screenshot, action, etc.) to reset the timer.
3. **Stop session** — `DELETE /api/sessions/{session_id}` (HTTP) or close the last WebSocket connection. Idle timeout also closes sessions.
4. **Persistence** — When a session is terminated (HTTP delete or last WS disconnect), state (cookies, localStorage, sessionStorage, metadata including current page URL) is saved to storage if configured. Use `GET /api/stored-sessions` to list stored sessions. When resuming without a `url` parameter, the saved URL is used for redirect.

---

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 OK | Request successful |
| 400 | Bad request – missing/invalid body (e.g. `url` required for navigate) |
| 401 | Unauthorized – invalid or missing token |
| 403 | Forbidden – user_id mismatch |
| 404 | Session not found |
| 428 | User ID not set (UserIdSetup required) |
| 502 | Browser/CDP error – navigate, screenshot, action, or snapshot failed |
| 503 | Service not initialized or storage not configured |

Error responses include a JSON body:
```json
{
  "detail": "Error message describing what went wrong"
}
```
