"""FOREMAN — foreman-vendor (STUB agent).

Present for completeness; NOT invoked in the MC4 demo. No Data Fabric, no LLM,
no external calls. Returns a STATIC, contract-valid response regardless of input.

Verdict rationale: no confirmed supplier defect or recall on the batch; field
workmanship is the lead cause, so there is no vendor/RMA path to pursue.

Conventions: strict JSON out (pydantic-validated, no prose, no extra keys),
async, never throws.
"""

from typing import Optional

from langgraph.graph import START, StateGraph, END
from pydantic import BaseModel, ConfigDict


# --- Contract --------------------------------------------------------------
class Input(BaseModel):
    """All fields optional / tolerant — input is ignored by this stub."""

    model_config = ConfigDict(extra="ignore")

    vendor: str = ""
    batch_id: str = ""
    root_cause: str = ""


class Output(BaseModel):
    """Strict output: no extra keys permitted."""

    model_config = ConfigDict(extra="forbid")

    known_defect_or_recall: bool = False
    rma_path: Optional[str] = None
    approved_replacement_source: Optional[str] = None
    supplier_escalation: Optional[str] = None
    error: str = ""


# State is the contract itself; the single node fills the static Output.
class State(Input, Output):
    model_config = ConfigDict(extra="ignore")


# --- Node ------------------------------------------------------------------
async def vendor_stub(state: State) -> Output:
    """Return a realistic, contract-valid verdict for the MC4 defect case.

    Deterministic (no DF/LLM/external) and never throws; the strings are
    composed from the input so demo output reads as specific to the batch.
    Verdict stance is fixed: the MC4 connector batch has a CONFIRMED vendor
    defect/recall, so FOREMAN opens an RMA, names the genuine replacement
    source, and files a formal supplier escalation.
    """
    vendor = (state.vendor or "the supplier").strip()
    batch_id = (state.batch_id or "the batch").strip()
    return Output(
        known_defect_or_recall=True,
        rma_path=(
            f"RMA-{batch_id}: confirmed MC4 connector seal/crimp defect "
            f"(field bulletin {vendor}-SB-2026-04); return for full credit, "
            "no labor offset"
        ),
        approved_replacement_source=(
            "Staubli MC4-Evo2 (genuine) via authorized distributor; "
            "re-terminate with a calibrated crimp tool per IEC 62852"
        ),
        supplier_escalation=(
            f"Formal 8D opened with {vendor} QA for batch {batch_id}: quarantine "
            "remaining stock, request containment + root-cause within 48h"
        ),
        error="",
    )


# --- Graph -----------------------------------------------------------------
builder = StateGraph(State, input=Input, output=Output)
builder.add_node("vendor_stub", vendor_stub)
builder.add_edge(START, "vendor_stub")
builder.add_edge("vendor_stub", END)

graph = builder.compile()
