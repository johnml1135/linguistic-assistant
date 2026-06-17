# Harness optimization research — top 5 improvements for LingGym-style MC

Goal: raise accuracy/robustness on multiple-choice word-gloss inference (pick A–D) over
an OpenAI-compatible chat endpoint (ik_llama.cpp), for local models (Gemma 4 31B QAT,
Qwen 3.6 27B). Each technique below is **research-verified** and **runnable in our
harness**, and is A/B-tested in `benchmarks/linggym/ab.py`.

> **Read the results with this caveat:** LingGym is contamination-inflated (these mid-2026
> models likely trained on it) and we sit near ceiling (~84–85%), so accuracy headroom is
> small and most deltas land within sampling noise. Two of the five (prior-debiasing,
> permutation) target **selection bias**, a separate axis from memorization, so they remain
> measurable here. The honest home for these A/Bs is the uncontaminated FLEx morph/phon set;
> this run validates the techniques + harness wiring and gives a first signal.

## Validated defaults (already in use, not separate A/Bs)
- **Greedy decoding (temperature 0).** Best for single-shot forced-choice; deterministic.
  Greedy ≥ sampling unless you spend many samples ([sampling-temperature study](https://arxiv.org/html/2402.05201v3)).
- **No chain-of-thought for MC.** CoT helps multi-step math but is flat-to-negative on
  simple MC classification ([TextReasoningBench](https://arxiv.org/pdf/2603.19558); Wharton
  [CoT tech report](https://gail.wharton.upenn.edu/research-and-insights/tech-report-chain-of-thought/)).
  LingGym's own authors found CoT didn't help. (We run `--reasoning off`.)

---

## The five

### 1. First-token log-probability scoring (replaces generate-and-parse)
Instead of generating text and regex-parsing a letter, read the model's probability over the
next token and take `argmax` of {A,B,C,D}. For single-letter answers this is exact, removes
all parse failures, and is more stable than generation (which is sensitive to wording).
- **Evidence:** logprob scoring is more robust than free-form parsing; parsing errors are a
  documented eval failure mode ([Right Answer, Wrong Score](https://arxiv.org/html/2503.14996v2);
  [xFinder](https://arxiv.org/html/2405.11874v1) — regex 81% vs fine-tuned 97% extraction).
  Surface-form/length issues that plague *string*-option logprobs ([Holtzman et al. 2021](https://aclanthology.org/2021.emnlp-main.564.pdf))
  **don't apply** here because every option is one token (a letter).
- **Cost:** 1× (1 token). **Implementation:** chat `logprobs:true, top_logprobs:N`.
- **Expected:** +0–3 pp accuracy; →0 parse failures; enables #2.

### 2. Letter-prior debiasing (PriDe / calibration) on the A–D logits
LLMs have a strong, content-independent preference for certain option letters; permutation
attacks swing accuracy 25–50 pp ([Zheng et al. 2024, ICLR](https://arxiv.org/abs/2309.03882);
[Zong et al. 2024](https://arxiv.org/html/2310.01651v3)). Estimate the model's per-letter
prior (from cyclic permutations on a small held-out slice) and subtract it from each item's
A–D logits before argmax (PriDe).
- **Evidence:** PriDe recovers +1–12 pp on MMLU at ~5% of permutation cost, prior is
  transferable ([Zheng et al. 2024](https://arxiv.org/abs/2309.03882)). Related: SCOPE/CalibraEval.
- **Cost:** ~1× + a one-time small estimation pass. **Needs #1 (logits).**
- **Expected:** small accuracy gain here (near ceiling), larger robustness gain.

### 3. Cyclic option-permutation + majority vote
Present each item in all 4 cyclic option orders, map each pick back to its **content**, and
majority-vote. Removes positional luck and is the most reliable single technique for true
capability.
- **Evidence:** cyclic ≈ full permutation in recovery at 4× (not 24×) cost; majority-vote
  over permutations gives large robustness/accuracy gains ([Zheng et al. 2024](https://arxiv.org/abs/2309.03882);
  [Quantifying & Mitigating Selection Bias](https://arxiv.org/html/2511.21709)).
- **Cost:** 4×. **Implementation:** re-render the option block in each rotation; remap.
- **Expected:** +0–4 pp accuracy; biggest consistency gain.

### 4. Few-shot exemplars (k=3, held-out)
Prepend a few solved items (from a pool disjoint from the eval set). Modest, cheap, but can
backfire if mismatched; instruction-tuned models gain less than base models.
- **Evidence:** ICL +1–7 pp on knowledge/MC ([GPT-3](https://arxiv.org/pdf/2005.14165));
  **retrieval-selected** demonstrations beat random by +5–21 pp on low-resource NER/QA
  ([Nature 2025](https://www.nature.com/articles/s44387-025-00062-2)); gains saturate by
  ~8–20 shots ([Many-shot ICL, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/file/8cb564df771e9eacbfe9d72bd46a24a9-Paper-Conference.pdf)).
- **Cost:** 1× (longer prompt). **Implementation:** prepend k examples (start static; retrieval later).
- **Expected:** +0–4 pp; variance high.

### 5. Knowledge/skill injection via the system role
Add a concise **system prompt**: a linguist task framing + a compact **Leipzig glossing
abbreviation reference** (PFV, NF, OBL, ERG, TOP, noun-class tags…). Targets the observed
failure mode (mis-reading gloss-tag *function*, not vocabulary).
- **Evidence:** injecting auto-generated linguistic instructions beats the BERT baseline on
  all 7 SIGMORPHON glossing languages ([Prompt and circumstance, SIGMORPHON 2025](https://aclanthology.org/2025.sigmorphon-main.1/));
  system-role instructions have a far larger effect than user-role ([LLM Shots, WWW 2025](https://dl.acm.org/doi/10.1145/3701716.3717814)).
  **Caveat:** a vague "you are an expert" persona can *hurt* knowledge tasks
  ([USC personas study](https://arxiv.org/abs/2603.18507)) and dumping a full glossary can
  add noise ([knowledge-injection](https://arxiv.org/abs/2311.01150)) — so we inject a
  *targeted reference + task definition*, not a persona.
- **Cost:** 1×. **Expected:** +0–5 pp; the most project-relevant (it's the skills thesis),
  and transfers directly to the morphophonology product.

## A/B protocol
- Fixed random sample (seed) from the full set, identical items for both models and all arms.
- Baseline = current harness (generate+parse, greedy, no-think, zero-shot, no system prompt).
- One arm per technique vs baseline; then the best combination.
- Report accuracy, Δ vs baseline, unparsed count, and wall-clock. Greedy ⇒ deterministic, so
  Δs are not sampling-of-the-model noise, but **item-sampling** noise applies (±~3–5 pp at
  N≈200–400) — small Δs are not significant; we say so.

Sources are linked inline above; full agent research notes summarized here.
