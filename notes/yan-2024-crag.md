# Yan et al. 2024 — Corrective Retrieval Augmented Generation (CRAG)

**Citation.** Shi-Qi Yan, Jia-Chen Gu, Yun Zhu, Zhen-Hua Ling. *Corrective
Retrieval Augmented Generation.* arXiv:2401.15884 (2024) —
<https://arxiv.org/abs/2401.15884>

**Why this source.** Phase 5. Its **retrieval evaluator is the closest
published analogue of the A4 judge** (`detectors/explicit_judge.py`): a
separate component that scores the retrieved evidence and triggers an action.
It serves the judge design and ADR-006 (the judge outputs yes/no only and puts
nothing into the answer context), where CRAG does the opposite: it refines and
supplements the context. Read after ReAct.

**Cross-refs used throughout:**
- [`docs/adr/adr-006-judge-outputs-boolean-only.md`](../docs/adr/adr-006-judge-outputs-boolean-only.md) (planned)
- `src/agentic_pokedex/arms/detectors/explicit_judge.py`, `prompts/`
- [`notes/joren-2025-sufficient-context.md`](joren-2025-sufficient-context.md) — the autorater
- [`notes/asai-2024-self-rag.md`](asai-2024-self-rag.md)

**Legend.** 🔄 → `notes/phase5-synthesis.md`.

---

## §3 — Task Formulation

### 3.1 — What is being corrected
**Prompt.**
- How do the authors formalize the problem (retriever R, generator G, input X,
  documents D)? Is "sufficient" or "correct retrieval" defined anywhere, or only
  operationally through the evaluator?

**My take.**

**Refined write-up.**

---

## §4 — CRAG

### 4.1 — Retrieval evaluator (§4.2)
**Prompt.**
- Which model (a fine-tuned T5-large) and trained on what labels? Does it score
  each document or the set? Why does per-document scoring break for S1 (two
  units that are only sufficient *together*) and S3 (a set)?
- Is the evaluator's accuracy reported (§5 "Accuracy of the Retrieval
  Evaluator")? Against what ground truth?

**My take.**

**Refined write-up.**

### 4.2 — Action trigger (§4.3)
**Prompt.**
- Write the rule: upper and lower thresholds → Correct / Incorrect / Ambiguous.
  How were the thresholds chosen? (Constants do not transfer: note the
  mechanism only.)
- Map the three actions onto the project's: answer / continue / abstain. Which
  CRAG action has no project counterpart (web search as a fallback source)?

**My take.**

**Refined write-up.**

### 4.3 — Knowledge refinement and web search (§4.4–4.5)
**Prompt.**
- Describe decompose-then-recompose. It **changes the context** the generator
  sees. Explain in one paragraph why ADR-006 forbids this for A4: which
  confounder would it introduce into the A4 − A3 comparison?

**My take.**

**Refined write-up.**

---

## §5 — Experiments

### 5.1 — Ablations and overhead
**Prompt.**
- Which ablation isolates the evaluator's contribution? How big is it, and is
  variance reported?
- "Computational Overhead Analysis": how is cost measured? Compare with the
  project's per-arm token and US$ reporting.
- "Robustness to Retrieval Performance": what happens when retrieval quality is
  degraded on purpose? Is that a controlled insufficiency, like S1–S4?

**My take.**

**Refined write-up.**

---

## §6 — Conclusion & Limitation

### 6.1 — Stated limitations
**Prompt.**
- What do the authors admit? Does any limitation concern *multi-step*
  retrieval (CRAG corrects once)?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
