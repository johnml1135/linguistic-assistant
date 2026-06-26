"""Report generator — turn an evidence packet into a ``ParadigmReport``.

Two backends behind one ``generate()``:
  * ``heuristic`` — deterministic, offline; reads the packet's ranked hypotheses straight into cells. This
    is the *weak baseline generator* the loop is meant to beat (and the smoke-test generator, so we never
    score opus-vs-opus and sit at ceiling — see plan §4).
  * an LLM endpoint (``gemma``/``opus``/``vllm``/…) via the swappable ``propose.harness`` client — Gemma
    reads the packet ONLY and writes the structured report + prose for Opus.

Both emit the same ``ParadigmReport`` schema so the scorer compares apples to apples.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[2]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

from review.paradigm.schema import Cell, Citation, ParadigmReport, REPORT_JSON_SCHEMA  # noqa: E402

SYSTEM_PROMPT = (
    "You are a field linguist's assistant. You are given an EVIDENCE PACKET assembled from a parallel "
    "corpus by two tools: HC (a morphological parser) and THOT (a word-alignment model), plus a ranked "
    "A/B/C hypothesis explorer. Your job: decide whether the named grammatical paradigm is present, and "
    "if so lay out its cells, what conditions any allomorphy, and what does NOT fit.\n\n"
    "HARD RULE: reason ONLY from the packet. Do NOT use anything you happen to know about this specific "
    "language — no recalled case inventories, no remembered class semantics. If the packet does not "
    "support a cell, you may not assert it. Cite the packet stat behind every claim. Write the `prose` "
    "field as a tight report a senior reviewer (Opus) will adjudicate: lead with the call (detected or "
    "not + confidence), then the cells with their evidence, then the residue and what you're unsure of."
)


def _user_prompt(packet: dict) -> str:
    return (f"PARADIGM IN QUESTION: {packet.get('paradigm_type')}\n"
            f"LANGUAGE CODE: {packet.get('language')}\n"
            f"QUESTION: {packet.get('question', '')}\n\n"
            f"EVIDENCE PACKET (JSON):\n{json.dumps(packet, ensure_ascii=False, indent=1)}\n\n"
            "Return a ParadigmReport object matching the schema.")


# --------------------------------------------------------------------------- heuristic (offline baseline)
def heuristic_report(packet: dict) -> ParadigmReport:
    """Deterministic report straight from the packet — the weak baseline generator."""
    lang = packet["language"]
    ptype = packet["paradigm_type"]
    if ptype == "noun-class":
        return _heuristic_noun_class(packet)
    # generic fallback: report the top hypotheses as cells with no synthesis
    hyps = packet.get("hypotheses", {}).get("hypotheses", [])
    cells = [Cell(label=h.get("label", "?"), markers=h.get("prefixes", []),
                  function="", support=h.get("n_explained", 0), examples=h.get("examples", []))
             for h in hyps[:8]]
    return ParadigmReport(language=lang, paradigm_type=ptype, detected=bool(cells),
                          confidence=0.4, cells=cells,
                          fit_none=packet.get("hypotheses", {}).get("fit_none", {"n": 0, "examples": []}),
                          prose=f"Heuristic: {len(cells)} candidate cells for {ptype} in {lang}.")


def _heuristic_noun_class(packet: dict) -> ParadigmReport:
    """Braid ALL THREE evidence streams into cells — class groups (HC), concord-only classes (THOT votes),
    and strong residue patterns (the 'another pattern?' probe). A class is real if a prefix group OR a
    dominant concord vote OR a recurring residue affix supports it; reporting only the first stream
    (as the naive baseline did) silently drops concord-only and locative classes."""
    lang = packet["language"]
    hyps = packet["hypotheses"]["hypotheses"]
    concord = {r["noun_prefix"]: r for r in packet["agreement"]["rows"]}
    cells = []
    seen_markers: set[str] = set()
    # stream 1: prefix class groups (HC/recover)
    for h in hyps:
        prefixes = h.get("prefixes", [])
        markers = list(prefixes)
        func_bits = []
        for p in prefixes:
            r = concord.get(p)
            if r and r["candidates"]:
                func_bits.append(f"{p}->concord {r['candidates'][0]['marker']} ({r['candidates'][0]['share']})")
        seen_markers |= {m.lower().strip("-") for m in markers}
        cells.append(Cell(label=h.get("label", "?"), markers=markers,
                          function="; ".join(func_bits), support=h.get("n_explained", 0),
                          examples=h.get("examples", [])))
    # stream 2: concord-only classes (THOT) — a class with a dominant concord vote not yet in any group
    for pfx, r in concord.items():
        if not r["candidates"] or r["candidates"][0]["share"] < 0.5:
            continue
        if pfx.lower().strip("-") in seen_markers:
            continue
        top = r["candidates"][0]
        seen_markers.add(pfx.lower().strip("-"))
        cells.append(Cell(label=f"{pfx}- class (concord {top['marker']})",
                          markers=[pfx, top["marker"]],
                          function=f"concord-defined class: {pfx}->{top['marker']} (share {top['share']})",
                          support=top["support"], examples=[]))
    # stream 3: strong residue affixes (the 'another pattern?' probe) — recurring, stem-attested
    for p in packet.get("residue", {}).get("patterns", []):
        if p.get("n_real", 0) < 8:
            continue
        if p["pattern"].lower().strip("-") in seen_markers:
            continue
        seen_markers.add(p["pattern"].lower().strip("-"))
        cells.append(Cell(label=f"{p['pattern']} {p['side']} pattern (residue)",
                          markers=[p["pattern"]],
                          function=f"recurring {p['side']} in residue, {p['n_real']} stems attested",
                          support=p["n"], examples=p.get("examples", [])))
    hc = packet["hc"]
    cites = [
        Citation(claim="prefixal class grouping exists", source="hc",
                 stat=f"{hc['n_classified']}/{hc['n_nouns']} nouns classified ({hc['frac_classified']})"),
        Citation(claim="classes trigger concord agreement", source="thot",
                 stat=f"{packet['thot']['n_classes_with_concord']}/{packet['thot']['n_classes_voting']} "
                      f"classes have a dominant concord marker"),
    ]
    fit_none = packet["hypotheses"]["fit_none"]
    detected = len(cells) >= 2 and packet["thot"]["n_classes_with_concord"] >= 2
    prose = (f"{lang}: prefixal noun-class system DETECTED. {len(cells)} class groups, "
             f"{hc['frac_classified']} of nouns classified, "
             f"{packet['thot']['n_classes_with_concord']} classes with dominant concord. "
             f"Residue: {fit_none['n']} nouns fit no class.")
    return ParadigmReport(language=lang, paradigm_type="noun-class", detected=detected,
                          confidence=0.6 if detected else 0.3, cells=cells, conditioning="phonology",
                          fit_none=fit_none, evidence_citations=cites, prose=prose)


# --------------------------------------------------------------------------- LLM backend (Gemma/opus/…)
def llm_report(packet: dict, endpoint: str | None = None, client=None) -> ParadigmReport:
    """Run the LLM path: prompt -> client.complete(json_schema) -> json.loads -> tolerant from_dict.
    Pass an explicit `client` to inject a mock; otherwise `endpoint` is resolved via propose.harness."""
    from propose.harness.base import Message
    if client is None:
        from propose.harness.registry import build_client
        client = build_client(endpoint)
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=_user_prompt(packet))]
    res = client.complete(messages, max_tokens=2048, json_schema=REPORT_JSON_SCHEMA)
    data = json.loads(res.text)
    data.setdefault("language", packet["language"])
    data.setdefault("paradigm_type", packet["paradigm_type"])
    return ParadigmReport.from_dict(data)


def generate(packet: dict, endpoint: str | None = None, client=None) -> ParadigmReport:
    """Generate a report. endpoint None/'heuristic' (and no client) -> deterministic baseline; else the
    LLM path (resolved endpoint, or an injected `client`)."""
    if client is None and endpoint in (None, "heuristic"):
        return heuristic_report(packet)
    return llm_report(packet, endpoint, client=client)
