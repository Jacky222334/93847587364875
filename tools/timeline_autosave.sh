#!/usr/bin/env bash
set -euo pipefail

# Local timeline autosave for reproducibility / archiving.
# Creates timestamped snapshots under: 04_exotic_manis/audit/timeline/
#
# Contents per snapshot:
# - git bundle (full repo history)
# - git metadata (status, log, config, remotes)
# - working tree diff (if any)
# - optional: compiled PDF (if present and --include-pdf)
#
# Usage:
#   ./tools/timeline_autosave.sh
#   ./tools/timeline_autosave.sh --include-pdf

INCLUDE_PDF=0
if [[ "${1:-}" == "--include-pdf" ]]; then
  INCLUDE_PDF=1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not a git repository: $REPO_ROOT" >&2
  exit 1
fi

TS="$(date -u +"%Y%m%dT%H%M%SZ")"
OUT_DIR="$REPO_ROOT/audit/timeline/$TS"
mkdir -p "$OUT_DIR"

echo "Writing snapshot: $OUT_DIR"

# Core git metadata
git rev-parse HEAD > "$OUT_DIR/HEAD.txt"
git branch --show-current > "$OUT_DIR/branch.txt" || true
git status --porcelain=v1 -b > "$OUT_DIR/status.txt"
git remote -v > "$OUT_DIR/remotes.txt" || true
git log --decorate --oneline -n 200 > "$OUT_DIR/log_last200_oneline.txt"
git log --decorate -n 50 > "$OUT_DIR/log_last50_full.txt"
git show -s --format=fuller HEAD > "$OUT_DIR/HEAD_fuller.txt"
git config --list --show-origin > "$OUT_DIR/git_config_show_origin.txt" || true

# Working tree patch (if any)
git diff > "$OUT_DIR/working_tree.diff" || true
git diff --cached > "$OUT_DIR/index.diff" || true

# Full history bundle (restorable without network)
git bundle create "$OUT_DIR/repo.bundle" --all

# Manifest
{
  echo "timestamp_utc=$TS"
  echo "repo_root=$REPO_ROOT"
  echo "head=$(cat "$OUT_DIR/HEAD.txt")"
} > "$OUT_DIR/manifest.txt"

# Optional compiled PDF (kept local; ignored by .gitignore)
PDF_PATH="$REPO_ROOT/docs/manuskript_04_pua_highimpact_apa7.pdf"
if [[ "$INCLUDE_PDF" -eq 1 && -f "$PDF_PATH" ]]; then
  cp -a "$PDF_PATH" "$OUT_DIR/"
  echo "included_pdf=$(basename "$PDF_PATH")" >> "$OUT_DIR/manifest.txt"
fi

echo "OK: snapshot complete."

