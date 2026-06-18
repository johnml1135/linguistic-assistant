"""Phase 1 of the phonology-induction loop: collapse vowel-harmony allomorph families.

The TDD cycle (`cycle/tdd.py`) lists harmony allomorphs as separate affixes (`lar`/`ler`,
`nın`/`nin`/`nun`/`nün`) and reports the redundancy as `enumeration_debt`. This module turns that
debt into the optimization target: from a harmony family it proposes a single **archiphoneme** affix
(`lAr`, `nIn`) plus the conditioning **natural class**, then *generates* the surface allomorphs from
the rule. A family is collapsible only when the rule regenerates every observed allomorph (coverage
holds) and the affix count drops (Occam) — the same engine+oracle discipline as the HC gate, run here
with the harmony-rule expander as the offline oracle.

Text-only: no audio and no `hc.exe` are required to propose or verify a collapse. The audio add-on can
later *confirm* a family's conditioning feature, but it is never needed to run this step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Archiphoneme natural classes per language: symbol -> the surface vowels it ranges over.
# 'A' = low/unrounded 2-way backness alternation; 'I' = high 4-way (backness x rounding).
HARMONY_CLASSES: dict[str, dict[str, set[str]]] = {
    "tur": {
        "A": set("ae"),
        "I": set("ıiuü"),
    },
    "hun": {
        # Hungarian back/front low alternation (-nak/-nek, -ban/-ben, -hoz/-hez ...).
        "A": set("ae"),
        # High/closed alternation (-ig stays, but -tól/-től uses the long-mid set below).
        "I": set("ií"),
        "O": set("óő"),
    },
}


@dataclass(frozen=True)
class ArchiphonemeProposal:
    """A proposed collapse of one harmony family into one archiphoneme affix + rule."""

    members: list[str]
    archiphoneme: str
    conditioning_symbol: str | None
    generated: set[str]
    collapsible: bool
    reason: str = ""

    @property
    def affixes_removed(self) -> int:
        return (len(set(self.members)) - 1) if self.collapsible else 0


@dataclass
class CollapseReport:
    """Result of collapsing a set of harmony families."""

    collapsed: list[ArchiphonemeProposal] = field(default_factory=list)
    retained: list[ArchiphonemeProposal] = field(default_factory=list)
    debt_before: int = 0
    debt_after: int = 0

    @property
    def affixes_removed(self) -> int:
        return sum(p.affixes_removed for p in self.collapsed)


def enumeration_debt(families: dict[str, list[str]]) -> int:
    """Redundant allomorph count: each family of N members costs N-1 affixes a rule could remove."""
    return sum(len(set(members)) - 1 for members in families.values())


def _class_for(vowels: set[str], classes: dict[str, set[str]]) -> str | None:
    """Smallest harmony class whose members are a superset of ``vowels`` (deterministic)."""
    candidates = [(len(members), symbol) for symbol, members in classes.items() if vowels <= members]
    if not candidates:
        return None
    return min(candidates)[1]


def propose_archiphoneme(members: list[str], classes: dict[str, set[str]]) -> ArchiphonemeProposal | None:
    """Propose a single archiphoneme + conditioning class for a harmony family.

    Conservative: auto-collapsible only when the members differ in exactly one position, that position
    is a vowel alternation, and the observed vowels fall within a single harmony class. Anything else is
    returned with ``collapsible=False`` so it stays on the generalize worklist for review.
    """
    uniq = sorted(set(members))
    if len(uniq) < 2:
        return None

    lengths = {len(m) for m in uniq}
    if len(lengths) != 1:
        return ArchiphonemeProposal(uniq, "", None, set(), False, "members differ in length")

    width = lengths.pop()
    diff_positions = [i for i in range(width) if len({m[i] for m in uniq}) > 1]
    if len(diff_positions) != 1:
        return ArchiphonemeProposal(uniq, "", None, set(), False, "not a single-position alternation")

    pos = diff_positions[0]
    vowels = {m[pos] for m in uniq}
    all_vowels = set().union(*classes.values())
    if not vowels <= all_vowels:
        return ArchiphonemeProposal(uniq, "", None, set(), False, "differing position is not a harmony vowel")

    symbol = _class_for(vowels, classes)
    if symbol is None:
        return ArchiphonemeProposal(uniq, "", None, set(), False, "vowels span no single harmony class")

    template = uniq[0]
    archiphoneme = template[:pos] + symbol + template[pos + 1 :]
    generated = expand_archiphoneme(archiphoneme, classes)
    if not set(uniq) <= generated:
        return ArchiphonemeProposal(uniq, archiphoneme, symbol, generated, False, "rule does not regenerate members")

    return ArchiphonemeProposal(uniq, archiphoneme, symbol, generated, True, "")


def expand_archiphoneme(archiphoneme: str, classes: dict[str, set[str]]) -> set[str]:
    """Generate surface forms by substituting each archiphoneme symbol with its class members.

    This is the forward (generate) direction of the harmony rule; offline it is the oracle that the
    proposed collapse must satisfy (it must regenerate every attested allomorph).
    """
    surfaces = {""}
    for ch in archiphoneme:
        if ch in classes:
            surfaces = {prefix + v for prefix in surfaces for v in sorted(classes[ch])}
        else:
            surfaces = {prefix + ch for prefix in surfaces}
    return surfaces


def collapse_families(
    families: dict[str, list[str]],
    classes: dict[str, set[str]],
) -> CollapseReport:
    """Collapse every auto-collapsible harmony family; leave the rest as residual debt."""
    report = CollapseReport(debt_before=enumeration_debt(families))
    for members in families.values():
        proposal = propose_archiphoneme(members, classes)
        if proposal is None:
            continue
        if proposal.collapsible:
            report.collapsed.append(proposal)
        else:
            report.retained.append(proposal)
    collapsed_keys = {tuple(p.members) for p in report.collapsed}
    residual = {
        skel: members
        for skel, members in families.items()
        if tuple(sorted(set(members))) not in collapsed_keys
    }
    report.debt_after = enumeration_debt(residual)
    return report
