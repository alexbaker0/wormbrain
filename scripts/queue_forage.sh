#!/usr/bin/env bash
# Objective review (OBJECTIVES.md): gait -> serial foraging -> patch world, one objective
# (food eaten - energy) throughout; then the ablation without the food-contact sense, and
# the behaviour scorecard for all of them. Results are committed and pushed as they land.
# Checkpointed: rerunning continues where it stopped (finished stages are skipped).
#   setsid nohup scripts/queue_forage.sh > queue_forage.log 2>&1 &
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

commit() {
  local msg="$1"; shift
  git add -A "$@" 2>/dev/null
  if git diff --cached --quiet; then return; fi
  git -c user.name="Alex Baker" -c user.email=alexbaker01@gmail.com commit -q -F - <<MSG
$msg

Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014hVhNRfvdS3L9xvDdFvo3X
MSG
  for wait in 0 2 4 8 16; do sleep "$wait"; git push -q origin main && return; done
  echo "push failed for: $msg"
}

train() {  # config name, workers
  if [ -f "reports/$1/results.json" ]; then echo "$(date -u +%FT%TZ) $1 already done"; return; fi
  echo "$(date -u +%FT%TZ) starting $1"
  uv run python -W ignore scripts/chemotaxis_study.py --config "configs/$1.yaml" \
    --conditions real --seeds 2 --workers "$2" --out "reports/$1"
  echo "$(date -u +%FT%TZ) finished $1"
  commit "Objective review ($1): results" "reports/$1"
}

card() {
  [ -f "reports/$1/scorecard.md" ] && return
  echo "$(date -u +%FT%TZ) scorecard $1"
  uv run python -W ignore scripts/scorecard.py "reports/$1"
  commit "Objective review ($1): behaviour scorecard" "reports/$1"
}

train forage 4
card forage
(train forage_patch 2; card forage_patch) &
(train forage_nosense 2; card forage_nosense) &
wait
echo "$(date -u +%FT%TZ) done"
