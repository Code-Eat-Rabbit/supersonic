#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== SuperSonic 3-Model Benchmark ==="
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
    echo "ERROR: DASHSCOPE_API_KEY not set"
    exit 1
fi

if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:9080 | grep -q "302\|200"; then
    echo "ERROR: SuperSonic not running"
    exit 1
fi
echo "[1/2] Service OK. Running benchmark queries (~10-15 min)..."
cd "$SCRIPT_DIR"
PYTHONUNBUFFERED=1 .venv312/bin/python build_pred_result.py

echo "[2/2] Computing report..."
LATEST=$(ls -td output/*/ 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
    echo "ERROR: No output dir"
    exit 1
fi
.venv312/bin/python evaluation.py --multi "$LATEST/raw_results.json"
echo ""
echo "=== Done ==="
echo "Report: ${LATEST}/benchmark_report.json"
