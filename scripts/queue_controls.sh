#!/usr/bin/env bash
# Wiring-control study under the curriculum (symmetric body, head proprioception, offset):
# rewired and random wiring (seeds 0-1, both glutamate settings) and real wiring seeds 2-3,
# through crawl -> broad gradient -> patch world. Real seeds 0-1 are in curr_sym_*.
# Checkpointed: rerunning continues where it stopped (finished stages are skipped).
#   setsid nohup scripts/queue_controls.sh > queue_controls.log 2>&1 &
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

SKIP=""
for g in excitatory inhibitory; do
  SKIP="$SKIP real_glu-${g}_seed0 real_glu-${g}_seed1"
  for c in rewired random; do SKIP="$SKIP ${c}_glu-${g}_seed2 ${c}_glu-${g}_seed3"; done
done

train() {
  if [ -f "reports/$1/results.json" ]; then echo "$(date -u +%FT%TZ) $1 already done"; return; fi
  echo "$(date -u +%FT%TZ) starting $1"
  uv run python -W ignore scripts/chemotaxis_study.py --config "configs/$1.yaml" \
    --conditions real rewired random --seeds 4 --workers 4 --out "reports/$1" --skip $SKIP
  echo "$(date -u +%FT%TZ) finished $1"
  commit "Wiring controls under the curriculum ($1): results" "reports/$1"
}

# let any earlier queue finish its common tests first
[ -n "${NO_WAIT:-}" ] || while pgrep -f "scripts/queue_curriculum.sh" > /dev/null; do sleep 30; done
train curr_sym_grad_more
train curr_sym_patch_more
echo "$(date -u +%FT%TZ) analyses"
uv run python -W ignore scripts/patch_behaviour.py reports/curr_sym_patch_more
uv run python -W ignore scripts/steering_probe.py reports/curr_sym_patch_more
uv run python -W ignore scripts/curriculum_controls.py
commit "Wiring controls under the curriculum: analysis" reports/curr_sym_patch_more reports/curriculum_controls
echo "$(date -u +%FT%TZ) done"
