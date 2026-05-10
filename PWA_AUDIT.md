# VetSync PWA Audit and Improvement Notes

Date: 2026-04-30

## Audit Findings

- Service worker registration used `/static/service-worker.js`, which limited the worker scope to `/static/`. Page navigation, offline fallback, and dashboard/booking flows were therefore not reliably controlled by the service worker.
- `service-worker.js` had a placeholder fetch handler, so navigation caching, static asset caching, API offline behavior, and offline page fallback were effectively missing.
- The manifest declared 192x192 and 512x512 icons while pointing to a 350x350 source image. This can fail installability checks or produce poor home screen icons.
- The manifest was missing several installability and cross-platform metadata fields, including `scope`, `id`, richer app naming, shortcuts, language, and flexible orientation.
- Offline booking storage existed in page JavaScript, but it did not use browser Background Sync where available and did not share a service-worker-level sync path.
- The mobile navigation worked visually, but the menu button lacked expanded state, control linkage, and an accessible label.
- Some mobile layouts had risk of cramped footer columns and controls with small touch affordances.

## Implemented Improvements

### Root-scoped service worker

Added a Flask route at `/service-worker.js` with `Service-Worker-Allowed: /` and changed registration to:

```js
navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
```

Impact: the worker can now control full app navigation, not only static assets. This is required for reliable offline fallback and app-shell behavior.

### Real caching and offline strategies

Rebuilt `app/static/service-worker.js` with:

- App-shell precaching for core pages, CSS, JavaScript, manifest, and key images.
- Network-first navigation handling with `/offline` fallback.
- Stale-while-revalidate caching for local static assets.
- Network-only API handling that returns a structured 503 JSON response when offline.
- Cache version cleanup on activation.

Impact: installed users can reopen cached app screens, get a clear offline page for uncached navigation, and keep assets fast without serving permanently stale files.

### Offline booking sync

Kept the existing IndexedDB booking queue and added:

- Shared IndexedDB store naming between page JavaScript and service worker.
- Background Sync registration with tag `sync-offline-bookings`.
- Service-worker sync handler that submits queued `/book` requests with session credentials.
- Browser fallback sync on the `online` event when Background Sync is unavailable.

Impact: appointment requests made offline are stored locally and retried when the device reconnects, improving mobile and low-connectivity usability.

### Manifest and icons

Updated `app/static/manifest.json` with:

- `id`, `scope`, `start_url`, `display_override`, `orientation: "any"`, `lang`, `dir`, and categories.
- App shortcuts for booking and dashboard access.
- Dedicated icon files:
  - `app/static/images/pwa-icon-180.png`
  - `app/static/images/pwa-icon-192.png`
  - `app/static/images/pwa-icon-512.png`
  - `app/static/images/pwa-maskable-512.png`

Impact: the app is more likely to pass browser installability checks across Chrome, Edge, Android, iOS/iPadOS, and desktop platforms.

### Accessibility and responsive shell fixes

Updated the base template and CSS with:

- Theme and Apple mobile web app meta tags.
- Apple touch icon.
- Skip-to-content link.
- `main` landmark target.
- Hamburger menu `aria-label`, `aria-expanded`, and `aria-controls`.
- Keyboard Escape support for closing the mobile menu.
- Visible focus states for keyboard users.
- Larger mobile menu hit area and safer small-screen footer/button layout.

Impact: navigation is easier on phones and tablets, works better with keyboard and assistive technology, and avoids cramped footer columns on narrow screens.

## Remaining Recommendations

- Run a Lighthouse PWA/accessibility audit in Chrome and Edge after deployment over HTTPS.
- Test iOS install behavior on Safari because iOS has stricter and different PWA support than Chromium browsers.
- Consider replacing mojibake text/icons in templates with clean UTF-8 or icon components; several existing files display corrupted emoji sequences.
- Add automated browser tests for offline fallback, install metadata, and mobile navigation state.
