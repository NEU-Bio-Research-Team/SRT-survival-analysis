#!/usr/bin/env bash
# Sequential driver for the whole Đợt 1-4 programme. Every step is resumable:
# rerunning this script after a crash skips finished cells/specs and continues.
set -u
cd "$(dirname "$0")/.."
PY=${PY:-/home/minhquang/miniconda3/envs/srt-stage2/bin/python}
LOG=stage2_benchmark/artifacts/logs/run_all.log
mkdir -p stage2_benchmark/artifacts/logs
step() { echo "$(date +%F\ %T) >>> $*" | tee -a "$LOG"; }
STEPS=${STEPS:-"batch4 batch1"}
for s in $STEPS; do
  case $s in
    batch4) step "Đợt 4 inference"; $PY -m stage2_benchmark.inference.run_inference 2>&1 | tee -a "$LOG" ;;
    batch1|batch2|batch2_lobo|batch3)
            step "plan $s"; $PY -m stage2_benchmark.runners.batch --plan $s >> "$LOG" 2>&1
            $PY -m stage2_benchmark.runners.aggregate --plan $s >> "$LOG" 2>&1 ;;
    *) $PY -m stage2_benchmark.runners.$s >> "$LOG" 2>&1 ;;
  esac
done
step "run_all finished: $STEPS"
