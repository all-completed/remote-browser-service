---
name: remote-browser-service
description: >
  Control a remote Chrome browser via HTTP API. Use for web automation,
  scraping, form filling, navigation, and page inspection. Exposes accessibility
  tree, text extraction, screenshots, and actions — optimized
  for AI agents. Requires an active browser session (created via HTTP or WebSocket).
metadata:
  openclaw:
    emoji: "🌐"
    requires:
      env:
        - name: AC_API_KEY
          secret: true
          optional: true
          description: "Bearer token or API key for auth (user_id derived from token)"
---

# Remote Browser Service

Browser control for AI agents via HTTP API. Workflow: navigate, snapshot, act.

## Setup

Ensure you have an active session:

1. **Create session** — `POST /api/sessions` (HTTP, no WebSocket), or open WebSocket to `/ws/{session_id}` (DevTools CDP), or run from UI. Optional `url` in body (HTTP) or query (WS) to navigate immediately.
2. **Or restore** — Use stored session from `GET /api/stored-sessions`
3. **Auth** — Pass `Authorization: Bearer <token>` or `X-API-Key`, or `?access_token=<token>`

Base URL: `https://<host>` (or `RBS_BASE_URL`). Replace `{session_id}` in examples. User ID is derived from the token.

## Core Workflow

1. **Navigate** to a URL
2. **Snapshot** the accessibility tree (get refs) — `GET .../json`
3. **Act** on refs or selectors (click, type, fill, press)
4. **Snapshot** again to see results

Refs (`e0`, `e1`, …) from `/json` can be used with `/action` via `selector` (use `ref` as selector for `e5` → `"e5"` maps to role/name; for now use CSS `selector`).

## API Reference

### Create session (HTTP)

```bash
curl -X POST "https://<host>/api/sessions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'
# Optional: {"session_id": "my-session", "url": "https://example.com"}
# Fork from stored session: {"session_id": "my-fork", "from": "original-session"}
# Ephemeral (start from metadata/fork but don't save): {"ephemeral": true}
```

Sessions idle for 5 min are closed. Use `POST .../ping` to keep alive.

### List sessions

```bash
curl "https://<host>/api/sessions" \
  -H "Authorization: Bearer <token>"
```

### List stored sessions

```bash
curl "https://<host>/api/stored-sessions" \
  -H "Authorization: Bearer <token>"
```

Returns `{sessions: [...], count}`. Connect via WebSocket to `/ws/{session_id}` to resume.

### Navigate

```bash
curl -X POST "https://<host>/api/sessions/{session_id}/navigate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# With timeout (seconds)
curl -X POST "https://<host>/api/sessions/{session_id}/navigate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "timeout": 60}'
```

### Set location

```bash
# Override geolocation for the page (e.g. for location-aware sites)
curl -X POST "https://<host>/api/sessions/{session_id}/location" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 37.7749, "longitude": -122.4194}'

# With accuracy (meters)
curl -X POST "https://<host>/api/sessions/{session_id}/location" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 51.5074, "longitude": -0.1278, "accuracy": 50}'
```

### Image (download by selector)

```bash
# Capture a single element (e.g. image) by CSS selector
curl "https://<host>/api/sessions/{session_id}/image?selector=img.hero" \
  -H "Authorization: Bearer <token>" \
  -o image.jpg

# With quality, raw binary (selector=#banner for id)
curl "https://<host>/api/sessions/{session_id}/image?selector=img&quality=90&raw=true" \
  -H "Authorization: Bearer <token>" \
  -o element.jpg
```

Use `selector` (CSS) or `ref` (from snapshot). Returns JPEG of the element's bounding box.

### Snapshot (accessibility tree)

```bash
# Full tree
curl "https://<host>/api/sessions/{session_id}/json" \
  -H "Authorization: Bearer <token>"

# Interactive elements only (buttons, links, inputs) — much smaller
curl "https://<host>/api/sessions/{session_id}/json?filter=interactive" \
  -H "Authorization: Bearer <token>"

# Limit depth
curl "https://<host>/api/sessions/{session_id}/json?depth=5" \
  -H "Authorization: Bearer <token>"
```

Returns `{nodes: [{ref, role, name, depth, value?, disabled?, focused?, nodeId?}], count}`.

### Extract text

```bash
# Readability mode (default) — strips nav/footer/ads
curl "https://<host>/api/sessions/{session_id}/text" \
  -H "Authorization: Bearer <token>"

# Raw innerText
curl "https://<host>/api/sessions/{session_id}/text?mode=raw" \
  -H "Authorization: Bearer <token>"
```

