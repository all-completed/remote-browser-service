# Remote Browser Service

A service that creates remote browser sessions on-demand. Control a headless Chrome browser via HTTP API or WebSocket (Chrome DevTools Protocol) for web automation, scraping, form filling, navigation, and page inspection.

## Index

- [Features](#features)
- [Principals](#principals)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Documentation](#documentation)

## Features

- **On-demand sessions**: Create browser sessions via HTTP or WebSocket
- **WebSocket proxy**: Connect to browser DevTools (CDP) through the server
- **Session persistence**: Cookies, localStorage, sessionStorage saved between runs (optional)
- **HTTP API**: Navigate, screenshot, accessibility tree, text extraction, browser actions
- **AI-oriented**: Accessibility tree (Pinchtab format), refs for elements, optimized for agents

## Principals

1. **Session lifecycle**: Create session (HTTP `POST` or WebSocket connect) → use it → terminate or let idle timeout close it. Sessions idle for 5 minutes are closed; use `POST .../ping` to keep alive.

2. **Authentication**: Bearer token (Auth0 or API key), `X-API-Key` header, or `access_token` query param. User-scoped paths require matching `user_id`.

3. **Two connection modes**:
   - **HTTP**: Start session with `POST /api/sessions`, control via REST (navigate, screenshot, action, etc.)
   - **WebSocket**: Connect to `/ws/{session_id}` or `/users/{user_id}/ws/{session_id}` for CDP (e.g. Playwright)

4. **Stored sessions**: When a session ends, state can be saved (cookies, storage, metadata). Resume later by connecting to the same `session_id`.

## Usage

### Playwright (recommended)

Use the provided client script. See [docs/websocket_connection.md](docs/websocket_connection.md) for full description and examples.

```bash
pip install -r requirements.txt
playwright install chromium

# Local (no auth when AUTH0 unset)
python websocket_connection.py --server-url http://localhost:8080 --user-id dev-user --session-id abc123

# Remote (API key from AC_API_KEY env or --api-token)
python websocket_connection.py --server-url https://<host> --user-id YOUR_USER_ID --session-id abc123

# Short URL: user_id from token (token required)
python websocket_connection.py --server-url https://<host> --session-id abc123 --short-url
```

### WebSocket URLs

- **Full path**: `wss://<host>/users/{user_id}/ws/{session_id}?mode=browser`
- **Short alias**: `wss://<host>/ws/{session_id}?mode=browser&access_token=<token>` (user_id from token)

## API Endpoints

See [docs/api.md](docs/api.md) for full API documentation.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/api/users/me/api-key` | Auth0 | Get / generate API token |
| GET | `/api/sessions` | Yes | List active sessions |
| POST | `/api/sessions` | Yes | Start session via HTTP |
| GET | `/api/sessions/{session_id}` | Yes | Get session details |
| DELETE | `/api/sessions/{session_id}` | Yes | Terminate session |
| POST | `/api/sessions/{session_id}/navigate` | Yes | Navigate to URL |
| GET | `/api/sessions/{session_id}/json` | Yes | Accessibility tree (Pinchtab format) |
| GET | `/api/sessions/{session_id}/text` | Yes | Readable page text |
| GET | `/api/sessions/{session_id}/screenshot` | Yes | JPEG screenshot |
| POST | `/api/sessions/{session_id}/action` | Yes | Browser action (click, type, fill, etc.) |
| GET | `/api/stored-sessions` | Yes | List stored session IDs |
| DELETE | `/api/stored-sessions/{session_id}` | Yes | Delete stored session |

**Authentication**: Bearer token, `X-API-Key` header, or `api_key` / `access_token` query param.

## Documentation

- [api.md](docs/api.md) – Full API reference: endpoints, auth, errors, session lifecycle
- [websocket_connection.md](docs/websocket_connection.md) – Client script: arguments and examples
- [SKILL.md](docs/SKILL.md) – AI agent skill: workflow and quick reference

## License

Copyright (c) 2026
