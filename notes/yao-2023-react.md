# Yao et al. 2023 — ReAct: Synergizing Reasoning and Acting in Language Models

**Citation.** Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran,
Karthik Narasimhan, Yuan Cao. *ReAct: Synergizing Reasoning and Acting in
Language Models.* ICLR 2023. arXiv:2210.03629 — <https://arxiv.org/abs/2210.03629>

**Why this source.** Phase 5. It serves **the A3 loop** (`arms/agent.py`,
`detectors/implicit.py`): A3 is "the model itself decides to stop / continue /
abstain (ReAct)". It also backs ADR-004 (hand-rolled loop). Read first in
Phase 5; CRAG and Self-RAG are read against it.

**Cross-refs used throughout:**
- [`docs/adr/adr-004-hand-rolled-agent-loop.md`](../docs/adr/adr-004-hand-rolled-agent-loop.md) (planned)
- `src/agentic_pokedex/arms/agent.py`, `detectors/implicit.py`, `tools/contract.py`
- [`docs/evaluation.md`](../docs/evaluation.md) — error taxonomy, per-step log (planned)

**Legend.** 🔄 → `notes/phase5-synthesis.md`.

---

## §2 — ReAct: Synergizing Reasoning + Acting

### 2.1 — Formal setup
**Prompt.**
- Write the setup in the paper's notation: the action space augmented with the
  language space (thoughts), the context c_t, the policy π(a_t | c_t).
- In ReAct, where is the **stopping decision**? Which action ends the
  episode, and what information does the model have when it takes it?
- Is abstention an action in ReAct? If not, how must the project's A3 extend
  the action space (structured `{answer, abstain}` output)?

**My take.**

**Refined write-up.**

---

## §3 — Knowledge-Intensive Reasoning Tasks

### 3.1 — The Wikipedia tool API (§3.1)
**Prompt.**
- Describe `search[entity]`, `lookup[string]`, `finish[answer]`. What does
  `search` return when the entity is not found? Compare with the project's
  `search(query, k ≤ 5)` and `open_page(title, section)`.
- Does ReAct's search reveal how many results exist? Relate this to ADR-009 (no
  truncation cues in the main condition).

**My take.**

**Refined write-up.**

### 3.2 — Methods and results (§3.2–3.3)
**Prompt.**
- What are the baselines (Standard, CoT, CoT-SC, Act) and the switching
  heuristics ReAct → CoT-SC and back? Which heuristic uses a *step budget*?
  Compare with T_max = 6.
- Results on HotpotQA: is ReAct better than CoT alone? What does that say about
  the claim "agents win at multi-hop", which ADR-001 discarded as a thesis?

**My take.**

**Refined write-up.**

### 3.3 — The failure-mode table (§3.3, Appendix E.1)
**Prompt.**
- Copy the categories and ReAct/CoT percentages (reasoning error, search result
  error, hallucination, label ambiguity). How many trajectories were
  hand-labeled?
- "Repetitively generates the previous thoughts and actions" is filed under
  reasoning error. In the project's taxonomy, is it a search failure or a
  decision failure? 🔄 Compare with Ferrazzi's 53% identical documents.
- Which of their categories could be labeled **mechanically** with the
  project's exact per-step labels, and which need human judgment?

**My take.**

**Refined write-up.**

---

## §6 + Appendix C — Conclusion and Prompts

### 6.1 — Limitations and prompt design
**Prompt.**
- What limitations do the authors state (prompting with few-shot examples,
  context length)?
- Read the HotpotQA prompt (C.1). What in its few-shot trajectories implicitly
  teaches *when to stop*? The A3 prompt must not teach stopping by example
  more than A4's; note what to hold constant across arms.

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
