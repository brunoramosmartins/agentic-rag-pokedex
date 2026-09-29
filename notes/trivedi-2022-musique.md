# Trivedi et al. 2022 — MuSiQue: Multihop Questions via Single-hop Question Composition

**Citation.** Harsh Trivedi, Niranjan Balasubramanian, Tushar Khot, Ashish
Sabharwal. *MuSiQue: Multihop Questions via Single-hop Question Composition.*
TACL 2022. arXiv:2108.00573 — <https://arxiv.org/abs/2108.00573> · data:
<https://github.com/StonyBrookNLP/musique>

**Why this source.** Phase 2. It serves the **anti-shortcut filters of the
generator** (`examiner/filters.py`): the single-unit shortcut filter is
modeled on the central care of MuSiQue's construction. It also
serves Phase 10: MuSiQue-Full's answerable/unanswerable pairs are the external
calibration set. Read before writing `filters.py`; skim Ho et al. 2020
(2WikiMultiHopQA) right after, for the template side.

**Cross-refs used throughout:**
- [`docs/examiner.md`](../docs/examiner.md) — filters, N-of-M counts, strata (planned)
- `src/agentic_pokedex/examiner/filters.py`, `generate.py`
- `src/agentic_pokedex/evaluation/musique.py` — Phase 10 adapter
- [`docs/data-sources.md`](../docs/data-sources.md) — MuSiQue license (Phase 0, G1)
- [`notes/ho-2020-2wikimultihopqa.md`](ho-2020-2wikimultihopqa.md)

**Legend.** 🔄 → `notes/phase2-synthesis.md`.

---

## §1–2 — Introduction and Related Work

### 1.1 — The cheating problem
**Prompt.**
- What is "disconnected reasoning", in the authors' words? Give the paper's own
  example (the connected vs disconnected question figure).
- Why do earlier multi-hop datasets (HotpotQA, 2Wiki) allow it? Predict, then
  check: is the fix in MuSiQue about *questions* or about *contexts*?

**My take.**

**Refined write-up.**

---

## §3–4 — Desiderata and Connected Reasoning via Composition

### 3.1 — The formal condition (§3, §4.1–4.2)
**Prompt.**
- Write the connectedness condition formally (the M(q, C) notation). What are
  its two parts?
- The questions are composed as a DAG of single-hop questions. Compare with the
  project's gold chain of facts from Neo4j: is a Cypher template a DAG of
  single-hop questions?
- The project's filter: "if a single unit contains the answer and all of the
  question's anchors, reclassify to S0 or discard". Is that the same condition
  as MuSiQue's, weaker, or stronger? Write a case that passes one and fails the
  other.

**My take.**

**Refined write-up.**

---

## §5 — Dataset Construction Pipeline (S1–S8)

### 5.1 — The eight steps
**Prompt.**
- One line per step S1–S8. Mark which steps have a counterpart in the project's
  generator and which are unnecessary because the graph is the source of truth
  (e.g. S1, filtering annotation errors).
- S3 filters disconnected pairs with *trained models*. The project filters with
  *the fact→units registry*, exactly. What does the project gain, and what does
  it lose (e.g. lexical shortcuts a model finds but the registry does not see)?
- S6: how are distractor paragraphs chosen? Compare with the project's
  near-certain units in S2 (wrong version).

**My take.**

**Refined write-up.**

### 5.2 — Unanswerable contrast questions (S8)
**Prompt.**
- How is the unanswerable version built? Compare with S4: "the learnset
  section for version X is **withheld** from the corpus; other versions remain".
  Same construction, or different?
- The authors argue that paired answerable/unanswerable questions stop models
  from exploiting artifacts. Does the project have pairs? Should it (for the
  Phase 10 comparison)?

**My take.**

**Refined write-up.**

---

## §6–7 — Quality Assessment and Experimental Setup

### 6.1 — Cheatability and DiRe (§7.2.2–7.2.3)
**Prompt.**
- What are the "artifact-based models" and the cheatability score? What exactly
  does the DiRe score measure?
- The project publishes a **shortcut rate** after filtering (Phase 2 DoD). Is
  there a cheap analogue of the cheatability score the project could compute,
  e.g. A1 (single-shot) accuracy on S1?
- Human performance (§7.3): how many annotators, what agreement? Compare with
  the G3 audit (60 questions, ≥ 58 correct).

**My take.**

**Refined write-up.**

---

## §8 — Empirical Findings

### 8.1 — What the ablations prove (§8.2)
**Prompt.**
- Which construction steps do the ablations show are valuable, and by how much?
  Is variance reported?
- 🔄 In the Phase 10 setting (a question's paragraphs become the corpus), what
  would "insufficient" mean for a MuSiQue-Full unanswerable question? Is it
  always the `missing-hop` subtype?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
