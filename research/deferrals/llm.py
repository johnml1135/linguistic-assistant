"""LLM-assisted steps (Phase B/C) over a ticket — all additive, HC-gated, and gracefully optional.

Every function degrades to a deterministic / no-op result when no endpoint is available, and nothing here
can override a deterministic gate: the LLM supplies reach (hypotheses, feature guesses) and readability
(prose, question phrasing), and the HC counterfactual + regression gates remain the source of truth.

  resolve_or_defer  — propose a typed edit OR defer (the gradable judgement; used by eval_gemma)
  llm_verdict       — rank/explain gate-passing hypotheses (task 10.3); CANNOT un-reject a regressor
  phrase_question   — rephrase a discriminating question for a non-linguist (task 14.4)
  propose_feature   — guess an undeclared profile feature value (task 15.7), to be probe-verified
  fanout_investigate — Phase C: one model call per HC mechanism + a synthesis (task 7.2/7.3)
"""

from __future__ import annotations

import json
from pathlib import Path

_SKILLS = Path(__file__).resolve().parents[1] / "skills"
_VALID_EDIT = {"add_lexentry", "add_allomorph", "add_affix", "split_homograph"}


def _client(endpoint: str):
    from harness import build_client
    return build_client(endpoint)


def _ask_json(client, system: str, user: str) -> dict:
    from harness.base import Message
    res = client.complete([Message("system", system), Message("user", user)])
    t = res.text or ""
    try:
        return json.loads(t[t.find("{"): t.rfind("}") + 1])
    except Exception:
        return {}


# --------------------------------------------------------------------------- resolve-or-defer (gradable)
def resolve_or_defer(rec: dict, *, endpoint: str = "ik_llama", profile_summary: str = "") -> dict:
    """Ask the model to propose a typed edit OR defer for one deferred form. Returns the parsed decision
    ({decision, edit, confidence, rationale}); on any failure returns a safe defer."""
    try:
        client = _client(endpoint)
    except Exception as e:
        return {"decision": "defer", "edit": {}, "confidence": "low", "rationale": f"no endpoint ({e})"}
    skill = (_SKILLS / "resolve_deferral.md").read_text(encoding="utf-8")
    user = json.dumps({"language": rec.get("language", rec.get("pair", "")), "form": rec.get("form", rec.get("word", "")),
                       "pivot_gloss": rec.get("pivot_gloss", rec.get("aligner_top1", "?")),
                       "near_lemma": rec.get("near_lemma"), "context": rec.get("context", ""),
                       "profile": profile_summary}, ensure_ascii=False)
    out = _ask_json(client, skill, user)
    dec = out.get("decision")
    if dec not in ("resolve", "defer"):
        return {"decision": "defer", "edit": {}, "confidence": "low", "rationale": "unparseable model output"}
    edit = out.get("edit") or {}
    if dec == "resolve" and edit.get("kind") not in _VALID_EDIT:
        return {"decision": "defer", "edit": {}, "confidence": "low", "rationale": "invalid edit kind"}
    return {"decision": dec, "edit": edit, "confidence": out.get("confidence", "low"),
            "rationale": out.get("rationale", "")}


# --------------------------------------------------------------------------------- verdict (task 10.3)
def llm_verdict(ticket, *, endpoint: str = "ik_llama") -> dict:
    """Ask the model to rank/explain the hypotheses that PASSED the deterministic regression gate. It may
    re-order and explain, but it CANNOT accept a hypothesis the gate rejected (we filter to gate-passers
    before asking, and ignore any id outside that set)."""
    passers = [h for h in ticket.hypotheses if h.verdict.get("acceptable")]
    if not passers:
        return {"ok": True, "ranking": [], "note": "no gate-passing hypotheses to rank"}
    try:
        client = _client(endpoint)
    except Exception as e:
        return {"ok": False, "reason": f"no endpoint ({e})", "ranking": [h.id for h in passers]}
    sys = ("You rank candidate fixes for a word-analysis decision. You are given ONLY fixes that already "
           "passed an automatic safety check. Pick the best and explain briefly. Return STRICT JSON: "
           '{"order": ["<id>", ...], "best": "<id>", "why": "<one sentence>"}. Use only the given ids.')
    payload = {"target": ticket.target, "candidates": [
        {"id": h.id, "description": h.description,
         "metrics": {k: h.metrics.get(k) for k in ("delta_mdl", "net_delta", "over_generation")}}
        for h in passers]}
    out = _ask_json(client, sys, json.dumps(payload, ensure_ascii=False))
    valid = {h.id for h in passers}
    order = [i for i in out.get("order", []) if i in valid] or [h.id for h in passers]
    best = out.get("best") if out.get("best") in valid else order[0]
    ticket.tags["llm_verdict"] = {"best": best, "why": out.get("why", "")}
    return {"ok": True, "ranking": order, "best": best, "why": out.get("why", "")}


