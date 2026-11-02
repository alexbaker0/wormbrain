#!/usr/bin/env bash
# Overnight curriculum: for the usual and the symmetric body (both with head
# proprioception and the back/belly offset), crawl -> steer up a broad gradient -> patch
# world; then behaviour, steering and smell-reach analyses and the common tests. Results
# are committed and pushed as they land. Training checkpoints every generation, so
# rerunning this script continues where it stopped (finished stages are skipped).
#   setsid nohup scripts/queue_curriculum.sh > queue_curriculum.log 2>&1 &
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
  if [ -f "reports/$1/results.json" ]; then echo "$(date -u +%FT%TZ) $1 already done"; return; fi
  echo "$(date -u +%FT%TZ) starting $1"
  uv run python -W ignore scripts/chemotaxis_study.py --config "configs/$1.yaml" \
    --conditions real --seeds 2 --workers 2 --out "reports/$1"
  echo "$(date -u +%FT%TZ) finished $1"
  commit "Curriculum ($1): results" "reports/$1"
}

# wait for any earlier queue (its common tests) so runs don't compete for the cores
while pgrep -f "scripts/queue_sym.sh" > /dev/null; do sleep 30; done

(train curr_usual_grad && train curr_usual_patch) &
(train curr_sym_grad && train curr_sym_patch) &
wait
echo "$(date -u +%FT%TZ) analyses"
uv run python -W ignore scripts/patch_behaviour.py reports/curr_usual_patch reports/curr_sym_patch
for d in curr_usual_grad curr_usual_patch curr_sym_grad curr_sym_patch; do
  uv run python -W ignore scripts/steering_probe.py "reports/$d"
  uv run python -W ignore scripts/smell_reach.py "$d"
done
commit "Curriculum: behaviour, steering probe and smell reach" reports/curr_*
echo "$(date -u +%FT%TZ) scoring all scenarios on common tests"
uv run python -W ignore scripts/compare_natural.py
commit "Natural-reward study: common tests including the curriculum" reports/natural_rewards
echo "$(date -u +%FT%TZ) done"
