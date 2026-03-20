---
name: remote-browser-service
description: >
  Control a remote Chrome browser via HTTP API (Kubernetes or Docker backend). Use for web automation,
  scraping, form filling, navigation, and page inspection. Exposes accessibility
  tree, text extraction, Chrome screenshots, VNC-native screenshots,
  DOM actions, and VNC actions — optimized
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

Browser control for AI agents via HTTP API. Supports both DOM-oriented automation
and remote-desktop/VNC control when you need the actual framebuffer.

## Index

- [Setup](#setup)
- [Core Workflow](#core-workflow)
- [API Reference](#api-reference)
- [Screenshot](#screenshot)
- [VNC interface](#vnc-interface)
- [VNC screenshot](#vnc-screenshot)
- [Act on elements](#act-on-elements)
- [VNC action](#vnc-action)
- [HTML snapshot](#html-snapshot)
- [Token Cost Guide](#token-cost-guide)
- [Environment Variables](#environment-variables)
- [Tips](#tips)

## Setup

Ensure you have an active session:

1. **Create session** — `POST /api/sessions` (HTTP, no WebSocket), or open WebSocket to `/ws/{session_id}` (DevTools CDP), or run from UI. Optional `url` in body (HTTP) or query (WS) to navigate immediately.
2. **Or restore** — Use stored session from `GET /api/stored-sessions`
3. **Auth** — Pass `Authorization: Bearer <token>` or `X-API-Key`, or `?access_token=<token>`

Base URL: `https://rb.all-completed.com` (or `RBS_BASE_URL`). Replace `{session_id}` in examples. User ID is derived from the token.

## Core Workflow

1. **Navigate** to a URL
2. **Snapshot** the accessibility tree (get refs) — `GET .../json`
3. **Act** on refs or selectors (click, type, fill, press)
4. **Snapshot** again to see results

For visual or OS-level flows, use the VNC path instead:

1. **Open VNC interface** — `GET /users/{user_id}/vnc/{session_id}` when you want a live noVNC view
2. **Capture VNC framebuffer** — `GET .../vnc/screenshot`
3. **Send VNC input** — `POST .../vnc/action` with coordinates or keys
4. **Capture again** to verify pixel-level results

Refs (`e0`, `e1`, …) from `/json` can be used with `/action` via `selector` (use `ref` as selector for `e5` → `"e5"` maps to role/name; for now use CSS `selector`).

Supported actions by mode:

| Mode               | Kind     | Example                                                     |
|--------------------|----------|-------------------------------------------------------------|
| DOM (`/action`)    | `click`  | `{"kind":"click","selector":"button.submit"}`               |
| DOM (`/action`)    | `tap`    | `{"kind":"tap","selector":"button.submit"}`                 |
| DOM (`/action`)    | `type`   | `{"kind":"type","selector":"#email","text":"user@example.com"}` |
| DOM (`/action`)    | `fill`   | `{"kind":"fill","selector":"#email","text":"user@example.com"}` |
| DOM (`/action`)    | `press`  | `{"kind":"press","key":"Enter"}`                            |
| DOM (`/action`)    | `focus`  | `{"kind":"focus","selector":"input[name=search]"}`          |
| DOM (`/action`)    | `hover`  | `{"kind":"hover","selector":"button.submit"}`               |
| DOM (`/action`)    | `select` | `{"kind":"select","selector":"select","value":"option-1"}`  |
| DOM (`/action`)    | `scroll` | `{"kind":"scroll","scrollY":800}`                           |
| VNC (`/vnc/action`) | `move`   | `{"kind":"move","x":320,"y":240}`                           |
| VNC (`/vnc/action`) | `click`  | `{"kind":"click","x":320,"y":240,"button":"left","repeat":1}` |
| VNC (`/vnc/action`) | `type`   | `{"kind":"type","text":"hello world"}`                      |
| VNC (`/vnc/action`) | `press`  | `{"kind":"press","keys":["Ctrl","l"]}`                      |
| VNC (`/vnc/action`) | `scroll` | `{"kind":"scroll","x":320,"y":240,"direction":"down","repeat":3}` |

## API Reference

### Create session (HTTP)

```bash
curl -X POST "https://rb.all-completed.com/api/sessions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}'
# Optional: {"session_id": "my-session", "url": "https://example.com"}
# Fork from stored session: {"session_id": "my-fork", "from": "original-session"}
# Ephemeral (start from metadata/fork but don't save): {"ephemeral": true}
```

Sessions idle for 5 min are closed. Use `POST .../ping` to keep alive.

Maximum 1 concurrent session per user. If creation returns 429 or WebSocket closes with a limit error: **wait a bit** (previous session may still be shutting down) **and/or close the previous session** via `DELETE /api/sessions/{session_id}` before retrying.

### List sessions

```bash
curl "https://rb.all-completed.com/api/sessions" \
  -H "Authorization: Bearer <token>"
```

### List stored sessions

```bash
curl "https://rb.all-completed.com/api/stored-sessions" \
  -H "Authorization: Bearer <token>"
```

Returns `{sessions: [...], count}`. Connect via WebSocket to `/ws/{session_id}` to resume.

### Navigate

```bash
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/navigate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# With timeout (seconds)
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/navigate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "timeout": 60}'
```

### Set location

```bash
# Override geolocation for the page (e.g. for location-aware sites)
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/location" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 37.7749, "longitude": -122.4194}'

# With accuracy (meters)
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/location" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 51.5074, "longitude": -0.1278, "accuracy": 50}'
```

### Image (download by selector)

```bash
# Capture a single element (e.g. image) by CSS selector
curl "https://rb.all-completed.com/api/sessions/{session_id}/image?selector=img.hero" \
  -H "Authorization: Bearer <token>" \
  -o image.jpg

# With quality, raw binary (selector=#banner for id)
curl "https://rb.all-completed.com/api/sessions/{session_id}/image?selector=img&quality=90&raw=true" \
  -H "Authorization: Bearer <token>" \
  -o element.jpg
```

Use `selector` (CSS) or `ref` (from snapshot). Returns JPEG of the element's bounding box.

### Snapshot (accessibility tree)

```bash
# Full tree
curl "https://rb.all-completed.com/api/sessions/{session_id}/json" \
  -H "Authorization: Bearer <token>"

# Interactive elements only (buttons, links, inputs) — much smaller
curl "https://rb.all-completed.com/api/sessions/{session_id}/json?filter=interactive" \
  -H "Authorization: Bearer <token>"

# Limit depth
curl "https://rb.all-completed.com/api/sessions/{session_id}/json?depth=5" \
  -H "Authorization: Bearer <token>"
```

Returns `{nodes: [{ref, role, name, depth, value?, disabled?, focused?, nodeId?}], count}`.

### Extract text

```bash
# Readability mode (default) — strips nav/footer/ads
curl "https://rb.all-completed.com/api/sessions/{session_id}/text" \
  -H "Authorization: Bearer <token>"

# Raw innerText
curl "https://rb.all-completed.com/api/sessions/{session_id}/text?mode=raw" \
  -H "Authorization: Bearer <token>"
```

Returns `{url, title, text}`. Cheapest option (~800 tokens for most pages).

### Screenshot

```bash
# JSON with base64
curl "https://rb.all-completed.com/api/sessions/{session_id}/screenshot" \
  -H "Authorization: Bearer <token>"

# Raw JPEG bytes
curl "https://rb.all-completed.com/api/sessions/{session_id}/screenshot?raw=true" \
  -H "Authorization: Bearer <token>" \
  -o screenshot.jpg

# With quality (1-100)
curl "https://rb.all-completed.com/api/sessions/{session_id}/screenshot?quality=50&raw=true" \
  -H "Authorization: Bearer <token>" \
  -o screenshot.jpg

# Region capture (offset x,y and width,height in CSS pixels)
curl "https://rb.all-completed.com/api/sessions/{session_id}/screenshot?x=0&y=0&width=800&height=600&raw=true" \
  -H "Authorization: Bearer <token>" \
  -o region.jpg
```

Use this when Chrome DevTools rendering is enough. If you need browser chrome,
OS dialogs, permission prompts, or the exact remote desktop pixels, use
`/vnc/screenshot` instead.

### VNC interface

```bash
# Built-in noVNC client page for a session
open "https://rb.all-completed.com/users/{user_id}/vnc/{session_id}"

# Under the hood the page connects to the VNC websocket proxy
# /users/{user_id}/vnc/ws/{session_id}
```

Use the VNC interface when you need a live remote-desktop view of the session
instead of DOM snapshots.

### VNC screenshot

```bash
# Raw PNG bytes from the VNC framebuffer
curl "https://rb.all-completed.com/api/sessions/{session_id}/vnc/screenshot?raw=true" \
  -H "Authorization: Bearer <token>" \
  -o screen.png

# Cropped framebuffer region
curl "https://rb.all-completed.com/api/sessions/{session_id}/vnc/screenshot?x=0&y=0&width=800&height=600&raw=true" \
  -H "Authorization: Bearer <token>" \
  -o region.png
```

Unlike `/screenshot`, this captures the VNC framebuffer directly. Use it for
browser chrome, native permission prompts, OS-level dialogs, or anything only
visible in the remote desktop.

### Page size

```bash
# Get page content dimensions (use with screenshot clip)
curl "https://rb.all-completed.com/api/sessions/{session_id}/page-size" \
  -H "Authorization: Bearer <token>"
```

Returns `{width, height}` in CSS pixels.

### Act on elements

```bash
# Click by selector
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "click", "selector": "button.submit"}'

# Click by coordinates (viewport x,y)
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "click", "x": 100, "y": 200}'

# Type into element (focus + insertText)
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "type", "selector": "#email", "text": "user@example.com"}'

# Fill (set value directly)
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "fill", "selector": "#email", "text": "user@example.com"}'

# Press a key
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "press", "key": "Enter"}'
# Press Enter in a specific input: -d '{"kind": "press", "key": "Enter", "selector": "input#search"}'

# Focus, hover, select, scroll
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "focus", "selector": "input[name=search]"}'

curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind": "scroll", "scrollY": 800}'
```

**Action kinds:** `click`, `type`, `fill`, `press`, `focus`, `hover`, `select`, `scroll`. Use `selector` (CSS) or `ref` (from snapshot). For `click` you can use `x` and `y` (viewport coordinates) instead of selector. For `fill`, the server focuses the field, `select()` only if the field already has text (then `Input.insertText` replaces), otherwise focuses and inserts like `type`—controlled inputs (e.g. React) update reliably. For `press` use `key` (e.g. `Enter`, `Tab`, `Escape`, `Space`, `ArrowUp`); optional `selector` focuses element first.

### VNC action

```bash
# Move mouse
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/vnc/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind":"move","x":320,"y":240}'

# Click at framebuffer coordinates
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/vnc/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind":"click","x":320,"y":240,"button":"left","repeat":1}'

# Press keys directly over VNC
curl -X POST "https://rb.all-completed.com/api/sessions/{session_id}/vnc/action" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kind":"press","keys":["Ctrl","l"]}'
```

**VNC action kinds:** `move`, `click`, `type`, `press`, `scroll`.

These actions are framebuffer-oriented and do not use DOM selectors. Prefer them
when DOM automation cannot see or control the target UI.

### HTML snapshot

```bash
# Full DOM with inlined CSS (opens in browser)
curl "https://rb.all-completed.com/api/sessions/{session_id}/html" \
  -H "Authorization: Bearer <token>"
```

## Token Cost Guide

| Method | Typical tokens | When to use |
|--------|----------------|-------------|
| `/text` | ~800 | Reading page content |
| `/json?filter=interactive` | ~3,600 | Finding buttons/links to click |
| `/json` | ~10,500 | Full page structure |
| `/screenshot` | ~2K (vision) | Visual verification from Chrome/DevTools |
| `/vnc/screenshot` | ~2K (vision) | Visual verification from the actual remote desktop |
| `/image?selector=` | ~1K (vision) | Download image or capture single element |

**Strategy:** Use `/text` when you only need content. Use `/json?filter=interactive` for action-oriented tasks. Use full `/json` for complete page understanding. Use `/screenshot` for Chrome-rendered visual checks. Use `/vnc/screenshot` and `/vnc/action` when you need the real remote desktop surface.

## Environment Variables

| Var | Description |
|-----|-------------|
| `RBS_BASE_URL` | Base URL (e.g. https://rb.all-completed.com) |
| `AC_API_KEY` | Bearer token or API key (user_id derived from token) |

## Tips

- **Session required** — Ensure a session exists before calling navigate/json/text/action. Create via `POST /api/sessions` (HTTP), WebSocket, or restore from stored sessions.
- **429 / session limit** — If create fails with 429 or WebSocket closes (limit exceeded): wait a few seconds and/or terminate the existing session with `DELETE /api/sessions/{session_id}` first, then retry.
- **Refs from snapshot** — Use `selector` with the `ref` string (e.g. `"e5"`) when the action API supports ref→DOM resolution; otherwise prefer CSS selectors.
- **Readability vs raw** — `/text` (default) strips nav/footer/ads; `?mode=raw` returns full `innerText`.
- **Interactive filter** — `?filter=interactive` on `/json` reduces nodes by ~75% for action tasks.
- **VNC vs DOM** — Use `/action` for selectors/refs in the page DOM. Use `/vnc/action` and `/vnc/screenshot` for pixel-level automation and UI outside the DOM.
- **Stored sessions** — Sessions persist to S3 when WebSocket closes (cookies, localStorage, sessionStorage, metadata). List with `GET /api/stored-sessions`, then connect via WebSocket to resume. If `url` is not provided on connect, the saved page URL is used for redirect. Use `GET/PUT /api/stored-sessions/{session_id}` to read or update metadata (e.g. redirect URL).
