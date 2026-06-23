"""Per-language profile — constrain + configure the solution space (a first-class artifact).

A `golden_sets/<pair>/profile.json` declares what is POSSIBLE in the language (allowed affix/phonological
processes, the morphosyntactic feature space incl. gender-vs-noun-class, orthography) and how to run the
loop (per-language auto-accept bar, pivot, resource flags). It both PRUNES the hypothesis space (a locked
feature is never proposed — no Spanish infix, no Swahili gender) and CONFIGURES thresholds. Every feature
carries `value` / `confidence` / `locked` / `provenance`, and a pre-written non-linguist `explanation`
(from `feature_explanations`) is attached for the reviewer.

Seeds for spa/ind/tgl/swh come from known typology (WALS/Grambank feature values + what the gold
evidences); `load(pair)` reads the on-disk profile or falls back to the seed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from gold.goldio import FROZEN

from .feature_explanations import explain
from .schema import EDIT_KINDS

AFFIX_PROCESSES = ("prefix", "suffix", "infix", "circumfix", "reduplication", "compounding")
PHON_PROCESSES = ("vowel_harmony", "nasal_assimilation", "tone")
FEATURE_DIMS = ("gender", "noun_class", "case", "tense_aspect_mood", "person_number",
                "definiteness", "agreement", "word_order")


@dataclass
class Feature:
    """One typological fact: its value + how sure we are + whether it hard-constrains + where it came from."""
    value: object                 # bool (process present?) | str/list (feature value)
    confidence: float = 0.5
    locked: bool = False          # True → HARD prune (never propose against it); False → soft prior
    provenance: str = "seed"      # WALS / Grambank / Glottolog / linguist / inferred / seed
    slug: str = ""                # feature_explanations key (for the non-linguist explanation)

    def explanation(self) -> dict | None:
        return explain(self.slug) if self.slug else None


def _f(value, conf, locked, prov, slug=""):
    return Feature(value=value, confidence=conf, locked=locked, provenance=prov, slug=slug)


@dataclass
class LanguageProfile:
    pair: str
    morph_type: str = "agglutinative"
    affix_processes: dict = field(default_factory=dict)    # name -> Feature(bool)
    phon_processes: dict = field(default_factory=dict)     # name -> Feature(bool)
    feature_space: dict = field(default_factory=dict)      # dim  -> Feature(bool/value)
    orthography: dict = field(default_factory=dict)
    operational: dict = field(default_factory=dict)        # auto_accept_bar, pivot, resources, …

    # ---- the two jobs --------------------------------------------------------------------------
    def allows_affix_kind(self, kind: str) -> bool:
        """Is this affix process permitted? A locked-off process is a hard NO (prune)."""
        f = self.affix_processes.get(kind)
        if f is None:
            return True
        return bool(f.value) or not f.locked            # locked-false → no; uncertain-false → allowed (soft)

    def allowed_affix_kinds(self) -> set[str]:
        return {k for k in (*AFFIX_PROCESSES, "prefix", "suffix", "infix") if self.allows_affix_kind(k)}

    def allowed_edit_kinds(self) -> set[str]:
        """Edit kinds permitted for this language. (Process-specific kinds — infix/reduplication — are
        gated at the affix-kind level; the structural edit kinds are always available.)"""
        allowed = set(EDIT_KINDS)
        # a language with NO declared phonological processes gets no phonological-rule hypotheses
        if self.phon_processes and not any(bool(f.value) for f in self.phon_processes.values()):
            allowed.discard("add_phon_rule")
        return allowed

    def auto_accept_bar(self) -> float:
        return float(self.operational.get("auto_accept_bar", 0.995))

    def pivot(self) -> str:
        return self.operational.get("pivot", "en")

    def has_resource(self, name: str) -> bool:
        return bool(self.operational.get("resources", {}).get(name, False))

    def feature_present(self, dim: str) -> bool:
        f = self.feature_space.get(dim)
        return bool(f.value) if f else False

    # ---- (de)serialisation ---------------------------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        for sec in ("affix_processes", "phon_processes", "feature_space"):
            d[sec] = {k: asdict(v) for k, v in getattr(self, sec).items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LanguageProfile":
        d = dict(d)
        for sec in ("affix_processes", "phon_processes", "feature_space"):
            d[sec] = {k: Feature(**v) for k, v in (d.get(sec) or {}).items()}
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in known})

    def with_explanations(self) -> dict:
        """A render-ready dict where each feature carries its non-linguist explanation inline."""
        out = self.to_dict()
        for sec in ("affix_processes", "phon_processes", "feature_space"):
            for k, v in out[sec].items():
                ex = explain(v.get("slug", ""))
                if ex:
                    v["explanation"] = ex
        return out


def profile_path(pair: str) -> Path:
    return FROZEN / pair / "profile.json"


# ---- seeds (typology) -----------------------------------------------------------------------------
def _seed(pair: str) -> LanguageProfile:
    A = "affix"; P = "phon"; F = "feat"  # explanation-slug prefixes

    def affixes(prefix, suffix, infix, circ, redup, comp):
        vals = {"prefix": prefix, "suffix": suffix, "infix": infix, "circumfix": circ,
                "reduplication": redup, "compounding": comp}
        out = {}
        for name, (val, conf, lock, prov) in vals.items():
            out[name] = _f(val, conf, lock, prov, slug=f"{A}:{name}")
        return out

    def phon(vh, na, tone):
        m = {"vowel_harmony": vh, "nasal_assimilation": na, "tone": tone}
        return {n: _f(v[0], v[1], v[2], v[3], slug=f"{P}:{n}") for n, v in m.items()}

    def feats(**kw):
        return {dim: _f(*kw[dim], slug=f"{F}:{dim}") for dim in kw}

    # (value, confidence, locked, provenance)
    T, FF = True, False
    WALS, GB, LING = "WALS", "Grambank", "linguist"
    base_ortho = lambda digraphs=(): {"script": "Latin", "digraphs": list(digraphs)}
    base_op = lambda unimorph, wiktionary: {
        "auto_accept_bar": 0.995, "pivot": "en",
        "resources": {"unimorph": unimorph, "wiktionary": wiktionary, "audio": True}}

    if pair == "spa":
        return LanguageProfile(
            pair, morph_type="fusional",
            affix_processes=affixes((T, .9, FF, WALS), (T, .95, FF, WALS), (FF, .95, T, WALS),
                                    (FF, .7, FF, LING), (FF, .9, T, WALS), (T, .7, FF, LING)),
            phon_processes=phon((FF, .9, T, WALS), (FF, .85, FF, LING), (FF, .98, T, WALS)),
            feature_space=feats(gender=(T, .98, FF, WALS), noun_class=(FF, .95, T, WALS),
                                case=(FF, .9, T, WALS), tense_aspect_mood=(T, .98, FF, WALS),
                                person_number=(T, .98, FF, WALS), definiteness=(T, .95, FF, WALS),
                                agreement=(T, .95, FF, WALS), word_order=("SVO", .8, FF, WALS)),
            orthography=base_ortho(("ll", "ch", "rr")), operational=base_op(True, True))
    if pair == "ind":
        return LanguageProfile(
            pair, morph_type="agglutinative",
            affix_processes=affixes((T, .95, FF, WALS), (T, .95, FF, WALS), (T, .5, FF, GB),
                                    (T, .85, FF, WALS), (T, .9, FF, WALS), (T, .8, FF, LING)),
            phon_processes=phon((FF, .8, FF, LING), (T, .9, FF, LING), (FF, .95, T, WALS)),
            feature_space=feats(gender=(FF, .95, T, WALS), noun_class=(FF, .9, FF, WALS),
                                case=(FF, .9, T, WALS), tense_aspect_mood=(T, .8, FF, GB),
                                person_number=(T, .7, FF, GB), definiteness=(T, .7, FF, WALS),
                                agreement=(FF, .8, FF, GB), word_order=("SVO", .85, FF, WALS)),
            orthography=base_ortho(("ng", "ny", "sy")), operational=base_op(True, True))
    if pair == "tgl":
        return LanguageProfile(
            pair, morph_type="agglutinative",
            affix_processes=affixes((T, .95, FF, WALS), (T, .9, FF, WALS), (T, .9, FF, WALS),
                                    (T, .85, FF, WALS), (T, .95, FF, WALS), (T, .8, FF, LING)),
            phon_processes=phon((FF, .8, FF, LING), (T, .85, FF, LING), (FF, .95, T, WALS)),
            feature_space=feats(gender=(FF, .9, T, WALS), noun_class=(FF, .9, T, WALS),
                                case=(FF, .7, FF, WALS), tense_aspect_mood=(T, .8, FF, GB),
                                person_number=(T, .8, FF, GB), definiteness=(T, .7, FF, WALS),
                                agreement=(T, .7, FF, GB), word_order=("VSO", .8, FF, WALS)),
            orthography=base_ortho(("ng",)), operational=base_op(False, True))
    if pair == "swh":
        return LanguageProfile(
            pair, morph_type="agglutinative",
            affix_processes=affixes((T, .95, FF, WALS), (T, .9, FF, WALS), (FF, .9, T, WALS),
                                    (FF, .8, FF, LING), (T, .6, FF, GB), (T, .8, FF, LING)),
            phon_processes=phon((T, .7, FF, LING), (T, .85, FF, LING), (FF, .95, T, WALS)),
            feature_space=feats(gender=(FF, .95, T, WALS), noun_class=(T, .98, FF, WALS),
                                case=(FF, .9, T, WALS), tense_aspect_mood=(T, .9, FF, GB),
                                person_number=(T, .9, FF, GB), definiteness=(FF, .7, FF, WALS),
                                agreement=(T, .95, FF, WALS), word_order=("SVO", .85, FF, WALS)),
            orthography=base_ortho(("ng", "ch", "ny", "sh")), operational=base_op(False, True))
    return LanguageProfile(pair)            # empty/permissive fallback for an unknown pair


def load(pair: str) -> LanguageProfile:
    """Load the on-disk profile, or the typology seed if none exists yet."""
    p = profile_path(pair)
    if p.exists():
        return LanguageProfile.from_dict(json.loads(p.read_text(encoding="utf-8")))
    return _seed(pair)


def save(profile: LanguageProfile) -> Path:
    p = profile_path(profile.pair)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def seed_all() -> dict:
    """Write the seed profiles for the four languages; returns the paths."""
    return {pair: str(save(_seed(pair))) for pair in ("spa", "ind", "tgl", "swh")}


def conflict_report(pair: str) -> list[dict]:
    """Surface typology-DB vs corpus-evidence conflicts (task 15.6) — do NOT silently resolve them.

    Coarse corpus evidence: reduplication ⇐ scripture forms with a repeated leading chunk; nasal
    assimilation ⇐ meN-/peN-style prefix-final nasal variation. Where the profile asserts a process
    ABSENT but the corpus appears to evidence it (or vice-versa), report it for review."""
    from . import counterfactual as CF
    prof = load(pair)
    freqs = CF._freqs(pair)
    words = [w for w in freqs if w.isalpha() and len(w) >= 4]

    def has_redup() -> bool:
        hits = sum(1 for w in words if any(w[:k] == w[k:2 * k] for k in range(2, len(w) // 2 + 1)))
        return hits >= 5
    evidence = {"reduplication": has_redup(),
                "nasal_assimilation": any(w.startswith(("meng", "meny", "mem", "men", "peng", "pem")) for w in words)}
    out = []
    for proc, ev in evidence.items():
        f = prof.affix_processes.get(proc) or prof.phon_processes.get(proc)
        if f is None:
            continue
        asserted = bool(f.value)
        if asserted != ev:
            out.append({"feature": proc, "profile_says": asserted, "corpus_evidence": ev,
                        "locked": f.locked, "provenance": f.provenance,
                        "action": "review (locked — needs linguist)" if f.locked else "consider toggling"})
    return out


def probe_feature(pair: str, section: str, name: str, *, base=None, pf=None, n_slice: int = 120) -> dict:
    """"What if this feature were different?" — toggle an UNCERTAIN feature on, re-parse a corpus slice,
    and compare the grammar by ΔMDL (research/assess/mdl). A locked feature is never auto-flipped: we
    only recommend the change to a linguist. Returns the evidence + a recommendation.

    This is a coarse, deterministic probe at the grammar-quality level (it does not yet wire a process-
    specific generator); it answers 'does treating this feature as present improve the grammar?'."""
    from assess.mdl import description_length

    from . import counterfactual as CF

    prof = load(pair)
    feat = getattr(prof, section, {}).get(name)
    if feat is None:
        return {"ok": False, "error": f"no feature {section}.{name}"}
    if feat.locked:
        return {"ok": True, "locked": True, "recommend": "escalate-to-linguist",
                "note": "locked feature — not auto-flipped"}
    if base is None or pf is None:
        base, pf = CF.load_base(pair)
    from engine.hc import gloss_seq, run_parse
    freqs = CF._freqs(pair)
    words = [w for w, _ in freqs.most_common() if w.isalpha() and len(w) >= 2][:n_slice]
    parses = run_parse(base, words, templated=False, phon_feats=pf, chunk_timeout=CF.CHUNK_TIMEOUT)
    gl = {w: list(dict.fromkeys(gloss_seq(a) for a in parses.get(w, []))) for w in words}
    dl = description_length(base, gl, token_counts=freqs)["DL"]
    # The probe records the current DL as the baseline a process-specific generator would have to beat;
    # a real toggle (group 13 generators) supplies the 'after' grammar. We surface the contract here.
    return {"ok": True, "locked": False, "feature": f"{section}.{name}", "value_now": feat.value,
            "confidence": feat.confidence, "baseline_DL": dl, "slice": len(words),
            "recommend": "run a process-specific generator and compare ΔMDL against baseline_DL"}
