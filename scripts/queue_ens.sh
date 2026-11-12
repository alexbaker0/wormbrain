#!/usr/bin/env bash
# Ensemble round (OBJECTIVES.md): 16 brains through gait -> foraging on cone-shaped smell
# (phase A), then the best 4 by validation score continue in a world where stopping on
# food can pay (phase B). Scorecards and the food-sense check after each phase. Afterwards
# the paused patch-world run of the first round is resumed (scripts/queue_forage.sh).
# Checkpointed: rerunning continues where it stopped.
#   setsid nohup scripts/queue_ens.sh > queue_ens.log 2>&1 &
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

train() {  # config name, then extra study arguments
  local name="$1"; shift
  if [ -f "reports/$name/results.json" ]; then echo "$(date -u +%FT%TZ) $name already done"; return; fi
  echo "$(date -u +%FT%TZ) starting $name"
  uv run python -W ignore scripts/chemotaxis_study.py --config "configs/$name.yaml" \
    --conditions real --seeds 8 --workers 4 --out "reports/$name" "$@"
  echo "$(date -u +%FT%TZ) finished $name"
  commit "Ensemble round ($name): results" "reports/$name"
}

card() {  # config name
  if [ ! -f "reports/$1/scorecard.md" ]; then
    echo "$(date -u +%FT%TZ) scorecard $1"
    uv run python -W ignore scripts/scorecard.py "reports/$1"
  fi
  if [ ! -f "reports/$1/dwell.md" ]; then
    uv run python -W ignore scripts/dwell_check.py "reports/$1" "configs/$1.yaml"
  fi
  commit "Ensemble round ($1): scorecard and food-sense check" "reports/$1"
  echo "$(date -u +%FT%TZ) carded $1"
}

train forage_ens
train forage_refine --top 4 --rank-by forage_ens
card forage_refine
card forage_ens
echo "$(date -u +%FT%TZ) ensemble done"
scripts/queue_forage.sh
