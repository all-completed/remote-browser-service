# Keeper `request_fill` — field `length` and `format`

When an agent asks the user to supply a value via `request_fill` (tool
`request_fill` / `POST /api/sessions/{session_id}/request-fill`), each field may
declare a `length` and a `format`. These shape the **Keeper input box** the user
types into — they make entry easier and catch typos. They never affect what the
agent sees (the agent never receives the value), and the user is always free to
type whatever they want; these are input *aids*, not server-enforced validation.

See also: [keeper-protocol.md](keeper-protocol.md), [api.md](api.md).

## `length`

- Type: integer, `1`–`4096` (values outside the range are clamped; non-integers
  are ignored).
- Effect: sets the Keeper input's `maxlength`, so the user cannot type more than
  `length` characters. Shown to the user as a `max N` hint.
- Use it when the value has a known fixed/maximum size — e.g. a 6-digit OTP
  (`length: 6`), a fixed-length card PIN, or a bounded username.

```json
{ "selector": "#otp", "label": "One-time code", "field": "code", "length": 6, "format": "numeric" }
```

## `format`

A string. Capped at 200 chars. Three recognized forms:

| `format` value        | Keeper behavior |
|-----------------------|-----------------|
| `email`               | Sets `inputmode=email` and an `you@example.com` placeholder; hint `email`. |
| `numeric` / `digits` / `number` | Sets `inputmode=numeric` and strips any non-digit as the user types; hint `digits only`. |
| any other string      | Treated as a **regex** and applied as the input's `pattern` attribute; shown to the user as `format: <regex>`. Invalid regexes are ignored. |

### Examples

Email login field:
```json
{ "selector": "#email", "label": "Email", "field": "email", "format": "email" }
```

Numeric 2FA code, max 8 digits:
```json
{ "selector": "#twofa", "label": "2FA code", "field": "code", "length": 8, "format": "digits" }
```

Custom pattern (e.g. a license key of 4 groups of 4 alphanumerics):
```json
{ "selector": "#key", "label": "License key", "field": "text",
  "format": "[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}" }
```

## `field` (related)

`field` is the prompt *kind*, separate from `format`. It controls masking and the
default presentation:

- `password` (default) — masked input.
- `code` — masked (treat like a secret).
- `login`, `email`, `text` — shown as plain text.

The reveal (👁) button lets the user toggle masking regardless of `field`.

## Notes

- `length`/`format` are **per field**; in a multi-field request each entry sets
  its own.
- They are advisory client-side aids. The service inserts exactly what the user
  typed; it does not re-validate against `format` server-side.
- Choosing a good `label`, `length`, and `format` improves the user's confidence
  and reduces input errors — prefer setting them when you know the value's shape.
