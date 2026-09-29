#!/usr/bin/env bash
# .github/setup/issues.sh
# Seed the issues for the phases opened so far. Each later phase adds its
# block here when it is opened, never ahead of time.
#
# Requires: gh CLI, authenticated (uses gh's built-in `-q`, not the jq binary).
# Labels and milestones must already exist (run labels.sh and milestones.sh first).
# Idempotent: an issue with an identical title is skipped rather than duplicated.
#
# Usage:
#   bash .github/setup/issues.sh

set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI not installed." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh not authenticated." >&2
  exit 1
fi

# Snapshot titles that already exist so we can skip duplicates.
existing_titles="$(gh issue list --state all --limit 500 --json title -q '.[].title')"

# mk_issue TITLE MILESTONE LABELS_CSV  <<'BODY' body BODY
mk_issue() {
  local title="$1" milestone="$2" labels="$3"
  local body
  body="$(cat)"

  if grep -Fxq "$title" <<<"$existing_titles"; then
    printf "  skip  %s\n" "$title"
    return
  fi

  gh issue create \
    --title "$title" \
    --milestone "$milestone" \
    --label "$labels" \
    --body "$body" >/dev/null
  printf "  ok    %s\n" "$title"
}

M0="Phase 0 — Foundation"
M1="Phase 1 — World"
M2="Phase 2 — Examiner"

echo "Creating issues..."

# ============================================================================
# Phase 0 — opened 2026-09-24
# ============================================================================

mk_issue "[Phase 0] Hypothesis, measurability gate and contingency docs" \
  "$M0" "phase:0,type:docs" <<'BODY'
## Context
Publish the measurability gate before any pipeline code, so every threshold is fixed before any number exists.

## Tasks
- [ ] `docs/hypothesis.md` (v0.1, central axis, per-stratum predictions)
- [ ] `docs/measurability-gate.md` (gates 1-8 and the outcome space)
- [ ] `docs/contingency.md` (G1-G5 with exit plans)

## Definition of Done
- [ ] All three docs committed; predictions match what E-001 registers.

## References
- Milestone: Phase 0
BODY

mk_issue "[Phase 0] Data sources and licensing — G1 verdict" \
  "$M0" "phase:0,type:docs,gate:g1" <<'BODY'
## Context
Gate G1: PokéAPI CSV available, BSD-3, learnset coverage for the chosen versions.

## Tasks
- [ ] `docs/data-sources.md`: PokéAPI license confirmed, MuSiQue license, decision on Pokédex text in the published benchmark, trademark notice
- [ ] Dated model price table
- [ ] PokéAPI CSV and MuSiQue samples downloaded with SHA-256 (not committed)

## Definition of Done
- [ ] Every source has a verdict (ok / ok-with-restriction / blocked); hashes recorded.

## References
- Milestone: Phase 0 · Gate: G1
BODY

mk_issue "[Phase 0] ADRs 001-010" \
  "$M0" "phase:0,type:docs" <<'BODY'
## Context
Record the decisions that shape the project before any code.

## Tasks
- [ ] ADR-001 theme and thesis ... ADR-010 depth placebo and release slicing (titles in `docs/adr/`)

## Definition of Done
- [ ] Ten ADRs in `docs/adr/` with status Accepted.

## References
- Milestone: Phase 0
BODY

mk_issue "[Phase 0] Experiment registry: E-001 full draft, E-002 registered" \
  "$M0" "phase:0,type:experiment,hypothesis:h1,hypothesis:h2" <<'BODY'
## Context
Pre-register Layer 1 while no number exists to contaminate it.

## Tasks
- [ ] `experiments/registry.md` created
- [ ] E-001: hypotheses, per-stratum predictions, threshold, falsifier, outcome space with precedence, error taxonomy, lambda* cases
- [ ] E-002 (typed expansion) with its decision rule

## Definition of Done
- [ ] E-001 complete as a draft; E-002 has a written decision rule.

## References
- Milestone: Phase 0 · Hypothesis: `docs/hypothesis.md`
BODY

