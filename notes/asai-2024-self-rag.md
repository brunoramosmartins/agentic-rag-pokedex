# Asai et al. 2024 — Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection

**Citation.** Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh
Hajishirzi. *Self-RAG: Learning to Retrieve, Generate, and Critique through
Self-Reflection.* ICLR 2024. arXiv:2310.11511 — <https://arxiv.org/abs/2310.11511>

**Why this source.** Phase 5. It serves **the decision to retrieve by
reflection**: Self-RAG trains the model itself to emit "should I retrieve?" and
"is this passage supporting?" tokens. That is a *trained, internal* detector,
which sits between A3 (implicit, prompted) and A5 (trained, external
classifier). Read after ReAct and CRAG.

**Cross-refs used throughout:**
- `src/agentic_pokedex/arms/detectors/implicit.py`, `explicit_judge.py`, `trained.py`
- [`docs/adr/adr-006-judge-outputs-boolean-only.md`](../docs/adr/adr-006-judge-outputs-boolean-only.md) (planned)
- [`notes/yan-2024-crag.md`](yan-2024-crag.md), [`notes/jiang-2023-flare.md`](jiang-2023-flare.md)

**Legend.** 🔄 → `notes/phase5-synthesis.md`.

---

## §3 — Self-RAG: Learning to Retrieve, Generate and Critique

### 3.1 — Reflection tokens (§3.1, Appendix A)
**Prompt.**
- List the four reflection token types and their possible values (Retrieve,
  IsRel, IsSup, IsUse). Which one is closest to "is this enough?"
- IsSup grades whether the *generated output* is supported by a passage. The
  project's sufficiency label grades whether the *evidence* allows an answer,
  before any answer is generated. Explain why these are different questions.

**My take.**

**Refined write-up.**

### 3.2 — Training the critic and the generator (§3.2)
**Prompt.**
- Where do the critic's training labels come from (GPT-4 annotations)? How
  good are they, per the paper? Compare with the project's labels, exact by
  construction.
- The project does not fine-tune (4 GB GPU, RL parked). What is the cheapest
  idea from Self-RAG that survives without training?

**My take.**

**Refined write-up.**

### 3.3 — Inference: adaptive retrieval and critique-guided decoding (§3.3)
**Prompt.**
- How is the retrieval decision made at inference (a threshold on the Retrieve
  token probability)? This is a *per-segment* sequential decision: is it
  analogous to the project's per-step decision?
- Segment-level beam search with critique scores: what does it cost in extra
  forward passes?

**My take.**

**Refined write-up.**

---

## §4–5 — Experiments, Results and Analysis

### 4.1 — What the ablations say
**Prompt.**
- Which ablation removes the retrieval decision (always vs adaptive retrieve)?
  What changes?
- How is correctness graded on the short-form QA tasks (match, or a model
  judge)? Any CIs or seeds?
- 🔄 Is there an abstention outcome anywhere in Self-RAG's evaluation?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
