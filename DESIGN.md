# HomePanel design

## Intent
An everyday touch console at 1024 x 768, with music always within reach. Russian interface.

## Layout
A Home Assistant inspired dashboard: narrow navigation rail, clock and weather header, room filters, device cards and scene buttons. The server display hides the prototype navigation and music strip: the native 48px toolbar selects Dashboard or the actual Music Assistant frontend. Mobile web layout stacks the same content.

## Colour roles
Dark canvas #111418, rail #0b1015, card #1c232b, raised surface #28323d, selected surface #17354a; primary text #e1e3e6, secondary #a9adb2; accent #03a9f4, accent ink #061e2b. Status failure #ffb4a8. Light canvas #f5f6f8, card #ffffff, primary #202a33, secondary #52616d, selected surface #d7eefc, accent #03a9f4. The shared semantic colour roles apply across navigation, controls, cards and status. Plain CSS literals are intentional legacy web fallbacks; the iPad application uses UIKit and H.264 decoding.

## Type
The executable token source is the `:root` and `body.light` blocks at the top of
`homepanel/frontend/style.css`. Component declarations consume these semantic
colour, spacing and touch-target tokens. Each variable declaration follows its
literal fallback so legacy browsers can ignore variables without losing styling.

System sans-serif: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif. Body 15px, labels 12px, heading 28px, clock 64px. No network fonts.

## Spacing and shapes
8px base, 16px card gaps, 24px page padding; card/control radius 12px; minimum touch area 44px. Device cards 150px minimum tall. Inline SVG line icons share a 24-unit viewBox.

## Behaviour
Native buttons, selects and range inputs. Visible keyboard outline, named icon controls, error status live region. No autoplay audio, perpetual animation, blurred layers or external images. Loading, offline and unavailable are distinct states.

## Theme and motion
Dark by default; optional light theme and a separate night dimmer. 120ms opacity/colour transitions only; reduced motion preference honoured. Fullscreen uses feature detection, with Add to Home Screen instructions for legacy Safari.

## Verification limits
Modern Chromium screenshots and ES5 parsing cannot establish real iOS 9 compatibility or full WCAG conformance. Record actual QA in docs/VERIFICATION.md. Real iPad, real HA and HA OS app installation require separate hardware/environment validation.
