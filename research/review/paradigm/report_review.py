"""Report-review step — the trunk's decision stage (Opus-as-Reviewer). Takes a generated ParadigmReport +
its evidence packet and returns a per-cell verdict (promote | defer | reject), under the firewall: decide
ONLY from packet evidence, never recalled language knowledge.

Two backends behind one `review_report()`:
  * `heuristic` — deterministic, evidence-gated: a cell is promoted if its markers are backed by the
    packet (and, for role-bearing cells, the role is consistent); deferred if support is thin; REJECTED if
    its markers are absent from the packet (a hallucination). The offline baseline.
  * an LLM endpoint (opus/local) — the firewall reviewer reads the packet + report and adjudicates.

This is the report-level analogue of the delta store's confidence routing (accept/review/defer).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review.paradigm import score as SC          # noqa: E402
from review.paradigm.schema import ParadigmReport  # noqa: E402

REVIEW_SYSTEM = (
    "You are Opus-as-Reviewer. Decide, for each cell of a grammatical paradigm report, whether to PROMOTE "
    "(accept into the grammar), DEFER (needs more data / human), or REJECT (not supported). FIREWALL: use "
    "ONLY the evidence packet provided — never anything you recall about this specific language. Reject any "
    "cell whose markers are not in the packet. Return a JSON object {verdicts: [{cell, decision, why}], "
    "summary}."
)


def heuristic_review(report: ParadigmReport, packet: dict) -> dict:
    """Evidence-gated verdicts (the offline firewall baseline)."""
    pm = SC.packet_markers(packet)
    role_cells = [c for c in packet.get("cells", []) if isinstance(c, dict) and c.get("role")]
    verdicts = []
    for cell in report.cells:
        cms = SC._markers(cell)
        in_packet = bool(cms & pm)
        # support: explicit, or a packet family's strength
        share = 0.0
        for c in role_cells:
            if cms & {SC._norm(m) for m in c.get("markers", [])}:
                share = max(share, float(c.get("share", 0) or 0))
        support = int(getattr(cell, "support", 0) or 0)
        if not in_packet:
            decision, why = "reject", "markers absent from the packet (unsupported / hallucinated)"
        elif support >= 30 or share >= 0.7:
            decision, why = "promote", f"well-supported in packet (support={support}, share={share})"
        elif support >= 6 or share >= 0.4 or cms:
            decision, why = "promote", f"backed by packet evidence (support={support}, share={share})"
        else:
            decision, why = "defer", "thin support — defer for more data"
        verdicts.append({"cell": cell.label, "decision": decision, "why": why})
    promoted = [v for v in verdicts if v["decision"] == "promote"]
    rejected = [v for v in verdicts if v["decision"] == "reject"]
    return {"language": report.language, "paradigm_type": report.paradigm_type, "verdicts": verdicts,
            "n_promote": len(promoted), "n_defer": len(verdicts) - len(promoted) - len(rejected),
            "n_reject": len(rejected),
            "recommendation": ("promote" if report.detected and promoted and not rejected
                               else "review" if promoted else "reject")}


def llm_review(report: ParadigmReport, packet: dict, endpoint: str) -> dict:
    from propose.harness.base import Message
    from propose.harness.registry import build_client
    client = build_client(endpoint)
    schema = {"type": "object", "properties": {
        "verdicts": {"type": "array", "items": {"type": "object", "properties": {
            "cell": {"type": "string"}, "decision": {"type": "string", "enum": ["promote", "defer", "reject"]},
            "why": {"type": "string"}}, "required": ["cell", "decision"]}},
        "summary": {"type": "string"}}, "required": ["verdicts"]}
    user = (f"REPORT:\n{json.dumps(report.to_dict(), ensure_ascii=False)}\n\n"
            f"EVIDENCE PACKET:\n{json.dumps(packet, ensure_ascii=False)[:6000]}")
    extra = {}
    try:
        from propose.harness.openai_compat import OpenAICompatClient
        if isinstance(client, OpenAICompatClient):
            extra["chat_template_kwargs"] = {"enable_thinking": False}
    except Exception:
        pass
    res = client.complete([Message(role="system", content=REVIEW_SYSTEM), Message(role="user", content=user)],
                          max_tokens=4000, json_schema=schema, **extra)
    from review.paradigm.report import _extract_json
    d = _extract_json(res.text, getattr(res, "reasoning", "") or "")
    vs = d.get("verdicts", [])
    nP = sum(1 for v in vs if v.get("decision") == "promote")
    nR = sum(1 for v in vs if v.get("decision") == "reject")
    return {"language": report.language, "paradigm_type": report.paradigm_type, "verdicts": vs,
            "n_promote": nP, "n_defer": len(vs) - nP - nR, "n_reject": nR,
            "recommendation": d.get("summary", "promote" if nP and not nR else "review")}


def review_report(report: ParadigmReport, packet: dict, endpoint: str | None = None) -> dict:
    if endpoint in (None, "heuristic"):
        return heuristic_review(report, packet)
    return llm_review(report, packet, endpoint)
