#!/usr/bin/env bash
# Extend the panel to 2022-2024. Three passes in the order that matters:
# the vn pass is the panel itself, mirror is the cheap cross-check, and world
# is the heavy denominator pull that most often runs into the daily quota.
# Each pass skips files already on disk, so re-running resumes.
set -u
cd "$(dirname "$0")/.."
YEARS=2022,2023,2024
for p in vn mirror world; do
  echo "=================== PASS $p  ($(date '+%F %T')) ==================="
  python3 scripts/fetch_trade.py --pass "$p" --years "$YEARS" || {
    echo "PASS $p stopped (exit $?) - most likely the Comtrade daily quota."
    echo "Re-run this script when the quota is back; finished files are kept."
    exit 1
  }
done
echo "=================== ALL PASSES DONE ($(date '+%F %T')) ==================="
