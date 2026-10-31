#!/usr/bin/env bash
# Overnight natural-reward study: run the scenarios one after another, commit and push
# each result as it lands, then score everything with scripts/compare_natural.py.
#   setsid nohup scripts/overnight_natural.sh > overnight.log 2>&1 &
set -u
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

commit() {  # commit the given paths with a message, push with retries
  local msg="$1"; shift
  git add -A "$@" 2>/dev/null
  if git diff --cached --quiet; then return; fi
  git -c user.name="Alex Baker" -c user.email=alexbaker01@gmail.com commit -q -F - <<EOF
$msg

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014hVhNRfvdS3L9xvDdFvo3X
EOF
  for wait in 0 2 4 8 16; do
    sleep "$wait"
    git push -q origin main && return
  done
  echo "push failed for: $msg"
}

echo "$(date -u +%FT%TZ) waiting for the straightness fine-tune pilot"
while pgrep -f "chemotaxis_finetune.yaml" > /dev/null; do sleep 30; done
commit "Fine-tune pilot (straightness penalty): results" reports/chemotaxis_finetune_pilot

for scenario in natural_fast natural_eat natural_energy natural_moving natural_far; do
  echo "$(date -u +%FT%TZ) starting $scenario"
  uv run python -W ignore scripts/chemotaxis_study.py --config "configs/$scenario.yaml" \
    --conditions real --seeds 2 --workers 4 --out "reports/$scenario"
  commit "Natural-reward scenario $scenario: results" "reports/$scenario"
done

echo "$(date -u +%FT%TZ) scoring all scenarios on common tests"
uv run python -W ignore scripts/compare_natural.py
commit "Natural-reward study: common tests across scenarios" reports/natural_rewards
echo "$(date -u +%FT%TZ) done"
