# Decision Journal

Every non-trivial decision logged the day it is made. Never reconstructed later;
backfilled entries are marked retrospective.

---

## 2026-09-24 — Phase 0 opened

**Scope.** Phase 0 — Foundation, Licensing & Measurability Gate. Timebox: 5
partial working days. Ends with tag `v0.1-foundation` (no release).

**Gate check.** Phase 0 has no predecessor phase inside this repo. Several
Phase 0 deliverables reuse the previous project, P2 (`graphrag-mtg-rules`):
`power.py` must reproduce P2's E-026 detectability table (measurability gate
7), and the Neo4j loader and `bm25.py` are adapted from it. The P2 repo is not
present on this machine as of today; its location is an open item for this
phase.

**Carry-overs.** None.

**Scope decisions.** None taken at kickoff.

**Housekeeping.** A WSL download artifact (`*:Zone.Identifier`) and `.venv/`
are untracked; both go to `.gitignore` as part of the scaffold task.

## 2026-09-24 — All repo artifacts in English, including `notes/`

Every file in the repo is written in English, notes included, to follow common
development and documentation practice. `notes/phase0-foundation.md` was
rewritten in English the same day.

## 2026-09-24 — Reading companions for the full reading plan; AURC source corrected

Reading companions were written up front for all 15 sources of the reading
plan, plus one synthesis file per phase with more than one source
(`notes/phase{0,2,5,8}-synthesis.md`). Skim-mode sources get short notes that
cover only the sections serving a decision.

Two corrections found while checking the sources:
- **AURC is not in Geifman & El-Yaniv 2017.** Its primary source is Geifman,
  Uziel & El-Yaniv, *Bias-Reduced Uncertainty Estimation for Deep Neural
  Classifiers* (ICLR 2019, arXiv:1805.08206), added as a skim companion inside
  `notes/geifman-2017-selective-classification.md`.
- **Longpre et al. 2021 also serves Phase 1** (the twin's renaming scheme,
  ADR-003), not only Phase 10. Its §2 is flagged for reading before Phase 1.

## 2026-09-24 — Scaffold choices

Built from scratch rather than copied from P2: the P2 repo is not available
locally (open item above).

- **src layout, package `agentic_pokedex`**, only the package root for now.
  Subpackages (`world/`, `examiner/`, `arms/`, …) are created by the phase that
  first needs them, so the tree never shows modules that do not exist yet.
- **Optional extras per concern** (`graph`, `retrieval`, `llm`,
  `observability`, `classifier`, `demo`, `dev`) instead of one flat dependency
  list: torch/sentence-transformers are not installed until Phase 1 needs the
  dense index. Core stays numpy/scipy/pandas.
- **CI integration job tolerates "no tests collected"** (pytest exit code 5)
  until Phase 1 adds the first `@pytest.mark.integration` test. Remove the
  tolerance then.
- **Milestone due dates are soft targets** from the effort estimate (week 1
  starts 2026-09-24); the project has no hard deadline.
- **Phoenix image is `latest`, Neo4j is `5-community`.** Pin exact versions
  before the first registered run (Phase 3), and record them in E-001.

## 2026-09-24 — ADRs 001–010 drafted as Proposed

The ten ADRs record decisions already taken during planning, with links to the
reading companions that motivate them. Status is **Proposed**, not Accepted:
each one is reviewed and flipped by hand, which is the Phase 0 DoD. ADR-001
carries one open item — the exact definition of the sufficiency label —
resolved after `notes/phase0-synthesis.md` S.3.

`papers/` added to `.gitignore` for local PDF copies of the reading plan.

## 2026-09-24 — The repo is self-contained; planning files stay local

The planning document used to steer the project is personal and is not
versioned; neither is local tool configuration. Both are gitignored. Every
repo file must stand on its own: the hypothesis, the measurability gate, the
contingency gates and the ADRs restate their content instead of pointing to an
external plan. `docs/hypothesis.md`, `docs/measurability-gate.md` and
`docs/contingency.md` were written the same day under this rule, and earlier
files were edited to remove references to the planning document.

The power table in `docs/measurability-gate.md` was recomputed before
publishing (MDE = 3.08 · SD / √n; n for 0.25 = 152 / 342 / 608; H3 n = 99 / 223 /
396; per-stratum MDE at n = 80 = 0.31 / 0.47 / 0.63): all values match.
