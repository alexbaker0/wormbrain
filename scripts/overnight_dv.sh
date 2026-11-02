#!/usr/bin/env bash
# Back/belly offset (patches_dv) and offset + tied D/V classes (patches_tied), trained side
# by side, then all scenarios scored on the common tests. Each result is committed and
# pushed as it lands. Training checkpoints every generation, so rerunning this script
# after an interruption continues where it stopped.
#   setsid nohup scripts/overnight_dv.sh > overnight_dv.log 2>&1 &
# real_glu-excitatory_seed0 is left out: its milestone-4 crawler barely moves (0.03 mm/s)
# and it scored 0 in every patch-world run.
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

commit() {
  local msg="$1"; shift
  git add -A "$@" 2>/dev/null
  if git diff --cached --quiet; then return; fi
  git -c user.name="Alex Baker" -c user.email=alexbaker01@gmail.com commit -q -F - <<MSG
$msg

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014hVhNRfvdS3L9xvDdFvo3X
MSG
  for wait in 0 2 4 8 16; do sleep "$wait"; git push -q origin main && return; done
  echo "push failed for: $msg"
}

train() {
  echo "$(date -u +%FT%TZ) starting $1"
  uv run python -W ignore scripts/chemotaxis_study.py --config "configs/$1.yaml" \
    --conditions real --seeds 2 --workers 3 --out "reports/$1" --skip real_glu-excitatory_seed0
  echo "$(date -u +%FT%TZ) finished $1"
  commit "Patch world ($1): results" "reports/$1"
}

train patches_dv &
train patches_tied &
wait
echo "$(date -u +%FT%TZ) scoring all scenarios on common tests"
uv run python -W ignore scripts/compare_natural.py
commit "Natural-reward study: common tests including offset and tied classes" reports/natural_rewards
echo "$(date -u +%FT%TZ) done"
