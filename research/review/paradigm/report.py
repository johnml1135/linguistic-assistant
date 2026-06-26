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
import re
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
    "support a cell, you may not assert it. Cite the packet stat behind every claim.\n\n"
    "A cell (class/case/voice) can be evidenced THREE ways — use ALL of them, not just the first:\n"
    "  (1) a prefix/suffix GROUP in `hypotheses` (the orthographic grouping);\n"
    "  (2) a dominant CONCORD/agreement vote in `agreement.rows` — a marker with high `share` defines a "
    "real class even if it has no prefix group;\n"
    "  (3) a recurring affix in `residue.patterns` with high `n_real` — a pattern the grouping missed "
    "(e.g. a locative suffix).\n"
    "Enumerate cells from all three streams before concluding; reporting only the prefix groups silently "
    "drops concord-only and residue classes.\n"
    "Each cell's `markers` MUST be the actual SURFACE forms from the packet (prefixes, suffixes, concord "
    "markers), e.g. [\"ki\",\"vi\",\"cha\"] — never a bare class number or an English description.\n\n"
    "Write the `prose` field as a tight report a senior reviewer (Opus) will adjudicate: lead with the "
    "call (detected or not + confidence), then the cells with their evidence, then the residue and what "
    "you're unsure of."
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
    # generic fallback: prefer the packet's explicit `cells` (case/agreement), else the hypotheses groups
    cells = []
    if packet.get("cells"):
        for c in packet["cells"]:
            ms = c.get("markers", [])
            cells.append(Cell(label="/".join(str(x) for x in ms[:3]) or "?", markers=ms,
                              function=c.get("function") or c.get("role", ""),
                              support=c.get("n_stems", 0)))
    else:
        for h in packet.get("hypotheses", {}).get("hypotheses", [])[:8]:
            cells.append(Cell(label=h.get("label", "?"), markers=h.get("prefixes", []),
                              function="", support=h.get("n_explained", 0), examples=h.get("examples", [])))
    return ParadigmReport(language=lang, paradigm_type=ptype, detected=packet.get("detected", bool(cells)),
                          confidence=float(packet.get("confidence", 0.4)), cells=cells,
                          conditioning=packet.get("conditioning"),
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
def _extract_json(*texts: str) -> dict:
    """Pull the JSON object out of model output. Reasoning models often leave `content` empty and the
    answer in the reasoning trail, or wrap it in ``` fences — so try each text, parsing the outermost
    balanced {...} block."""
    for t in texts:
        if not t:
            continue
        try:
            return json.loads(t)
        except Exception:
            pass
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            for end in range(len(m.group(0)), m.start(), -1):  # shrink to the last valid close brace
                try:
                    return json.loads(m.group(0)[:end - m.start()])
                except Exception:
                    continue
    raise ValueError("no JSON object found in model output")


def llm_report(packet: dict, endpoint: str | None = None, client=None, max_tokens: int = 8000) -> ParadigmReport:
    """Run the LLM path: prompt -> client.complete(json_schema) -> robust JSON extract -> tolerant
    from_dict. Pass an explicit `client` to inject a mock; otherwise `endpoint` resolves via propose.harness.
    max_tokens is generous because reasoning models spend most of their budget thinking before the answer."""
    from propose.harness.base import Message
    if client is None:
        from propose.harness.registry import build_client
        client = build_client(endpoint)
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=_user_prompt(packet))]
    extra = {}
    # Local reasoning servers (llama.cpp) keep thinking open and never emit final `content` for this task;
    # disable server-side thinking so they return the structured answer. Only valid for openai-compat.
    try:
        from propose.harness.openai_compat import OpenAICompatClient
        if isinstance(client, OpenAICompatClient):
            extra["chat_template_kwargs"] = {"enable_thinking": False}
    except Exception:
        pass
    res = client.complete(messages, max_tokens=max_tokens, json_schema=REPORT_JSON_SCHEMA, **extra)
    data = _extract_json(res.text, getattr(res, "reasoning", "") or "")
    data.setdefault("language", packet["language"])
    data.setdefault("paradigm_type", packet["paradigm_type"])
    return ParadigmReport.from_dict(data)


def generate(packet: dict, endpoint: str | None = None, client=None) -> ParadigmReport:
    """Generate a report. endpoint None/'heuristic' (and no client) -> deterministic baseline; else the
    LLM path (resolved endpoint, or an injected `client`)."""
    if client is None and endpoint in (None, "heuristic"):
        return heuristic_report(packet)
    return llm_report(packet, endpoint, client=client)