mk_issue "[Phase 0] Outcome-space test" \
  "$M0" "phase:0,type:test" <<'BODY'
## Context
Lesson from P2 Phase 11: a registered rule only protects if every outcome maps to exactly one row.

## Tasks
- [ ] `tests/test_outcome_space.py` enumerates all (H1, placebo, mediation, falsifier, O2 ceiling) combinations and the four lambda* cases

## Definition of Done
- [ ] Every combination falls into exactly one row of the outcome space.

## References
- Milestone: Phase 0 · `docs/measurability-gate.md`, outcome space
BODY

mk_issue "[Phase 0] power.py reproduces P2 E-026 + token meter" \
  "$M0" "phase:0,type:statistics" <<'BODY'
## Context
Gate 7: no instrument produces a number before running against a known answer.

## Tasks
- [ ] `evaluation/power.py` reproduces P2's E-026 detectability table
- [ ] Token meter that prints an estimated cost before any LLM loop (`--limit N` support)

## Definition of Done
- [ ] power.py output matches E-026; cost estimate printed before any loop.

## References
- Milestone: Phase 0 · Measurability gate 7
BODY

mk_issue "[Phase 0] Scaffold, docker-compose, CI and initial README" \
  "$M0" "phase:0,type:chore" <<'BODY'
## Context
Scaffold with a 5-day timebox against over-engineering.

## Tasks
- [ ] `pyproject.toml`, `.gitignore`
- [ ] Issue/PR templates, `.github/setup/{labels,milestones,issues}.sh`
- [ ] `docker-compose.yml` (Neo4j + Phoenix)
- [ ] CI: lint + unit + integration (Neo4j service)
- [ ] README with problem statement, trademark notice and PokéAPI attribution

## Definition of Done
- [ ] `docker compose up` healthy; `pip install -e .` works; CI green.

## References
- Milestone: Phase 0
BODY

# ============================================================================
# Phase 1 — opened 2026-09-29
# ============================================================================

mk_issue "[Phase 1] Download PokéAPI with hash checks and load the graph" \
  "$M1" "phase:1,type:feat" <<'BODY'
## Context
The world starts from the pinned PokéAPI commit recorded in `docs/data-sources.md`. Raw CSVs are never committed.

## Tasks
- [ ] `world/download.py`: fetch the CSVs at the pinned commit into `data/raw/`, verify SHA-256 against `docs/data-sources.md`
- [ ] `world/load_graph.py`: CSV → Neo4j (species, forms, types and efficacy, evolution chains, moves, abilities with the hidden flag, learnsets per version group, flavor text)
- [ ] Load statistics: counts per node label and relationship type
- [ ] `graph` extra in `pyproject.toml`; integration tests marked `@pytest.mark.integration`

## Definition of Done
- [ ] A hash mismatch aborts the download; load statistics printed and recorded in `docs/world.md`.

## References
- Milestone: Phase 1 · `docs/data-sources.md`
BODY

mk_issue "[Phase 1] Learnset coverage report and choice of base version groups" \
  "$M1" "phase:1,type:research,gate:g1" <<'BODY'
## Context
Adjacent generations differ in only ~3% of move levels (G1), which would leave S2 without pairs. The version scope is frozen from measured coverage (PI-002).

## Tasks
- [ ] Coverage report per version group (DLC groups excluded: they are empty)
- [ ] Choose 3-4 base groups **spanning different generations**
- [ ] Report the rate of (species, move) pairs whose level differs between the chosen groups

## Definition of Done
- [ ] Choice and its numbers in `docs/world.md`; the frozen scope recorded in the decision journal.

## References
- Milestone: Phase 1 · `docs/data-sources.md` (learnset coverage) · PI-002
BODY

mk_issue "[Phase 1] Counterfactual twin with seeded renaming and round-trip test" \
  "$M1" "phase:1,type:feat,gate:g2" <<'BODY'
## Context
The twin renames and never changes facts, so parametric memory cannot substitute for evidence (ADR-003).

