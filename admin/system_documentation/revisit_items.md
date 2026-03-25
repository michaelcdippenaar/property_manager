# Items to Revisit

## LeasesView Header & Tab Navigation
**Date flagged:** 2026-03-25
**Location:** `admin/src/views/leases/LeasesView.vue` (lines 1–55)
**Status:** Improved but needs further refinement

**What was done:**
- Separated page title ("Leases") + action buttons from tab navigation
- Tabs now use underline style instead of filled pills to distinguish from action buttons

**What still needs attention:**
- Tab + action button layout may still feel dense on smaller screens
- "Build Lease Template" tab label may be confusing since there's also a "Build Lease" item in the sidebar nav — consider renaming
- Action buttons change depending on active tab (Import/Add vs Upload Template) — could be jarring; consider keeping both sets visible but disabling irrelevant ones
- The tab underline style doesn't match the FilterPills pattern used on Maintenance/Suppliers views — decide on one pattern for sub-navigation across the app
- Consider whether leases and templates should be separate sidebar routes entirely rather than tabs within one view

## All Leases / Lease Templates Cross-Over Confusion
**Date flagged:** 2026-03-25
**Location:** `admin/src/views/leases/LeasesView.vue`, sidebar nav, router
**Status:** Needs UX decision

**Problem:**
- The sidebar already has separate links: "All Leases", "Templates", "Calendar", "Build Lease"
- But LeasesView.vue bundles "All Leases" and "Lease Templates" into a single view with tabs
- This creates cross-over: clicking "Templates" in the sidebar goes to `/leases/templates` (LeaseTemplatesView.vue), but clicking the "Lease Templates" tab inside LeasesView shows a different templates UI within the same page
- Two separate template management experiences exist — one as a standalone view, one embedded in the leases tab
- User can lose context about which "templates" view they're in

**Options to resolve:**
1. **Remove the tab** — LeasesView shows only leases; templates live exclusively at `/leases/templates` (LeaseTemplatesView.vue). Simplest fix.
2. **Remove the standalone view** — Merge LeaseTemplatesView into the LeasesView tab and remove the sidebar link. Reduces duplication.
3. **Keep both but differentiate** — Rename one (e.g., tab becomes "Quick Templates" for inline management, sidebar route becomes "Template Editor" for the full builder). Adds clarity but keeps two surfaces.

## Lease Expand Panel — Minor Polish
**Date flagged:** 2026-03-25
**Location:** `admin/src/views/leases/LeasesView.vue` (lines 103-230)
**Status:** Good — minor polish later

**What was done:**
- Redesigned from flat sprawl to card-based two-column layout (details left, actions+docs right on lg:)
- Added navy left border on active row + slate-50 background with navy/10 borders
- Split terms into primary (rent, deposit, period) and secondary (water, electricity, notice)

**Minor things to revisit:**
- Actions + documents cards below fold on smaller screens — consider sticky or always-visible placement
- 4th column in terms grid can get cut off at narrow widths
- Payment ref field may need truncation for long references

## Add "Questions" Tab Under Issues
**Date flagged:** 2026-03-25
**Location:** `admin/src/views/maintenance/RequestsView.vue`, router
**Status:** Todo

**Description:**
- Add a new tab called "Questions" alongside the existing Issues view under Maintenance
- Needs UX/data design: what are "Questions" — tenant queries? Pre-issue triage? Clarification requests on existing issues?
- Implementation: could be a FilterPills tab or a separate route under `/maintenance/questions`

## Template Editor — Navigate Back to Last Edited Template
**Date flagged:** 2026-03-25
**Location:** `admin/src/views/leases/TemplateEditorView.vue`, router
**Status:** Todo

**Description:**
- When user is editing a template and navigates away (e.g. to Build Lease), clicking "Create Template" in sidebar should return them to the template they were editing
- Could store last-edited template ID in localStorage or route state

## Template Editor — AI Auto-Scan on Save
**Date flagged:** 2026-03-25
**Location:** `admin/src/views/leases/TemplateEditorView.vue`
**Status:** Todo / Idea

**Description:**
- When the user saves the document, the AI should automatically scan through and give warnings
- Could check for: missing fields, incomplete clauses, legal compliance issues, formatting problems
- Show warnings as a toast or inline panel after save completes

## Template Editor — Responsive Collapse
**Date flagged:** 2026-03-25
**Location:** `admin/src/views/leases/TemplateEditorView.vue`
**Status:** Partial

**Description:**
- When page gets smaller, AI panel and right side field menu should auto-collapse
- AI chat already collapses at < 1200px width
- Right panel (field palette) needs similar responsive behavior — collapse to icon strip or hide entirely on narrow screens
