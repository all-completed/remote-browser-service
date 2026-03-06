## Skills for agents

This repository exposes a Remote Browser Service API that can be driven by "agent skills".

### Session lifecycle note (important)

When a DevTools WebSocket session is opened, it is now immediately visible in `GET /api/users/{user_id}/sessions` (and `GET /api/sessions`) with a `status` field:

- **`starting`**: pod/browser is still warming up
- **`ready`**: session is ready to use
- **`error`**: session failed to start (see `last_error`)

See `docs/api.md` for the full endpoint reference. For coordinate-based clicks, use `GET .../element-bounds?selector=...` to get an element's bounding box, then `POST .../action` with `{"kind": "click", "x": cx, "y": cy}`.
