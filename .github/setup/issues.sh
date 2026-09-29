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

echo "Done."
