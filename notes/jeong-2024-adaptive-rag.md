# Jeong et al. 2024 — Adaptive-RAG (skim)

**Citation.** Soyeong Jeong, Jinheon Baek, Sukmin Cho, Sung Ju Hwang, Jong C.
Park. *Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language
Models through Question Complexity.* NAACL 2024. arXiv:2403.14403 —
<https://arxiv.org/abs/2403.14403>

**Why this source.** Mode: **skim**. Phase 5. It serves **the argument for why
routing is not the thesis** (ADR-001: the original P3 plan was a router, and was
discarded because routing is a cost argument, not a quality one). Adaptive-RAG
routes *before* retrieval by predicted question complexity; this project
decides *during* retrieval by the state of the evidence.

**Cross-refs used throughout:**
- [`docs/adr/adr-001-theme-and-thesis.md`](../docs/adr/adr-001-theme-and-thesis.md) (planned)
- [`notes/singh-2025-agentic-rag-survey.md`](singh-2025-agentic-rag-survey.md) — "Adaptive Agentic RAG" box

**Legend.** 🔄 → `notes/phase5-synthesis.md`.

---

## §3 — Method (§3.1–3.2)

### 3.1 — The complexity classifier
**Prompt.**
- What are the three classes, and how are training labels produced
  automatically (which strategy answered correctly, plus the dataset's
  inductive bias)? Note: labels come from outcomes, not from evidence.
- The decision is made **once, from the question alone**. Can it detect S2
  (wrong version) or S4 (no answer in the corpus)? Why not?

**My take.**

**Refined write-up.**

---

## §5 — Experimental Results and Analyses

### 5.1 — Quality vs cost
**Prompt.**
- Is the headline gain in accuracy, in efficiency, or both? Compare with the
  "multi-step always" baseline.
- One sentence for ADR-001: "Adaptive-RAG shows that routing by question
  complexity ___; it does not address ___."

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
