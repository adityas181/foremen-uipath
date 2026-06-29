"""FOREMAN Voice webhook server (drives the live two-way phone conversation).

A tiny, SELF-CONTAINED FastAPI app that Twilio calls back into while a call is in
progress. The ``foreman-voice`` agent first POSTs the spoken brief + recommendation
here (keyed by a token), then rings the manager pointing at ``/voice?token=...``.
From there Twilio walks a 3-turn conversation entirely off this server's TwiML, and
the agent polls ``/decision`` for the outcome.

Conversation
  /voice    turn 1 — <Say> the brief, then <Gather> the manager's reply
  /respond  turn 2 — log the reply, <Say> the recommendation, <Gather> "Do you approve?"
  /decide   turn 3 — read the answer, decide approved/hold, confirm and hang up
  /decision (the agent polls this) — {status, decision, transcript}

Decision rule (safety-first): HOLD words are checked BEFORE approve words, and any
ambiguous or silent answer falls back to HOLD — we NEVER auto-authorise.

State lives in a single in-memory dict keyed by token, so run ONE instance. There
are deliberately NO external UI-push / backend calls — the server is standalone.

Run ephemerally (port 8090):
  uv run --with fastapi --with "uvicorn[standard]" python voice_server.py
"""

from __future__ import annotations

from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape, quoteattr

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="foreman-voice webhook")

# token -> {message, recommendation, language, status, decision, transcript[]}
SESSIONS: dict[str, dict] = {}

# Spoken-answer classification. HOLD is checked first and wins ties; anything
# ambiguous or silent also resolves to HOLD so we never auto-approve.
HOLD_WORDS = ("hold", "no", "wait", "stop", "don't", "dont", "deny", "stand down")
APPROVE_WORDS = ("approve", "yes", "go ahead", "do it", "proceed", "authorise", "authorize")

# Speak a little slower than default. Applied via SSML <prosody rate>, which only
# takes effect with Amazon Polly voices (e.g. "Polly.Aditi") — legacy "alice" ignores it.
SPEECH_RATE = "95%"

# How long to wait (seconds of trailing silence) before treating the manager's reply as
# finished. "auto" cuts off on the first short pause; a fixed value lets them finish a
# full sentence. Raise it if FOREMAN still jumps in too soon.
SPEECH_TIMEOUT = "4"


def _twiml(body: str) -> Response:
    """Wrap a TwiML body in a <Response> document with the right content type."""
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'
    return Response(content=xml, media_type="application/xml")


def _say(text: str, language: str, voice: str = "alice") -> str:
    inner = xml_escape(text or "")
    if SPEECH_RATE and SPEECH_RATE != "100%":
        inner = f"<prosody rate={quoteattr(SPEECH_RATE)}>{inner}</prosody>"
    return (
        f"<Say voice={quoteattr(voice or 'alice')} "
        f'language="{xml_escape(language or "en-IN")}">{inner}</Say>'
    )


def _gather(action: str, prompt: str, language: str, voice: str = "alice") -> str:
    """A speech <Gather> that fires ``action`` even on silence (actionOnEmptyResult).

    ``speechTimeout`` is a fixed number of seconds (not "auto") so a brief mid-sentence
    pause doesn't cut the manager off; ``timeout`` allows a few seconds to start speaking.
    """
    return (
        f'<Gather input="speech" speechTimeout="{xml_escape(SPEECH_TIMEOUT)}" '
        f'timeout="6" speechModel="phone_call" enhanced="true" '
        f'actionOnEmptyResult="true" method="POST" action="{xml_escape(action)}">'
        f"{_say(prompt, language, voice)}</Gather>"
    )


async def _speech_result(request: Request) -> str:
    """Pull Twilio's SpeechResult out of the posted form (empty string if absent)."""
    try:
        form = await request.form()
        return str(form.get("SpeechResult") or "").strip()
    except Exception:
        return ""


# Turn 2 is a FIXED demo script (not the LLM opener/recommendation) so the call speaks
# the exact approved transcript. Edit this string to change what FOREMAN says in turn 2.
TURN2_LINE = (
    "Thank you. Field engineer Varun found a melted MC4 connector — a DC-arc and fire "
    "risk — and the same install crew and connector lot put other strings at risk. I'd "
    "like to isolate the asset now, swap to matched-brand connectors, and open a crew "
    "audit on the rest. Do I have your approval?"
)


def _greeting(sess: dict) -> str:
    """Turn 1 opener: a polite, human greeting that asks for a moment + flags approval.

    Names the SITE ("operations agent for <site>") and the ASSET ("issue in asset
    <asset>"); each falls back to the other if one is missing.
    """
    who = (sess.get("to_role") or "").strip()
    site = (sess.get("site_id") or "").strip()
    asset = (sess.get("asset_id") or "").strip()
    name = "" if (not who or who.lower() in ("the manager", "manager")) else f" {who}"
    intro = f"Hello{name}, this is FOREMAN"
    for_id = site or asset
    if for_id:
        intro += f" — the operations agent for {for_id}"
    issue = "There's a slightly urgent safety issue"
    asset_mention = asset or site
    if asset_mention:
        issue += f" in asset {asset_mention}"
    issue += " that needs your approval."
    return f"{intro}. Is this a good time to talk? {issue}"


