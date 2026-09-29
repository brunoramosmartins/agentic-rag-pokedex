#!/usr/bin/env bash
# .github/setup/milestones.sh
# Create one GitHub milestone per project phase (0..10).
#
# Milestones carry no due date: this is a personal project worked on
# sporadically, with no hard deadline. Descriptions give the effort size
# (S / M / L, in partial working days) as a relative estimate only.
#
# Requires: gh CLI (uses gh's built-in `-q` jq expression, not the jq binary).
# Idempotent: skips titles that already exist on the repo.
#
# Usage:
#   bash .github/setup/milestones.sh

set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI not installed. See https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh not authenticated. Run 'gh auth login' first." >&2
  exit 1
fi

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
echo "Target repo: $REPO"

existing="$(gh api "repos/$REPO/milestones?state=all&per_page=100" -q '.[].title')"

create_milestone() {
  local title="$1" description="$2"

  if grep -Fxq "$title" <<<"$existing"; then
    printf "  skip  %s (already exists)\n" "$title"
    return
  fi

  gh api "repos/$REPO/milestones" -X POST \
    -f title="$title" \
    -f description="$description" >/dev/null
  printf "  ok    %s\n" "$title"
}

echo "Creating milestones..."

create_milestone "Phase 0 — Foundation" \
  "Size S (3-5 partial days). ADRs 001-010, G1, measurability gate, E-001 draft, scaffold. Tag: v0.1-foundation"
create_milestone "Phase 1 — World" \
  "Size L (8-11). PokéAPI -> graph -> twin -> pages -> index; E-003 identity probe. Tag: v0.2-world"
create_milestone "Phase 2 — Examiner" \
  "Size L (9-12). Generator, gold chains, step labels, G3 audit. Tag: v0.3-examiner (pre-release)"
create_milestone "Phase 3 — Pilot Gate" \
  "Size S (3-5). E-002, pilot, measured reasoning, preliminary G2 and G4, n_max. Tag: v0.4-pilot-gate"
create_milestone "Phase 4 — Baselines" \
  "Size M (5-7). A0, A1, A2, A6, O1 tuned in good faith on group A. Tag: v0.5-baselines"
create_milestone "Phase 5 — Agent" \
  "Size L (8-11). A3, A4, A4p, O2 with per-step logs. Tag: v0.6-agent-detectors"
create_milestone "Phase 6 — Layer 1 Verdict" \
  "Size M (5-7). Single opening of eval-L1. Tag: v0.7-layer1-verdict (pre-release)"
create_milestone "Phase 7 — Release" \
  "Size M (<= 5, timebox). Demo + README. Tag: v1.0.0 (stable)"
create_milestone "Phase 8 — Trained Detector" \
  "Timebox: 15 partial days of effort. Calibrated sufficiency classifier and its registry entry."
create_milestone "Phase 9 — Layer 2 Verdict" \
  "Size S (3-5). Single opening of eval-L2. Tag: v1.1.0"
create_milestone "Phase 10 — External Validity" \
  "Size M (5-7). MuSiQue, real world, second model. Tag: v1.2.0"

echo "Done."
