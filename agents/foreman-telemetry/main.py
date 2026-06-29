"""FOREMAN — foreman-telemetry (STUB agent).

Present for completeness; NOT invoked in the MC4 demo. No Data Fabric, no LLM,
no external calls. Returns a STATIC, contract-valid response regardless of input.

The connector already melted — there is no incipient signal left to trend, so
the static verdict reports a hard failure with zero remaining useful life.

Conventions: strict JSON out (pydantic-validated, no prose, no extra keys),
async, never throws.
"""

from langgraph.graph import START, StateGraph, END
from pydantic import BaseModel, ConfigDict


# --- Contract --------------------------------------------------------------
class Input(BaseModel):
    """All fields optional / tolerant — input is ignored by this stub."""

    model_config = ConfigDict(extra="ignore")

    asset_id: str = ""
    fault: str = ""


class Output(BaseModel):
    """Strict output: no extra keys permitted."""

    model_config = ConfigDict(extra="forbid")

    trend: str = ""
    anomaly_score: float = 0.0
    remaining_useful_life: str = ""
    corroborates_perception: bool = False
    fix_now_or_schedule: str = ""
    error: str = ""


# State is the contract itself; the single node fills the static Output.
class State(Input, Output):
    model_config = ConfigDict(extra="ignore")


# --- Node ------------------------------------------------------------------
async def telemetry_stub(state: State) -> Output:
    """Return the static, contract-valid verdict. Never throws."""
    return Output(
        trend="hard-failed (no incipient signal)",
        anomaly_score=1.0,
        remaining_useful_life="0 (already failed)",
        corroborates_perception=True,
        fix_now_or_schedule="now",
        error="",
    )


# --- Graph -----------------------------------------------------------------
builder = StateGraph(State, input=Input, output=Output)
builder.add_node("telemetry_stub", telemetry_stub)
builder.add_edge(START, "telemetry_stub")
builder.add_edge("telemetry_stub", END)

graph = builder.compile()
