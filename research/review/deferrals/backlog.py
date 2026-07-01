"""The issue backlog — the core-workflow entry that unifies every deferral source into one ticket queue.

This is where the pipeline's Stage-2 sources converge: the model's `defer` records (propose / affix), the
**concept-driven lexeme discovery** (`discover.py` — "we have no word for HAND; here are the candidates"),
and (optionally) the morpheme-alignment deferrals. Each source yields `defer` records; this module
de-duplicates them, builds tickets (`build.build_all`), and writes the prioritized
`deferrals/<pair>/tickets.jsonl` the review UI works through.

So `discover` is not an orphan CLI — it is a registered backlog source here, run as part of building the
queue:  corpus → align → {propose, **discover**, morph} → backlog → review (UI/deltas).
"""

from __future__ import annotations

from . import build, discover


def _dedup(records: list[dict]) -> list[dict]:
    """Drop records that target the same lexeme/affix (first writer wins; keeps the queue clean)."""
    out, seen = [], set()
    for r in records:
        key = (r.get("word") or "", r.get("affix") or "")
        if key == ("", ""):
            out.append(r)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def gather(pair: str, *, use_propose: bool = True, use_discover: bool = True, use_morph: bool = False,
           backend: str = "eflomal", discover_top: int = 20, extra_records: list[dict] | None = None) -> list[dict]:
    """Collect `defer` records from every enabled source (de-duplicated)."""
    records: list[dict] = list(extra_records or [])
    if use_propose:
        records += build.load_defer_records(pair)                 # model defer records (propose / affix)
    if use_discover:
        rep = discover.run(pair, backend=backend, top=discover_top)
        records += [discover.to_defer_record(r) for r in rep["reports"]]
    if use_morph:
        from align.morph_align_hc import run as morph_run, to_deferral_records
        # the morpheme-alignment deferrals (the noisy function-morpheme tail) — heavy; off by default
        markers = []  # morph_run returns a summary; deferred markers come from its store file
        records += to_deferral_records(markers)
    return _dedup(records)


def build_backlog(pair: str, *, with_counterfactuals: bool = False, **gather_kw) -> dict:
    """Build the unified ticket backlog for a pair and persist it. Returns a summary.

    `with_counterfactuals=False` by default so the queue builds fast (HC counterfactuals are attached
    per-ticket on demand in the review step / when a ticket is opened)."""
    from .store import TicketStore
    records = gather(pair, **gather_kw)
    tickets = build.build_all(pair, records, with_counterfactuals=with_counterfactuals)
    store = TicketStore(pair)
    new = store.upsert(tickets)
    store.save()
    by_source = {}
    for r in records:
        by_source[r.get("source", "?")] = by_source.get(r.get("source", "?"), 0) + 1
    return {"pair": pair, "records": len(records), "tickets": len(tickets), "new": new,
            "by_source": by_source, "store": str(store.path)}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", required=True, choices=["spa", "ind", "tgl", "swh"])
    ap.add_argument("--backend", default="eflomal", help="eflomal (THOT) | cooccur (offline)")
    ap.add_argument("--no-discover", action="store_true", help="skip concept-driven lexeme discovery")
    ap.add_argument("--no-propose", action="store_true", help="skip existing model defer records")
    ap.add_argument("--discover-top", type=int, default=20)
    args = ap.parse_args(argv)
    s = build_backlog(args.pair, backend=args.backend, use_discover=not args.no_discover,
                      use_propose=not args.no_propose, discover_top=args.discover_top)
    print(f"[{args.pair}] backlog: {s['records']} defer records ({s['by_source']}) "
          f"→ {s['tickets']} tickets ({s['new']} new) → {s['store']}")
    print("  open the review UI:  uv run python -m deferrals.webui --pair " + args.pair)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
