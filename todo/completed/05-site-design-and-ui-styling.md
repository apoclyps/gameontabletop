# Site Design and UI Styling

## Goal

Give the site a cohesive visual identity that feels appropriate for a tabletop gaming community — clean, modern, and inviting — while staying accessible and responsive across devices.

## Background

The current UI is functional but unstyled beyond bare Tailwind defaults:

- Colour palette is generic blue/gray with no brand identity
- `tailwind.config.js` has no custom tokens — every page hard-codes raw utility classes
- There is no global layout shell; each page is a standalone centred card with no shared navigation
- Typography uses the browser default sans-serif with no scale definition
- No logo, wordmark, or iconography
- Feedback is delivered via inline `<p>` tags (errors in red, success in green) with no toast or notification system
- No dark mode support
- Pages feel sparse on wide viewports; the `max-w-md` cards leave large empty margins on desktop

## User Decisions

- **Post-login destination**: Dashboard (groups and upcoming nights) — not the Profile page
- **Nav links**: Dashboard · Games · Friends/Members · Profile (avatar dropdown)
- **Colour palette**: Slate + teal — modern and clean with a slight warmth
- **User identity in nav**: Avatar (initials fallback) + username, opening a dropdown with Profile and Logout
- **Mobile nav**: Hamburger icon → slide-in drawer from the right
- **Dark mode**: Include in this pass alongside light-mode styles
- **Fonts**: Fitting pair chosen by the implementer (display + body)
- **Implementation scope**: Full pass — tokens, shell, components, and pages in one go

## Acceptance Criteria

### Design Tokens (Tailwind Config)

- [ ] A custom colour palette is defined in `tailwind.config.js` using a slate + teal foundation:
  - Primary action: teal (buttons, links, active states)
  - Surface/neutral: slate shades for backgrounds, borders, and text
  - Semantic: green (success), amber (warning), red (danger)
- [ ] A custom font stack is configured:
  - Display font (headings, nav wordmark): a fitting serif or slab-serif loaded from Fontsource or Google Fonts
  - Body font: a clean, legible sans-serif
  - Fonts added via `<link rel="preconnect">` in `index.html`
- [ ] Spacing, border-radius, and shadow scales are defined in the config so all pages use consistent tokens
- [ ] `@tailwindcss/typography` plugin added for any prose/markdown content
- [ ] `darkMode: 'class'` enabled in the config

### Global Layout Shell

- [ ] `AppShell.vue` wraps all authenticated pages and provides:
  - Top nav bar: wordmark/logo on the left; links (Dashboard, Games, Friends) in the centre; avatar+username dropdown on the right
  - Avatar dropdown: links to Profile and a Logout action
  - Avatar falls back to the user's initials in a coloured circle when no `avatar_url` is set
  - Hamburger icon on mobile (≤ `md` breakpoint) that opens a slide-in drawer from the right containing the same nav links
  - Drawer closes on overlay click or route navigation
  - Footer with links (About, Contact, Terms, Privacy)
- [ ] `AuthLayout.vue` wraps guest pages (login, register, forgot-password, reset-password, verify-email):
  - Logo/wordmark centred above the card
  - No full navigation — just the logo and the card
- [ ] Router (`router/index.js`) assigns layout per route via `meta.layout`:
  - `layout: 'app'` → AppShell (all authenticated routes)
  - `layout: 'auth'` → AuthLayout (login, register, etc.)
  - `layout: 'none'` → bare RouterView (invite accept page — partially public)
- [ ] After a successful login, the user is redirected to `/dashboard`, not `/profile`
  - Update the `guestOnly` guard redirect from `/profile` to `/dashboard`

### Branding

- [ ] Logo/wordmark SVG created and stored at `frontend/src/assets/logo.svg`; works on both light and dark backgrounds
- [ ] `favicon.ico` and `apple-touch-icon.png` added to `frontend/public/`
- [ ] `<title>` in `index.html` updated to "Game On Tabletop"
- [ ] Each route sets a descriptive page title via `router.afterEach` using `meta.title`

### Component Library (Shared UI Primitives)

Extract repeated inline patterns into reusable components in `frontend/src/components/ui/`:

- [ ] `BaseButton.vue` — variant props (`primary`, `secondary`, `danger`, `ghost`), size props (`sm`, `md`, `lg`), loading state spinner; replaces all ad-hoc button styles
- [ ] `BaseInput.vue` — label, error message, leading/trailing icon slots; replaces the repeated `<label>/<input>` pattern across form pages
- [ ] `BaseCard.vue` — consistent padding, shadow, and border-radius using design tokens
- [ ] `BaseAlert.vue` — replaces inline `<p class="text-red-500">` with a proper alert box supporting `error`, `success`, `warning`, and `info` variants with icon + dismiss button
- [ ] `ToastNotification.vue` + `useToast()` composable — dismissible toast that slides in from the top-right; replaces inline feedback on ProfilePage and elsewhere
- [ ] `BaseAvatar.vue` — displays `avatar_url` image or a coloured circle with initials; used in nav and on profile/member lists
- [ ] `SkeletonLoader.vue` — generic placeholder blocks matching the shape of common content (card, list row, heading)

### Page-level Improvements

- [ ] **Login / Register / Forgot-password / Reset-password / Verify-email**: use `AuthLayout.vue`; add logo above card title; use `BaseInput`, `BaseButton`, `BaseAlert`
- [ ] **Dashboard**: replace the current bare list with a richer card grid; show group avatar/icon, upcoming night date, and member count
- [ ] **Group page**: surface the next upcoming occurrence prominently; use `BaseCard` and `BaseButton` throughout
- [ ] **Occurrence page**: RSVP buttons use `BaseButton` variants; RSVP counts styled with teal/green/red tokens
- [ ] **Profile page**: two-column layout on desktop — avatar preview left, form right; show avatar image when `avatar_url` is set; use `BaseInput` and `useToast` for save feedback
- [ ] **Empty / loading states**: replace `animate-pulse` text with `SkeletonLoader` components shaped like the content they replace
- [ ] **404 page**: add `NotFoundPage.vue` with an on-brand illustration or message and a link back to Dashboard

### Dark Mode

- [ ] `useColorScheme()` composable reads and persists preference to `localStorage`; toggles `dark` class on `<html>`; respects `prefers-color-scheme` as the initial default
- [ ] All components and pages have `dark:` variants for backgrounds, text, and borders using the slate/teal token set
- [ ] A toggle button (sun/moon icon) in the nav bar switches between light and dark

### Accessibility

- [ ] All interactive elements have visible focus rings (`focus-visible:ring` utilities)
- [ ] Colour contrast meets WCAG AA for all text/background combinations
- [ ] Form fields have associated `<label>` elements via `BaseInput.vue`
- [ ] `role="alert"` on error/success messages in `BaseAlert.vue`
- [ ] Drawer and dropdown menus trap focus and close on Escape

## Implementation Notes

- Implement tokens and `AppShell` first — every subsequent page change depends on them
- Avoid adding a full component library (Vuetify, PrimeVue) — build the small primitive set with Tailwind for full control and a lean bundle
- For icons use `@heroicons/vue` — outline style, well-suited to the teal/slate palette, tree-shakeable
- All new components should have Vitest unit tests using `@vue/test-utils`
- The invite page (`/invites/:token`) is semi-public (works before login) — keep it outside `AppShell` but give it the `AuthLayout` look so it still feels on-brand
