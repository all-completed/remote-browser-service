# Remote Browser Service

A service that creates remote browser sessions on-demand. Control a headless Chrome browser via HTTP API or WebSocket (Chrome DevTools Protocol) for web automation, scraping, form filling, navigation, and page inspection.

https://rb.all-completed.com

## Index

- [Features](#features)
- [Principals](#principals)
- [Usage](#usage)
  - [Playwright (recommended)](#playwright-recommended)
  - [Raw WebSocket Connection](#raw-websocket-connection)
  - [OpenClaw (ClawHub skill)](#openclaw-clawhub-skill)
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
cd examples
pip install -r requirements.txt
playwright install chromium

# Local (no auth when AUTH0 unset)
python websocket_connection.py --server-url http://localhost:8080 --user-id dev-user --session-id abc123

# Remote (API key from AC_API_KEY env or --api-token)
python websocket_connection.py --server-url https://rb.all-completed.com --user-id YOUR_USER_ID --session-id abc123

# Short URL: user_id from token (token required)
python websocket_connection.py --server-url https://rb.all-completed.com --session-id abc123 --short-url
```

### WebSocket URLs

- **Full path**: `wss://<host>/users/{user_id}/ws/{session_id}?mode=browser`
- **Short alias**: `wss://<host>/ws/{session_id}?mode=browser&access_token=<token>` (user_id from token)

### OpenClaw (ClawHub skill)

Install the skill so your OpenClaw agent can control the remote browser:

```bash
# Install OpenClaw (if not already)
npm install -g openclaw@latest

# Install ClawHub CLI and log in
npm i -g clawhub
clawhub login

# Install the skill into your OpenClaw workspace
clawhub install remote-browser-service
```

Configure your API key in `~/.openclaw/openclaw.json`:

```json5
{
  skills: {
    entries: {
      "remote-browser-service": {
        enabled: true,
        env: { AC_API_KEY: "YOUR_API_KEY" },
      },
    },
  },
}
```

Or set the `AC_API_KEY` environment variable. See [skills/remote-browser-service/SKILL.md](skills/remote-browser-service/SKILL.md) for full API reference.

## API Endpoints

See [docs/api.md](docs/api.md) for full API documentation.

| Method | Path                                | Auth           | Description                            |
| ------ | ----------------------------------- | -------------- | -------------------------------------- |
| GET    | `/health`                           | No             | Health check                           |
| GET    | `/api/users/me/api-key`             | Auth0          | Get user metadata / current API token  |
| PUT    | `/api/users/me/api-key`             | Auth0          | Generate new API token                 |
| PUT    | `/api/users/me/user_id`             | Auth0          | Set `user_id` once                     |
| GET    | `/api/sessions`                     | Yes            | List active sessions                   |
| POST   | `/api/sessions`                     | Yes            | Start session via HTTP                 |
| GET    | `/api/sessions/{session_id}`        | Yes            | Get session details                    |
| POST   | `/api/sessions/{session_id}/ping`   | Yes            | Keep session alive                     |
| DELETE | `/api/sessions/{session_id}`        | Yes            | Terminate session                      |
| POST   | `/api/sessions/{session_id}/navigate` | Yes          | Navigate to URL                        |
| POST   | `/api/sessions/{session_id}/location` | Yes          | Set page geolocation                   |
| GET    | `/api/sessions/{session_id}/html`   | Yes            | HTML snapshot with inlined CSS         |
| GET    | `/api/sessions/{session_id}/json`   | Yes            | Accessibility tree (Pinchtab format)   |
| GET    | `/api/sessions/{session_id}/text`   | Yes            | Readable page text                     |
| GET    | `/api/sessions/{session_id}/screenshot` | Yes        | JPEG screenshot                        |
| GET    | `/api/sessions/{session_id}/page-size` | Yes         | Page content dimensions                |
| GET    | `/api/sessions/{session_id}/element-bounds` | Yes    | Element bounding box by selector       |
| GET    | `/api/sessions/{session_id}/image`  | Yes            | Capture a single element by selector   |
| POST   | `/api/sessions/{session_id}/action` | Yes            | Browser action (click, type, fill, etc.) |
| GET    | `/api/stored-sessions`              | Yes            | List stored session IDs                |
| GET    | `/api/stored-sessions/{session_id}` | Yes            | Get stored session metadata            |
| PUT    | `/api/stored-sessions/{session_id}` | Yes            | Update stored session metadata         |
| DELETE | `/api/stored-sessions/{session_id}` | Yes            | Delete stored session                  |
| GET    | `/ws/{session_id}`                  | Token in query | DevTools CDP WebSocket                 |
| GET    | `/users/{user_id}/ws/{session_id}`  | Yes            | DevTools CDP WebSocket                 |
| GET    | `/users/{user_id}/vnc/{session_id}` | Yes            | noVNC client page                      |
| WS     | `/users/{user_id}/vnc/ws/{session_id}` | Yes         | VNC WebSocket proxy                    |

**Authentication**: Bearer token, `X-API-Key` header, or `api_key` / `access_token` query param.

## Documentation

- [api.md](docs/api.md) – Full API reference: endpoints, auth, errors, session lifecycle
- [websocket_connection.md](docs/websocket_connection.md) – Client script: arguments and examples
- [skills/remote-browser-service/SKILL.md](skills/remote-browser-service/SKILL.md) – OpenClaw skill (ClawHub): workflow and quick reference

## Project Structure

```
remote-browser-service/
├── docs/                     # Documentation
│   ├── api.md               # API reference
│   ├── websocket_connection.md
│   └── SKILL.md             # Skill reference (also in skills/)
├── examples/                 # Client scripts
│   ├── websocket_connection.py
│   └── requirements.txt
├── skills/                   # OpenClaw / ClawHub skill bundle
│   └── remote-browser-service/
│       └── SKILL.md
└── README.md
```

## License

Copyright (c) All Completed, 2026
