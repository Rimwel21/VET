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
            staffBtn.disabled         = true;
        } else {
            staffBtn.textContent      = enabled ? '🟢 Enabled' : '🔴 Disabled';
            staffBtn.style.background = enabled ? '#16a34a' : '#dc2626';
            staffBtn.disabled         = false;
        }
    }

    // ── Client profile toggle switch ──
    const profileBtn = document.getElementById('profile-push-btn');
    if (profileBtn) {
        if (unsupported) {
            profileBtn.innerHTML        = '⛔ Not Supported';
            profileBtn.style.background = '#94a3b8';
            profileBtn.style.cursor     = 'not-allowed';
            profileBtn.disabled         = true;
        } else {
            profileBtn.innerHTML        = enabled ? '🟢 ON' : '🔴 OFF';
            profileBtn.style.background = enabled ? '#16a34a' : '#dc2626';
            profileBtn.disabled         = false;
        }
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

function uint8ArraysEqual(a, b) {
    if (!a || !b) return false;
    if (a.byteLength !== b.byteLength) return false;
    for (let i = 0; i < a.byteLength; i++) {
        if (a[i] !== b[i]) return false;
    }
    return true;
}

let isPushToggling = false;

async function initPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        updatePushBellUI(false, true);
        return;
    }
    try {
        const reg          = await navigator.serviceWorker.ready;
        let   subscription = await reg.pushManager.getSubscription();

        // Always fetch current VAPID public key
        const res = await fetch(PUSH_VAPID_URL, { credentials: 'include' });
        if (!res.ok) { updatePushBellUI(false); return; }
        const { public_key } = await res.json();
        const serverKeyUint8 = urlBase64ToUint8Array(public_key);

        if (subscription) {
            const subKeyUint8 = subscription.options.applicationServerKey
                ? new Uint8Array(subscription.options.applicationServerKey)
                : null;

            if (uint8ArraysEqual(subKeyUint8, serverKeyUint8)) {
                // VAPID keys match! Already subscribed — update UI and re-sync
                updatePushBellUI(true);
                await syncSubscriptionWithServer(subscription);
                return;
            } else {
                console.warn('[Push] VAPID key mismatch detected. Healing browser subscription...');
                await subscription.unsubscribe();
                subscription = null; // Force re-subscription below with new key
            }
        }

        // Subscribe using the current valid server key
        subscription = await reg.pushManager.subscribe({
            userVisibleOnly:      true,
            applicationServerKey: serverKeyUint8
        });
        await syncSubscriptionWithServer(subscription);
        if (typeof showInAppToast === 'function') {
            showInAppToast('Notifications Enabled', 'You will now receive push alerts.', null);
        }
    } catch (err) {
        console.warn('[Push] Blocked or failed:', err.message);
        updatePushBellUI(false);
        if (typeof showInAppToast === 'function') {
            showInAppToast('Permission Denied', 'Please allow notifications in browser settings.', null);
        }
    }
}

/** Called when user taps the bell or the staff sidebar button */
async function togglePushNotifications() {
    if (isPushToggling) return;
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        if (typeof showInAppToast === 'function') showInAppToast('Not Supported', 'Push notifications are not supported on this browser.', null);
        return;
    }
    
    isPushToggling = true;
    try {
        const reg      = await navigator.serviceWorker.ready;
        const existing = await reg.pushManager.getSubscription();
        if (existing) {
            // Already on — offer to disable
            if (confirm('Push notifications are enabled ✅\n\nTap OK to disable them on this device.')) {
                try {
                    await fetch('/api/v1/push/unsubscribe', {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrf() },
                        body: JSON.stringify({ endpoint: existing.endpoint })
                    });
                } catch (err) {
                    console.error('[Push] Server unsubscribe error:', err);
                }
                await existing.unsubscribe();
                updatePushBellUI(false);
                if (typeof showInAppToast === 'function') {
                    showInAppToast('Notifications Disabled', 'You will no longer receive push alerts.', null);
                }
            }
        } else {
            // Off — try to enable
            await initPushNotifications();
        }
    } catch (err) {
        console.error('[Push] Toggle error:', err);
        if (typeof showInAppToast === 'function') {
            showInAppToast('Error', 'Failed to update preference, please try again.', null);
        }
    } finally {
        isPushToggling = false;
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
                if (subscription) {
                    // Subscription exists — trigger self-healing check and synchronization
                    await initPushNotifications();
                } else {
                    // No subscription exists — just update disabled UI (do not auto-prompt)
                    updatePushBellUI(false);
                }
            } catch (e) {
                updatePushBellUI(false);
            }
        }, 800);
    }
});
