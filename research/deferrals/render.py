"""Render a `DeferralTicket` to human-readable markdown — derived ONLY from the ticket JSON.

The markdown is a view, never a second source of truth: everything shown (target, context, hypotheses
with their HC counterfactual diffs, and the scripted speaker questions) comes straight off the record, so
a UI/CLI/bug-tracker can regenerate it at any time.
"""

from __future__ import annotations

from .schema import Counterfactual, DeferralTicket, Hypothesis


def _fmt_analyses(analyses: list) -> str:
    if not analyses:
        return "·(no parse)"
    return " / ".join("-".join(seq) for seq in analyses[:3]) + ("  …" if len(analyses) > 3 else "")


def _render_counterfactual(cf: Counterfactual) -> str:
    flag = " _(unverified — HC timed out / unavailable)_" if cf.unverified else ""
    lines = [f"  - **{cf.ref or 'example'}** — “{cf.text}”{flag}"]
    focus = cf.focus
    words = list(dict.fromkeys([*cf.now.keys(), *cf.if_hyp.keys()]))
    for w in words:
        now_set = {tuple(seq) for seq in cf.now.get(w, [])}
        if_set = {tuple(seq) for seq in cf.if_hyp.get(w, [])}
        if now_set == if_set and w != focus:
            continue                                  # pure reordering / no real change → suppress noise
        mark = "**→** " if w == focus else ""
        lines.append(f"    - {mark}`{w}`: now {_fmt_analyses(cf.now.get(w, []))}  "
                     f"⟶  if-true {_fmt_analyses(cf.if_hyp.get(w, []))}")
    if len(lines) == 1:
        lines.append("    - (no parse change on the shown words)")
    return "\n".join(lines)


def _render_hypothesis(h: Hypothesis) -> str:
    head = f"### Hypothesis {h.id}: {h.description}"
    meta = [f"_mechanism_: `{h.mechanism}`  ·  _source_: {h.source}"]
    if h.unverified:
        meta.append("  ·  ⚠ **unverified**")
    if h.metrics:
        m = h.metrics
        bits = []
        for k, label in (("delta_mdl", "ΔMDL"), ("net_delta", "net parse Δ"), ("coverage_gain", "coverage+"),
                         ("over_generation", "over-gen"), ("worst_part_rank", "worst-part")):
            if k in m:
                bits.append(f"{label} {m[k]}")
        if bits:
            meta.append("  ·  " + ", ".join(bits))
    if h.verdict:
        v = h.verdict
        meta.append(f"\n_verdict_: {'acceptable' if v.get('acceptable') else 'rejected'} "
                    f"(gains {v.get('gains', '?')}, regressions {v.get('regressions', '?')}, "
                    f"net {v.get('net', '?')})")
    body = [head, "".join(meta), "", "_If this were true, scripture re-parses as:_"]
    for cf in h.counterfactuals:
        body.append(_render_counterfactual(cf))
    return "\n".join(body)


def render(ticket: DeferralTicket) -> str:
    """The full markdown package for a ticket."""
    t = ticket
    out = [
        f"# Resolution ticket `{t.id}`",
        f"**type** {t.type} · **domain** {t.domain} · **status** {t.status} · "
        f"**confidence** {t.confidence} · **impact** {t.impact.get('priority', '?')} "
        f"(freq {t.impact.get('freq', 0)}, ~{t.impact.get('wordforms', 0)} wordforms)",
        "",
        t.context_md,
        "",
        "## Hypotheses",
    ]
    if not t.hypotheses:
        out.append("_No deterministic hypotheses; needs LLM enrichment or speaker elicitation._")
    for h in t.hypotheses:
        out.append(_render_hypothesis(h))
        out.append("")
    out.append("## Ways to ask the speaker")
    for o in t.presentation_options:
        tag = f"  _(tells apart {', '.join(o.discriminates)})_" if o.discriminates else ""
        out.append(f"- **[{o.kind}]** {o.text}{tag}")
    if t.dependencies:
        out += ["", "## Related tickets", "- " + ", ".join(f"`{d}`" for d in t.dependencies)]
    if t.resolution.action:
        r = t.resolution
        out += ["", "## Resolution",
                f"- **{r.action}** {('→ ' + r.hypothesis_id) if r.hypothesis_id else ''} "
                f"{('— ' + r.reason) if r.reason else ''} {('(' + r.by + ')') if r.by else ''}"]
    return "\n".join(out)