def _issue_only(opener: str) -> str:
    """Drop a leading 'This is FOREMAN about <id> — ' so it isn't spoken twice."""
    o = (opener or "").strip()
    if o.lower().startswith("this is foreman"):
        for sep in (" — ", " – ", " - ", ". ", ", "):
            i = o.find(sep)
            if 0 < i <= 70:
                rest = o[i + len(sep):].strip()
                return (rest[:1].upper() + rest[1:]) if rest else o
    return o


@app.post("/prepare")
async def prepare(request: Request) -> JSONResponse:
    """Store the brief + recommendation for a token before the call is placed."""
    body = await request.json()
    token = str(body.get("token") or "").strip()
    if not token:
        return JSONResponse({"ok": False, "error": "token required"}, status_code=400)
    SESSIONS[token] = {
        "message": body.get("message") or "",
        "recommendation": body.get("recommendation") or "",
        "language": body.get("language") or "en-IN",
        "voice": body.get("voice") or "alice",
        "case_id": body.get("case_id") or "",
        "to_role": body.get("to_role") or "",
        "asset_id": body.get("asset_id") or "",
        "site_id": body.get("site_id") or "",
        "status": "waiting",
        "decision": "",
        "transcript": [],
    }
    return JSONResponse({"ok": True, "token": token})


@app.api_route("/voice", methods=["GET", "POST"])
async def voice(token: str = "") -> Response:
    """Turn 1: read the brief, then listen for the manager's reply."""
    sess = SESSIONS.get(token)
    lang = sess["language"] if sess else "en-IN"
    if not sess:
        return _twiml(_say("Sorry, this call is not configured. Goodbye.", lang))
    voice = sess.get("voice", "alice")
    # Turn 1: greet, ask if it's a good time, flag that approval is needed; then listen.
    body = (
        _gather(f"/respond?token={quote(token, safe='')}", _greeting(sess), lang, voice)
        + _say("Sorry, I didn't catch that. I'll try again later. Goodbye.", lang, voice)
        + "<Hangup/>"
    )
    return _twiml(body)


@app.post("/respond")
async def respond(request: Request, token: str = "") -> Response:
    """Turn 2: log the reply, read the recommendation, ask for approval."""
    sess = SESSIONS.get(token)
    lang = sess["language"] if sess else "en-IN"
    if not sess:
        return _twiml(_say("Sorry, this call is not configured. Goodbye.", lang))
    voice = sess.get("voice", "alice")
    reply = await _speech_result(request)
    if reply:
        sess["transcript"].append(f"manager: {reply}")
    # Turn 2: fixed scripted line (see TURN2_LINE), then ask for approval and listen.
    body = (
        _gather(f"/decide?token={quote(token, safe='')}", TURN2_LINE, lang, voice)
        + _say("I didn't hear a decision, so I'll hold and not proceed. Goodbye.", lang, voice)
        + "<Hangup/>"
    )
    return _twiml(body)


@app.post("/decide")
async def decide(request: Request, token: str = "") -> Response:
    """Turn 3: classify the answer (HOLD-first, never auto-approve) and confirm."""
    sess = SESSIONS.get(token)
    lang = sess["language"] if sess else "en-IN"
    if not sess:
        return _twiml(_say("Sorry, this call is not configured. Goodbye.", lang))

    voice = sess.get("voice", "alice")
    answer = (await _speech_result(request)).lower()
    sess["transcript"].append(f"decision-answer: {answer or '(silence)'}")

    if any(w in answer for w in HOLD_WORDS):
        decision = "hold"
    elif any(w in answer for w in APPROVE_WORDS):
        decision = "approved"
    else:
        decision = "hold"  # ambiguous or silent -> never auto-authorise

    sess["decision"] = decision
    sess["status"] = "decided"

    confirm = (
        "Thank you. That's logged as authorised — we're proceeding now."
        if decision == "approved"
        else "Understood — I'll hold and not proceed, and flag this for review. Thank you."
    )
    return _twiml(_say(confirm, lang, voice) + "<Hangup/>")


@app.get("/decision")
async def decision(token: str = "") -> JSONResponse:
    """The agent polls this until status == 'decided'."""
    sess = SESSIONS.get(token)
    if not sess:
        return JSONResponse({"status": "waiting", "decision": "", "transcript": []})
    return JSONResponse(
        {
            "status": sess["status"],
            "decision": sess["decision"],
            "transcript": sess["transcript"],
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090)
