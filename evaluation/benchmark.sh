#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== SuperSonic 3-Model Benchmark ==="
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Check env
if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
    echo "ERROR: DASHSCOPE_API_KEY environment variable not set"
    echo "Usage: DASHSCOPE_API_KEY=sk-xxx bash benchmark.sh"
    exit 1
fi

# Check service
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:9080 | grep -q "302\|200"; then
    echo "ERROR: SuperSonic not running on http://localhost:9080"
    echo "Start it first: cd assembly && S2_DB_TYPE=h2 bin/supersonic-daemon.sh start"
    exit 1
fi
echo "[1/3] SuperSonic service is running"

# Run queries (build_models + agents + 100 queries per model)
echo "[2/3] Running 3-model benchmark queries (~15-20 min)..."
cd "$SCRIPT_DIR"
.venv312/bin/python build_pred_result.py

# Evaluate
echo "[3/3] Computing benchmark report..."
LATEST_OUTPUT=$(ls -td output/*/ 2>/dev/null | head -1)
if [ -z "$LATEST_OUTPUT" ]; then
    echo "ERROR: No output directory found"
    exit 1
fi
.venv312/bin/python evaluation.py --multi "$LATEST_OUTPUT/raw_results.json"

echo ""
echo "=== Benchmark Complete ==="
echo "Report: ${LATEST_OUTPUT}/benchmark_report.json"
