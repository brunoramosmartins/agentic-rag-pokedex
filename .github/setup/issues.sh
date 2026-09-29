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
- [ ] Probe protocol registered in `experiments/registry.md` **before the run** (model, prompt, match rule, page sample, seed)
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
- [ ] One rendered page of each type (species, move, ability, type)

## Definition of Done
- [ ] Rebuild diff is empty; `docs/world.md` published.

## References
- Milestone: Phase 1
BODY

echo "Done."
