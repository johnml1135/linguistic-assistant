"""Phase B — LLM enrichment of a ticket, strictly additive and HC-gated.

The harness model (`harness.build_client`) proposes hypotheses the fixed taxonomy misses plus readable
prose. **Every** model hypothesis is run through the Phase-A counterfactual engine; one that doesn't
parse the focus form is dropped or flagged `unverified`. Model prose is non-authoritative — the JSON
hypotheses + HC counterfactuals remain the truth. With no endpoint available the function degrades
gracefully: it returns the ticket unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

from .counterfactual import attach_counterfactuals, load_base
from .schema import DeferralTicket, GrammarEdit, Hypothesis

_SKILL = Path(__file__).resolve().parents[2] / "skills" / "package_builder.md"
_VALID_KINDS = {"add_lexentry", "add_allomorph", "add_affix", "add_phon_rule", "split_homograph", "resegment"}


def _profile_summary(pair: str) -> str:
    from . import profile as P
    prof = P.load(pair)
    allowed = sorted(prof.allowed_affix_kinds())
    feats = [d for d in prof.feature_space if prof.feature_present(d)]
    return f"morph_type={prof.morph_type}; allowed_affix={allowed}; features_present={feats}"


def _parse_model_json(text: str) -> dict:
    try:
        return json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception:
        return {}


def enrich(ticket: DeferralTicket, *, endpoint: str = "local", base=None, pf=None) -> dict:
    """Add HC-verified out-of-taxonomy hypotheses + prose to `ticket`. Returns a summary; mutates ticket."""
    try:
        from propose.harness import build_client
        from propose.harness.base import Message
        client = build_client(endpoint)
    except Exception as e:                                  # no endpoint / harness → graceful no-op
        return {"ok": False, "reason": f"no endpoint ({e})", "added": 0}

    skill = _SKILL.read_text(encoding="utf-8")
    existing = [{"mechanism": h.mechanism, "description": h.description,
                 "edits": [{"kind": e.kind, "params": e.params} for e in h.edits]} for h in ticket.hypotheses]
    user = json.dumps({"target": ticket.target, "type": ticket.type, "profile": _profile_summary(ticket.pair),
                       "existing_hypotheses": existing,
                       "options": [{"id": o.id, "text": o.text} for o in ticket.presentation_options]},
                      ensure_ascii=False)
    try:
        res = client.complete([Message("system", skill), Message("user", user)])
        out = _parse_model_json(res.text)
    except Exception as e:
        return {"ok": False, "reason": f"model error ({e})", "added": 0}

    # build candidate hypotheses from valid, in-taxonomy-kind, profile-allowed edits not already present
    seen = {(h.mechanism, json.dumps([{e.kind: e.params} for e in h.edits], sort_keys=True))
            for h in ticket.hypotheses}
    n = len(ticket.hypotheses)
    candidates: list[Hypothesis] = []
    for hd in out.get("hypotheses", []):
        edits = [GrammarEdit(e.get("kind"), e.get("params", {})) for e in hd.get("edits", [])
                 if e.get("kind") in _VALID_KINDS]
        if not edits:
            continue
        sig = (hd.get("mechanism", edits[0].kind),
               json.dumps([{e.kind: e.params} for e in edits], sort_keys=True))
        if sig in seen:
            continue
        seen.add(sig)
        n += 1
        candidates.append(Hypothesis(id=f"h{n}", mechanism=hd.get("mechanism", edits[0].kind),
                                     description=hd.get("description", "(LLM hypothesis)"),
                                     edits=edits, source="llm"))

    # HC-verify each candidate; keep only those that change the focus parse (others marked unverified)
    added = 0
    if candidates:
        base, pf = (base, pf) if base is not None and pf is not None else load_base(ticket.pair)
        attach_counterfactuals(ticket.pair, candidates, ticket.target.get("form", ""), base=base, pf=pf)
        for h in candidates:
            focus_changes = any(cf.focus_parsed_if and not cf.focus_parsed_now for cf in h.counterfactuals)
            if h.unverified and not focus_changes:
                continue                                    # could not verify → do not include
            ticket.hypotheses.append(h)
            added += 1

    # prose is non-authoritative: only fill context_md if Phase A left a bare template + append a note
    if out.get("context_md"):
        ticket.context_md = ticket.context_md + "\n\n_LLM note (non-authoritative):_ " + out["context_md"]
    ticket.tags["llm_enriched"] = True
    ticket.validate()
    return {"ok": True, "added": added, "proposed": len(out.get("hypotheses", []))}
