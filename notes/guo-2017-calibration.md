# Guo et al. 2017 — On Calibration of Modern Neural Networks

**Citation.** Chuan Guo, Geoff Pleiss, Yu Sun, Kilian Q. Weinberger. *On
Calibration of Modern Neural Networks.* ICML 2017. arXiv:1706.04599 —
<https://arxiv.org/abs/1706.04599>

**Why this source.** Phase 8. It serves **calibration of the trained
detector** (`classifier/calibrate.py`): ECE, reliability diagrams, and the
choice "isotonic vs sigmoid calibration on real dev states". The theoretical
threshold treats P(sufficient) as a real probability, so it only works if the
classifier is calibrated. Read after Geifman 2017.

**Cross-refs used throughout:**
- `src/agentic_pokedex/classifier/calibrate.py`, `train.py`
- [`docs/evaluation.md`](../docs/evaluation.md) — v1.1: AUROC, ECE, reliability diagram (planned)
- Model card (Phase 8 deliverable)

**Legend.** 🔄 → `notes/phase8-synthesis.md`.

---

## §2 — Definitions

### 2.1 — Perfect calibration, reliability diagrams, ECE
**Prompt.**
- Write perfect calibration formally, then ECE and MCE with M bins. Why is ECE
  sensitive to the number of bins, and what does that mean with a small
  real-state dev set?
- NLL as a calibration-aware metric: why do the authors report it too?

**My take.**

**Refined write-up.**

---

## §3 — Observing Miscalibration

### 3.1 — What makes models miscalibrated
**Prompt.**
- Which factors do they link to miscalibration (depth, width, batch norm,
  weight decay)? The project uses logistic regression and
  `HistGradientBoostingClassifier`, not deep nets: which findings still apply,
  and which do not?
- "NLL overfitting without accuracy overfitting": is there an analogue for a
  gradient-boosted classifier trained on simulated states?

**My take.**

**Refined write-up.**

---

## §4 — Calibration Methods

### 4.1 — Binary methods (§4.1)
**Prompt.**
- List the binary methods: histogram binning, isotonic regression, BBQ, Platt
  scaling. Write Platt scaling as a formula.
- Phase 8 compares **isotonic vs sigmoid** (sigmoid = Platt). What does each
  assume, and which needs more calibration data? Given the real-state dev set
  size, which do you predict wins?

**My take.**

**Refined write-up.**

### 4.2 — Temperature scaling (§4.2)
**Prompt.**
- Write temperature scaling. Why does it not change the ranking (and so not the
  AUROC or the risk-coverage curve)? 🔄 Link to Geifman: ranking vs calibration.
- Is temperature scaling relevant to a binary classifier at all, or only to
  the multiclass case?

**My take.**

**Refined write-up.**

---

## §5 — Results

### 5.1 — Dataset shift
**Prompt.**
- Do the results cover calibration **under distribution shift**? The project's
  key risk is shift: simulated → real states, and group A → group B templates.
  What does the paper say (or not say) about calibration that holds out of
  distribution?

**My take.**

**Refined write-up.**

---

## Lessons Learned

## Failed Attempts
