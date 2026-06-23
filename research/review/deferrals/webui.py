"""A THROWAWAY local web UI to dream about "working through issues" — the deferral-ticket review UX.

Purpose: feel the bug-tracker workflow a linguist will use, before any C# is written. It is a pure
**consumer** of the existing `deferrals/` functions — it owns no logic (Workstream 5 of the repo
assessment). Stdlib only (`http.server`), no new dependencies; disposable by design. The lessons (not the
code) graduate to the C# loop console later.

Run:  uv run python -m deferrals.webui --pair spa --seed-demo --port 8765
Then open http://127.0.0.1:8765/ and work the queue: open a ticket → accept an option / accept + words /
reject with a reason → it writes through `TicketStore.resolve` to `deltas/` and re-scores dependents.
"""

from __future__ import annotations

import html
import http.server
import json
import urllib.parse

from . import build
from .render import render
from .schema import Resolution
from .store import TicketStore

# a few synthetic defer records so the UI has something to show without a live Gemma run
_DEMO = [
    {"word": "amare", "gloss": "love", "pos": "Verb", "aligner_top1": "love", "conf": "medium",
     "current_gold": None, "decision": "defer", "source": "demo"},
    {"word": "abriere", "gloss": "open", "pos": "Verb", "aligner_top1": "open", "conf": "low",
     "decision": "defer", "source": "demo"},
    {"affix": "ndo", "kind": "suffix", "function": "gerund", "feature": {"Aspect": "Prog"},
     "conf": "low", "source": "demo"},
]


def seed_demo(store: TicketStore) -> int:
    """Populate the store with demo tickets (no counterfactuals → fast/offline) if it is empty."""
    if store.tickets:
        return 0
    tickets = build.build_all(store.pair, _DEMO, with_counterfactuals=False)
    n = store.upsert(tickets)
    store.save()
    return n


# --------------------------------------------------------------------------- tiny markdown → HTML
def _md_to_html(md: str) -> str:
    out = []
    for line in md.splitlines():
        e = html.escape(line)
        if line.startswith("### "):
            out.append(f"<h3>{e[4:]}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{e[3:]}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{e[2:]}</h1>")
        elif line.startswith("- "):
            out.append(f"<li>{e[2:]}</li>")
        elif not line.strip():
            out.append("<br>")
        else:
            out.append(f"<p>{e}</p>")
    return "\n".join(out).replace("**", "")


_CSS = ("<style>body{font:15px/1.5 system-ui,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;"
        "color:#1a1a1a}a{color:#0645ad}h1{font-size:1.5rem}h2{font-size:1.15rem;margin-top:1.4rem;"
        "border-bottom:1px solid #ddd}.pri-high{color:#b00}.pri-medium{color:#a60}.pri-low{color:#777}"
        "li{margin:.2rem 0}form{background:#f6f6f6;padding:1rem;border-radius:8px;margin-top:1rem}"
        "label{display:block;margin:.5rem 0}input,select,textarea{font:inherit}"
        "button{font:inherit;padding:.4rem .9rem;background:#0645ad;color:#fff;border:0;border-radius:6px;"
        "cursor:pointer}.q{background:#eef;padding:.4rem .6rem;border-radius:6px;margin:.2rem 0}</style>")


def queue_html(store: TicketStore) -> str:
    rows = []
    for t in store.list():
        cls = f"pri-{t.impact.get('priority','low')}"
        badge = "✓ resolved" if t.status in ("resolved", "wont_fix") else t.status
        rows.append(f"<li><a href='/ticket/{html.escape(t.id)}'>{html.escape(t.id)}</a> "
                    f"<span class='{cls}'>[{t.impact.get('priority','?')}]</span> "
                    f"· {t.type} · {len(t.hypotheses)} hyp · <em>{badge}</em></li>")
    body = "<ol>" + "\n".join(rows) + "</ol>" if rows else "<p>No tickets. Restart with --seed-demo.</p>"
    return (f"<!doctype html>{_CSS}<h1>Issue queue — {store.pair}</h1>"
            f"<p>{len(store.list(status='open'))} open · work them top-down (impact × resolvability).</p>{body}")


