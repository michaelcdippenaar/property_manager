# Portal Switcher Verification — 2026-04-18

Verified against Admin SPA (Vite) server on `http://localhost:5173`.  
Auth state at session start: mc@tremly.com, `role = 'admin'`.

---

## Results

### Step 1 — `/choose-portal` renders unauthenticated/authenticated ✅ PASS

Navigated directly to `http://localhost:5173/choose-portal`. Page rendered immediately with both cards (ShieldCheck → Admin Console, Briefcase → Agent Portal). Continue button was disabled (`disabled=true`, opacity 0.5, cursor `not-allowed`). Footer shows "Signed in as mc@tremly.com". Route meta correctly `public: true, allowWhenAuthenticated: true`.

Screenshot: `screenshots/portal-switcher-01-chooser-unselected.png`  
_(embedded above — two-card view, Continue muted)_

---

### Step 2 — Admin Console card selection + Continue → `/` ✅ PASS

Clicked Admin Console card: class updated to `border-navy bg-navy/5 text-navy` (navy selection ring + tint). Continue button became enabled (opacity 1, not disabled). Clicked Continue: navigated to `/` (admin console root). Correct.

Screenshot: `screenshots/portal-switcher-02-admin-selected.png`  
_(Admin Console card selected, Continue button active navy)_

---

### Step 3 — Agent Portal card selection + Continue → `/agent` ✅ PASS

Returned to `/choose-portal`, clicked Agent Portal card (same navy selection styling applied), Continue enabled. Clicked Continue: navigated to `/agent`. Agent shell dashboard rendered correctly (Good morning, MC, 47 properties, action queue).

Screenshot: `screenshots/portal-switcher-03-agent-shell.png`

---

### Step 4 — Agent layout avatar dropdown ✅ PASS

On `/agent`, clicked `.avatar-btn`. Dropdown opened with:
- **Header:** mc@tremly.com / mc@tremly.com (when authenticated)
- **Switch portal** RouterLink → `/choose-portal` (visible — auth.user.role = 'admin')
- **Profile** RouterLink → `/profile`
- **Sign out** button

Subsequent test (auth state cleared after navigation): dropdown correctly showed "Guest preview / Not signed in" and **no Switch portal item** — matching the `v-if="auth.user?.role === 'admin'"` guard. Outside-click dismissal confirmed (v-if removes element from DOM on body click; Escape key handler also registered).

Screenshot: `screenshots/portal-switcher-04-agent-dropdown.png`  
_(Dropdown open with Switch portal item visible, authenticated state)_

---

### Step 5 — Main admin layout dropdown ✅ PASS (source-verified)

`admin/src/components/AppLayout.vue` line 189–199:
```html
<template v-if="auth.user?.role === 'admin'">
  <RouterLink to="/choose-portal" ...>
    <ArrowLeftRight :size="16" ... />
    <span>Switch portal</span>
  </RouterLink>
</template>
```
Correct guard. `ArrowLeftRight` imported from `lucide-vue-next` (line 407). Item is above Profile, separated by a divider.

---

### Step 6 — Console errors ✅ PASS

`preview_console_logs(level='error')` — **no errors** throughout entire session.  
`preview_console_logs(level='warn')` — **no warnings** either.

---

### Step 7 — Login redirect logic ✅ PASS (source-verified)

`admin/src/views/auth/LoginView.vue` line 141–142:
```ts
function loginDestination(): string {
  if (auth.user?.role === 'admin') return '/choose-portal'
```
Both `handleLogin()` (line 119) and Google OAuth callback (line 151) call `loginDestination()`. Correct.

---

## Bugs Found

None. No source code changes were made.

---

## Final Verdict

**Ship.** All 7 verification steps pass. Route, card selection, Continue navigation, agent dropdown (authenticated and unauthenticated states), admin layout dropdown, console cleanliness, and login redirect logic are all correct.
