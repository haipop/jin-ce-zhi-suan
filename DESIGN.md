# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-06-10
- Primary product surfaces: FastAPI dashboard at `/`, packaged desktop launcher.
- Evidence reviewed: `dashboard.html`, `server.py`, `desktop_launcher.py`, `desktop.spec`, `README.md`, `pyproject.toml`.

## Brand
- Personality: clear, professional, local-first, research-oriented.
- Trust signals: visible risk disclaimers, calm controls, readable metrics, explicit local service behavior.
- Avoid: cyberpunk terminals, neon glow, heavy glass effects, marketing-page composition, decorative visual noise.

## Product goals
- Goals: make the quant research dashboard comfortable for long sessions, keep high-density controls scannable, and make packaged use feel like a desktop client.
- Non-goals: investment advice, trading recommendations, or changing strategy/backtest behavior.
- Success signals: default UI reads as fresh and light, core panels remain information-dense but not cramped, dashboard data remains scrollable and readable, desktop package opens an embedded client window.

## Personas and jobs
- Primary personas: local quant research users, learners, maintainers validating A-share strategies.
- User jobs: configure data sources, run backtests, inspect reports, monitor near-real-time status, manage strategy experiments.
- Key contexts of use: local desktop, browser fallback, offline or limited-network environments.

## Information architecture
- Primary navigation: top status/header, main workflow strip, central dashboard panels, modal workbenches.
- Core routes/screens: `/` dashboard, `/report` report page, desktop launcher.
- Content hierarchy: status and risk first, task controls second, "三省" decision chain above the "六部" execution grid, detailed diagnostics in the right-side log rail and modals.

## Design principles
- Principle 1: dense but calm; prefer readable tables and restrained controls over dramatic visual styling.
- Principle 2: local-client confidence; desktop and browser modes should feel like the same product.
- Tradeoffs: preserve the single-file dashboard structure for low-risk maintenance, even if CSS overrides are more compact than a full component refactor.

## Visual language
- Color: cool white and pale blue surfaces, professional blue as the primary accent, semantic red/green for market and risk states.
- Typography: existing Inter and JetBrains Mono; compact dashboard type, no viewport-scaled fonts.
- Spacing/layout rhythm: dense dashboard rhythm with page-level scrolling; group the three decision provinces as a top row, the six execution ministries as a 3x2 grid beneath it, and keep logs in a separate observation rail.
- Shape/radius/elevation: 6-8px radii, minimal shadows, no nested decorative cards.
- Motion: keep status motion functional; remove heavy glow perception through lighter colors.
- Imagery/iconography: existing logo and Font Awesome icons.

## Components
- Existing components to reuse: top header, workflow strip, glass panels, tables, modals, drawers, strategy selectors.
- New/changed components: default `theme-fresh` CSS layer and desktop client window mode.
- Variants and states: browser fallback remains available; desktop client is default.
- Token/component ownership: `dashboard.html` owns dashboard tokens; `desktop_launcher.py` owns client/browser mode.

## Accessibility
- Target standard: readable contrast for normal dashboard use.
- Keyboard/focus behavior: preserve existing focusable controls and modal behavior.
- Contrast/readability: dark text on light surfaces, strong semantic colors only where they convey state.
- Screen-reader semantics: no change to existing labels and structure.
- Reduced motion and sensory considerations: avoid new decorative animation.

## Responsive behavior
- Supported breakpoints/devices: existing desktop-first dashboard plus mobile-width browser smoke checks.
- Layout adaptations: wide screens use a main workflow area plus a right log rail; narrower screens stack decision, execution, and logs vertically. Page-level scrolling must remain available so cards are never compressed into unreadable rows.
- Touch/hover differences: preserve existing click targets and hover affordances.

## Interaction states
- Loading: light overlay with blue spinner.
- Empty: pale panels with muted text.
- Error: rose-tinted state, not neon.
- Success: emerald-tinted state.
- Disabled: low-contrast text and subtle border.
- Offline/slow network, if applicable: existing static asset fallback prompts remain.

## Content voice
- Tone: precise, cautious, research-focused.
- Terminology: keep existing project language such as "金策智算", "回测", "策略", "风控".
- Microcopy rules: avoid implying guaranteed returns or investment guidance.

## Implementation constraints
- Framework/styling system: single `dashboard.html` using Tailwind CDN-compatible class names and native JavaScript.
- Design-token constraints: add CSS variables and scoped overrides where practical, but layout fixes may adjust shell/grid markup when readability or scrolling requires it.
- Performance constraints: no new frontend framework; no remote-only assets.
- Compatibility constraints: desktop client uses optional `pywebview`; browser mode remains fallback.
- Test/screenshot expectations: static regression tests plus server smoke screenshots on desktop and mobile widths.

## Open questions
- [ ] Whether the report page should receive the same fresh theme in a later pass.
