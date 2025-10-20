#!/usr/bin/env bash
# sort_py_by_lines.sh — list .py files sorted by line count (desc)

set -e

echo "🔍 Sorting Python files by line count..."
find . -type f -name "*.py" ! -path "*/venv/*" ! -path "*/.venv/*" ! -path "*/__pycache__/*" \
  | xargs wc -l 2>/dev/null | sort -nr | head -10
