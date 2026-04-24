#!/usr/bin/env bash
# =============================================================================
# check_task_board_integrity.sh
#
# Validates the integrity of the tasks/ board directory tree.
#
# WHAT IT CHECKS
# --------------
# 1. No duplicate IDs across state directories.
#    Each task ID (e.g. OPS-025) must exist in exactly one of:
#      tasks/{backlog,in-progress,review,testing,blocked,done,discoveries}/
#    IDs are extracted from filenames matching the pattern ^[A-Z]+-[0-9]+\.md$
#    (i.e. date-slug.md files in done/ are silently skipped).
#    Any ID found in 2+ directories is an ERROR (exits non-zero).
#
# 2. No orphan IDs (filename/frontmatter mismatch).
#    Every task file's `id:` frontmatter value must match its filename stem.
#    e.g. tasks/done/OPS-025.md must contain `id: OPS-025`.
#    Mismatches are an ERROR (exits non-zero).
#
# 3. Frontmatter schema sanity (WARNING, non-fatal).
#    Required frontmatter keys: id, stream, title, priority, effort, status,
#    created, updated.  Missing keys are reported as warnings; the script still
#    exits 0 unless another check fails.
#
# 4. DEC reference validity.
#    If a file's `depends_on:` list contains DEC-NNN entries, each referenced
#    DEC must exist as a file in tasks/done/ or tasks/backlog/.
#    Dangling DEC references are an ERROR (exits non-zero).
#
# USAGE
# -----
#   bash scripts/check_task_board_integrity.sh
#
# Exit codes:
#   0  — clean tree (warnings may still be printed to stderr)
#   1  — one or more errors detected
# =============================================================================

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASKS_DIR="${REPO_ROOT}/tasks"

# Directories that are considered "state" dirs for duplicate/orphan checks
STATE_DIRS="backlog in-progress review testing blocked done discoveries"

ERRORS=0
WARNINGS=0

# Colour helpers (fall back gracefully if terminal doesn't support colours)
RED=""
YELLOW=""
RESET=""
if [ -t 2 ] && command -v tput >/dev/null 2>&1; then
  RED="$(tput setaf 1 2>/dev/null || true)"
  YELLOW="$(tput setaf 3 2>/dev/null || true)"
  RESET="$(tput sgr0 2>/dev/null || true)"
fi

err()  { echo "${RED}ERROR${RESET}: $*" >&2; ERRORS=$((ERRORS + 1)); }
warn() { echo "${YELLOW}WARN${RESET}:  $*" >&2; WARNINGS=$((WARNINGS + 1)); }
info() { echo "INFO:  $*"; }

# ---------------------------------------------------------------------------
# Build a list of "ID|statedir" pairs for all structured task files
# ---------------------------------------------------------------------------
# Temp file for all ID|dir pairs
PAIRS_FILE="$(mktemp)"
trap 'rm -f "$PAIRS_FILE"' EXIT

