# Ho et al. 2020 — 2WikiMultiHopQA (skim)

**Citation.** Xanh Ho, Anh-Khoa Duong Nguyen, Saku Sugawara, Akiko Aizawa.
*Constructing A Multi-hop QA Dataset for Comprehensive Evaluation of Reasoning
Steps.* COLING 2020. arXiv:2011.01060 — <https://arxiv.org/abs/2011.01060>

**Why this source.** Mode: **skim**. Phase 2. It serves **template-based
generation from a knowledge graph** (`examiner/templates.py`, `generate.py`):
it is the closest precedent for "the graph is the examiner", with evidence
triples as the reasoning path. Read after Trivedi 2022 (MuSiQue), which is the
full read on shortcuts.

**Cross-refs used throughout:**
- [`docs/examiner.md`](../docs/examiner.md), `src/agentic_pokedex/examiner/templates.py`, `surfaces.py`
- [`docs/adr/adr-007-graph-as-examiner-not-tool.md`](../docs/adr/adr-007-graph-as-examiner-not-tool.md) (planned)
- [`notes/trivedi-2022-musique.md`](trivedi-2022-musique.md)

**Legend.** 🔄 → `notes/phase2-synthesis.md`.

---

## §2 — Task Overview (§2.1–2.2)

### 2.1 — Question types and evidence
**Prompt.**
- The four question types (comparison, inference, compositional,
  bridge-comparison): map each onto the project's strata S0–S4. Which type has
  no counterpart, and which stratum has no counterpart in 2Wiki (hint: S3, S4)?
- What is "evidence" here (a set of triples)? Compare with the project's gold
  chain + **all** minimal sufficient sets of units. Why does the project need
  sets of *units*, not just triples?

**My take.**

**Refined write-up.**

---

## §3 + Appendix A — Dataset Generation Process

### 3.1 — Templates and logical rules
**Prompt.**
- How are templates written, and how many? How are Wikidata logical rules
  used for "inference" questions?
- They removed templates that turn into single-hop questions (§1, §3). Is that a
  template-level filter, while the project's shortcut filter is
  question-level? Which is better for the project, and why?
- Surface forms: do they paraphrase with a model or write by hand? The project
  writes 3 surface forms per template by hand; does 2Wiki give a reason to
  change that?

**My take.**

**Refined write-up.**

---

## §5.4 — Mismatches between Wikipedia and Wikidata

### 5.1 — When the text and the graph disagree
**Prompt.**
- What kinds of mismatch did they find, and how often? This is the risk the
  project avoids by *rendering* pages from the graph (ADR-002). Write one
  sentence for ADR-002 citing this section.

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
