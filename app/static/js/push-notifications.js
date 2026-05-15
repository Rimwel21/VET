/**
 * VetSync Push Notification Manager
 * Session-based auth (CSRF token). Works for both Client & Staff views.
 */

const PUSH_VAPID_URL = '/api/v1/push/public-key';
const PUSH_SUB_URL   = '/api/v1/push/subscribe';

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const out     = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; i++) out[i] = rawData.charCodeAt(i);
    return out;
}

function getCsrf() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

/**
 * Update every push toggle button on the page.
 * Works for:
 *   #push-bell-btn   (client header)
 *   #btn-enable-push (staff sidebar)
 */
function updatePushBellUI(enabled, unsupported = false) {
    // ── Client header bell ──
    const bell = document.getElementById('push-bell-btn');
    if (bell) {
        if (unsupported) {
            bell.innerHTML     = '🔕';
            bell.title         = 'Push notifications not supported on this browser';
            bell.style.cssText = 'background:#94a3b8; color:white; cursor:not-allowed; opacity:0.6;';
            return;
        }
        bell.innerHTML     = enabled ? '🔔' : '🔕';
        bell.title         = enabled ? 'Notifications enabled — tap to check' : 'Tap to enable push notifications';
        bell.style.cssText = enabled
            ? 'background:#16a34a; color:white; border-radius:8px; border:none; font-size:1.1rem; padding:5px 9px; cursor:pointer; transition:.2s;'
            : 'background:#dc2626; color:white; border-radius:8px; border:none; font-size:1.1rem; padding:5px 9px; cursor:pointer; transition:.2s;';
    }

    // ── Staff sidebar push button ──
    const staffBtn = document.getElementById('btn-enable-push');
    if (staffBtn) {
        if (unsupported) {
            staffBtn.textContent      = '⛔ Not Supported';
            staffBtn.style.background = '#94a3b8';
            staffBtn.style.cursor     = 'not-allowed';
            return;
        }
        staffBtn.textContent      = enabled ? '🟢 Notifications ON' : '🔴 Notifications OFF';
        staffBtn.style.background = enabled ? '#16a34a' : '#dc2626';
        staffBtn.style.cursor     = 'pointer';
    }
}

async function syncSubscriptionWithServer(subscription) {
    try {
        const key  = subscription.getKey('p256dh');
        const auth = subscription.getKey('auth');
        const res  = await fetch(PUSH_SUB_URL, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrf() },
            body: JSON.stringify({
                endpoint: subscription.endpoint,
                keys: {
                    p256dh: btoa(String.fromCharCode(...new Uint8Array(key))),
                    auth:   btoa(String.fromCharCode(...new Uint8Array(auth)))
                }
            })
        });
        updatePushBellUI(res.ok);
        console.log('[Push] Sync:', res.ok ? 'OK' : 'Failed (' + res.status + ')');
    } catch (err) {
        console.error('[Push] Sync error:', err);
    }
}

async function initPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        updatePushBellUI(false, true);
        return;
    }
    try {
        const reg          = await navigator.serviceWorker.ready;
        let   subscription = await reg.pushManager.getSubscription();

        if (subscription) {
            // Already subscribed — update UI and re-sync
            updatePushBellUI(true);
            await syncSubscriptionWithServer(subscription);
            return;
        }

        // Not yet subscribed — request permission & subscribe
        const res = await fetch(PUSH_VAPID_URL, { credentials: 'include' });
        if (!res.ok) { updatePushBellUI(false); return; }
        const { public_key } = await res.json();

        subscription = await reg.pushManager.subscribe({
            userVisibleOnly:      true,
            applicationServerKey: urlBase64ToUint8Array(public_key)
        });
        await syncSubscriptionWithServer(subscription);
    } catch (err) {
        // User denied or other error
        console.warn('[Push] Blocked or failed:', err.message);
        updatePushBellUI(false);
    }
}

/** Called when user taps the bell or the staff sidebar button */
async function togglePushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    const reg      = await navigator.serviceWorker.ready;
    const existing = await reg.pushManager.getSubscription();
    if (existing) {
        // Already on — offer to disable
        if (confirm('Push notifications are enabled ✅\n\nTap OK to disable them on this device.')) {
            await existing.unsubscribe();
            updatePushBellUI(false);
        }
    } else {
        // Off — try to enable
        await initPushNotifications();
    }
}

// Auto-check state on load (client dashboard, profile, booking & all staff pages)
window.addEventListener('load', () => {
    const p = window.location.pathname;
    const isClientPage = p.includes('/dashboard') || p.includes('/profile') || p.includes('/book');
    const isStaffPage  = p.includes('/staff') || p.includes('/admin');

    if (isClientPage || isStaffPage) {
        setTimeout(async () => {
            if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
                updatePushBellUI(false, true);
                return;
            }
            try {
                const reg          = await navigator.serviceWorker.ready;
                const subscription = await reg.pushManager.getSubscription();
                // Just update UI based on current subscription state — no auto-subscribe
                updatePushBellUI(!!subscription);
            } catch (e) {
                updatePushBellUI(false);
            }
        }, 800);
    }
});