## Tasks
- [ ] `world/twin.py`: seeded pronounceable pseudo-words for species, forms, moves, abilities, types and version names; numbers untouched
- [ ] Filter against real names and a dictionary; uniqueness across all twin names
- [ ] Renaming carried through free text (flavor text rewritten with the same map)
- [ ] Round-trip test

## Definition of Done
- [ ] Round trip = identity on 100% of entities; no collision with a real name or between twin names.

## References
- Milestone: Phase 1 · ADR-003 · Gate: G2
BODY

mk_issue "[Phase 1] Renderer and fact-to-units registry" \
  "$M1" "phase:1,type:feat" <<'BODY'
## Context
Sections are the evidence units; the registry knows every copy of every fact, so the sufficiency label stays exact under redundancy (ADR-002, ADR-009).

## Tasks
- [ ] `world/render.py`: one page per entity, sections of ~100-400 tokens with a metadata header, typed links
- [ ] Controlled redundancy (e.g. learnset on the species page and "Learned by" on the move page)
- [ ] Hubs split into several units with the **same header** and no pagination marker; cue variant (`(k/N)`) only behind the ablation option
- [ ] Withheld units (for S4) left out of the index and recorded
- [ ] `world/registry.py`: fact → units, all copies; **free-text (flavor) units marked** for the Phase 2 shortcut scan (PI-001)

## Definition of Done
- [ ] 100% of graph facts in ≥ 1 unit; registry complete; no cue in the main condition (tested).

## References
- Milestone: Phase 1 · ADR-002 · ADR-009 · PI-001
BODY

mk_issue "[Phase 1] Index and the two tools" \
  "$M1" "phase:1,type:feat" <<'BODY'
## Context
Every arm gets the same tool contract. The main condition shows no total-hit count.

## Tasks
- [ ] `world/index.py`: BM25 + local dense index (`retrieval` extra)
- [ ] `tools/search.py` (`k ≤ 5`, units with headers, no total count; count only as the ablation option)
- [ ] `tools/open_page.py` (exact title, optional section)
- [ ] Each call returns at most ~700 tokens

## Definition of Done
- [ ] Unit tests for the contract, including the absence of the count in the main condition.

## References
- Milestone: Phase 1 · ADR-009
BODY

mk_issue "[Phase 1] Identity probe — preliminary G2" \
  "$M1" "phase:1,type:experiment,gate:g2" <<'BODY'
## Context
Can the model name the real entity behind a twin page? The positive control keeps a broken probe from reading as a safe twin.

## Tasks
- [ ] Probe protocol registered as E-003 in `experiments/registry.md` **before the run** (model, prompt, match rule, page sample, seed)
- [ ] 50 twin pages + 50 real pages with the entity's own name masked (positive control)
- [ ] Script supports `--limit N` and prints the estimated cost first

## Definition of Done
- [ ] Positive control identified in ≥ 50% (else the probe is broken); twin identified in ≤ 10% → preliminary G2, published N-of-M.

## References
- Milestone: Phase 1 · `docs/contingency.md` (G2) · `docs/measurability-gate.md` (gate 7)
BODY

mk_issue "[Phase 1] Admissible answers per answer slot" \
  "$M1" "phase:1,type:statistics,gate:g2" <<'BODY'
## Context
The closed-book check of G2 is chance-adjusted on small answer spaces (PI-009).

## Tasks
- [ ] Count admissible answers per answer slot in the corpus (type: 18; level: observed range; species/move: open)

## Definition of Done
- [ ] Counts in `docs/world.md`, ready for the Phase 3 closed-book check.

## References
- Milestone: Phase 1 · `docs/contingency.md` (G2) · PI-009
BODY

mk_issue "[Phase 1] Idempotent rebuild and docs/world.md" \
  "$M1" "phase:1,type:docs" <<'BODY'
## Context
Idempotence is proven, not presumed. The world doc is the reference for Phase 2.

