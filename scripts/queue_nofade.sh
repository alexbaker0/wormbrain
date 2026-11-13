#!/usr/bin/env bash
# No-fade round (OBJECTIVES.md section 8): the lasting-food screen and far phases again
# with a smell that does not fade as the food is eaten. Scorecard and food-sense check for
# the 8 continued brains. Checkpointed: rerunning continues where it stopped.
#   setsid nohup scripts/queue_nofade.sh > queue_nofade.log 2>&1 &
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
  commit "No-fade round ($name): results" "reports/$name"
}

card() {  # config name
  if [ ! -f "reports/$1/scorecard.md" ]; then
    echo "$(date -u +%FT%TZ) scorecard $1"
    uv run python -W ignore scripts/scorecard.py "reports/$1"
  fi
  if [ ! -f "reports/$1/dwell.md" ]; then
    uv run python -W ignore scripts/dwell_check.py "reports/$1" "configs/$1.yaml"
  fi
  commit "No-fade round ($1): scorecard and food-sense check" "reports/$1"
  echo "$(date -u +%FT%TZ) carded $1"
}

# The same 8 brains that the lasting-food round continued (reports/forage_far), so the two
# rounds can be compared brain by brain. (A full 32-brain screen was started first; the
# container kept being suspended, so the round was cut to these 8.)
SAME="real_glu-inhibitory_seed1 real_glu-inhibitory_seed2 real_glu-inhibitory_seed6
real_glu-inhibitory_seed15 real_glu-excitatory_seed7 real_glu-excitatory_seed9
real_glu-excitatory_seed10 real_glu-excitatory_seed15"
train forage_screen2 --only $SAME
train forage_far2 --only $SAME
card forage_far2
echo "$(date -u +%FT%TZ) nofade done"
