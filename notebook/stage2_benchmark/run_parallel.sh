#!/usr/bin/env bash
# Two processes side by side (resumable, disjoint cells):
#   GPU worker : the neural models of batch2 (D06, L07, L08, L09, L10) on CUDA
#   CPU driver : everything else of batch2, then LOBO and batch3 (no neural
#                models there), then waits for the worker and writes reports.
# Rerunning after a crash resumes both halves.
set -u
cd "$(dirname "$0")/.."
PY=${PY:-/home/minhquang/miniconda3/envs/srt-stage2/bin/python}
LOG=stage2_benchmark/artifacts/logs/run_all.log
NEURAL="D06 L07 L08 L09 L10"
step() { echo "$(date +%F\ %T) >>> $*" | tee -a "$LOG"; }
step "parallel: GPU worker batch2 [$NEURAL]"
SRT_THREADS=2 $PY -m stage2_benchmark.runners.batch --plan batch2 --models $NEURAL \
    >> stage2_benchmark/artifacts/logs/gpu_worker.out 2>&1 &
GPU=$!
step "parallel: CPU driver batch2 (excluding neural)"
SRT_THREADS=4 $PY -m stage2_benchmark.runners.batch --plan batch2 --exclude-models $NEURAL >> "$LOG" 2>&1
for s in batch2_lobo batch3; do
  step "plan $s"
  SRT_THREADS=4 $PY -m stage2_benchmark.runners.batch --plan $s >> "$LOG" 2>&1
  $PY -m stage2_benchmark.runners.aggregate --plan $s >> "$LOG" 2>&1
done
step "waiting for GPU worker (pid $GPU)"
wait $GPU
step "aggregate batch2"
$PY -m stage2_benchmark.runners.aggregate --plan batch2 >> "$LOG" 2>&1
step "run_parallel finished"
