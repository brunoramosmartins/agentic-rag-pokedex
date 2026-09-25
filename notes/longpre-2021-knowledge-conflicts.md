# Longpre et al. 2021 — Entity-Based Knowledge Conflicts in Question Answering

**Citation.** Shayne Longpre, Kartik Perisetla, Anthony Chen, Nikhil Ramesh,
Chris DuBois, Sameer Singh. *Entity-Based Knowledge Conflicts in Question
Answering.* EMNLP 2021. arXiv:2109.05052 — <https://arxiv.org/abs/2109.05052>

**Why this source.** Listed under Phase 10 (memory × evidence), but it also
serves the **counterfactual twin** built in Phase 1 (ADR-003): Longpre's
substitution framework is the published precedent for replacing entities in
the context to separate parametric memory from contextual evidence. Consider
reading §2 before Phase 1, when the renaming scheme is fixed, and the rest in
Phase 10.

**Cross-refs used throughout:**
- [`docs/adr/adr-003-counterfactual-twin-as-primary.md`](../docs/adr/adr-003-counterfactual-twin-as-primary.md) (planned)
- [`docs/world.md`](../docs/world.md), `src/agentic_pokedex/world/twin.py` (Phase 1)
- [`docs/contingency.md`](../docs/contingency.md) — G2: the twin does not leak (planned)
- [`docs/evaluation.md`](../docs/evaluation.md) — "Memory × evidence" section (Phase 10)

---

## §2 — Substitution Framework

### 2.1 — Types of substitution (§2.2)
**Prompt.**
- List the substitution types (corpus, type swap, popularity, alias, …). Which
  one is closest to the twin? Note the difference: Longpre replaces the
  *answer* in a real context; the twin renames *every* entity and keeps the
  facts.
- Why does the twin also rename types and version names (ADR-003: "Fire beats
  Grass" is a parametric shortcut in the middle of a chain)? Is there a
  Longpre finding that supports this choice?
- §2.3 substitution quality: how did they check that substituted passages stay
  coherent? Compare with the twin's round-trip identity test.

**My take.**

**Refined write-up.**

---

## §3 — Experimental Setup

### 3.1 — The memorization ratio (§3.3)
**Prompt.**
- Define the memorization ratio M_R. Could the project compute an analogue in
  Phase 10 (real vs twin: answer matches the *real* fact while the context says
  otherwise)? Note: the twin never contradicts facts, so what exactly is
  measured instead?

**My take.**

**Refined write-up.**

---

## §4 — Experiments

### 4.1 — What drives over-reliance on memory (§4.1–4.2)
**Prompt.**
- Which factors increase memorization (model size, entity popularity,
  retriever quality during training)? Popular Pokémon are extremely popular
  entities: what does that predict for the real-world arm in Phase 10?
- Relate to G2's thresholds (identity probe > 10% of 50 pages; closed-book on
  the twin > 5%). Does Longpre give any reason to expect the Pokédex text to be
  the main leak?

**My take.**

**Refined write-up.**

### 4.2 — Mitigation (§4.4)
**Prompt.**
- What mitigation do they propose (training with substituted examples)? The
  project does not train the generator: is there a prompting-level analogue, or
  is the twin itself the mitigation?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
