"""Smoke-test the harness against any configured endpoint.

Examples
--------
    # local (start `ollama run gemma4:27b` first)
    python scripts/smoke_test.py --endpoint ollama --prompt "Gloss 'ninakupenda'."

    # frontier (needs ANTHROPIC_API_KEY)
    python scripts/smoke_test.py --endpoint opus --prompt "Gloss 'ninakupenda'."

    # override the model for a registered endpoint
    python scripts/smoke_test.py --endpoint ollama --model qwen3.6:27b --prompt "..."
"""

from __future__ import annotations

import argparse
import sys

# Allow running as `python scripts/smoke_test.py` from the research/ dir.
sys.path.insert(0, ".")

from harness import Message, build_client  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--endpoint", required=True, help="registered endpoint name (e.g. ollama, opus)")
    ap.add_argument("--model", default=None, help="override the endpoint's default model")
    ap.add_argument("--prompt", required=True, help="user prompt to send")
    ap.add_argument("--system", default=None, help="optional system prompt")
    ap.add_argument("--max-tokens", type=int, default=512)
    args = ap.parse_args()

    overrides = {"model": args.model} if args.model else {}
    client = build_client(args.endpoint, **overrides)

    messages = []
    if args.system:
        messages.append(Message("system", args.system))
    messages.append(Message("user", args.prompt))

    result = client.complete(messages, max_tokens=args.max_tokens)

    print(f"--- {client.name} ({result.model}) ---")
    print(result.text)
    print("--- meta ---")
    print(
        f"in={result.input_tokens} out={result.output_tokens} "
        f"latency={result.latency_s:.2f}s stop={result.stop_reason}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