# ------------------------------------------------------------------------- question phrasing (task 14.4)
def phrase_question(ticket, option_id: str, *, endpoint: str = "ik_llama") -> str | None:
    """Rephrase one presentation option as a question a non-linguist speaker can answer. Returns the new
    text (and stores it on the option) or None if unavailable."""
    opt = next((o for o in ticket.presentation_options if o.id == option_id), None)
    if opt is None:
        return None
    try:
        client = _client(endpoint)
    except Exception:
        return None
    sys = ("Rephrase this question so a fluent speaker who is NOT a linguist can answer it. Keep it short, "
           "concrete, jargon-free, about their own language. Return STRICT JSON: {\"question\": \"...\"}.")
    out = _ask_json(client, sys, json.dumps({"form": ticket.target.get("form"), "question": opt.text}))
    q = out.get("question")
    if q:
        opt.text = q
    return q


# ----------------------------------------------------------------------- feature proposer (task 15.7)
def propose_feature(pair: str, section: str, name: str, sample_words: list[str], *,
                    endpoint: str = "ik_llama") -> dict:
    """When a profile feature has no DB value, ask the model to guess it from sample data. The result is
    `provenance: inferred`, unlocked, low-trust — it must be probe-verified (profile.probe_feature)."""
    try:
        client = _client(endpoint)
    except Exception as e:
        return {"ok": False, "reason": f"no endpoint ({e})"}
    sys = (f"Does the {pair} language have the feature '{name}' ({section})? Judge ONLY from the sample "
           "words. Return STRICT JSON: {\"present\": true|false, \"confidence\": \"high|medium|low\", "
           "\"evidence\": \"one sentence\"}.")
    out = _ask_json(client, sys, json.dumps({"sample_words": sample_words[:40]}, ensure_ascii=False))
    if "present" not in out:
        return {"ok": False, "reason": "unparseable"}
    return {"ok": True, "feature": f"{section}.{name}", "present": bool(out["present"]),
            "confidence": out.get("confidence", "low"), "evidence": out.get("evidence", ""),
            "provenance": "inferred", "locked": False, "note": "probe-verify before trusting"}


# --------------------------------------------------------------------- Phase C fan-out (task 7.2/7.3)
def fanout_investigate(ticket, *, endpoint: str = "ik_llama", base=None, pf=None) -> dict:
    """One model call per HC mechanism (each proposes a typed edit for the focus), HC-verify each, then a
    synthesis pick. Additive + HC-gated: only verified edits become hypotheses (task 7.2/7.3)."""
    from .counterfactual import attach_counterfactuals, load_base
    from .schema import GrammarEdit, Hypothesis
    try:
        client = _client(endpoint)
    except Exception as e:
        return {"ok": False, "reason": f"no endpoint ({e})", "added": 0}
    form = ticket.target.get("form", "")
    pivot = ticket.target.get("aligner_top1") or ticket.target.get("gloss") or "?"
    mechanisms = [("add_lexentry", "a brand-new dictionary word"),
                  ("add_allomorph", "another form of an existing word"),
                  ("add_affix", "an affix (prefix/suffix)")]
    n = len(ticket.hypotheses)
    candidates = []
    for kind, desc in mechanisms:
        sys = (f"Propose how to analyse the {ticket.pair} word '{form}' (meaning ~'{pivot}') AS {desc}. "
               f"Return STRICT JSON: {{\"edit\": {{\"kind\": \"{kind}\", \"params\": {{...}}}}, "
               "\"rationale\": \"one sentence\"}. If this mechanism does not fit, return {\"edit\": {}}.")
        out = _ask_json(client, sys, json.dumps({"form": form, "pivot_gloss": pivot}))
        e = out.get("edit") or {}
        if e.get("kind") == kind and e.get("params"):
            n += 1
            candidates.append(Hypothesis(id=f"h{n}", mechanism=kind,
                                         description=out.get("rationale", desc),
                                         edits=[GrammarEdit(kind, e["params"])], source="workflow"))
    added = 0
    if candidates:
        base, pf = (base, pf) if base is not None and pf is not None else load_base(ticket.pair)
        attach_counterfactuals(ticket.pair, candidates, form, base=base, pf=pf)
        for h in candidates:
            if any(cf.focus_parsed_if and not cf.focus_parsed_now for cf in h.counterfactuals):
                ticket.hypotheses.append(h)
                added += 1
    ticket.tags["fanout"] = {"mechanisms": len(mechanisms), "verified_added": added}
    ticket.validate()
    return {"ok": True, "added": added, "proposed": len(candidates)}
