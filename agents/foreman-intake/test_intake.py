"""Local tests for the FOREMAN Intake gatekeeper - the five required scenarios.

These run FULLY OFFLINE and deterministically: the LLM extraction, the reply
phrasing, and the Data Fabric asset lookup are injected as fakes, so the tests
exercise the real gatekeeper DECISION logic (presence -> complete -> missing ->
reply) and the real validation wiring without credentials or network.

Run either way:
    uv run python test_intake.py        # plain runner, prints PASS/FAIL, exits non-zero on failure
    uv run pytest test_intake.py        # if pytest is installed

Scenarios:
  a) media only                  -> missing issue + asset
  b) + issue text                -> missing asset
  c) + valid asset id            -> complete, site_id populated (issue carried forward)
  d) everything in one message   -> complete
  e) invalid/unknown asset id    -> not complete, reply asks to re-check
"""

import asyncio

from main import Extraction, GraphInput, evaluate_intake, _fallback_reply

# --- Fakes -------------------------------------------------------------------

# Known-good asset in the live Data Fabric Asset entity (assetid -> siteid).
_KNOWN = {"AST-PDU-DEL-0512": "DEL-0512"}


def make_extract(issue_text="", asset_id="", asset_type="", site_hint=""):
    """A fake LLM extractor that returns a fixed Extraction (simulating the model)."""

    async def _extract(latest_message, current_issue_text):
        # mirror the real wrapper's carry-forward when the model finds no new issue
        return Extraction(
            issue_text=issue_text or (current_issue_text or ""),
            asset_id=asset_id,
            asset_type=asset_type,
            site_hint=site_hint,
        )

    return _extract


def fake_validate(explicit_id, asset_type, site_hint):
    """A fake Data Fabric validator: exact id lookup + one NL (PDU @ DEL) match."""
    if explicit_id:
        return (explicit_id, _KNOWN[explicit_id]) if explicit_id in _KNOWN else ("", "")
    if (not explicit_id) and asset_type == "power_distribution_unit" and site_hint.upper().startswith("DEL"):
        return "AST-PDU-DEL-0512", "DEL-0512"
    return "", ""


async def echo_reply(missing, issue_text, bad_asset):
    """A fake reply composer that echoes the core's decision so we can assert on it."""
    return f"ASK missing={','.join(missing)} bad_asset={bad_asset!r}"


def _run(state, *, extract):
    return asyncio.run(
        evaluate_intake(state, extract=extract, validate=fake_validate, compose_reply=echo_reply)
    )


# --- The five scenarios ------------------------------------------------------


def test_a_media_only_missing_issue_and_asset():
    out = _run(
        GraphInput(latest_message="", has_media=True),
        extract=make_extract(),  # media-only: nothing extracted
    )
    assert out.complete is False
    assert out.missing == ["issue", "asset"]  # media present, so not listed
    assert out.asset_verified is False
    assert out.asset_id == "" and out.site_id == ""
    assert out.reply_message  # a reply is sent
    return out


def test_b_issue_text_missing_asset():
    out = _run(
        GraphInput(latest_message="The PDU is sparking and smells burnt", has_media=True),
        extract=make_extract(issue_text="The PDU is sparking and smells burnt"),
    )
    assert out.complete is False
    assert out.missing == ["asset"]
    assert out.issue_text == "The PDU is sparking and smells burnt"
    assert out.asset_verified is False
    assert out.reply_message
    return out


def test_c_valid_asset_id_completes_with_site():
    # Idempotent carry-forward: issue came from a previous message (current_issue_text).
    out = _run(
        GraphInput(
            latest_message="it's AST-PDU-DEL-0512",
            has_media=True,
            current_issue_text="The PDU is sparking and smells burnt",
        ),
        extract=make_extract(asset_id="AST-PDU-DEL-0512"),
    )
    assert out.complete is True
    assert out.missing == []
    assert out.asset_id == "AST-PDU-DEL-0512"
    assert out.site_id == "DEL-0512"  # site_id populated from the matched record
    assert out.asset_verified is True
    assert out.issue_text == "The PDU is sparking and smells burnt"  # carried forward
    assert out.reply_message == ""  # nothing to ask
    return out


def test_d_everything_in_one_message_completes():
    out = _run(
        GraphInput(latest_message="The PDU AST-PDU-DEL-0512 is sparking", has_media=True),
        extract=make_extract(issue_text="The PDU is sparking", asset_id="AST-PDU-DEL-0512"),
    )
    assert out.complete is True
    assert out.missing == []
    assert out.asset_id == "AST-PDU-DEL-0512"
    assert out.site_id == "DEL-0512"
    assert out.asset_verified is True
    assert out.reply_message == ""
    return out


def test_e_unknown_asset_id_not_complete_and_reply_asks_recheck():
    out = _run(
        GraphInput(
            latest_message="it's AST-XXX-9999",
            has_media=True,
            current_issue_text="The PDU is sparking",
        ),
        extract=make_extract(asset_id="AST-XXX-9999"),
    )
    assert out.complete is False
    assert out.missing == ["asset"]
    assert out.asset_verified is False
    assert out.asset_id == "" and out.site_id == ""  # never echo an unvalidated id
    # the core flagged the bad asset so the reply can ask the worker to re-check it
    assert "AST-XXX-9999" in out.reply_message
    # and the real (LLM-free) phrasing fallback also surfaces the re-check ask
    fb = _fallback_reply(["asset"], "AST-XXX-9999")
    assert "AST-XXX-9999" in fb and "double-check" in fb
    return out


_TESTS = [
    ("a) media only -> missing issue + asset", test_a_media_only_missing_issue_and_asset),
    ("b) + issue text -> missing asset", test_b_issue_text_missing_asset),
    ("c) + valid asset id -> complete (+site_id)", test_c_valid_asset_id_completes_with_site),
    ("d) everything in one message -> complete", test_d_everything_in_one_message_completes),
    ("e) unknown asset id -> reply asks re-check", test_e_unknown_asset_id_not_complete_and_reply_asks_recheck),
]


if __name__ == "__main__":
    failures = 0
    for label, fn in _TESTS:
        try:
            out = fn()
            print(f"PASS  {label}")
            print(
                f"      -> complete={out.complete} missing={out.missing} "
                f"asset_id={out.asset_id!r} site_id={out.site_id!r} reply={out.reply_message!r}"
            )
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {label}\n      {exc!r}")
    print(f"\n{len(_TESTS) - failures}/{len(_TESTS)} passed")
    raise SystemExit(1 if failures else 0)
