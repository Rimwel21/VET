// ===================== JWT AUTO-PERSIST =====================
(function() {
    const metaToken = document.querySelector('meta[name="jwt-token"]');
    if (metaToken && metaToken.content) {
        localStorage.setItem('access_token', metaToken.content);
        console.log('[JWT] Token successfully persisted from page meta.');
    }
})();

// ===================== SECURITY UTILITIES =====================
function escapeHTML(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ===================== NAVBAR =====================
const navbar = document.getElementById('navbar');
const navLinks = document.querySelector('.nav-links');
const hamburger = document.querySelector('.hamburger');
const blurOverlay = document.getElementById('blurOverlay');
let menuTransitionLocked = false;

if (navbar) {
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 20);
    });
}

function setMenuState(isOpen) {
    if (!navLinks) return;
    navLinks.classList.toggle('open', isOpen);

    if (hamburger) {
        hamburger.setAttribute('aria-expanded', String(isOpen));
        hamburger.setAttribute('aria-label', isOpen ? 'Close navigation menu' : 'Open navigation menu');
        hamburger.classList.toggle('active', isOpen);
    }
    
    if (blurOverlay) {
        blurOverlay.classList.toggle('active', isOpen);
    }
    
    document.body.classList.toggle('menu-open', isOpen);
}

function toggleMenu() {
    if (menuTransitionLocked) return;
    menuTransitionLocked = true;
    setMenuState(!(navLinks && navLinks.classList.contains('open')));
    setTimeout(() => {
        menuTransitionLocked = false;
    }, 180);
}

// Close when clicking links
document.querySelectorAll('.nav-links a').forEach((link) => {
    link.addEventListener('click', () => setMenuState(false));
});

// Close when clicking overlay or outside
document.addEventListener('click', (event) => {
    if (!navLinks || !navLinks.classList.contains('open')) return;
    if (navLinks.contains(event.target) || (hamburger && hamburger.contains(event.target))) return;
    setMenuState(false);
});

if (blurOverlay) {
    blurOverlay.addEventListener('click', () => setMenuState(false));
}

window.addEventListener('resize', () => {
    if (window.innerWidth > 1023) {
        setMenuState(false);
    }
});

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        setMenuState(false);
    }
});

// ===================== SMOOTH SCROLL =====================
document.querySelectorAll('a[href*="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (event) {
        const href = this.getAttribute('href');
        
        // Handle both "#anchor" and "/path#anchor"
        let targetId = '';
        if (href.startsWith('#')) {
            targetId = href;
        } else {
            try {
                const url = new URL(this.href, window.location.origin);
                if (url.pathname === window.location.pathname && url.hash) {
                    targetId = url.hash;
                }
            } catch (e) { return; }
        }

        if (targetId) {
            const target = document.querySelector(targetId);
            if (target) {
                event.preventDefault();
                const offset = 80;
                const bodyRect = document.body.getBoundingClientRect().top;
                const elementRect = target.getBoundingClientRect().top;
                const elementPosition = elementRect - bodyRect;
                const offsetPosition = elementPosition - offset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth',
                });
                
                // If menu is open, close it
                if (typeof setMenuState === 'function') setMenuState(false);
            }
        }
    });
});

// ===================== SCROLL ANIMATIONS =====================
if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.service-card, .stat-card, .team-card, .service-full-card').forEach((el) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(el);
    });
}

// ===================== FLASH AUTO-DISMISS =====================
setTimeout(() => {
    document.querySelectorAll('.flash').forEach((el) => {
        el.style.transition = 'opacity 0.5s';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 500);
    });
}, 4000);

// ===================== OFFLINE SYNC (IndexedDB) =====================
const DB_NAME = 'VetCareOfflineDB';
const DB_VERSION = 1;
const STORE_NAME = 'offline_bookings';

function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
            }
        };
        request.onsuccess = (event) => resolve(event.target.result);
        request.onerror = (event) => reject(event.target.error);
    });
}

async function saveOfflineBooking(bookingData) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const request = transaction.objectStore(STORE_NAME).add(bookingData);
        request.onsuccess = () => resolve(true);
        request.onerror = () => reject(request.error);
    });
}

async function getOfflineBookings() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readonly');
        const request = transaction.objectStore(STORE_NAME).getAll();
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
    });
}

async function deleteOfflineBooking(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, 'readwrite');
        const request = transaction.objectStore(STORE_NAME).delete(id);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}

async function registerBookingSync() {
    if (!('serviceWorker' in navigator)) return false;

    const registration = await navigator.serviceWorker.ready;
    if ('sync' in registration) {
        await registration.sync.register('sync-offline-bookings');
        return true;
    }

    return false;
}

