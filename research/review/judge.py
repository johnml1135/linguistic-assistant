"""The constraint judge — "is this environment/constraint better AND more constrained?" (deterministic).

THOT stays a dumb counter; the judge does the reasoning. A candidate environment is APPLIED (the morpheme
token is split `m␁in` / `m␁out` and THOT re-aligns — see `dossier.realign_distributions`), producing two
source distributions. The judge asks: does conditioning on the environment make the aligned English word
predictable?

  accuracy        = information gain  IG(E) = I(source ; bucket)  (the two split distributions diverge ⇒
                    "the right `u` aligns to the right English word")
  artifact guard  = discard environments whose carved-out bucket is one HOST LEXEME's translation variance
                    (high IG, but `ku` before 'w' is just the verb `kuwa` "to be" — not a sense split).
                    A genuine homograph keeps BOTH buckets lexically diverse (see `is_artifact`).
  selection       = among GENUINE splits, the highest information-gain (a real two-sense split, not the
                    narrowest token-isolating environment).

NB this is the HOMOGRAPH metric (one form, senses → different English words). Allomorphy (one form, one
English correspondence) scores ≈0 here by construction and is handled by the MDL/round-trip gate instead.
Pure + offline-testable; no THOT/HC/LLM here.
"""

from __future__ import annotations

import math


def entropy(counts: dict) -> float:
    """Shannon entropy (bits) of a distribution given as {label: weight}; 0 for pure/empty. Accepts raw
    counts or probabilities (it normalises)."""
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


def information_gain_dist(dist_in: dict, dist_out: dict, n_in: int, n_out: int) -> float:
    """IG = I(source ; bucket), from the TWO THOT distributions a single split run produces — NOT
    re-derived per-occurrence (that reintroduces the conflated-verse-content confound). dist_* are
    P(source | token) for the split tokens `m␁in` / `m␁out`.

      baseline H   = entropy of the count-weighted mixture of the two distributions
      conditioned H = P(in)·H(dist_in) + P(out)·H(dist_out)
      IG = baseline − conditioned   (≥ 0; > 0 exactly when the two distributions diverge)
    """
    n = n_in + n_out
    if n == 0:
        return 0.0
    mix: dict = {}
    for k, v in dist_in.items():
        mix[k] = mix.get(k, 0.0) + n_in * v
    for k, v in dist_out.items():
        mix[k] = mix.get(k, 0.0) + n_out * v
    h_base = entropy(mix)
    h_cond = (n_in / n) * entropy(dist_in) + (n_out / n) * entropy(dist_out)
    return round(h_base - h_cond, 4)


def is_artifact(r: dict, *, max_host_share: float = 0.5, min_hosts: int = 4) -> bool:
    """True if the carved-out (smaller) bucket is one stem's translation variance, not a sense split.
    A genuine homograph keeps BOTH buckets lexically diverse; `ku` before 'w' = just the verb `kuwa`
    ("to be") — same infinitive, high IG, but an ARTIFACT. Tolerant of missing host fields (synthetic
    results treated as genuine)."""
    if r["n_in"] <= r["n_out"]:
        n_hosts, share = r.get("n_hosts_in", 99), r.get("top_host_share_in", 0.0)
    else:
        n_hosts, share = r.get("n_hosts_out", 99), r.get("top_host_share_out", 0.0)
    return share > max_host_share or n_hosts < min_hosts


def decide_dist(results: list[dict], *, min_gain: float = 0.15) -> dict:
    """Decide from realigned split distributions. `results`: [{label, info_gain, coverage, n_hosts_*, …}].
    First DISCARD host-translation artifacts (a bucket that is one lexeme — high IG but not a homograph),
    then accept the GENUINE split with the highest information-gain ≥ min_gain (a real two-sense split,
    not the narrowest token-isolating env). Else defer (one morpheme, an artifact-only field, or needs a
    speaker). The kept artifacts are reported so the contamination is visible."""
    genuine = [r for r in results if not is_artifact(r)]
    artifacts = [r for r in results if is_artifact(r)]
    ranked = sorted(genuine, key=lambda r: (-r["info_gain"], -min(r.get("n_hosts_in", 0), r.get("n_hosts_out", 0))))
    good = [r for r in ranked if r["info_gain"] >= min_gain]
    decision, best = "defer", None
    if good:
        best = good[0]                                   # highest-IG genuine split
        decision = "accept"
    return {"decision": decision, "best": best["label"] if best else None,
            "best_gain": best["info_gain"] if best else 0.0,
            "best_coverage": best["coverage"] if best else 0.0,
            "best_spec": best.get("spec") if best else None,
            "n_genuine": len(genuine), "n_artifacts": len(artifacts),
            "ranked": ranked}
