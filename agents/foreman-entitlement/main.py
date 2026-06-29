"""FOREMAN — foreman-entitlement (STUB agent).

Present for completeness; NOT invoked in the MC4 demo. No Data Fabric, no LLM,
no external calls. Returns a STATIC, contract-valid response regardless of input.

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
    site_id: str = ""
    root_cause: str = ""


class Output(BaseModel):
    """Strict output: no extra keys permitted."""

    model_config = ConfigDict(extra="forbid")

    vendor: str = ""
    warranty_active: bool = False
    vendor_liable: bool = False
    claim_basis: str = ""
    recovery_inr: float = 0.0
    error: str = ""


# State is the contract itself; the single node fills the static Output.
class State(Input, Output):
    model_config = ConfigDict(extra="ignore")


# --- Node ------------------------------------------------------------------
async def entitlement_stub(state: State) -> Output:
    """Return the static, contract-valid verdict. Never throws."""
    return Output(
        vendor="",
        warranty_active=False,
        vendor_liable=False,
        claim_basis="field workmanship - not a claimable vendor/spec defect",
        recovery_inr=0.0,
        error="",
    )


# --- Graph -----------------------------------------------------------------
builder = StateGraph(State, input=Input, output=Output)
builder.add_node("entitlement_stub", entitlement_stub)
builder.add_edge(START, "entitlement_stub")
builder.add_edge("entitlement_stub", END)

graph = builder.compile()
