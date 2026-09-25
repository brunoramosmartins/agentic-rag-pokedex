# Jiang et al. 2023 — FLARE: Active Retrieval Augmented Generation (skim)

**Citation.** Zhengbao Jiang, Frank F. Xu, Luyu Gao, Zhiqing Sun, Qian Liu,
Jane Dwivedi-Yu, Yiming Yang, Jamie Callan, Graham Neubig. *Active Retrieval
Augmented Generation.* EMNLP 2023. arXiv:2305.06983 —
<https://arxiv.org/abs/2305.06983>

**Why this source.** Mode: **skim**. Phase 5 (and Phase 8). It serves one
idea: **retrieval triggered by low token confidence**. That is a cheap signal
of the model's state — a candidate feature for the trained detector
(`classifier/features.py`, "confidence declared by the model").

**Cross-refs used throughout:**
- `src/agentic_pokedex/classifier/features.py` (Phase 8)
- [`notes/asai-2024-self-rag.md`](asai-2024-self-rag.md), [`notes/kadavath-2022-lms-know-what-they-know.md`](kadavath-2022-lms-know-what-they-know.md)

**Legend.** 🔄 → `notes/phase5-synthesis.md`.

---

## §2 — Retrieval Augmented Generation (§2.1–2.3)

### 2.1 — The active retrieval framework
**Prompt.**
- How do the authors formalize "active" retrieval: a query function q_t and a
  decision of *when* to retrieve at each step? Write it in their notation.
- Is "when to stop retrieving" part of the framework, or only "when to
  retrieve"?

**My take.**

**Refined write-up.**

---

## §3.2 — Direct FLARE

### 3.1 — Confidence-based triggering (§3.2.1–3.2.2)
**Prompt.**
- The rule: retrieve if any token of the tentative sentence has probability
  below θ. What does it assume about calibration? 🔄 Does Kadavath 2022 support
  that assumption?
- The project's primary model is reached through an API: are token
  log-probabilities available for it? If not, the feature needs a different
  proxy. Note it for Phase 8.

**My take.**

**Refined write-up.**

---

## §9 — Limitations

### 9.1 — Where it does not help
**Prompt.**
- On which datasets did FLARE not help, and what reason do the authors give?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
