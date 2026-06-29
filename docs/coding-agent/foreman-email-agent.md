---
name: foreman-email-agent
description: foreman-email — fast-LLM composes incident-summary email + Gmail SMTP send with 3 attachments; FLATTENED input (supervisor+voice outputs 1:1)
metadata: 
  node_type: memory
  type: project
  originSessionId: f8307778-eb6b-40ea-be33-7ab0a64203d3
---

foreman-email is the LAST step of the FOREMAN fleet (uipath-langchain/LangGraph, `compose → send`). Built & dry-run-verified.

- **Input is FLATTENED, not bundled dicts.** Supervisor/voice agents expose each output as its own field (confirmed by user's Studio Web screenshots), so Input mirrors them 1:1: supervisor → case, diagnosis, risk, safety_gate, auto_resolve_blocked, invoked, not_invoked, action_plan, summary, worker_message, report_url, errors; voice → spoken_opener, spoken_recommendation, transcript, decision, call_sid, call_to(=voice `to`), call_from(=voice `from_`); plus email config (decision_context, recipients, cc, media_blob_path, media_bucket=foremenbucket, media_folder="Shared/foremen v1", max_attachment_mb=24, dry_run). Internally `_supervisor_dict`/`_voice_dict` re-bundle for the shape-driven extractor.
- **compose**: UiPathChat gpt-4.1-mini-2025-04-14 → STRICT JSON {subject, body}; body starts "Summary of the episode for everyone involved." + labeled lines (Report/Root cause/Systemic/Decision/Actions/Warranty/Full SOP). Fallback subject="[<asset_id>] Case summary", body=summary. Never throws.
- **send**: MIMEMultipart; 3 attachments each size-guarded (max_attachment_mb) + individually fault-tolerant (skip → note in `error`, never block rest): (a) SOP PDF httpx.get(report_url), (b) call-transcript.txt built in-memory→temp file, (c) video via `sdk.buckets.download_async` (NOTE: SDK has NO `get_read_uri`; download to temp instead). SMTP smtp.gmail.com:587 STARTTLS.
- **Gmail auth** env-first then Shared Assets: GMAIL_USER|Gmail-User, GMAIL_APP_PASSWORD|Gmail-App-Password (a Google App Password, needs 2FA). Wired into .env as placeholders. Same auth-token-gotcha applies for bucket fetch ([[foreman-auth-token-gotcha]]).
- Orchestrated by [[foreman-supervisor-v1-agent]]; consumes [[foreman-voice-agent]] output. Gotcha: Orchestrator SAS report_url expires in minutes → PDF skipped gracefully on stale link.