def ticket_html(store: TicketStore, tid: str, msg: str = "") -> str:
    t = store.get(tid)
    if t is None:
        return f"{_CSS}<p>No such ticket. <a href='/'>back</a></p>"
    opts = "".join(f"<option value='{h.id}'>{h.id}: {html.escape(h.description)}</option>" for h in t.hypotheses)
    form = ""
    if t.status not in ("resolved", "wont_fix"):
        form = f"""
        <form method='post' action='/resolve'>
          <input type='hidden' name='id' value='{html.escape(t.id)}'>
          <label><input type='radio' name='action' value='accept_option' checked> Accept option:
            <select name='hypothesis_id'>{opts}</select></label>
          <label><input type='radio' name='action' value='accept_with_words'> Accept + extra forms
            (comma-sep): <input name='extra_words' size='30'></label>
          <label><input type='radio' name='action' value='reject_with_reason'> Reject — reason:
            <input name='reason' size='40'></label>
          <button type='submit'>Resolve &amp; advance</button>
        </form>"""
    note = f"<p style='color:#070'><b>{html.escape(msg)}</b></p>" if msg else ""
    return (f"<!doctype html>{_CSS}<p><a href='/'>← queue</a></p>{note}"
            f"{_md_to_html(render(t))}{form}")


# --------------------------------------------------------------------------- the server
def make_handler(store: TicketStore):
    class H(http.server.BaseHTTPRequestHandler):
        def _send(self, body: str, code: int = 200):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/":
                self._send(queue_html(store))
            elif path.startswith("/ticket/"):
                self._send(ticket_html(store, urllib.parse.unquote(path[len("/ticket/"):])))
            else:
                self._send("<p>not found</p>", 404)

        def do_POST(self):
            if urllib.parse.urlparse(self.path).path != "/resolve":
                return self._send("<p>not found</p>", 404)
            n = int(self.headers.get("Content-Length", 0))
            form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8"))
            g = lambda k: form.get(k, [""])[0]  # noqa: E731
            res = Resolution(
                action=g("action"), hypothesis_id=g("hypothesis_id"),
                extra_words=[w.strip() for w in g("extra_words").split(",") if w.strip()],
                reason=g("reason"), by="webui")
            out = store.resolve(g("id"), res)
            store.save()
            # show the loop closing: re-score dependents (cyclical re-eval), then back to the ticket
            msg = f"{res.action} → {out.get('status')}; {out.get('ops',0)} delta op(s) written."
            self.send_response(303)
            self.send_header("Location", f"/ticket/{urllib.parse.quote(g('id'))}?done=1")
            self.end_headers()
            # stash a one-shot message via a module attr (prototype shortcut)
            H._last_msg[g("id")] = msg

        def log_message(self, *a):  # quiet
            pass

    H._last_msg = {}
    return H


def serve(pair: str, port: int = 8765, seed: bool = False) -> None:
    store = TicketStore(pair)
    if seed:
        seed_demo(store)
    handler = make_handler(store)
    # weave the one-shot resolve message into ticket views
    orig = handler.do_GET

    def do_GET(self):  # noqa: ANN001
        path = urllib.parse.urlparse(self.path)
        if path.path.startswith("/ticket/"):
            tid = urllib.parse.unquote(path.path[len("/ticket/"):])
            msg = handler._last_msg.pop(tid, "")
            return self._send(ticket_html(store, tid, msg))
        return orig(self)

    handler.do_GET = do_GET
    srv = http.server.HTTPServer(("127.0.0.1", port), handler)
    print(f"[{pair}] issue-review UI on http://127.0.0.1:{port}/  ({len(store.list())} tickets) — Ctrl-C to stop")
    srv.serve_forever()


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pair", default="spa", choices=["spa", "ind", "tgl", "swh"])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--seed-demo", action="store_true", help="seed a few demo tickets if the store is empty")
    args = ap.parse_args(argv)
    serve(args.pair, port=args.port, seed=args.seed_demo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
