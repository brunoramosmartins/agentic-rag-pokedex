# Ferrazzi et al. 2026 — Is Agentic RAG worth it?

**Citation.** Pietro Ferrazzi, Milica Cvjetićanin, Alessio Piraccini, Davide
Giannuzzi. *Is Agentic RAG worth it? An experimental comparison of RAG
approaches.* Industry Day at LREC 2026. arXiv:2601.07711 —
<https://arxiv.org/abs/2601.07711>

**Why this source.** It is the closest published head-to-head of "enhanced"
(fixed pipeline) vs "agentic" RAG, with cost, and it is the empirical anchor for
three project decisions: arm **A3** (the implicit detector: the agent decides on
its own whether to search again), arm **A2** (the fixed pipeline that "must be
ruled out first"), and the Phase 8 feature **novelty of the last search**, which
comes straight from its "10% of re-retrievals, 53% identical documents" result.
Read in Phase 0, **after Joren 2025**: Joren gives the sufficiency vocabulary,
and this paper shows an agent that almost never uses its chance to look again.

**Cross-refs used throughout:**
- [`docs/hypothesis.md`](../docs/hypothesis.md) — H1, the S0 control stratum (planned)
- [`docs/adr/adr-001-theme-and-thesis.md`](../docs/adr/adr-001-theme-and-thesis.md) — positioning (planned)
- [`docs/adr/adr-004-hand-rolled-agent-loop.md`](../docs/adr/adr-004-hand-rolled-agent-loop.md) — the loop (planned)
- [`docs/evaluation.md`](../docs/evaluation.md) — cost per arm, the agent cost multiplier (planned)
- `src/agentic_pokedex/classifier/features.py` — "novelty of the last search" (Phase 8)
- [`notes/joren-2025-sufficient-context.md`](joren-2025-sufficient-context.md)

**Legend.** 🔄 = needs synthesis with another source → `notes/phase0-synthesis.md`.

---

## §1 — Introduction

### 1.1 — What "Enhanced" and "Agentic" mean here
**Prompt.**
- Write both definitions in the authors' words. Where does this project's A2
  (search → expand typed links up to budget B) fall: Enhanced, or neither?
- Is the paper's agent a ReAct-style loop? Which framework is it built on, and
  what can the agent do that the Enhanced pipeline cannot?
- Predict before reading §3: will the paper measure *answer correctness*, or
  mostly retrieval and routing quality?

**My take.**

**Refined write-up.**

---

## §2 — Related Work

### 2.1 — Where the gap is
**Prompt.**
- What prior comparative studies do they cite, and why do they say those are
  insufficient?
- 🔄 Does the related work mention sufficiency, abstention or stopping at all?
  Compare with Joren §2.

**My take.**

**Refined write-up.**

---

## §3 — Evaluation

### 3.1 — Datasets (§3.1, Table 2)
**Prompt.**
- List the four datasets and their task type. Are any of them multi-hop? This is
  the claim ADR-001 makes ("only single-hop datasets"): verify it against
  Table 2.
- Is there an unanswerable or out-of-scope condition anywhere? If not, what does
  that imply about what the paper *cannot* say about abstention?
- The project's S0 stratum (one hop, sufficient) is designed to "replicate the
  null" of this paper. After reading Table 2, is that a fair description?

**My take.**

**Refined write-up.**

### 3.2 — User intent handling and query rewriting (§3.2–3.3)
**Prompt.**
- How is "user intent handling" defined, and how are invalid queries generated
  (Appendix: invalid query generation)? Is an out-of-scope query the same thing
  as this project's S4 (answer absent from the corpus)? Argue yes or no.
- Query rewriting: the agent wins on retrieval quality. Which metric (NDCG, see
  appendix), at which k? Is any significance test or CI reported?

**My take.**

**Refined write-up.**

### 3.3 — Document list refinement: the 10% / 53% result (§3.4, Appendix C.2)
**Prompt.**
- Quote the exact sentence with "10% of the times" and "53%". What is the
  denominator of each percentage (queries? retrieval calls? documents)?
- The authors interpret it as "once the model has taken a decision, it is not
  likely to reconsider it". Is that a claim about *search* or about *deciding*?
  Map it to the project's split (failing to search vs failing to decide).
- Read the example in Appendix C.2. Would a feature "overlap between the
  current and previous retrieval" have flagged it? This is the Phase 8 feature.
- How does this finding motivate arm A4p (the depth placebo)? If the agent
  rarely searches again, what does "searching more, blindly" buy?

**My take.**

**Refined write-up.**

### 3.4 — Underlying LLM (§3.5)
**Prompt.**
- Which models are compared, and how is quality judged here (an LLM-as-judge)?
  This project forbids an LLM judge on primary endpoints; note which of the
  paper's conclusions depend on a judge.

**My take.**

**Refined write-up.**

---

## §4 — Cost and Time

### 4.1 — The cost multiplier
**Prompt.**
- What is measured (tokens, US$, latency) and how? Record the headline
  multipliers (the abstract says up to 3.6× cost).
- Is cost reported *next to* the quality gain, per dataset? The project reports
  the agent's cost multiplier next to every gain; is there a template here worth
  copying as a concept?

**My take.**

**Refined write-up.**

---

## §5 — Conclusion and Limitations

### 5.1 — What the paper does not claim
**Prompt.**
- List the stated limitations. Is multi-hop reasoning among them?
- One-sentence positioning: "Ferrazzi et al. compare agentic and enhanced RAG
  on ___ and find ___; they do not measure ___." Fill the blanks. This sentence
  goes to ADR-001 and the README.
- 🔄 Joren shows models *answer* when context is insufficient; Ferrazzi shows
  agents rarely *search again*. Are these the same failure seen from two sides?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
