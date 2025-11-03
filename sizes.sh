#!/usr/bin/env bash
# sort_code_by_lines.sh — list large source files (Python, JS, TS, HTML, etc.) sorted by line count (desc)
# Useful to spot refactoring candidates for Codex CLI.

set -e

echo "🔍 Sorting source files by line count (Python / JS / TS / HTML / JSX / TSX)..."

find . -type f \( \
    -name "*.py"  -o \
    -name "*.js"  -o \
    -name "*.jsx" -o \
    -name "*.ts"  -o \
    -name "*.tsx" -o \
    -name "*.html" \
  \) \
  ! -path "*/venv/*" \
  ! -path "*/.venv/*" \
  ! -path "*/__pycache__/*" \
  ! -path "*/node_modules/*" \
  ! -path "*/dist/*" \
  ! -path "*/build/*" \
  ! -path "*/coverage/*" \
	  | xargs wc -l 2>/dev/null | sort -nr | head -20
