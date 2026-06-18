# research/

**Stage 1 — the Python research playground** (see the repo root README's maturity stages). Where ideas
are iterated and proven against the golden set before the C# validation program (`src/`) inherits the
proven pieces. Provider-agnostic LLM harness, golden sets, and the offline alignment/QA tooling.

## Packages
| Package | What it is |
|---|---|
| `harness/` | provider-agnostic `LLMClient` (`openai_compat` = ik_llama/local, `anthropic` = BYOK, `mock`) + endpoint registry |
| `golden/` | own gold sets + ablation harness + HC-verified `word→gloss` round-trip (sibling-owned) |
| `proposal/` | the shared **propose core** (`Case → ChangeSet`) + the change-set op vocabulary |
| `eval/` | the golden eval runner (propose → score → report) |
| `bilingual/` | the **Apertium-alignment bridge** — deterministic lemma/bidix reference-finder + FLExTrans `.dix` interop |
| `align/` | **statistical** word-gloss alignment (eflomal / THOT via `sil-machine`, co-occurrence fallback) |
| `benchmarks/` | LingGym calibration + results |

## Environment (uv)
The project is managed with **[uv](https://docs.astral.sh/uv/)**; deps are pinned in `uv.lock`.

```bash
cd research
uv sync                    # core (anthropic, httpx)
uv sync --extra align      # + sil-machine[thot] (+ eflomal on Linux) for word alignment
uv sync --extra data-prep  # + flexlibs (Windows + a FieldWorks install only)
```

`requires-python` is `>=3.10,<3.14` (upper bound from `sil-machine`). No torch/transformers/GPU extras.

## Running things
Most tools run from the `research/` dir (modules import `from harness import …`, etc.):

```bash
python eval/run.py --fixture            # offline eval/proposal loop
python bilingual/tests_smoke.py         # Apertium bridge (offline)
python align/tests_smoke.py             # word-gloss alignment (offline, co-occurrence backend)
```

Smoke tests across `eval/`, `bilingual/`, `align/` are dependency-free (no model, no native build, no
network) so CI stays green while real golden data and the native toolchains land on the box.

## Serving local models
`../serving/` builds & runs `ik_llama.cpp` `llama-server` behind an OpenAI-compatible endpoint that the
`harness` drives. See `serving/README.md`.