async function syncOfflineBookings() {
    if (!navigator.onLine) return;

    const offlineBookings = await getOfflineBookings();
    if (offlineBookings.length === 0) return;

    for (const booking of offlineBookings) {
        try {
            const formData = new FormData();
            Object.entries(booking).forEach(([key, value]) => {
                if (key !== 'id') formData.append(key, value);
            });

            const response = await fetch('/book', {
                method: 'POST',
                body: formData,
                credentials: 'include',
                headers: {
                    'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content
                }
            });

            if (response.ok || response.redirected || response.status === 400) {
                await deleteOfflineBooking(booking.id);
            }
        } catch (err) {
            console.error('Sync failed for booking:', booking, err);
        }
    }
}

window.addEventListener('online', async () => {
    const registered = await registerBookingSync().catch(() => false);
    if (!registered) {
        syncOfflineBookings();
    }
});

const bookingForm = document.getElementById('bookingForm');
if (bookingForm) {
    bookingForm.addEventListener('submit', async (event) => {
        if (navigator.onLine) return;

        event.preventDefault();
        const formData = new FormData(bookingForm);
        const bookingData = {};
        formData.forEach((value, key) => {
            bookingData[key] = value;
        });

        try {
            await saveOfflineBooking(bookingData);
            await registerBookingSync().catch(() => false);
            alert('You are offline. Your booking was saved on this device and will sync when the connection returns.');
            window.location.href = '/dashboard';
        } catch (err) {
            alert('Failed to save booking offline. Please try again before closing the app.');
        }
    });
}

if (navigator.onLine) {
    syncOfflineBookings();
}

// ===================== PWA INSTALLATION =====================
let deferredPrompt = null;

function showPwaInstallInstructions() {
    // Remove existing if any
    document.getElementById('pwa-install-modal')?.remove();

    const ua = navigator.userAgent.toLowerCase();
    const isiOS = /iphone|ipad|ipod/.test(ua);
    const isAndroid = /android/.test(ua);

    let instructionsHtml = '';
    if (isiOS) {
        instructionsHtml = `
            <div class="pwa-instruction-step">
                <span class="step-icon">📤</span>
                <p>Tap the <strong>Share</strong> button in the Safari toolbar (at the bottom or top of your screen).</p>
            </div>
            <div class="pwa-instruction-step">
                <span class="step-icon">➕</span>
                <p>Scroll down the options list and select <strong>Add to Home Screen</strong>.</p>
            </div>
            <div class="pwa-instruction-step">
                <span class="step-icon">✨</span>
                <p>Tap <strong>Add</strong> in the top-right corner to complete the installation.</p>
            </div>
        `;
    } else if (isAndroid) {
        instructionsHtml = `
            <div class="pwa-instruction-step">
                <span class="step-icon">⋮</span>
                <p>Tap the menu icon (three dots) in the top-right corner of Chrome/Edge.</p>
            </div>
            <div class="pwa-instruction-step">
                <span class="step-icon">📲</span>
                <p>Select <strong>Install app</strong> or <strong>Add to Home screen</strong> from the list.</p>
            </div>
        `;
    } else {
        instructionsHtml = `
            <div class="pwa-instruction-step">
                <span class="step-icon">💻</span>
                <p>Click the <strong>Install Icon</strong> (desktop monitor with down arrow) on the right side of your browser's address bar.</p>
            </div>
            <div class="pwa-instruction-step">
                <span class="step-icon">⚙️</span>
                <p>Or open the browser menu (⋮ or •••) and select <strong>Save and share</strong> -> <strong>Install VetSync</strong>.</p>
            </div>
        `;
    }

    const modal = document.createElement('div');
    modal.id = 'pwa-install-modal';
    modal.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(8px);
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    modal.innerHTML = `
        <div class="pwa-modal-card" style="
            background: white;
            padding: 30px;
            border-radius: 20px;
            max-width: 480px;
            width: 100%;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            border: 1.5px solid #dde8ff;
            position: relative;
            transform: translateY(20px);
            transition: transform 0.3s ease;
        ">
            <button onclick="document.getElementById('pwa-install-modal').style.opacity = '0'; setTimeout(() => document.getElementById('pwa-install-modal').remove(), 300)" style="
                position: absolute;
                top: 16px;
                right: 16px;
                background: #f1f5f9;
                border: none;
                font-size: 18px;
                cursor: pointer;
                color: #64748b;
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            ">✕</button>
            <div style="text-align: center; margin-bottom: 24px;">
                <span style="font-size: 3rem;">🐾</span>
                <h3 style="color: #1a3c8f; font-family: 'Nunito', sans-serif; font-size: 1.5rem; font-weight: 800; margin: 12px 0 6px;">Install VetSync App</h3>
                <p style="color: #64748b; font-size: 0.88rem; margin: 0;">Add VetSync to your home screen or desktop for a fast, full-screen offline experience.</p>
            </div>
            <div style="display: flex; flex-direction: column; gap: 16px; margin-bottom: 24px;">
                ${instructionsHtml}
            </div>
            <button onclick="document.getElementById('pwa-install-modal').style.opacity = '0'; setTimeout(() => document.getElementById('pwa-install-modal').remove(), 300)" style="
                width: 100%;
                padding: 13px;
                background: #1a3c8f;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 700;
                font-size: 0.95rem;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(26,60,143,0.2);
            ">Got it, thanks!</button>
        </div>
    `;

    document.body.appendChild(modal);

    if (!document.getElementById('pwa-modal-styles')) {
        const style = document.createElement('style');
        style.id = 'pwa-modal-styles';
        style.innerHTML = `
            .pwa-instruction-step {
                display: flex;
                align-items: center;
                gap: 16px;
                background: #f8fafc;
                padding: 12px 16px;
                border-radius: 12px;
                border: 1.5px solid #dde8ff;
                text-align: left;
            }
            .pwa-instruction-step .step-icon {
                font-size: 1.5rem;
                flex-shrink: 0;
            }
            .pwa-instruction-step p {
                margin: 0;
                color: #334155;
                font-size: 0.88rem;
                line-height: 1.4;
            }
        `;
        document.head.appendChild(style);
    }

    setTimeout(() => {
        modal.style.opacity = '1';
        modal.querySelector('.pwa-modal-card').style.transform = 'translateY(0)';
    }, 50);
}