Returns `{url, title, text}`. Cheapest option (~800 tokens for most pages).

### Screenshot

```bash
# JSON with base64
curl "https://<host>/api/sessions/{session_id}/screenshot" \
  -H "Authorization: Bearer <token>"

# Raw JPEG bytes
curl "https://<host>/api/sessions/{session_id}/screenshot?raw=true" \
  -H "Authorization: Bearer <token>" \
  -o screenshot.jpg

# With quality (1-100)
curl "https://<host>/api/sessions/{session_id}/screenshot?quality=50&raw=true" \
  -H "Authorization: Bearer <token>" \
  -o screenshot.jpg

# Region capture (offset x,y and width,height in CSS pixels)
curl "https://<host>/api/sessions/{session_id}/screenshot?x=0&y=0&width=800&height=600&raw=true" \
  -H "Authorization: Bearer <token>" \
  -o region.jpg
```

### Page size

```bash
# Get page content dimensions (use with screenshot clip)
curl "https://<host>/api/sessions/{session_id}/page-size" \
  -H "Authorization: Bearer <token>"
```

Returns `{width, height}` in CSS pixels.

### Act on elements

```bash
# Click by selector
curl -X POST "https://<host>/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "click", "selector": "button.submit"}'

# Click by coordinates (viewport x,y)
curl -X POST "https://<host>/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "click", "x": 100, "y": 200}'

# Type into element (focus + insertText)
curl -X POST "https://<host>/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "type", "selector": "#email", "text": "user@example.com"}'

# Fill (set value directly)
curl -X POST "https://<host>/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "fill", "selector": "#email", "text": "user@example.com"}'

# Press a key
curl -X POST "https://<host>/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "press", "key": "Enter"}'
# Press Enter in a specific input: -d '{"kind": "press", "key": "Enter", "selector": "input#search"}'

# Focus, hover, select, scroll
curl -X POST "https://<host>/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "focus", "selector": "input[name=search]"}'

curl -X POST "https://<host>/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "scroll", "scrollY": 800}'
```

**Action kinds:** `click`, `type`, `fill`, `press`, `focus`, `hover`, `select`, `scroll`. Use `selector` (CSS) or `ref` (from snapshot). For `click` you can use `x` and `y` (viewport coordinates) instead of selector. For `press` use `key` (e.g. `Enter`, `Tab`, `Escape`, `Space`, `ArrowUp`); optional `selector` focuses element first.

### HTML snapshot

```bash
# Full DOM with inlined CSS (opens in browser)
curl "https://<host>/api/sessions/{session_id}/html" \
  -H "Authorization: Bearer <token>"
```

## Token Cost Guide

| Method | Typical tokens | When to use |
|--------|----------------|-------------|
| `/text` | ~800 | Reading page content |
| `/json?filter=interactive` | ~3,600 | Finding buttons/links to click |
| `/json` | ~10,500 | Full page structure |
| `/screenshot` | ~2K (vision) | Visual verification |
| `/image?selector=` | ~1K (vision) | Download image or capture single element |

**Strategy:** Use `/text` when you only need content. Use `/json?filter=interactive` for action-oriented tasks. Use full `/json` for complete page understanding. Use `/screenshot` for visual checks.

## Environment Variables

| Var | Description |
|-----|--------------|
| `RBS_BASE_URL` | Base URL (your service host) |
| `AC_API_KEY` | Bearer token or API key (user_id derived from token) |

## Tips

- **Session required** — Ensure a session exists before calling navigate/json/text/action. Create via `POST /api/sessions` (HTTP), WebSocket, or restore from stored sessions.
- **Refs from snapshot** — Use `selector` with the `ref` string (e.g. `"e5"`) when the action API supports ref→DOM resolution; otherwise prefer CSS selectors.
- **Readability vs raw** — `/text` (default) strips nav/footer/ads; `?mode=raw` returns full `innerText`.
- **Interactive filter** — `?filter=interactive` on `/json` reduces nodes by ~75% for action tasks.
- **Stored sessions** — Sessions persist when WebSocket closes (cookies, localStorage, sessionStorage, metadata). List with `GET /api/stored-sessions`, then connect via WebSocket to resume. If `url` is not provided on connect, the saved page URL is used for redirect. Use `GET/PUT /api/stored-sessions/{session_id}` to read or update metadata (e.g. redirect URL).
