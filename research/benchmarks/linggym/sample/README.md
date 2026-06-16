# sample/

A tiny vendored slice of the LingGym benchmark (6 items) so the pipeline runs offline
without fetching the full dataset. Used by `run.py`'s default `--root` and by tests.

**Attribution.** These items are from [LingGym](https://github.com/changbingY/LingGym)
(Yang, Ma, Shi, Zhu — *LingGym: How Far Are LLMs from Thinking Like Field Linguists?*,
EMNLP 2025), licensed **CC-BY-4.0**. For the full 19,612-item benchmark, run
`fetch_data.py` (pins the upstream commit).
