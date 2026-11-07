# HomePanel design

## Intent
An everyday touch console at 1024 x 768, with music always within reach. Russian interface.

## Layout
An original dashboard: narrow navigation rail, clock and weather header, room filters, device cards, four scene buttons, and a persistent music strip. Mobile layout stacks the same content. Music has its own large view.

## Colour roles
Dark canvas #141615, rail #101211, card #222623, raised surface #2c322d; primary text #f1f3ec, secondary #b0b9ad; accent #d6e8ae, accent ink #202b18. Status failure #ffb4a8. Light canvas #edf0e7, card #ffffff, primary #202820, secondary #505b4d, accent #d6e8ae. Plain CSS literals are intentional iOS 9 fallbacks.

## Type
System sans-serif: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif. Body 15px, labels 12px, heading 28px, clock 64px. No network fonts.

## Spacing and shapes
8px base, 16px card gaps, 24px page padding; radius 18px, control radius 12px; minimum touch area 44px. Device cards 150px minimum tall. Inline SVG line icons share a 24-unit viewBox.

## Behaviour
Native buttons, selects and range inputs. Visible keyboard outline, named icon controls, error status live region. No autoplay audio, perpetual animation, blurred layers or external images. Loading, offline and unavailable are distinct states.

## Theme and motion
Dark by default; optional light theme and a separate night dimmer. 120ms opacity/colour transitions only; reduced motion preference honoured. Fullscreen uses feature detection, with Add to Home Screen instructions for legacy Safari.

## Verification limits
Modern Chromium screenshots and ES5 parsing cannot establish real iOS 9 compatibility or full WCAG conformance. Record actual QA in docs/VERIFICATION.md. Real iPad, real HA and HA OS app installation require separate hardware/environment validation.
