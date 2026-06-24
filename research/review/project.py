"""Cross-lingual syntactic projection — the "real syntax" layer.

Parse the PIVOT side (a major language of wider communication, which we can parse reliably) and project its
grammatical relations (subject / object / modifier) onto the vernacular through the THOT word alignment.
The pivot gives the ROLE; the vernacular data then reveals how that role is MARKED (the affix / agreement)
— which is what the frontier kept asking for (subject identification to crack the swh `wa`-residue).

Pivot-agnostic + parser-pluggable, one pivot at a time, swappable:
  - UDPipe  — ~100 UD languages incl. all top-20 LWCs (Arabic, Hindi, Chinese, Indonesian, Swahili…), no
              torch; the documented broad-coverage path (drop a model in ~/.cache/udpipe/<lang>.udpipe).
  - spaCy   — English + ~24 major languages, no torch for the small models; the default that's wired now.
Both are OPTIONAL (graceful): with no parser the projection layer is simply unavailable and the rest of
the system runs unchanged.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

# pivot → spaCy small model (no torch). UDPipe covers the rest of the top-20 (model files, not pip).
SPACY_MODELS = {"en": "en_core_web_sm", "es": "es_core_news_sm", "fr": "fr_core_news_sm",
                "pt": "pt_core_news_sm", "ru": "ru_core_news_sm", "zh": "zh_core_web_sm",
                "de": "de_core_news_sm", "it": "it_core_news_sm", "id": "xx_sent_ud_sm"}

_CACHE: dict = {}


def _spacy_parser(pivot: str):
    try:
        import spacy
        nlp = spacy.load(SPACY_MODELS.get(pivot, pivot), disable=["ner", "lemmatizer"])
    except Exception:
        return None

    def fn(sentence: str):
        doc = nlp(sentence)
        return [(t.i, t.text.lower(), t.pos_, t.dep_, t.head.i, t.morph.to_dict()) for t in doc]
    return fn


# Offline UDPipe-1 models (~6-30 MB each, no torch, loads in `ufal.udpipe`) from LINDAT's DSpace-7 REST
# CONTENT endpoint — the working get-around (the old direct URLs return a JS UI; the REST bytes endpoint
# does not). NB UDPipe **1** only (the 9.5 GB UDPipe-2 / TF bundles are a different format, not used here).
#
# VERSION-PINNED but easy to update: bump UDPIPE_VERSION (add the new release's handle to UDPIPE_RELEASES).
# Any language is fetchable — filenames are discovered live (`list_available`), not hardcoded.
UDPIPE_RELEASES = {"ud-2.5": "11234/1-3131"}        # release tag → LINDAT handle (add ud-2.x handles here)
UDPIPE_VERSION = "ud-2.5"                            # ← pinned default; change here to update everything

ISO_LANG = {"en": "english", "es": "spanish", "fr": "french", "de": "german", "pt": "portuguese",
            "ru": "russian", "zh": "chinese", "ar": "arabic", "hi": "hindi", "id": "indonesian",
            "tr": "turkish", "vi": "vietnamese", "ko": "korean", "ja": "japanese", "fa": "persian",
            "ur": "urdu", "ta": "tamil", "it": "italian", "nl": "dutch", "pl": "polish", "uk": "ukrainian",
            "ro": "romanian", "cs": "czech", "fi": "finnish", "he": "hebrew", "el": "greek",
            "sv": "swedish", "bg": "bulgarian", "da": "danish", "no": "norwegian", "th": "thai"}
DEFAULT_TREEBANK = {"english": "ewt", "russian": "syntagrus", "arabic": "padt", "hindi": "hdtb",
                    "urdu": "udtb", "persian": "seraji", "turkish": "imst", "vietnamese": "vtb",
                    "tamil": "ttb", "italian": "isdt", "spanish": "ancora", "korean": "kaist"}
HF_MODELS = {"la": ("latincy/la_udpipe_latincy", "la_udpipe_latincy_multi.udpipe")}   # non-LINDAT fallback


def _ssl_ctx():
    import ssl
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE                    # proxy injects a self-signed cert
    return c


def _lindat_handle(version: str | None) -> str:
    return UDPIPE_RELEASES.get(version or UDPIPE_VERSION, UDPIPE_RELEASES[UDPIPE_VERSION])


def list_available(version: str | None = None, refresh: bool = False) -> dict:
    """Query LINDAT for every UDPipe-1 model in the pinned release → {model_key: filename}, where model_key
    is '<language>-<treebank>' (e.g. 'english-ewt'). Cached to disk; `refresh=True` re-queries."""
    import json
    import urllib.request
    version = version or UDPIPE_VERSION
    cache = os.path.expanduser(f"~/.cache/udpipe/_index_{version}.json")
    if os.path.exists(cache) and not refresh:
        try:
            return json.load(open(cache, encoding="utf-8"))
        except Exception:
            pass
    handle, ctx = _lindat_handle(version), _ssl_ctx()

    def api(u):
        with urllib.request.urlopen(u, context=ctx, timeout=60) as r:
            return json.loads(r.read())
    try:
        it = api(f"https://lindat.mff.cuni.cz/repository/server/api/pid/find?id=hdl:{handle}")
        bnd = api(f"https://lindat.mff.cuni.cz/repository/server/api/core/items/{it['uuid']}/bundles")
        index = {}
        for b in bnd["_embedded"]["bundles"]:
            if b["name"] == "ORIGINAL":
                bs = api(b["_links"]["bitstreams"]["href"] + "?size=500")
                for x in bs["_embedded"]["bitstreams"]:
                    if x["name"].endswith(".udpipe"):
                        index[x["name"].split("-ud-")[0]] = x["name"]
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump(index, open(cache, "w", encoding="utf-8"))
        return index
    except Exception:
        return {}


def resolve_model(spec: str, version: str | None = None) -> str | None:
    """spec → filename. spec is an ISO code (`en`), a language (`english`), or a full key (`english-gum`).
    Falls back: default treebank → 'gsd' → any treebank for that language."""
    spec = spec.lower().replace("_", "-")
    avail = list_available(version)
    if not avail:
        return None
    if spec in avail:                                # exact 'language-treebank'
        return avail[spec]
    lang = ISO_LANG.get(spec, spec)                  # ISO → language name
    for tb in (DEFAULT_TREEBANK.get(lang), "gsd"):
        if tb and f"{lang}-{tb}" in avail:
            return avail[f"{lang}-{tb}"]
    cands = sorted(k for k in avail if k.split("-")[0] == lang)
    return avail[cands[0]] if cands else None


def download_model(spec: str, version: str | None = None, dest_key: str | None = None,
                   force: bool = False) -> str | None:
    """Fetch ANY UDPipe-1 model (by ISO / language / language-treebank) from the pinned LINDAT release into
    ~/.cache/udpipe/<dest_key>.udpipe and verify it loads. HF fallback. Guards the HTML-stub (<1 MB)."""
    import urllib.request
    dst = os.path.expanduser(f"~/.cache/udpipe/{dest_key or spec}.udpipe")
    if os.path.exists(dst) and os.path.getsize(dst) > 1_000_000 and not force:
        return dst
    urls = []
    fn = resolve_model(spec, version)
    if fn:
        urls.append(f"https://lindat.mff.cuni.cz/repository/server/api/core/bitstreams/handle/"
                    f"{_lindat_handle(version)}/{fn}")
    if spec in HF_MODELS:
        repo, hf = HF_MODELS[spec]
        urls.append(f"https://huggingface.co/{repo}/resolve/main/{hf}")
    ctx = _ssl_ctx()
    for u in urls:
        try:
            with urllib.request.urlopen(u, context=ctx, timeout=240) as r:
                data = r.read()
            if len(data) < 1_000_000:
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(data)
            from ufal.udpipe import Model
            if Model.load(dst) is None:
                os.remove(dst); continue
            return dst
        except Exception:
            continue
    return None


def _udpipe_parser(pivot: str):
    """Offline UDPipe: load ~/.cache/udpipe/<pivot>.udpipe, auto-downloading from the HF mirror if missing."""
    try:
        from ufal.udpipe import Model, Pipeline
        path = os.path.expanduser(f"~/.cache/udpipe/{pivot}.udpipe")
        if not os.path.exists(path) or os.path.getsize(path) <= 1_000_000:
            path = download_model(pivot)             # try the HF mirror
            if not path:
                return None
        model = Model.load(path)
        pipe = Pipeline(model, "tokenize", Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")
    except Exception:
        return None

    def fn(sentence: str, _keep=model):              # keep Model alive — else C++ frees it → segfault
        toks = []
        for line in pipe.process(sentence).splitlines():
            if line and not line.startswith("#") and "\t" in line:
                c = line.split("\t")
                if c[0].isdigit():
                    feats = dict(kv.split("=", 1) for kv in c[5].split("|") if "=" in kv) if c[5] != "_" else {}
                    toks.append((int(c[0]) - 1, c[1].lower(), c[3], c[7],
                                 int(c[6]) - 1 if c[6].isdigit() else int(c[0]) - 1, feats))
        return toks
    return fn


# LINDAT UDPipe REST service — the online get-around when no local model is available. Covers all top-20
# LWCs (the service hosts every UD model); model files themselves are currently un-downloadable (LINDAT
# serves a JS UI). pivot ISO → service model-prefix.
UDPIPE_REST = "https://lindat.mff.cuni.cz/services/udpipe/api/process"
REST_MODELS = {"en": "english", "es": "spanish", "fr": "french", "pt": "portuguese", "ru": "russian",
               "zh": "chinese", "de": "german", "it": "italian", "ar": "arabic", "hi": "hindi",
               "id": "indonesian", "sw": "swahili", "tr": "turkish", "vi": "vietnamese", "ko": "korean",
               "ja": "japanese", "fa": "persian", "ur": "urdu", "ta": "tamil", "th": "thai"}


def _udpipe_rest_parser(pivot: str):
    """Online UDPipe (no model download). Per-sentence POST — functional; batch the whole document for a
    full-corpus run (speed follow-on). Graceful: returns None only on import error (network errors raise
    per-call and are caught by callers)."""
    import json
    import ssl
    import urllib.parse
    import urllib.request
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE                  # proxy injects a self-signed cert in the chain
    model = REST_MODELS.get(pivot, pivot)

    def fn(sentence: str):
        data = urllib.parse.urlencode({"tokenizer": "", "tagger": "", "parser": "",
                                       "model": model, "data": sentence}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request(UDPIPE_REST, data=data),
                                        context=ctx, timeout=60) as r:
                conllu = json.loads(r.read())["result"]
        except Exception:
            return []
        toks = []
        for line in conllu.splitlines():
            if line and not line.startswith("#") and "\t" in line:
                c = line.split("\t")
                if c[0].isdigit():
                    h = int(c[6]) - 1 if c[6].isdigit() else int(c[0]) - 1
                    feats = dict(kv.split("=", 1) for kv in c[5].split("|") if "=" in kv) if c[5] != "_" else {}
                    toks.append((int(c[0]) - 1, c[1].lower(), c[3], c[7], h, feats))
        return toks
    return fn


def get_parser(pivot: str = "en", backend: str = "auto"):
    """Resolve a pivot parser. backend='auto' prefers the real offline UDPipe model (now available for ~60
    langs), then spaCy, then the online REST service — so the algorithm uses the best parser present."""
    key = (pivot, backend)
    if key not in _CACHE:
        if backend == "udpipe":
            _CACHE[key] = _udpipe_parser(pivot)
        elif backend == "udpipe_rest":
            _CACHE[key] = _udpipe_rest_parser(pivot)
        elif backend == "spacy":
            _CACHE[key] = _spacy_parser(pivot)
        else:  # auto
            _CACHE[key] = (_udpipe_parser(pivot) or _spacy_parser(pivot) or _udpipe_rest_parser(pivot))
    return _CACHE[key]


def available(pivot: str = "en", backend: str = "spacy") -> bool:
    return get_parser(pivot, backend) is not None


# ── projection: pivot relations → vernacular via the word alignment ─────────────────────────────────────
def _word_alignment(pair: str, sample: int):
    """Word-level vernacular↔pivot GlossTable + the verses (src = pivot/English, tgt = vernacular)."""
    from align import align
    from align.morph_align_hc import _verses
    verses = _verses(pair, sample)
    table, _used = align([(src, tgt) for _ref, src, tgt in verses], backend="hmm",
                         allow_cooccur_fallback=False)
    return verses, table


def project_verse(pivot_tokens: list, src: list, tgt: list, table) -> list[dict]:
    """For each vernacular word, inherit the dep-role, POS, morphological FEATS, and head of its
    best-aligned pivot token (restricted to tokens present in this verse). Returns
    [{vern, idx, role, pos, feats, head_vern}]. Tokens are (i, text, pos, dep, head, feats)."""
    dep = {}; pos_of = {}; feats_of = {}; head_word = {}
    for tok in pivot_tokens:
        i, txt, pos, d, h = tok[0], tok[1], tok[2], tok[3], tok[4]
        feats = tok[5] if len(tok) > 5 else {}
        if pos == "PROPN":               # names (the Matthew-1 genealogy tail) aren't structure — skip
            continue
        dep.setdefault(txt, d); pos_of.setdefault(txt, pos); feats_of.setdefault(txt, feats)
        head_word.setdefault(txt, pivot_tokens[h][1] if 0 <= h < len(pivot_tokens) else txt)
    v2e = {vw: (table.best(vw).source_word if table.best(vw) else None) for vw in set(tgt)}
    e2v: dict = {}
    for vw, ew in v2e.items():
        if ew:
            e2v.setdefault(ew, vw)
    out = []
    for idx, vw in enumerate(tgt):
        ew = v2e.get(vw)
        if ew and ew in dep:
            out.append({"vern": vw, "idx": idx, "role": dep[ew], "pos": pos_of.get(ew, ""),
                        "feats": feats_of.get(ew, {}), "head_vern": e2v.get(head_word.get(ew))})
    return out


# ── THING 1: derive TAM labels from the English Tense feature (retire the hardcoded TAM_KNOWN glosses) ───
def label_tam(pair: str, pivot: str = "en", sample: int = 0, min_count: int = 8) -> dict:
    """Project the English verb's Tense onto the vernacular verb, and tally (vernacular TAM marker → tense).
    Derives na→present, li→past, ta→future FROM DATA — no language-specific gloss table."""
    parser = get_parser(pivot)
    if parser is None:
        return {"error": "no pivot parser", "pivot": pivot}
    verses, table = _word_alignment(pair, sample)
    by_marker: dict[str, Counter] = {}
    for _ref, src, tgt in verses:
        if not src or not tgt:
            continue
        for p in project_verse(parser(" ".join(src)), src, tgt, table):
            tense = p["feats"].get("Tense")
            if p["pos"] == "VERB" and tense:
                v = p["vern"]; sm = subject_marker(v)
                if sm == "?" or len(v) <= len(sm) + 2:
                    continue
                by_marker.setdefault(v[len(sm):][:2], Counter())[tense] += 1   # 2-char TAM slot, derived
    labels = {}
    for tam, c in by_marker.items():
        if sum(c.values()) >= min_count:
            t, n = c.most_common(1)[0]
            labels[tam] = {"tense": t, "n": n, "confidence": round(n / sum(c.values()), 3)}
    return {"pair": pair, "derived_tam_labels": labels}


# ── THING 2: find the vernacular NEGATION marker by projecting English negation ─────────────────────────
NEG_WORDS = {"not", "n't", "no", "never", "cannot", "nor", "neither", "without"}


def induce_negation(pair: str, pivot: str = "en", sample: int = 0, min_neg: int = 10) -> dict:
    """A verse is negated if the English clause carries negation (dep=neg / Polarity=Neg / a neg word).
    Compare vernacular verb-initial morphemes in negated vs affirmative verses → the negation marker."""
    parser = get_parser(pivot)
    if parser is None:
        return {"error": "no pivot parser", "pivot": pivot}
    from gold.goldio import load_gold
    verbs = {w for w, p in load_gold(pair).get("pos", {}).items() if str(p).lower() == "verb"}
    verses, _table = _word_alignment(pair, sample)
    neg, aff = Counter(), Counter()
    for _ref, src, tgt in verses:
        if not tgt:
            continue
        toks = parser(" ".join(src)) if src else []
        is_neg = any(t[1] in NEG_WORDS or t[3] == "neg" or (len(t) > 5 and t[5].get("Polarity") == "Neg")
                     for t in toks)
        bucket = neg if is_neg else aff
        for w in tgt:
            if w in verbs and len(w) > 3:
                bucket[w[:2]] += 1
    out = []
    for pre, n in neg.most_common(25):
        a = aff.get(pre, 0)
        ratio = n / (a + 1)
        if n >= min_neg and ratio >= 2.0:                # over-represented in negated clauses
            out.append({"marker": pre, "in_neg": n, "in_aff": a, "ratio": round(ratio, 1)})
    return {"pair": pair, "negation_markers": out}


# ── THING 3: word order (S/V/O) from the projected roles ────────────────────────────────────────────────
def word_order(pair: str, pivot: str = "en", sample: int = 0) -> dict:
    """Constituent order from projected subject/verb/object positions → SVO/SOV/VSO… (a typological switch
    we already have the data for)."""
    parser = get_parser(pivot)
    if parser is None:
        return {"error": "no pivot parser", "pivot": pivot}
    verses, table = _word_alignment(pair, sample)
    full, sv = Counter(), Counter()
    for _ref, src, tgt in verses:
        if not src or not tgt:
            continue
        proj = project_verse(parser(" ".join(src)), src, tgt, table)
        s = next((p for p in proj if p["role"] in ("nsubj", "nsubjpass")), None)
        o = next((p for p in proj if p["role"] in ("obj", "dobj")), None)
        v = next((p for p in proj if p["role"] == "root" and p["pos"] == "VERB"), None)
        if s and v and o and len({s["idx"], v["idx"], o["idx"]}) == 3:
            order = sorted([("S", s["idx"]), ("V", v["idx"]), ("O", o["idx"])], key=lambda x: x[1])
            full["".join(x[0] for x in order)] += 1
        if s and v:
            sv["SV" if s["idx"] < v["idx"] else "VS"] += 1
    return {"pair": pair, "svo_orders": full.most_common(6), "subject_verb": sv.most_common(),
            "dominant": (full.most_common(1)[0][0] if full else None)}


def main(argv: list[str] | None = None) -> int:
    """Query/fetch UDPipe pivot models. `list [filter]` · `get <iso|lang|lang-treebank>` · `version`."""
    import argparse
    ap = argparse.ArgumentParser(description="UDPipe pivot models (pinned, queryable, any language).")
    ap.add_argument("cmd", choices=["list", "get", "version"])
    ap.add_argument("spec", nargs="?", default="")
    ap.add_argument("--version", default=None, help=f"release tag (default {UDPIPE_VERSION})")
    ap.add_argument("--refresh", action="store_true", help="re-query the model index")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if a.cmd == "version":
        print(f"pinned: {UDPIPE_VERSION}  ·  releases: {UDPIPE_RELEASES}")
    elif a.cmd == "list":
        idx = list_available(a.version, refresh=a.refresh)
        keys = sorted(k for k in idx if a.spec.lower() in k)
        langs = sorted({k.split("-")[0] for k in idx})
        print(f"{len(idx)} models, {len(langs)} languages in {a.version or UDPIPE_VERSION}"
              + (f" matching {a.spec!r}" if a.spec else "") + ":")
        for k in keys:
            print(f"  {k}")
    elif a.cmd == "get":
        if not a.spec:
            print("usage: get <iso|language|language-treebank>"); return 2
        path = download_model(a.spec, a.version, dest_key=a.spec)
        print(f"{'downloaded → ' + path if path else 'FAILED for ' + a.spec!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ── using projected subjects to discover the marking (the user's question) ──────────────────────────────
# Swahili verb = SM-TAM-(OM)-stem; the SUBJECT MARKER is the first prefix and agrees with the subject's
# noun class. Projecting the subject lets us read the SM off the verb and split prefix-ambiguous nouns.
_SM = sorted(["a", "wa", "u", "i", "li", "ya", "ki", "vi", "zi", "ku", "tu", "ni", "m", "ha", "ki"],
             key=len, reverse=True)


def subject_marker(verb: str) -> str:
    for s in _SM:
        if verb.startswith(s) and len(verb) > len(s) + 1:
            return s
    return "?"


def subject_verb_pairs(pair: str, pivot: str = "en", sample: int = 0):
    """(vernacular subject-noun, its vernacular verb) pairs, from projected `nsubj` relations."""
    parser = get_parser(pivot)
    if parser is None:
        return None
    verses, table = _word_alignment(pair, sample)
    pairs = []
    for _ref, src, tgt in verses:
        if not src or not tgt:
            continue
        proj = project_verse(parser(" ".join(src)), src, tgt, table)
        for p in proj:
            if p["role"] in ("nsubj", "nsubjpass") and p["head_vern"]:
                pairs.append((p["vern"], p["head_vern"]))
    return pairs


# verb subject-marker → noun class (Bantu head-marking). a-/u-/i- are shared by several classes → lower
# confidence; wa/ki/vi/li/zi/ya are clean. The m-noun cl1-vs-cl3 split rides on a- vs u-.
SM_TO_CLASS = {"a": "1", "wa": "2", "u": "3", "i": "4", "li": "5", "ya": "6", "ki": "7", "vi": "8", "zi": "10"}


def classify_by_subject_marking(pair: str, pivot: str = "en", sample: int = 0, min_count: int = 2) -> dict:
    """Per-NOUN class from the subject marker its verbs carry (projected subjects) — cracks prefix-ambiguous
    nouns (m- → cl1 via `a-` vs cl3 via `u-`) that adjacency/associative could not split."""
    pairs = subject_verb_pairs(pair, pivot, sample)
    if pairs is None:
        return {}
    by_noun: dict[str, Counter] = {}
    for noun, verb in pairs:
        by_noun.setdefault(noun, Counter())[subject_marker(verb)] += 1
    out = {}
    for noun, c in by_noun.items():
        clean = Counter({k: v for k, v in c.items() if k in SM_TO_CLASS})
        if sum(clean.values()) >= min_count:
            sm, n = clean.most_common(1)[0]
            out[noun] = {"class": SM_TO_CLASS[sm], "via_sm": sm, "n": n,
                         "confidence": round(n / sum(clean.values()), 3)}
    return out


# Swahili verb template = SM - TAM - (OM) - stem. With the SM known (from subject marking), the next
# morpheme is the tense/aspect marker. Known TAM set (for labelling); detection is by frequency.
TAM_KNOWN = {"na": "present", "li": "past", "ta": "future", "me": "perfect", "ki": "situative/-ing",
             "hu": "habitual", "ka": "consecutive", "nge": "conditional", "ja": "not-yet", "si": "negative"}


def induce_tam(pair: str, min_count: int = 20) -> dict:
    """Detect the verb's TAM slot: strip the subject marker off each gold verb, tally the next morpheme.
    The recurring second-position morphemes are the tense/aspect markers (na/li/ta/me…)."""
    from collections import Counter
    from gold.goldio import load_gold
    verbs = [w for w, p in load_gold(pair).get("pos", {}).items() if str(p).lower() == "verb"]
    tam: Counter = Counter()
    for v in verbs:
        sm = subject_marker(v)
        if sm == "?" or len(v) <= len(sm) + 2:
            continue
        rest = v[len(sm):]
        m = next((t for t in sorted(TAM_KNOWN, key=len, reverse=True) if rest.startswith(t)), rest[:2])
        tam[m] += 1
    found = [{"marker": m, "n": n, "gloss": TAM_KNOWN.get(m, "?")}
             for m, n in tam.most_common() if n >= min_count]
    return {"pair": pair, "tam_markers": found,
            "known_hits": [f for f in found if f["marker"] in TAM_KNOWN]}


# object markers (slot 3, between TAM and stem) — overlap the SM/noun-class forms; agree with the OBJECT's
# class. Detection is rough (OM is optional + medial), so this surfaces the inventory, not per-verb truth.
OM_SET = sorted(["ni", "ku", "tu", "wa", "m", "mw", "li", "ya", "ki", "vi", "zi", "i", "u", "wn", "ji", "pa"],
                key=len, reverse=True)


def induce_om(pair: str, min_count: int = 15) -> dict:
    """Detect the object-marker slot: after stripping SM + TAM, an OM appears (with a stem after it).
    Surfaces the OM inventory — completes the SM-TAM-OM-stem verb template."""
    from collections import Counter
    from gold.goldio import load_gold
    verbs = [w for w, p in load_gold(pair).get("pos", {}).items() if str(p).lower() == "verb"]
    om: Counter = Counter()
    for v in verbs:
        sm = subject_marker(v)
        if sm == "?":
            continue
        rest = v[len(sm):]
        tam = next((t for t in sorted(TAM_KNOWN, key=len, reverse=True) if rest.startswith(t)), None)
        if not tam:
            continue
        after = rest[len(tam):]
        cand = next((o for o in OM_SET if after.startswith(o) and len(after) > len(o) + 2), None)
        if cand:
            om[cand] += 1
    found = [{"marker": m, "n": n} for m, n in om.most_common() if n >= min_count]
    return {"pair": pair, "om_markers": found}


def subject_number_agreement(pair: str, pivot: str = "en", sample: int = 0, min_count: int = 20) -> dict:
    """Projection beyond Bantu: from projected subjects, does the verb's SUFFIX co-vary with subject
    NUMBER? (Spanish: sg subject → 3sg ending, pl → 3pl.) Subject number ~ noun ends in 's'. Surfaces the
    person/number agreement paradigm — a dependent of a non-class agreement system."""
    from collections import Counter
    pairs = subject_verb_pairs(pair, pivot, sample)
    if pairs is None:
        return {"error": "no pivot parser", "pivot": pivot}
    sg, pl = Counter(), Counter()
    for noun, verb in pairs:
        if len(verb) < 3:
            continue
        (pl if noun.endswith("s") and len(noun) > 3 else sg)[verb[-2:]] += 1
    top = lambda c: [(s, n) for s, n in c.most_common(6) if n >= min_count]   # noqa: E731
    return {"pair": pair, "singular_subject_endings": top(sg), "plural_subject_endings": top(pl),
            "n_pairs": len(pairs)}


def verb_template(pair: str, pivot: str = "en") -> dict:
    """Assemble the verb position-class template from the induced slots: SM (subject marking) - TAM - OM -
    stem. The golden-set byproduct for the verb's morphotactics."""
    sm = induce_subject_marking(pair, pivot)
    return {"pair": pair, "template": "SM-TAM-(OM)-stem",
            "slot1_SM": sm.get("sm_by_noun_prefix", {}),
            "slot2_TAM": [f["marker"] for f in induce_tam(pair).get("tam_markers", []) if f["marker"] in TAM_KNOWN],
            "slot3_OM": [f["marker"] for f in induce_om(pair).get("om_markers", [])]}


