#!/usr/bin/env bash
# Overnight: when the back/belly-offset run (patches_dv) has finished training, skip its
# common-test scoring and train the tied-classes variant (patches_tied); then score all.
#   setsid nohup scripts/overnight_dv.sh > overnight_dv.log 2>&1 &
set -u
cd "$(dirname "$0")/.."
LOG="${1:?path to the patches_dv queue log}"
until grep -q "Z scoring\|Z done" "$LOG" || ! pgrep -f queue_patches.sh > /dev/null; do sleep 30; done
pkill -f "scripts/queue_patches.sh"; pkill -f "scripts/compare_natural.py"; sleep 5
echo "$(date -u +%FT%TZ) patches_dv done; starting patches_tied"
CONFIGS=patches_tied scripts/queue_patches.sh
echo "$(date -u +%FT%TZ) overnight done"
