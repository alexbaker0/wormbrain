#!/usr/bin/env bash
# Patch-world study: from-scratch training, then fine-tuning of the milestone-6 brains;
# each result committed and pushed as it lands, then everything scored on common tests.
#   setsid nohup scripts/queue_patches.sh > patches.log 2>&1 &
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

for config in patches patches_finetune; do
  echo "$(date -u +%FT%TZ) starting $config"
  uv run python -W ignore scripts/chemotaxis_study.py --config "configs/$config.yaml" \
    --conditions real --seeds 2 --workers 4 --out "reports/$config"
  commit "Patch world ($config): results" "reports/$config"
done
echo "$(date -u +%FT%TZ) scoring all scenarios on common tests"
uv run python -W ignore scripts/compare_natural.py
commit "Natural-reward study: common tests including the patch world" reports/natural_rewards
echo "$(date -u +%FT%TZ) done"