def induce_subject_marking(pair: str, pivot: str = "en", sample: int = 0, min_support: int = 8) -> dict:
    """Discover the verb's subject-marker per noun class from projected subjects — and crack prefix-ambiguous
    nouns (swh `m-` → cl1 `a-` SM vs cl3 `u-` SM). The thing adjacency couldn't see."""
    pairs = subject_verb_pairs(pair, pivot, sample)
    if pairs is None:
        return {"error": f"no '{pivot}' pivot parser available (install a spaCy/UDPipe model)", "pivot": pivot}
    from review.classes import _BANTU_PREFIXES

    def npfx(n: str) -> str:
        for p in _BANTU_PREFIXES:
            if n.startswith(p) and len(n) > len(p) + 1:
                return p
        return "Ø"

    by_prefix: dict[str, Counter] = {}
    for noun, verb in pairs:
        by_prefix.setdefault(npfx(noun), Counter())[subject_marker(verb)] += 1
    sm_by_prefix = {}
    for pfx, c in by_prefix.items():
        clean = Counter({k: v for k, v in c.items() if k != "?"})
        if sum(clean.values()) >= min_support:
            top = clean.most_common(2)
            sm_by_prefix[pfx] = {"dominant_sm": top[0][0], "dist": dict(clean.most_common(4)),
                                 "n": sum(clean.values())}
    return {"pair": pair, "pivot": pivot, "n_subject_verb_pairs": len(pairs),
            "sm_by_noun_prefix": sm_by_prefix}

