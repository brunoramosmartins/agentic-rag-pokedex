#!/usr/bin/env bash
# .github/setup/milestones.sh
# Create one GitHub milestone per project phase (0..10).
#
# Due dates are soft targets from the effort estimate (week 1 starts
# 2026-09-24, 6-10 h/week). The project has no hard deadline.
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
  local title="$1" description="$2" due="$3"

  if grep -Fxq "$title" <<<"$existing"; then
    printf "  skip  %s (already exists)\n" "$title"
    return
  fi

  gh api "repos/$REPO/milestones" -X POST \
    -f title="$title" \
    -f description="$description" \
    -f due_on="${due}T23:59:59Z" >/dev/null
  printf "  ok    %s\n" "$title"
}

echo "Creating milestones..."

create_milestone "Phase 0 — Foundation" \
  "Week 1. ADRs 001-010, G1, measurability gate, E-001 draft, scaffold. Tag: v0.1-foundation" \
  "2026-09-30"
create_milestone "Phase 1 — World" \
  "Weeks 2-3. PokéAPI -> graph -> twin -> pages -> index. Tag: v0.2-world" \
  "2026-10-14"
create_milestone "Phase 2 — Examiner" \
  "Weeks 4-5. Generator, gold chains, step labels, G3 audit. Tag: v0.3-examiner (pre-release)" \
  "2026-10-28"
create_milestone "Phase 3 — Pilot Gate" \
  "Week 6. E-002, pilot, preliminary G2 and G4. Tag: v0.4-pilot-gate" \
  "2026-11-04"
create_milestone "Phase 4 — Baselines" \
  "Week 7. A0, A1, A2, A6, O1 tuned in good faith on group A. Tag: v0.5-baselines" \
  "2026-11-11"
create_milestone "Phase 5 — Agent" \
  "Weeks 8-9. A3, A4, A4p, O2 with per-step logs. Tag: v0.6-agent-detectors" \
  "2026-11-25"
create_milestone "Phase 6 — Layer 1 Verdict" \
  "Weeks 10-11. Single opening of eval-L1. Tag: v0.7-layer1-verdict (pre-release)" \
  "2026-12-09"
create_milestone "Phase 7 — Release" \
  "Week 12. Demo + README. Tag: v1.0.0 (stable)" \
  "2026-12-16"
create_milestone "Phase 8 — Trained Detector" \
  "Weeks 13-15 (3-week timebox). Calibrated sufficiency classifier, E-003." \
  "2027-01-06"
create_milestone "Phase 9 — Layer 2 Verdict" \
  "Week 16. Single opening of eval-L2. Tag: v1.1.0" \
  "2027-01-13"
create_milestone "Phase 10 — External Validity" \
  "Weeks 17-18. MuSiQue, real world, second model. Tag: v1.2.0" \
  "2027-01-27"

echo "Done."
