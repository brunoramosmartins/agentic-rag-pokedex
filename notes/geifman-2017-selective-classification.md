# Geifman & El-Yaniv 2017 — Selective Classification for Deep Neural Networks

**Citation.** Yonatan Geifman, Ran El-Yaniv. *Selective Classification for
Deep Neural Networks.* NeurIPS 2017. arXiv:1705.08500 —
<https://arxiv.org/abs/1705.08500>

**Companion for AURC.** The AURC metric is **not in this paper**, although it is often
attributed to it. Its primary source is Geifman, Uziel, El-Yaniv, *Bias-Reduced
Uncertainty Estimation for Deep Neural Classifiers*, ICLR 2019,
arXiv:1805.08206 — <https://arxiv.org/abs/1805.08206>. Read only its AURC
definition (skim).

**Why this source.** Phase 8. It serves **selective prediction**: risk,
coverage, the risk-coverage curve and choosing a threshold with a guarantee
(`evaluation/selective.py`, `classifier/policy.py`). The A5 detector is a
selective classifier: it outputs P(sufficient) and a threshold decides
answer vs keep searching / abstain. Read before Guo 2017 (calibration).

**Cross-refs used throughout:**
- [`docs/evaluation.md`](../docs/evaluation.md) — v1.1 metrics: risk-coverage, AURC, λ tipping point (planned)
- `src/agentic_pokedex/evaluation/selective.py`, `classifier/policy.py`
- `experiments/registry.md` — the Phase 8 entry (registered on Phase 8 day 1)
- [`notes/joren-2025-sufficient-context.md`](joren-2025-sufficient-context.md) — §5.1 selective generation

**Legend.** 🔄 → `notes/phase8-synthesis.md`.

---

## §2 — Problem Setting

### 2.1 — Definitions
**Prompt.**
- Write the definitions: selective classifier (f, g), coverage φ(f, g),
  selective risk R(f, g). Use LaTeX.
- The project's cost C ∈ {0 correct, 1 abstain, λ wrong}. Show that expected C
  is a linear function of coverage and selective risk:
  E[C] = (1 − φ)·1 + φ·R·λ (check it). What does minimizing E[C] imply about
  where on the risk-coverage curve you should operate?
- The paper's rejection is final. In the project, "not sufficient yet" means
  *keep searching* until T_max, then abstain. Does the selective framework still
  apply step by step? What breaks?

**My take.**

**Refined write-up.**

---

## §3 — Selection with Guaranteed Risk Control

### 3.1 — The SGR algorithm
**Prompt.**
- Write the SGR algorithm step by step: binary search over the threshold, the
  binomial tail bound, the confidence parameter δ, the target risk r*.
- What does the guarantee need that the project may not have (i.i.d. samples
  from the test distribution)? Is the dev split (group A only) i.i.d. with
  eval-L2 (groups A and B)?
- Compare with the project's theoretical threshold
  ≈ (1 − 1/λ) / P(correct | sufficient). One is a risk guarantee, the other a
  cost optimum. Which one goes into the Phase 8 entry?

**My take.**

**Refined write-up.**

---

## §4 — Confidence-Rate Functions for Neural Networks

### 4.1 — SR vs MC-dropout
**Prompt.**
- What is a confidence-rate function κ? Why is only the *ranking* it induces
  relevant to the risk-coverage curve (not its calibration)?
- 🔄 If only ranking matters for selection, why does Phase 8 also need
  calibration (Guo 2017)? Hint: the theoretical threshold uses P(sufficient) as
  a probability.

**My take.**

**Refined write-up.**

---

## §5 — Empirical Results

### 5.1 — How results are reported
**Prompt.**
- How is the guarantee validated empirically (train/test split, how many
  repetitions)? Borrow the *reporting template* for the model card, not the
  numbers.

**My take.**

**Refined write-up.**

---

## Companion — AURC (Geifman et al. 2019, skim)

### C.1 — The metric
**Prompt.**
- Write the AURC definition, and the "excess AURC" (E-AURC) the paper
  introduces. Why is E-AURC needed when comparing detectors with different
  base accuracy? Does the project need it (A4 vs A5 have different P(correct |
  sufficient)?)

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