## Tasks
- [ ] Forced rebuild changes zero units (test)
- [ ] `docs/world.md`: scope, twin, renderer, registry, load statistics, coverage choice, answer-space counts
- [ ] One rendered twin-side page of each type (species, move, ability, type), every flavor-text unit elided (`docs/data-sources.md`)

## Definition of Done
- [ ] Rebuild diff is empty; `docs/world.md` published.

## References
- Milestone: Phase 1
BODY

# ============================================================================
# Phase 2 — opened 2026-09-29
# ============================================================================

mk_issue "[Phase 2] Templates per stratum and surface forms" \
  "$M2" "phase:2,type:feat" <<'BODY'
## Context
The golden set is software: 3-5 Cypher templates per stratum (S0-S4), three hand-written surface forms each. No LLM paraphrase in v1 (it can change the question's meaning).

## Tasks
- [ ] `examiner/templates.py`: named Cypher constants, 3-5 per stratum; every template filters `LEARNS.version_group` to the version scope
- [ ] `examiner/surfaces.py`: 3 surface forms per template, twin and real text
- [ ] Template partition A / B, at least one B template per stratum
- [ ] Spec in `docs/examiner.md` before the generator runs

## Definition of Done
- [ ] Every stratum has 3-5 templates; partition recorded; surfaces reviewed.

## References
- Milestone: Phase 2 · `docs/hypothesis.md` (strata) · ADR-007
BODY

mk_issue "[Phase 2] S1 material and benign; templates beyond hidden ability" \
  "$M2" "phase:2,type:feat,hypothesis:h1" <<'BODY'
## Context
In 246 of 299 single-final evolution lines the base and final forms share their hidden ability: an agent that skips the missing hop is right by coincidence 82% of the time (PI-015).

## Tasks
- [ ] Material S1 (the anchor's own answer differs from the gold answer) forms S1 in the H1 pool
- [ ] Benign S1 (they coincide): a descriptive slice, 40 questions in eval-L1 for A3, A4, A4p, outside H1
- [ ] S1 templates beyond hidden ability (the hidden-ability template leaves 53 material lines)
- [ ] Material pool size per template published N-of-M

## Definition of Done
- [ ] S1 material pool reported against the n of measurability gate 3; benign slice generated and tagged.

## References
- Milestone: Phase 2 · PI-015 · E-001
BODY

mk_issue "[Phase 2] Generator and filters, with N-of-M counts" \
  "$M2" "phase:2,type:feat" <<'BODY'
## Context
Each question carries its gold answer with aliases, gold chain as fact ids, every minimal sufficient set of units, near-certain units (S2), withheld units (S4) and set size (S3). Filters publish N-of-M.

## Tasks
- [ ] `examiner/generate.py` from the graph and the fact -> units registry
- [ ] Filters: ambiguity; single-unit shortcut; S2 (level differs from every other scope group); S3 set size 3-25; S4 (no indexed unit implies the answer)
- [ ] World constraints (PI-016): S3 avoids hubs whose gold set includes a withheld species; hidden-ability templates sample only species that have one; level-0 and multi-level pairs are ambiguous; branching lines make "final form" ambiguous; forms have no learnsets
- [ ] **Negative test**: removing a template's version-group filter makes a test fail

## Definition of Done
- [ ] Every filter's N-of-M per stratum in `docs/examiner.md`; the negative test exists and fails without the filter.

## References
- Milestone: Phase 2 · PI-002 · PI-016 · `docs/world.md`
BODY

mk_issue "[Phase 2] Answer-concentration cap, before and after" \
  "$M2" "phase:2,type:statistics,gate:g2" <<'BODY'
## Context
A constant guess of the modal answer scores 22.6% on a move's type and 21.3% on a learn level with no leak. The cap is an experimental intervention, not a property of the world (PI-012).

## Tasks
- [ ] Each template's majority-answer rate <= max(10%, 1.5 x uniform chance)
- [ ] Publish every template's answer distribution before (all candidates) and after (the generated set)
- [ ] Report each template's majority-answer rate: it is G2's chance rate in Phase 3

## Definition of Done
- [ ] Cap enforced and tested; before/after tables in `docs/examiner.md`.

## References
- Milestone: Phase 2 · `docs/contingency.md` (G2) · PI-012
BODY

mk_issue "[Phase 2] Sufficiency labeler with golden trajectories" \
  "$M2" "phase:2,type:feat,type:test" <<'BODY'
## Context
The label is a pure function over the registry: a state is sufficient when the units seen cover at least one gold minimal sufficient set (fixed 2026-09-26). Subtypes: missing-hop, wrong-version, truncated, nonexistent.

## Tasks
- [ ] `labeling/sufficiency.py`
- [ ] Golden trajectories built by hand in `tests/fixtures/` (every subtype, redundant copies, withheld units)
- [ ] Specified in `docs/examiner.md`

## Definition of Done
- [ ] 100% correct on the golden trajectories (measurability gate 7).

## References
- Milestone: Phase 2 · ADR-001 (Updates) · ADR-002
BODY

mk_issue "[Phase 2] Shortcut scan validated on planted leaks" \
  "$M2" "phase:2,type:test" <<'BODY'
## Context
A unit that names a question's anchor together with its answer, outside the registered gold units, flags the question (PI-001). World v1 has no free text, so the flavor-text planted case is dropped (PI-013).

## Tasks
- [ ] Scan implemented in `examiner/`
- [ ] Planted leaks built by hand; the scan must flag all of them
- [ ] Run on every generated question; flags inspected and resolved

## Definition of Done
- [ ] 100% of planted leaks flagged; flags on generated questions published N-of-M.

## References
- Milestone: Phase 2 · `docs/measurability-gate.md` (gate 7)
BODY

mk_issue "[Phase 2] Splits and the template partition" \
  "$M2" "phase:2,type:feat" <<'BODY'
## Context
Only ids and seeds are versioned. dev and train are group A only; eval-L1 mixes groups A and B and carries the benign S1 slice.

## Tasks
- [ ] `examiner/splits.py` with registered seeds
- [ ] dev (150, group A), train, eval-L1 (400 + 40 benign S1), val-B, eval-L2, eval-L3 ids
- [ ] Opening counts initialised at 0 per evaluation split

## Definition of Done
- [ ] dev and train ids frozen; eval ids drawn by seed; eval-L1 size still adjustable until Phase 6.

## References
- Milestone: Phase 2 · `data/splits/`
BODY

mk_issue "[Phase 2] G3 audit — 60 stratified questions" \
  "$M2" "phase:2,type:research,gate:g3" <<'BODY'
## Context
Gate G3: a human audit of 60 stratified questions, with real names recovered through the twin map's inverse, must find >= 58 correct gold answers.

## Tasks
- [ ] Audit sheet (local only: real names are never committed)
- [ ] Audit; on failure, fix and re-audit a fresh sample (at most 3 iterations, then remove failing templates and record it)

## Definition of Done
- [ ] >= 58 of 60 correct; the result and any iteration recorded in the decision journal.

## References
- Milestone: Phase 2 · `docs/contingency.md` (G3)
BODY

mk_issue "[Phase 2] docs/examiner.md and the benchmark v0 pre-release" \
  "$M2" "phase:2,type:docs" <<'BODY'
## Context
The benchmark is published twin-side and fact-level only (`docs/data-sources.md`): ids, twin question text, answers with aliases, gold chains as fact ids, sufficient sets as unit ids, seeds.

## Tasks
- [ ] `docs/examiner.md`: templates, strata, filters with N-of-M, labeler, splits, shortcut rate, S3 set-size distribution
- [ ] Reachability: every insufficiency subtype and error code producible by at least one dev question
- [ ] Benchmark card written before the pre-release is uploaded

## Definition of Done
- [ ] `v0.3-examiner` pre-release with the benchmark files and card.

## References
- Milestone: Phase 2 · `docs/data-sources.md` (published benchmark)
BODY

echo "Done."
