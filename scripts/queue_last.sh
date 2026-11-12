#!/usr/bin/env bash
# Lasting-food round (OBJECTIVES.md section 7): screen 32 brains briefly with food close
# by, continue the best 8 with food far away, then the best 4 on one currency (food eaten
# minus energy, no approach credit). Scorecards and the food-sense check for the last two
# phases. Checkpointed: rerunning continues where it stopped.
#   setsid nohup scripts/queue_last.sh > queue_last.log 2>&1 &
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
    --conditions real --seeds 16 --workers 4 --out "reports/$name" "$@"
  echo "$(date -u +%FT%TZ) finished $name"
  commit "Lasting-food round ($name): results" "reports/$name"
}

card() {  # config name
  if [ ! -f "reports/$1/scorecard.md" ]; then
    echo "$(date -u +%FT%TZ) scorecard $1"
    uv run python -W ignore scripts/scorecard.py "reports/$1"
  fi
  if [ ! -f "reports/$1/dwell.md" ]; then
    uv run python -W ignore scripts/dwell_check.py "reports/$1" "configs/$1.yaml"
  fi
  commit "Lasting-food round ($1): scorecard and food-sense check" "reports/$1"
  echo "$(date -u +%FT%TZ) carded $1"
}

train forage_screen
train forage_far --top 8 --rank-by forage_screen
train forage_last --top 4 --rank-by forage_far
card forage_last
card forage_far
echo "$(date -u +%FT%TZ) lasting done"
