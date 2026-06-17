"""Construct inventories for the structural measures (size, generalization, dead-construct glosses).

Three sources, one shape (`GrammarInventory`):
- `from_langmodel` — the golden `LangModel` (HermitCrab path).
- `from_liblcm_xml` — a FieldWorks `.fwdata` / LibLCM XML dump (read-only; the Python stand-in for the
  C# `liblcm-grammar-analyzer`, by element local-name counting).
- `from_lift_xml` — a LIFT lexicon export (lexicon-only counts).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class GrammarInventory:
    source: str
    counts: dict[str, int] = field(default_factory=dict)
    glosses: list[str] = field(default_factory=list)  # for dead-construct detection
    n_alternations: int | None = None  # morphemes with >1 surface form
    n_rule_derived: int | None = None  # alternations a phonological rule derives (None = unknown)


def _ln(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


# ------------------------------------------------------------------------------------ HermitCrab (LangModel)

def from_langmodel(model) -> GrammarInventory:
    """Counts from a golden `LangModel`. v1 is concatenative (no phon rules / listed allomorphs)."""
    slots = {f"{sd}{o}" for a in model.affixes for sd, o in a.filled_slots()}
    counts = {
        "lexical_entry": len(model.lexicon),
        "affix": len(model.affixes),
        "slot": len(slots),
    }
    glosses = [e.gloss for e in model.lexicon] + [a.gloss for a in model.affixes]
    # An "alternation" here = one gloss realized by >1 distinct form (would-be allomorphy).
    by_gloss: dict[str, set[str]] = {}
    for e in model.lexicon:
        by_gloss.setdefault(e.gloss, set()).add(e.form)
    for a in model.affixes:
        by_gloss.setdefault(a.gloss, set()).add(a.form)
    n_alt = sum(1 for forms in by_gloss.values() if len(forms) > 1)
    return GrammarInventory("hermitcrab", counts, glosses, n_alternations=n_alt, n_rule_derived=0)


# --------------------------------------------------------------------------------------------- LibLCM XML

# LibLCM class local-names → the scorecard construct-type bucket (verified against the primitives research).
_LIBLCM_BUCKETS = {
    "LexEntry": "lexical_entry",
    "MoStemAllomorph": "allomorph",
    "MoAffixAllomorph": "allomorph",
    "MoAffixProcess": "affix_process",
    "MoStemMsa": "msa",
    "MoInflAffMsa": "msa",
    "MoDerivAffMsa": "msa",
    "MoUnclassifiedAffixMsa": "msa",
    "PhRegularRule": "phonological_rule",
    "PhMetathesisRule": "phonological_rule",
    "PhSegmentRule": "phonological_rule",
    "PhNCFeatures": "natural_class",
    "PhNCSegments": "natural_class",
    "PhPhoneme": "phoneme",
    "MoInflAffixTemplate": "affix_template",
    "MoInflAffixSlot": "slot",
    "FsClosedFeature": "feature",
    "FsComplexFeature": "feature",
    "MoStratum": "stratum",
    "MoCompoundRule": "compound_rule",
    "MoEndoCompound": "compound_rule",
    "MoExoCompound": "compound_rule",
    "MoAdhocProhib": "ad_hoc_rule",
    "MoAlloAdhocProhib": "ad_hoc_rule",
    "MoMorphAdhocProhib": "ad_hoc_rule",
}


def from_liblcm_xml(xml_text: str) -> GrammarInventory:
    """Count LibLCM constructs by element local-name from a .fwdata/LCM XML dump (read-only)."""
    counts: Counter = Counter()
    glosses: list[str] = []
    alt_per_entry: list[int] = []
    root = ET.fromstring(xml_text)
    for el in root.iter():
        ln = _ln(el.tag)
        bucket = _LIBLCM_BUCKETS.get(ln)
        if bucket:
            counts[bucket] += 1
        if ln == "LexEntry":
            allos = sum(1 for d in el.iter() if _ln(d.tag) in ("MoStemAllomorph", "MoAffixAllomorph"))
            if allos:
                alt_per_entry.append(allos)
        if ln == "Gloss":
            txt = "".join(t.text or "" for t in el.iter() if (t.text or "").strip())
            if txt.strip():
                glosses.append(txt.strip())
    n_alt = sum(1 for a in alt_per_entry if a > 1)
    return GrammarInventory(
        "liblcm", dict(sorted(counts.items())), glosses,
        n_alternations=n_alt, n_rule_derived=None,  # rule↔allomorph mapping not derivable from counts
    )


# --------------------------------------------------------------------------------------------- LIFT XML

def from_lift_xml(xml_text: str) -> GrammarInventory:
    """Lexicon-only counts from a LIFT export (entries, senses, allomorph/variant forms)."""
    counts: Counter = Counter()
    glosses: list[str] = []
    root = ET.fromstring(xml_text)
    for el in root.iter():
        ln = _ln(el.tag)
        if ln == "entry":
            counts["lexical_entry"] += 1
        elif ln == "sense":
            counts["sense"] += 1
        elif ln == "variant":
            counts["allomorph"] += 1
        elif ln == "gloss":
            txt = next((t.text for t in el.iter() if _ln(t.tag) == "text" and t.text), None)
            if txt:
                glosses.append(txt.strip())
    return GrammarInventory("lift", dict(sorted(counts.items())), glosses, n_alternations=0, n_rule_derived=0)
