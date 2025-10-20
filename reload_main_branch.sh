#!/usr/bin/env bash
# reload_env.sh — safely reload local environment after a merge to main
# Includes pruning stale branches and optional dependency reload

set -e  # exit on error

echo "🔄 Fetching latest updates from origin (with pruning)..."
git fetch --prune origin

echo "🌿 Switching to main branch..."
git checkout main

echo "⬇️ Pulling latest changes from origin/main..."
git pull origin main --ff-only

echo "🧹 Cleaning up fully merged local branches..."
git branch --merged main | egrep -v "(^\*|main|master|develop)" | xargs -r git branch -d

echo "🗑️  Removing remote-tracking branches that no longer exist on origin..."
git remote prune origin

# Optional environment reload
if [ -f .env ]; then
  echo "♻️ Reloading .env file into current shell..."
  set -a
  source .env
  set +a
  echo "✅ Environment variables reloaded."
else
  echo "ℹ️ No .env file found — skipping environment reload."
fi

# Optional: Refresh dependencies automatically
if [ -f package.json ]; then
  echo "📦 Detected Node.js project — updating npm packages..."
  npm install
fi

if [ -f requirements.txt ]; then
  echo "🐍 Detected Python project — updating pip dependencies..."
  if [ -d venv ]; then
    source venv/bin/activate
  elif [ -d .venv ]; then
    source .venv/bin/activate
  fi
  pip install -r requirements.txt
  deactivate 2>/dev/null || true
fi

echo "✅ Local environment fully reloaded, cleaned, and up to date!"

