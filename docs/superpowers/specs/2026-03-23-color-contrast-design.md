# Color Contrast Improvement

## Problem

Several text colors in the hacker terminal theme have insufficient contrast against dark backgrounds:

- `--color-text-muted: #5a8a62` on `#000000` — contrast ratio ~5.5:1 (visually poor despite passing AA)
- `--color-text-muted: #5a8a62` on `#0d1117` — contrast ratio ~4.8:1 (barely passes AA)
- `--color-diff-delete-text: #ff2244` on `rgba(255,0,64,0.25)` — contrast ratio ~4.4:1 (fails WCAG AA)

## Solution

Adjust three color tokens in `frontend/src/css/base.css`:

| Token | Before | After | Expected Contrast |
|-------|--------|-------|-------------------|
| `--color-text-muted` | `#5a8a62` | `#7ab882` | ~8:1 on `#000` |
| `--color-diff-delete-text` | `#ff2244` | `#ff5566` | ~5.5:1 on diff bg |
| `--color-diff-delete-bg` | `rgba(255,0,64,0.25)` | `rgba(255,0,64,0.15)` | increases text-bg separation |

## Impact

- `--color-text-muted` is referenced in 23 places (components.css, layout.css) — all update automatically
- `--color-diff-delete-text` is referenced in 2 places (components.css)
- `--color-diff-delete-bg` is referenced in 2 places (components.css)

## Theme Preservation

- Green and red tones maintained — no color palette change
- Glow effects, animations, and layout unchanged
- Hacker terminal aesthetic fully preserved

## Testing

- Verify existing tests still pass
- Visual confirmation in browser (diff display, muted text locations)
