#!/usr/bin/env bash
# sort_code_by_lines.sh — list large source files sorted by line count (desc)
# Covers Python, JS/TS, Web, and Apple platforms (iOS / iPadOS / tvOS / watchOS)

set -e

echo "🔍 Sorting source files by line count (Python / JS / TS / Web / Swift / Obj-C / Apple UI)..."

find . -type f \( \
    -name "*.py"  -o \
    -name "*.js"  -o \
    -name "*.jsx" -o \
    -name "*.ts"  -o \
    -name "*.tsx" -o \
    -name "*.html" -o \
    -name "*.swift" -o \
    -name "*.m" -o \
    -name "*.mm" -o \
    -name "*.h" -o \
    -name "*.storyboard" -o \
    -name "*.xib" -o \
    -name "*.xcconfig" \
  \) \
  ! -path "*/venv/*" \
  ! -path "*/.venv/*" \
  ! -path "*/__pycache__/*" \
  ! -path "*/node_modules/*" \
  ! -path "*/dist/*" \
  ! -path "*/build/*" \
  ! -path "*/coverage/*" \
  ! -path "*/DerivedData/*" \
  ! -path "*/Pods/*" \
  ! -path "*/.build/*" \
  ! -path "*.xcodeproj/*" \
  ! -path "*.xcworkspace/*" \
| xargs wc -l 2>/dev/null \
| sort -nr \
| head -20
