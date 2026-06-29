"""FOREMAN — foreman-cost (STUB agent).

Present for completeness; NOT invoked in the MC4 demo. No Data Fabric, no LLM,
no external calls. Returns a STATIC, contract-valid response regardless of input.

Verdict rationale: a charred connector is a safety-critical part — it is always
cut out and replaced, so there is no whole-life repair-vs-replace trade-off to
compute. The cost model collapses to a fixed "replace" decision.

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
    fix: str = ""


class Output(BaseModel):
    """Strict output: no extra keys permitted."""

    model_config = ConfigDict(extra="forbid")

    decision: str = "replace"
    whole_life_cost: float = 0.0
    capex_flag: bool = False
    rationale: str = ""
    error: str = ""


# State is the contract itself; the single node fills the static Output.
class State(Input, Output):
    model_config = ConfigDict(extra="ignore")


# --- Node ------------------------------------------------------------------
async def cost_stub(state: State) -> Output:
    """Return the fixed, contract-valid cost verdict for the MC4 defect case.

    Deterministic (no DF/LLM/external) and never throws. Input is ignored: a
    charred connector is always replaced, so there is no repair-vs-replace
    trade-off and the whole-life cost model is not exercised.
    """
    return Output(
        decision="replace",
        whole_life_cost=0.0,
        capex_flag=False,
        rationale=(
            "a charred connector is always cut out and replaced - "
            "no repair-vs-replace trade-off"
        ),
        error="",
    )


# --- Graph -----------------------------------------------------------------
builder = StateGraph(State, input=Input, output=Output)
builder.add_node("cost_stub", cost_stub)
builder.add_edge(START, "cost_stub")
builder.add_edge("cost_stub", END)

graph = builder.compile()
