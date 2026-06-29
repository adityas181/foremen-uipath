# FOREMAN Email agent

The last step of the FOREMAN fleet. Takes the **foreman-supervisor** outputs and
the **foreman-voice** outputs, uses a fast LLM (`UiPathChat gpt-4.1-mini`) to
COMPOSE a stakeholder incident-summary email (subject + body), and sends it via
**Gmail SMTP** with up to three attachments:

1. **SOP / report PDF** — fetched from `report_url`.
2. **call-transcript.txt** — generated in-memory from the voice fields.
3. **worker's video** — fetched from a UiPath Storage Bucket (`media_*`).

`compose → send`. Never throws — on any failure it returns the contract with a
non-empty `error`; a single bad attachment is skipped (noted in `error`) and never
blocks the rest of the send.

---

## Input — flattened to match the upstream nodes

The supervisor and voice agents expose **each output as its own field** (not one
bundled object), so this agent's Input mirrors them 1:1. In a Maestro flow every
field can be dragged straight from the upstream node.

**From foreman-supervisor:** `case`, `diagnosis`, `risk`, `safety_gate`,
`auto_resolve_blocked`, `invoked`, `not_invoked`, `action_plan`, `summary`,
`worker_message`, `report_url`, `errors`.

**From foreman-voice:** `spoken_opener`, `spoken_recommendation`, `transcript`,
`decision`, `call_sid`, `call_to` (voice `to`), `call_from` (voice `from_`).

**Email config:** `decision_context` (override the decision text; else uses voice
`decision`), `recipients` (comma-separated To), `cc`, `media_blob_path`,
`media_bucket` (default `foremenbucket`), `media_folder` (default
`Shared/foremen v1`), `max_attachment_mb` (default 24), `dry_run`.

## Output

`subject`, `body`, `attached` (filenames attached), `sent`, `error`.

---

## Auth — Gmail (env-first, then Assets)

Credentials are read **env-first**, then lazily from UiPath **Assets in folder
`Shared`**. A local `.env` run needs no UiPath connection for SMTP.

| env var              | Asset name (folder `Shared`) |
| -------------------- | ---------------------------- |
| `GMAIL_USER`         | `Gmail-User`                 |
| `GMAIL_APP_PASSWORD` | `Gmail-App-Password`         |

`GMAIL_APP_PASSWORD` is a **Google App Password** — NOT the account login. To get
one: enable 2-Step Verification on the Google account, then Google Account →
Security → App passwords → generate a 16-character password.

### Local run (env)

Already wired in `.env` — replace the placeholders:

```
GMAIL_USER=youraddress@gmail.com
GMAIL_APP_PASSWORD=your16charapppassword
```

### Cloud run (Assets)

Create two Text assets in folder `Shared`:

```
uipath assets create Gmail-User --folder-path Shared --value youraddress@gmail.com
uipath assets create Gmail-App-Password --folder-path Shared --value your16charapppassword
```

(Or create them in the Orchestrator UI — Assets → Add.)

> The video attachment fetch uses the UiPath SDK (`buckets.download_async`), which
> needs a live UiPath session. If `media_blob_path` is empty the bucket is never
> touched, so `dry_run` / SMTP-only runs need no UiPath auth. If you hit `401`s on
> the bucket fetch, an expired `UIPATH_ACCESS_TOKEN` in `.env` is shadowing the
> live session — comment it out so the SDK uses the auto-refreshing
> `.uipath/.auth.json`.

---

## Sample input

A ready-made `input.json` is checked in (supervisor `out.json` flattened + a sample
voice result). Build your own the same way: drop each supervisor/voice output into
the matching field.

## Run

```bash
# Compose + build attachments, DO NOT send (set "dry_run": true in the input)
uv run uipath run agent --file input.json --output-file out.json

# Real send: set "dry_run": false and fill recipients + Gmail creds
uv run uipath run agent --file input.json --output-file out.json
```

## Acceptance

- **`dry_run: true`** returns a JSON-clean `subject` and `body` (body starts with
  `Summary of the episode for everyone involved.` followed by the labeled lines —
  Report / Root cause / Systemic / Decision / Actions / Warranty; no SOP URL, since
  the PDF is attached). The sent email is `multipart/alternative` — this plain
  `body` plus a styled HTML version (accented section cards, Actions as a bullet
  list). The output also includes an `attached` list naming the PDF,
  `call-transcript.txt`, and the `.mp4`
  (each attachment present only if its source is reachable and within
  `max_attachment_mb`; otherwise it is skipped with a note in `error`).
- **Real run** (`dry_run: false`, valid `recipients` + Gmail creds) sends the email
  with those attachments and returns `sent: true`.

> Note: a SOP PDF behind an Orchestrator SAS link is only valid for a few minutes —
> if it has expired the PDF is skipped (`PDF fetch failed ... skipped`) while the
> rest of the email still sends. Use a fresh `report_url` from a live supervisor run.
