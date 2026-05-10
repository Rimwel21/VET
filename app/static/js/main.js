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
