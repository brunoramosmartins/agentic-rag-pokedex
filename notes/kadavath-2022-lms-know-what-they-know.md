# Kadavath et al. 2022 — Language Models (Mostly) Know What They Know

**Citation.** Saurav Kadavath, Tom Conerly, Amanda Askell, et al. (Anthropic).
*Language Models (Mostly) Know What They Know.* arXiv:2207.05221 (2022) —
<https://arxiv.org/abs/2207.05221>

**Why this source.** Phase 8. It serves **self-confidence as a feature** of
the trained detector ("confidence declared by the model" in
`classifier/features.py`) and it is the primary source for the P(True) signal
Joren et al. combine with sufficiency in their §5.1. 43 pages: read §1–5, skip
§7 and appendices D.

**Cross-refs used throughout:**
- `src/agentic_pokedex/classifier/features.py`
- [`notes/joren-2025-sufficient-context.md`](joren-2025-sufficient-context.md) — §5.1
- [`notes/jiang-2023-flare.md`](jiang-2023-flare.md) — token confidence

**Legend.** 🔄 → `notes/phase8-synthesis.md`.

---

## §2 — Larger Models are Calibrated on Diverse Multiple Choice Questions

### 2.1 — Calibration depends on format
**Prompt.**
- What formatting conditions make models calibrated, and which break it (e.g.
  "none of the above", RLHF policies)? The project asks for structured JSON
  output from an API model. Predict: is a *verbalized* confidence in that format
  calibrated?

**My take.**

**Refined write-up.**

---

## §3–4 — From Calibration to Knowing What You Know; P(True)

### 3.1 — P(True)
**Prompt.**
- Describe the P(True) procedure: propose answers, then ask "is the proposed
  answer True or False?". Why do multiple samples in context ("brainstorming")
  help?
- P(True) asks "is this answer correct?"; the project's label asks "is this
  evidence enough?". Under the counterfactual twin, when do the two diverge?
- Cost: P(True) needs extra calls. The trained detector must be **free of extra
  LLM calls**. Which cheap proxy of P(True) survives that rule?

**My take.**

**Refined write-up.**

---

## §5 — Training Models to Predict Whether They Can Answer Questions Correctly

### 5.1 — P(IK) and generalization
**Prompt.**
- What is P(IK), and how is it trained? How well does it generalize across
  tasks, and what fails (calibration on new tasks)?
- 🔄 This is the same generalization question as the A × B template gap in
  Phase 8. Write the parallel in two sentences.
- Does P(IK) change when relevant context is given in the prompt? That result
  is the closest one here to sufficiency; note the exact finding.

**My take.**

**Refined write-up.**

---

## §6 — Discussion

### 6.1 — Stated limitations
**Prompt.**
- Which limitations do the authors list? Do they apply to a closed API model
  where you cannot train a P(IK) head?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
