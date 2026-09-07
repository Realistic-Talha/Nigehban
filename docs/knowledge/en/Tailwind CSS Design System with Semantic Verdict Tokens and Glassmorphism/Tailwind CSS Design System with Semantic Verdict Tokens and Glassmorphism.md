---
kind: frontend_style
name: Tailwind CSS Design System with Semantic Verdict Tokens and Glassmorphism
category: frontend_style
scope:
    - '**'
source_files:
    - apps/web/tailwind.config.ts
    - apps/web/src/styles/globals.css
    - apps/web/src/lib/theme/tokens.ts
    - apps/web/src/providers/theme-provider.tsx
    - apps/web/postcss.config.js
    - apps/web/next.config.ts
---

## What system/approach is used

The frontend (`apps/web`) uses **Next.js** with **Tailwind CSS** as the styling engine, driven by a centralized design-token approach. Theme switching is handled via `next-themes` (attribute-based dark mode), and PostCSS with Autoprefixer processes styles. The project follows a component-driven architecture where visual consistency is enforced through shared Tailwind configuration, CSS custom properties, and a TypeScript token file — not via a UI component library (the `packages/ui` directory currently only contains a `.gitkeep`).

## Key files and packages

- `apps/web/tailwind.config.ts` — central Tailwind config: defines color palette, typography, shadows, keyframes, animations, container breakpoints, and a custom plugin that registers `.glass`, `.glass-elevated`, `.glass-subtle` utilities plus `rtl`/`ltr` variants.
- `apps/web/src/styles/globals.css` — root CSS variables for light/dark themes under `:root` and `.dark`, plus global base/component/utility layers (`@tailwind base/components/utilities`). Defines semantic tokens: `--background`, `--foreground`, `--card`, `--border`, `--ring`, `--glass-*`, and per-verdict colors (`--verdict-true`, `--verdict-false`, etc.).
- `apps/web/src/lib/theme/tokens.ts` — TypeScript constants mapping each verdict type to its Tailwind classes (`bg-verdict-*-bg`, `text-verdict-*-text`, `border-verdict-*-border`, `shadow-glow-*`), gradients, icons, and labels in English/Urdu; also exposes glass variant presets and animation duration presets.
- `apps/web/src/providers/theme-provider.tsx` — wraps the app with `NextThemesProvider`, defaulting to `dark` theme, enabling system preference detection, and using class-based toggling (`attribute="class"`).
- `apps/web/postcss.config.js` — runs `tailwindcss` then `autoprefixer`.
- `apps/web/next.config.ts` — enables `optimizeCss` experimental flag and transpiles `@nigehban/ui` / `@nigehban/shared-types` from the monorepo workspace.

## Architecture and conventions

1. **Design tokens live in two places**: CSS custom properties in `globals.css` (runtime theme values) and Tailwind color extensions in `tailwind.config.ts` (compile-time utility names). They are kept in sync — e.g., `colors.surface.DEFAULT` maps to `var(--card)` so components can use either `bg-surface` or `bg-[var(--card)]`.
2. **Semantic verdict tokens**: A domain-specific color system (`verdict-true`, `verdict-false`, `verdict-misleading`, `verdict-unverified`, `verdict-satire`, `verdict-scam`, `verdict-safe`, `verdict-manipulated`, `verdict-authentic`) provides a full palette per verdict including `DEFAULT`, `bg`, `text`, `border`, and `glow` variants. This is consumed via both Tailwind utilities (`bg-verdict-true-bg`, `text-verdict-true-text`) and CSS variables (`--verdict-true`).
3. **Glassmorphism pattern**: A custom Tailwind plugin adds `.glass`, `.glass-elevated`, `.glass-subtle` utilities backed by `--glass-bg`, `--glass-border`, `--glass-blur` CSS variables. These are exposed as reusable presets in `tokens.ts` (`glassVariants.default/elevated/subtle`).
4. **Dark mode strategy**: `darkMode: "class"` in Tailwind paired with `next-themes` toggling a `.dark` class on the root element. All themeable tokens are defined as CSS variables under both `:root` and `.dark`, so no Tailwind `dark:` variants are needed for most surfaces.
5. **Typography**: Font families are extended via `fontFamily.sans` and `fontFamily.display` pointing at `--font-inter` (Inter) and `fontFamily.urdu` for Noto Sans Arabic, supporting bilingual English/Urdu content.
6. **Animations**: Custom keyframes (`shimmer`, `pulse-glow`, `float`, `gradient-shift`, `scan-line`) and corresponding animation utilities are registered in Tailwind config and reused across motion components (`src/components/motion/`).
7. **RTL support**: A `rtl`/`ltr` variant is added via the Tailwind plugin, allowing direction-aware styling with `[dir="rtl"] &` selectors.
8. **Component styling convention**: Components compose Tailwind utility classes directly (no CSS modules or SCSS per component). Shared patterns like `rounded-2xl`, `bg-accent-emerald/20`, `text-muted-foreground`, `border-white/10` appear consistently across pages and components. Reusable micro-components live under `src/components/ui/` (e.g., `GlassCard`, `VerdictBadge`, `ConfidenceMeter`) and encapsulate common style combinations.
9. **Monorepo sharing**: The Tailwind `content` glob includes `../../packages/ui/src/**/*.{js,ts,jsx,tsx}`, indicating a planned shared UI package whose components will be styled via the same token system.

## Conventions and constraints

- **Theme variables are single source of truth**: Surface/background/border/ring colors must be referenced via CSS variables or the mapped Tailwind aliases (`surface`, `background`, `border`, `ring`) rather than hard-coded hex values, ensuring dark-mode compatibility.
- **Verdicts must use the token map**: New verdict types should extend both `tailwind.config.ts` colors and `tokens.ts verdictColors` to keep class names, gradients, and labels consistent.
- **Glass components use the provided presets**: Instead of writing inline backdrop-filter/shadow rules, components should use the `glassVariants` presets or the `.glass*` utilities from the Tailwind plugin.
- **Dark mode is class-based**: All theme-dependent styles rely on the `.dark` class toggled by `next-themes`; new themeable styles must define both light and dark variable values in `globals.css`.
- **Fonts**: Use the extended `fontFamily.sans` / `fontFamily.display` / `fontFamily.urdu` classes rather than raw font-family strings to ensure Inter/Noto Sans Arabic usage.
- **Animation durations**: Prefer the `animationDurations` constants from `tokens.ts` when defining motion timing to maintain consistency across the app.