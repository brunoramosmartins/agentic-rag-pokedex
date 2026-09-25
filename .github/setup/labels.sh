#!/usr/bin/env bash
# .github/setup/labels.sh
# Create the project's GitHub labels.
#
# Requires: gh CLI, authenticated against the target repo (gh auth status).
# Idempotent: --force overwrites color/description if a label already exists.
#
# Usage:
#   bash .github/setup/labels.sh

set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI not installed. See https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh not authenticated. Run 'gh auth login' first." >&2
  exit 1
fi

label() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --color "$color" --description "$desc" --force >/dev/null
  printf "  ok    %s\n" "$name"
}

echo "Creating labels..."

# type: kind of work
label "type:feat"        "a2eeef" "New pipeline, arm or evaluation code"
label "type:docs"        "0075ca" "Documentation, ADRs, decision journal"
label "type:test"        "cfd3d7" "Tests"
label "type:chore"       "7057ff" "Setup, config, infra, CI"
label "type:research"    "d876e3" "Reading notes, synthesis, TIL drafts"
label "type:experiment"  "fbca04" "Registered experiment (experiments/registry.md)"
label "type:statistics"  "006b75" "Power, bootstrap, Holm, selective metrics"
label "type:bug"         "d73a4a" "Something behaves differently from what was promised"

# phase: project phase (v1.0 = 0..7, v1.1 = 8..9, v1.2 = 10)
for i in 0 1 2 3 4 5 6 7 8 9 10; do
  label "phase:$i" "ededed" "Phase $i work"
done

# hypothesis: pre-registered H1..H3
label "hypothesis:h1" "f9d0c4" "H1 — A4 (explicit) reduces C vs A3 (implicit)"
label "hypothesis:h2" "f9d0c4" "H2 — A4 reduces C vs A2 (fixed pipeline)"
label "hypothesis:h3" "f9d0c4" "H3 — A5 (trained) non-inferior to A4 with fewer tokens"

# gate: contingency gates G1..G5
label "gate:g1" "c5def5" "G1 — data and licenses"
label "gate:g2" "c5def5" "G2 — the twin does not leak"
label "gate:g3" "c5def5" "G3 — generator correctness audit"
label "gate:g4" "c5def5" "G4 — power"
label "gate:g5" "c5def5" "G5 — last exit"

# status
label "status:blocked" "b60205" "Blocked on external dependency"

echo "Done."
