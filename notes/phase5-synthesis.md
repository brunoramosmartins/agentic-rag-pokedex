# Phase 5 — Reading Synthesis (ReAct × CRAG × Self-RAG × FLARE × Adaptive-RAG)

Cross-source questions for the Phase 5 readings. The output feeds the
detector design (`arms/detectors/`), the judge prompt, and the related-work
table in the README.

Sources:
- [`yao-2023-react.md`](yao-2023-react.md)
- [`yan-2024-crag.md`](yan-2024-crag.md)
- [`asai-2024-self-rag.md`](asai-2024-self-rag.md)
- [`jiang-2023-flare.md`](jiang-2023-flare.md)
- [`jeong-2024-adaptive-rag.md`](jeong-2024-adaptive-rag.md)

---

### S.1 — The detector table
**Prompt.**
- Build one table: method | when the decision is made (before / during /
  after retrieval) | signal (question, token probability, evaluator score,
  reflection token) | trained or prompted | touches the context (yes/no) |
  can abstain (yes/no). Add rows for A3, A4, A4p and A5. This table goes to the
  README.

**My take.**

**Refined write-up.**

### S.2 — The confounder each method carries
**Prompt.**
- For CRAG and Self-RAG, name what changes *besides* the stopping decision
  (context rewriting, extra retrieval, a different decoder). Explain why the
  A4p placebo and ADR-006 exist to remove exactly those confounders.

**My take.**

**Refined write-up.**

### S.3 — Loops that do not stop
**Prompt.**
- ReAct's repetitive-steps error and Ferrazzi's 53% identical re-retrievals:
  does the project log enough (units seen per step) to measure both
  mechanically? If not, what field is missing from the per-step log?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
