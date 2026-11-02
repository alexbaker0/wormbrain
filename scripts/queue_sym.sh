#!/usr/bin/env bash
# Symmetric body vs usual model, both trained from scratch in patch world v2 (seeds 0-1,
# both glutamate settings), side by side; then the behaviour analysis and the common tests.
# Training checkpoints every generation: rerunning this script continues where it stopped.
#   setsid nohup scripts/queue_sym.sh > queue_sym.log 2>&1 &
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
    --conditions real --seeds 2 --workers 2 --out "reports/$1"
  echo "$(date -u +%FT%TZ) finished $1"
  commit "Patch world from scratch ($1): results" "reports/$1"
}

train patches_sym &
train patches_scratch &
wait
echo "$(date -u +%FT%TZ) behaviour analysis"
uv run python -W ignore scripts/patch_behaviour.py reports/patches_sym reports/patches_scratch
commit "Symmetric body vs usual model: behaviour analysis" reports/patches_sym reports/patches_scratch
echo "$(date -u +%FT%TZ) scoring all scenarios on common tests"
uv run python -W ignore scripts/compare_natural.py
commit "Natural-reward study: common tests including the symmetric body" reports/natural_rewards
echo "$(date -u +%FT%TZ) done"
