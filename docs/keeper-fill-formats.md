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

## `generate`

Set `generate: true` on a field to have the **Keeper create a strong value itself**
(e.g. a new password for a sign-up or change-password flow), fill it, and save it —
instead of asking the user to type one.

**This is UNATTENDED by default.** When every field of a `request_fill` is a
`generate` field, the Keeper creates each value, fills it, and saves it with **no
prompt** — the user is never asked, and the request goes straight to `filled`.

- The value is generated **inside the Keeper** with a CSPRNG. It is never produced
  by, sent to, or returned to the agent (same guarantee as a typed value).
- **Policy (password):** length **>= 14** (a `length` below 14 is raised to 14; use
  `length` only to make it *longer*, capped at 128) and **always** at least one
  lowercase, one uppercase, and one digit. Symbols are included unless you set
  `symbols: false` — the mandatory set is exactly `a-z` / `A-Z` / `0-9`.
- **Numeric** (`format: "numeric"`/`"digits"`/`"number"`): digits only at the
  requested `length` — for PINs. The 14 floor does **not** apply here.
- The generated value is saved to the user's Keeper (synced across their devices) so
  it can auto-fill on the next login.
- **User opt-out:** each Keeper has a per-device setting to review generated values in
  a prompt (with a regenerate button) before they fill. The agent's request is
  identical either way, and the agent still only ever learns the `status`.

```json
{ "selector": "#new-password", "label": "New password", "field": "password", "generate": true }
```
```json
{ "selector": "#pw", "label": "New password", "field": "password",
  "generate": true, "length": 24, "symbols": false }
```

To have the **user** choose the password instead, send a normal (non-`generate`)
request_fill — that always prompts.

## `symbols`

Only meaningful with `generate: true` on a non-numeric field. Set `symbols: false` to
exclude symbols from the generated password (for sites that reject them) — the value is
then `a-z` / `A-Z` / `0-9` only, still >= 14 chars with each class guaranteed. Defaults
to `true`. Ignored for numeric and non-generate fields.

## `field` (related)

`field` is the prompt *kind*, separate from `format`. It controls masking and the
default presentation:

- `password` (default) — masked input.
- `code` — masked (treat like a secret).
- `login`, `email`, `text` — shown as plain text.

**Payment-card kinds** — the Keeper renders card-aware inputs, so you don't need
to set `length`/`format` (the defaults below apply):

| `field` | Masked | `format` (optional) | Input behavior | Submitted value |
|---|---|---|---|---|
| `card-holder-name` | no | — | text, capitalizes words | as typed |
| `card-number` | no (shown) | a `#`-mask, default `#### #### #### ####` | numeric; digits grouped per the mask (visible, like a checkout form) | **digits only** |
| `card-cvv` | yes | — | numeric; ≤4 | as typed |
| `card-exp` | no | a date template, default `MM/YY` | numeric, auto-formats; a **year-only** (`YYYY`/`YY`) or **month-only** (`MM`) format renders a **dropdown** | as displayed |
| `card-billing-address` | no | a component token (or empty) | empty → multi-line whole address; a token → single-line component | as typed |

The reveal (👁) button lets the user toggle masking regardless of `field` (single-line fields).

### Card field `format`

- **`card-number`** — `format` is a digit **mask** of `#` (slot) and spaces. Default
  `#### #### #### ####` (16 digits grouped in 4s, shown — not masked — so the user can
  read it back). Pass a 15/19-`#` mask for Amex/long cards. Always submitted as digits only.
- **`card-exp`** — `format` is a **date template** built from `M`/`Y` and separators.
  Recognized: `MM/YY` (default), `MM/YYYY`, `YY`, `YYYY`, `MM`. Combined templates are
  typed and auto-formatted (e.g. `MM/YYYY` → `12/2028`). **Single-component** templates
  render a **dropdown**: a year-only format (`YYYY`/`YY`) → a year picker (this year to
  +10, 4- or 2-digit per the format); a month-only format (`MM`) → a `01`–`12` month
  picker. Use single-component templates when the page has separate month / year fields.
- **`card-billing-address`** — `format` names the sub-component(s) for this field:
  `ADDRESS_LINE1`, `ADDRESS_LINE2`, `CITY`, `ZIP`, `STATE`, `COUNTRY` (comma-separate
  for a combined line). **No `format` → a multi-line textarea for the whole address.**
  So `.zip` → `{field:"card-billing-address", format:"ZIP"}`, `.state` →
  `{...,"format":"STATE"}`, each its own single-line field.

**Dropdowns:** if the target element is a `<select>` (common for expiry month/year,
state, country), the service **selects the matching `<option>`** (by value or visible
text) instead of typing — so the same `card-exp`/`card-billing-address` field works
whether the page uses a text input or a dropdown. The matcher also resolves basic
**country / US-state aliases** (e.g. `US` ↔ `United States`, `CA` ↔ `California`),
so the value matches whether the option uses a 2-letter code or the full name.

```json
{ "fields": [
  { "selector": "#cc-name",   "label": "Name on card",    "field": "card-holder-name" },
  { "selector": "#cc-number", "label": "Card number",     "field": "card-number" },
  { "selector": "#cc-exp",    "label": "Expiry",          "field": "card-exp" },
  { "selector": "#cc-cvv",    "label": "CVV",             "field": "card-cvv" },
  { "selector": "#cc-addr",   "label": "Billing address", "field": "card-billing-address" }
], "message": "Enter your card details to complete checkout" }
```

## Notes

- `length`/`format` are **per field**; in a multi-field request each entry sets
  its own.
- They are advisory client-side aids. The service inserts exactly what the user
  typed; it does not re-validate against `format` server-side.
- Choosing a good `label`, `length`, and `format` improves the user's confidence
  and reduces input errors — prefer setting them when you know the value's shape.
