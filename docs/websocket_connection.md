# websocket_connection.py

A client script for connecting to the Remote Browser Service via WebSocket. It uses Playwright to control the browser through the Chrome DevTools Protocol (CDP) over a WebSocket proxy.

## Overview

- **Playwright mode (default)**: Connects via CDP through the server WebSocket, navigates to a URL, and keeps the browser open until you disconnect or the duration elapses.
- **WebSocket-only mode** (`--no-playwright`): Raw WebSocket connection without Playwright; useful for debugging or custom CDP clients.

## Prerequisites

Install Playwright (required for default mode):

```bash
pip install playwright
playwright install chromium
```

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--url` | `WS_URL` env | WebSocket URL (for `--no-playwright` mode) |
| `--server-url` | `http://localhost:8080` or `SERVER_URL` | Server base URL (used to build WS endpoint) |
| `--session-id` | `test-session` or `SESSION_ID` | Session identifier |
| `--page-id` | - | Optional page ID for DevTools connection |
| `--navigate` | `https://www.google.com` or `NAVIGATE_URL` | URL to open with Playwright |
| `--duration` | - | Auto-close after N seconds (triggers session save) |
| `--no-playwright` | - | Use WebSocket only, no Playwright |
| `--user-id` | `dev-user` or `USER_ID` | User ID |
| `--api-token` | `AC_API_KEY` or `API_TOKEN` | API token for auth |
| `--short-url` | - | Use /ws/{session_id} (token required, user_id from token) |

## Examples

Run from `examples/` directory.

### Local server

```bash
cd examples
# Connect to local server, open Google (default)
python websocket_connection.py

# Custom session ID
python websocket_connection.py --session-id my-session

# Navigate to specific URL
python websocket_connection.py --session-id abc123 --navigate https://example.com

# Auto-close after 30 seconds (triggers session save)
python websocket_connection.py --session-id abc123 --navigate https://example.com --duration 30
```

### Remote server

```bash
# Connect to remote server (replace <host> with your service URL)
python websocket_connection.py --server-url https://<host> --session-id abc123

# Custom URL and duration
python websocket_connection.py --server-url https://<host> --session-id my-session \
  --navigate https://github.com --duration 60
```

### Using environment variables

```bash
export SERVER_URL=https://<host>
export SESSION_ID=my-session
export NAVIGATE_URL=https://example.com
python websocket_connection.py
```

### WebSocket-only mode (no Playwright)

```bash
# Raw WebSocket connection (prints incoming messages)
python websocket_connection.py --no-playwright --session-id abc123
```

## Session lifecycle: disconnect vs. idle timeout

**Closing a connection does not close the session.** A persistent session (the default)
stays alive until a **5-minute idle timeout** or an **explicit terminate** — not at the
moment your CDP or VNC socket drops. This applies to both transports:

- **CDP (`/ws`)** — While a client is connected the pod is pinned (`active_ws_connections > 0`),
  so the idle reaper skips it. On disconnect the pod is kept alive and the 5-minute idle clock
  restarts — so a reconnecting client (e.g. Playwright's `connectOverCDP`, which connects and
  disconnects repeatedly) doesn't churn the pod. **Exception:** `ephemeral` sessions are deleted
  immediately on the last disconnect (they are never saved).
- **VNC (`/vnc/ws`)** — Same as CDP: while a viewer streams the session is pinned, so it isn't
  reaped mid-view; on disconnect the pod is kept and the idle clock restarts.

**What restarts the 5-minute idle clock:** opening a CDP/VNC connection,
`GET /api/sessions/{id}/status`, `GET /api/sessions/{id}`, and `POST /api/sessions/{id}/ping`.

**To close a session immediately** instead of waiting out the idle timeout, terminate it:
`DELETE /api/sessions/{session_id}`. The idle handler and explicit terminate both save the
profile before deleting the session.

## Session persistence

When the session is torn down (idle timeout, explicit terminate, or `--duration` expiry), the
server saves the **whole browser profile** (cookies, `localStorage`, `sessionStorage`, IndexedDB,
Service Workers, Cache Storage — all consistent) before deleting it, and records the resumable
page URL. Reconnect with the same `--session-id` to restore it (you stay logged in).
