"""Deferral packages — turn a one-line `defer` record into a reviewable resolution ticket.

When the lexical/affix proposer or sense-picker defers a decision ("I don't know, ask a human"), this
package builds a **DeferralTicket**: a strict JSON + markdown package with auto-enumerated hypotheses
(each a typed HC grammar edit), HC-verified counterfactual parses ("if A were true this verse parses
thus"), 5–10 scripted speaker questions, triage tags (domain/impact/confidence/dependencies), and a
structured resolution that writes back to the `deltas/` ledger.

The deterministic spine (schema, counterfactual engine, taxonomy, builder, store, renderer) runs with
**no LLM**; the harness model only adds reach (out-of-taxonomy hypotheses) and readable prose, and every
model hypothesis is HC-verified before it enters a ticket.
"""

from __future__ import annotations