for state in $STATE_DIRS; do
  dir="${TASKS_DIR}/${state}"
  [ -d "$dir" ] || continue

  for filepath in "${dir}"/*.md; do
    [ -f "$filepath" ] || continue
    filename="$(basename "$filepath")"
    # Only files matching UPPERCASE_PREFIX-DIGITS.md (skip dated slugs, README, etc.)
    # Pattern: one or more uppercase letter/digit/hyphen groups, ending in -NNN.md
    case "$filename" in
      [A-Z]*-[0-9]*.md)
        # Further validate: no lowercase in base name (excluding extension)
        base="${filename%.md}"
        # Check that base looks like ID pattern (uppercase + hyphens + digits only)
        if echo "$base" | grep -qE '^[A-Z][A-Z0-9-]+-[0-9]+$'; then
          echo "${base}|${state}" >> "$PAIRS_FILE"
        fi
        ;;
    esac
  done
done

# ---------------------------------------------------------------------------
# 1. Duplicate ID check: any ID appearing in 2+ state dirs
# ---------------------------------------------------------------------------
DUPLICATE_FOUND=0
if [ -s "$PAIRS_FILE" ]; then
  # Sort by ID, then find IDs with more than one unique state dir
  sort "$PAIRS_FILE" | \
    awk -F'|' '{
      if ($1 in dirs) {
        dirs[$1] = dirs[$1] " " $2
      } else {
        dirs[$1] = $2
        ids[NR] = $1
      }
    }
    END {
      for (i in ids) {
        id = ids[i]
        n = split(dirs[id], parts, " ")
        if (n > 1) print id ": " dirs[id]
      }
    }' | sort > /tmp/_dup_check_$$

  if [ -s /tmp/_dup_check_$$ ]; then
    while IFS= read -r line; do
      err "Duplicate task ID found — ${line}"
      DUPLICATE_FOUND=1
    done < /tmp/_dup_check_$$
  fi
  rm -f /tmp/_dup_check_$$
fi

if [ "$DUPLICATE_FOUND" -eq 0 ]; then
  info "Duplicate ID check:  PASS"
fi

# ---------------------------------------------------------------------------
# 2. Orphan check: frontmatter `id:` must match filename stem
# ---------------------------------------------------------------------------
ORPHAN_FOUND=0
for state in $STATE_DIRS; do
  dir="${TASKS_DIR}/${state}"
  [ -d "$dir" ] || continue

  for filepath in "${dir}"/*.md; do
    [ -f "$filepath" ] || continue
    filename="$(basename "$filepath")"
    base="${filename%.md}"
    # Only structured task files
    if echo "$base" | grep -qE '^[A-Z][A-Z0-9-]+-[0-9]+$'; then
      expected_id="$base"
      # Extract `id:` from frontmatter (first 30 lines)
      fm_id="$(head -30 "$filepath" | grep -E '^id: ' | head -1 | sed 's/^id: *//' | tr -d "\"'" | tr -d '[:space:]')"
      if [ -z "$fm_id" ]; then
        err "Missing 'id:' in frontmatter: ${filepath#"${REPO_ROOT}/"}"
        ORPHAN_FOUND=1
      elif [ "$fm_id" != "$expected_id" ]; then
        err "ID mismatch in ${filepath#"${REPO_ROOT}/"}: filename='${expected_id}' frontmatter='${fm_id}'"
        ORPHAN_FOUND=1
      fi
    fi
  done
done

if [ "$ORPHAN_FOUND" -eq 0 ]; then
  info "Orphan ID check:     PASS"
fi

# ---------------------------------------------------------------------------
# 3. Frontmatter schema sanity (warnings only, non-fatal)
# ---------------------------------------------------------------------------
REQUIRED_KEYS="id stream title priority effort status created updated"

for state in $STATE_DIRS; do
  dir="${TASKS_DIR}/${state}"
  [ -d "$dir" ] || continue

  for filepath in "${dir}"/*.md; do
    [ -f "$filepath" ] || continue
    filename="$(basename "$filepath")"
    base="${filename%.md}"
    if echo "$base" | grep -qE '^[A-Z][A-Z0-9-]+-[0-9]+$'; then
      for key in $REQUIRED_KEYS; do
        if ! head -40 "$filepath" | grep -qE "^${key}:"; then
          warn "Missing required key '${key}:' in ${filepath#"${REPO_ROOT}/"}"
        fi
      done
    fi
  done
done

if [ "$WARNINGS" -eq 0 ]; then
  info "Frontmatter schema:  PASS (no missing keys)"
fi

# ---------------------------------------------------------------------------
# 4. DEC reference validity
# ---------------------------------------------------------------------------
DEC_ERROR_FOUND=0
for state in $STATE_DIRS; do
  dir="${TASKS_DIR}/${state}"
  [ -d "$dir" ] || continue

  for filepath in "${dir}"/*.md; do
    [ -f "$filepath" ] || continue
    filename="$(basename "$filepath")"
    base="${filename%.md}"
    if echo "$base" | grep -qE '^[A-Z][A-Z0-9-]+-[0-9]+$'; then
      # Extract DEC-NNN references from anywhere in the file
      dec_refs="$(grep -oE 'DEC-[0-9]+' "$filepath" 2>/dev/null | sort -u || true)"
      for dec in $dec_refs; do
        dec_file_done="${TASKS_DIR}/done/${dec}.md"
        dec_file_backlog="${TASKS_DIR}/backlog/${dec}.md"
        if [ ! -f "$dec_file_done" ] && [ ! -f "$dec_file_backlog" ]; then
          err "Dangling DEC reference '${dec}' in ${filepath#"${REPO_ROOT}/"} — not found in tasks/done/ or tasks/backlog/"
          DEC_ERROR_FOUND=1
        fi
      done
    fi
  done
done

if [ "$DEC_ERROR_FOUND" -eq 0 ]; then
  info "DEC reference check: PASS"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "${RED}FAIL${RESET}: ${ERRORS} error(s) found, ${WARNINGS} warning(s). Fix errors before committing." >&2
  exit 1
else
  echo "PASS: 0 errors, ${WARNINGS} warning(s)."
  exit 0
fi
