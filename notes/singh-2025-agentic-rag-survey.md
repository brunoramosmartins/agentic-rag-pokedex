# Singh et al. 2025 — Agentic RAG: A Survey (skim)

**Citation.** Aditi Singh, Abul Ehtesham, Saket Kumar, Tala Talaei Khoei,
Athanasios V. Vasilakos. *Agentic Retrieval-Augmented Generation: A Survey on
Agentic RAG.* arXiv:2501.09136 (2025, revised 2026) —
<https://arxiv.org/abs/2501.09136>

**Why this source.** Mode: **skim**, not a full read (42 pages). It serves one
decision: **placing the arms (A1–A5) in a published taxonomy** so the README and
ADR-001 use vocabulary a reader recognizes. Read last in Phase 0, after Joren
and Ferrazzi. Only the sections below are worth your time; the application
sections (healthcare, finance, legal…) are not.

Rule for surveys: every claim this project relies on must be traced to its
primary source; the survey is a map, never a citation for a number.

**Cross-refs used throughout:**
- [`docs/adr/adr-001-theme-and-thesis.md`](../docs/adr/adr-001-theme-and-thesis.md) (planned)
- `README.md` — "how this fits the literature" paragraph (Phase 7)
- [`notes/yan-2024-crag.md`](yan-2024-crag.md), [`notes/jeong-2024-adaptive-rag.md`](jeong-2024-adaptive-rag.md) — the primary sources behind two taxonomy boxes

**Legend.** 🔄 → `notes/phase0-synthesis.md`.

---

## §Taxonomy — "Taxonomy of Agentic RAG Systems"

### T.1 — Where do the arms sit?
**Prompt.**
- For each box (Single-Agent Router, Multi-Agent, Hierarchical, Corrective,
  Adaptive, Graph-Based, Document Workflows), write one line: who decides to
  retrieve again, and on what signal?
- Place A3 (implicit), A4 (boolean judge after each observation) and A5
  (calibrated classifier) in the taxonomy. Is A4 "Agentic Corrective RAG"? What
  is different (the judge only controls the loop; it never rewrites or adds
  context)?
- Does any box name the *stopping decision* as its central object? If not, that
  is the gap sentence for ADR-001.

**My take.**

**Refined write-up.**

---

## §Workflow patterns — "Evaluator-Optimizer" and "Routing"

### W.1 — Two patterns that look like this project
**Prompt.**
- Is the A4 loop an instance of Evaluator-Optimizer? Is A2 an instance of
  Prompt Chaining? One line each.
- Routing (Adaptive-RAG style) is the thesis ADR-001 discarded. Does the
  survey present routing as a quality or a cost argument?

**My take.**

**Refined write-up.**

---

## §Lessons + Open issues — "Lessons Learned and Practical Guidance", "Evaluation Methodologies Beyond Output Quality"

### L.1 — Process evaluation
**Prompt.**
- "Evaluation Must Account for Process, Not Just Outcomes": what do they
  propose? Does anything resemble per-step labels?
- "Agentic RAG Is Not Always the Right Default": which primary source backs it?
  🔄 Is it Ferrazzi?
- In "Benchmarks and Datasets", is there any benchmark with step-level
  sufficiency labels? If none, note it: it supports the claim that the
  generated benchmark is a publishable asset.

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