function initPwaButtons() {
    const buttons = [
        document.getElementById('pwaInstallBtn'),
        document.getElementById('pwa-install-btn')
    ].filter(Boolean);

    if (buttons.length === 0) return;

    // If already installed as a PWA — hide all install buttons
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
    if (isStandalone) {
        buttons.forEach(btn => btn.style.display = 'none');
        return;
    }

    // Always make install buttons visible (EC2 or any deployment)
    buttons.forEach(btn => {
        btn.style.display = 'inline-flex';
        btn.style.animation = 'fadeInUp 0.6s ease forwards';

        // Clone to remove any old listeners, then wire fresh click handler
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);

        newBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (deferredPrompt) {
                // Native browser install prompt available — use it
                try {
                    deferredPrompt.prompt();
                    const { outcome } = await deferredPrompt.userChoice;
                    console.log(`[PWA] Install outcome: ${outcome}`);
                    if (outcome === 'accepted') {
                        document.querySelectorAll('#pwaInstallBtn, #pwa-install-btn').forEach(b => b.style.display = 'none');
                        deferredPrompt = null;
                    }
                } catch (err) {
                    console.warn('[PWA] Prompt error, falling back to instructions:', err);
                    showPwaInstallInstructions();
                }
            } else {
                // EC2 / HTTP / browser that doesn't fire beforeinstallprompt
                // — always show the manual guide so users can still install
                showPwaInstallInstructions();
            }
        });
    });
}

// Capture the native install prompt when the browser fires it
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('[PWA] beforeinstallprompt captured');
    initPwaButtons();
});

// Run on load — shows button immediately even if no native prompt yet
window.addEventListener('load', () => {
    initPwaButtons();
});

window.addEventListener('appinstalled', () => {
    console.log('[PWA] Installed successfully!');
    document.querySelectorAll('#pwaInstallBtn, #pwa-install-btn').forEach(btn => btn.style.display = 'none');
    deferredPrompt = null;
});

// Helper for animations if not already present
if (!document.getElementById('pwa-anim-styles')) {
    const style = document.createElement('style');
    style.id = 'pwa-anim-styles';
    style.innerHTML = `
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(style);
}

// ===================== FORM DOUBLE-SUBMISSION PREVENTION =====================
document.addEventListener('submit', (event) => {
    const form = event.target;
    if (event.defaultPrevented) return;

    if (form.dataset.submitted === 'true') {
        event.preventDefault();
        return;
    }

    form.dataset.submitted = 'true';
    const buttons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
    buttons.forEach((btn) => {
        btn.disabled = true;
        if (btn.tagName === 'BUTTON') {
            btn.dataset.originalText = btn.innerHTML;
            btn.innerHTML = '⏳ Processing...';
        }
    });
});
