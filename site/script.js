import { translations } from './translations.js';

// API base URL comes from config.js (window.APP_CONFIG), which auto-detects
// local vs production. Falls back to localhost only if config.js failed to load.
const API_BASE_URL = (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) || 'http://localhost:8000';

// Which candidate site this is (config.js). Used to fetch only this site's jobs
// via /jobs?site=<key>. Empty/missing → fetch all (safe fallback).
const SITE_KEY = (window.APP_CONFIG && window.APP_CONFIG.SITE_KEY) || '';

// State
let currentLang = localStorage.getItem('lang') || 'ua';
let currentTheme = localStorage.getItem('theme') || 'light';
let user = (() => { try { return JSON.parse(localStorage.getItem('user')) || null; } catch { return null; } })();
let authToken = localStorage.getItem('candidate_token') || '';   // candidate JWT (Bearer)
let cookieConsent = localStorage.getItem('cookie-consent') === 'true';

let jobsData = [];
let categoriesData = [];   // admin-managed categories: [{id, label:{ua,cz,en}}]
let comments = [];

let activeFilter = 'All';
let gdprAgreed = false; // FIX: module-scope so resetJobForm() can properly reset it

// FIX: escHtml was used across the module (reviews, auth) but never defined —
// a latent ReferenceError. Single HTML-escaping helper for all dynamic content.
function escHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initLanguage();
    initModals();
    initApplyForm();
    initMobileMenu();
    fetchCategories();   // loads categories → builds filter buttons + re-renders jobs
    fetchJobs();
    fetchReviews();
    initCounters();
    initCookieConsent();
    updateAuthUI();
    validateSession();  // verify a stored candidate JWT + refresh profile (autofill source)
    initGoogleAuth();   // no-op until GIS loads; window.onGoogleLibraryLoad re-runs it
    lucide.createIcons();
});

async function fetchJobs() {
    // Jobs are fully API-driven now (no hardcoded fallback). The admin panel
    // manages them via the FastAPI /jobs endpoints.
    try {
        const url = `${API_BASE_URL}/jobs${SITE_KEY ? `?site=${encodeURIComponent(SITE_KEY)}` : ''}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Failed to fetch jobs (HTTP ${response.status})`);
        jobsData = await response.json();
    } catch (err) {
        console.warn('Could not load jobs from API:', err);
        jobsData = [];
    } finally {
        window.__candidateJobs = jobsData;   // expose for the AI widget (classic script)
        renderJobs();
        updateProfessions();   // keep the apply-form vacancy picker in sync with active jobs
        openJobFromHash();     // deep-link from Google Jobs (#job-<id>) → open that vacancy
    }
}

// Admin-managed categories drive the filter buttons + each job's category caption.
async function fetchCategories() {
    try {
        const response = await fetch(`${API_BASE_URL}/categories`);
        if (!response.ok) throw new Error(`Failed to fetch categories (HTTP ${response.status})`);
        categoriesData = await response.json();
    } catch (err) {
        console.warn('Could not load categories from API:', err);
        categoriesData = [];
    } finally {
        initJobFilters();
        renderJobs();
    }
}

// Localized category caption for a job's `type` (category id). Falls back to the raw id.
function categoryLabelFor(typeId) {
    const c = categoriesData.find(c => c.id === typeId);
    if (c && c.label) return c.label[currentLang] || c.label.en || typeId;
    return typeId || '';
}

async function fetchReviews() {
    try {
        const url = `${API_BASE_URL}/reviews${SITE_KEY ? `?site=${encodeURIComponent(SITE_KEY)}` : ''}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch reviews');
        comments = await response.json();
    } catch (err) {
        // No fake/seed reviews: on failure show the real (empty) state rather than
        // fabricated testimonials on a public production page.
        console.warn('Reviews API unavailable:', err);
        comments = [];
    } finally {
        renderReviews();
    }
}

// Translation Logic
function initLanguage() {
    updateLanguage(currentLang);
    
    // Lang selectors
    document.querySelectorAll('[data-lang]').forEach(el => {
        el.addEventListener('click', () => {
            const lang = el.getAttribute('data-lang');
            setLanguage(lang);
        });
    });
}

function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('lang', lang);
    document.documentElement.lang = lang;
    updateLanguage(lang);
    initJobFilters();   // re-render filter buttons in the new language
    renderJobs();
    renderReviews();
    renderBranches();
    renderLegalInfo();
    updateProfessions();

    // Update active class on selectors
    document.querySelectorAll('[data-lang]').forEach(el => {
        if (el.getAttribute('data-lang') === lang) {
            el.classList.remove('opacity-60');
            el.classList.add('text-primary', 'dark:text-accent', 'font-bold');
        } else {
            el.classList.add('opacity-60');
            el.classList.remove('text-primary', 'dark:text-accent', 'font-bold');
        }
    });

    // Mobile nav lang
    document.querySelectorAll('#lang-selector-mobile button').forEach(el => {
        if (el.getAttribute('data-lang') === lang) {
            el.classList.add('text-primary', 'dark:text-accent');
            el.classList.remove('text-slate-600', 'dark:text-slate-500');
        } else {
            el.classList.remove('text-primary', 'dark:text-accent');
            el.classList.add('text-slate-600', 'dark:text-slate-500');
        }
    });
}

function updateLanguage(lang) {
    const t = translations[lang];
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const path = el.getAttribute('data-i18n');
        const keys = path.split('.');
        let value = t;
        keys.forEach(key => {
            value = value ? value[key] : null;
        });
        if (value) {
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = value;
            } else {
                el.textContent = value;
            }
        }
    });
}

// Theme Logic
function initTheme() {
    if (localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
        currentTheme = 'dark';
    } else {
        document.documentElement.classList.remove('dark');
        currentTheme = 'light';
    }

    document.getElementById('theme-toggle').addEventListener('click', () => {
        if (document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
            currentTheme = 'light';
        } else {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            currentTheme = 'dark';
        }
    });
}

// Mobile Menu
function initMobileMenu() {
    const btn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');
    btn.addEventListener('click', () => {
        menu.classList.toggle('hidden');
    });
    menu.querySelectorAll('a, button').forEach(el => {
        el.addEventListener('click', () => menu.classList.add('hidden'));
    });
}

// Modals
function initModals() {
    const authModal = document.getElementById('auth-modal');
    const jobModal = document.getElementById('job-modal');

    // NOTE: btn-login-header clicks are handled via delegated listener on #auth-status-desktop (see updateAuthUI section)

    document.querySelectorAll('.btn-job-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!cookieConsent) {
                alert(translations[currentLang].cookies.required);
                return;
            }
            // Submitting an application requires a signed-in candidate account:
            // prompt sign-in (Google or email/password) first.
            if (!authToken) {
                openModal(authModal);
                showAuthError(translations[currentLang].auth.loginRequired);
                return;
            }
            openModal(jobModal);
            resetJobForm();
            // Prefill from the signed-in candidate's profile (Google or email account).
            if (user) {
                const nameEl = document.getElementById('apply-name');
                const emailEl = document.getElementById('apply-email');
                if (nameEl && user.displayName && user.displayName !== 'User') nameEl.value = user.displayName;
                if (emailEl && user.email) emailEl.value = user.email;
            }
        });
    });

    document.querySelectorAll('.modal-close, .modal-overlay').forEach(el => {
        el.addEventListener('click', (e) => {
            if (el.classList.contains('modal-overlay') && e.target !== el) return;
            closeAllModals();
        });
    });

    // ── Auth: Google (official GIS button, rendered by initGoogleAuth) + email/password ──

    // Tab toggle (login / register)
    document.querySelectorAll('#auth-tabs [data-auth-tab]').forEach(tabBtn => {
        tabBtn.addEventListener('click', () => switchAuthTab(tabBtn.dataset.authTab));
    });
    document.getElementById('login-form')?.addEventListener('submit', handleEmailLogin);
    document.getElementById('register-form')?.addEventListener('submit', handleRegister);

    // Job Form Handler — delegated to initApplyForm()

    // GDPR Checkbox
    const gdprContainer = document.getElementById('gdpr-checkbox-container');
    const gdprBox = document.getElementById('gdpr-checkbox');
    const submitBtn = document.getElementById('btn-submit-apply');

    gdprContainer.addEventListener('click', () => {
        setGdprState(!gdprAgreed);
    });

}

// ── Apply Form ────────────────────────────────────────────────────────────────
function flashFieldError(fieldId) {
    const el = document.getElementById(fieldId);
    if (!el) return;
    el.classList.add('ring-2', '!ring-red-400', '!border-red-400');
    el.focus();
    setTimeout(() => el.classList.remove('ring-2', '!ring-red-400', '!border-red-400'), 2000);
}

function initApplyForm() {
    const form = document.getElementById('job-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const t = translations[currentLang].apply;
        const btn = document.getElementById('btn-submit-apply');

        // ── Field values ───────────────────────────────────────────────────────
        const nameVal      = (document.getElementById('apply-name')?.value || '').trim();
        const emailVal     = (document.getElementById('apply-email')?.value || '').trim();
        const phoneBody    = (document.getElementById('apply-phone')?.value || '').replace(/\s/g, '');
        const prefix       = document.getElementById('phone-prefix')?.value || '+380';
        const professionVal= document.getElementById('apply-profession')?.value || '';
        const commentVal   = (document.getElementById('apply-comment')?.value || '').trim();

        // ── Client-side validation ─────────────────────────────────────────────
        if (!nameVal || nameVal.length < 2) {
            flashFieldError('apply-name');
            return;
        }
        const digitsOnly = phoneBody.replace(/\D/g, '');
        if (!phoneBody || digitsOnly.length < 7) {
            flashFieldError('apply-phone');
            return;
        }
        if (!professionVal) {
            flashFieldError('apply-profession-search');
            return;
        }

        // ── Lock button — swap text for animated Lucide spinner ────────────────
        btn.disabled = true;
        btn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 inline animate-spin"></i>';
        lucide.createIcons();

        const payload = {
            name:       nameVal,
            email:      emailVal || null,
            phone:      prefix + phoneBody,
            profession: professionVal || null,
            comment:    commentVal   || null,
            lang:       currentLang,   // localizes the email/Telegram status notifications
        };

        try {
            // The application is only "submitted" once the backend confirms it saved.
            // A network failure or non-2xx response must surface as an error — never a
            // fake success (which would make the candidate think they applied when no
            // record exists).
            const response = await fetch(`${API_BASE_URL}/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                const errBody = await response.json().catch(() => ({}));
                throw new Error(`API ${response.status}: ${JSON.stringify(errBody)}`);
            }

            // ── Success path (server confirmed the save) ────────────────────────
            form.reset();
            setGdprState(false); // resets gdprAgreed + disables button
            document.getElementById('job-step-1').classList.add('hidden');
            document.getElementById('job-success').classList.remove('hidden');
            lucide.createIcons();

        } catch (err) {
            console.error('Application submission error:', err);
            // Show error inline rather than blocking alert
            const errMsg = document.createElement('p');
            errMsg.className = 'text-red-500 text-xs font-bold text-center mt-3 animate-fade-in';
            errMsg.textContent = t.error || 'Something went wrong. Please try again.';
            btn.insertAdjacentElement('afterend', errMsg);
            setTimeout(() => errMsg.remove(), 4000);
        } finally {
            // Restore button text; disabled state is managed by setGdprState()
            btn.innerHTML = `<span data-i18n="apply.submit">${translations[currentLang].apply.submit}</span>`;
            btn.disabled = !gdprAgreed;
            lucide.createIcons();
        }
    });
}

function openModal(el) {
    el.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeAllModals() {
    document.querySelectorAll('#auth-modal, #job-modal, #job-details-modal').forEach(el => el.classList.add('hidden'));
    document.body.style.overflow = 'auto';
}

function resetJobForm() {
    document.getElementById('job-step-1').classList.remove('hidden');
    document.getElementById('job-success').classList.add('hidden');
    document.getElementById('job-form').reset();
    // FIX: reset both the visual state AND the module-level gdprAgreed variable
    setGdprState(false);
}

// FIX: single source of truth for GDPR checkbox state + button appearance
// Uses querySelector('i, svg') because lucide.createIcons() replaces <i> tags
// with <svg> elements — querySelector('i') alone returns null after that and throws.
// Button enabled/disabled visual is handled by CSS in style.css (no class juggling).
function setGdprState(agreed) {
    gdprAgreed = agreed;
    const gdprBox = document.getElementById('gdpr-checkbox');
    const submitBtn = document.getElementById('btn-submit-apply');
    if (!gdprBox || !submitBtn) return;

    const icon = gdprBox.querySelector('i, svg');

    // Drive the filled state via inline styles, not Tailwind classes: the box carries
    // `dark:bg-slate-900`, which (in dark mode) overrides a `bg-accent` class and left
    // the checkbox looking empty. Inline styles beat any class, so the tick shows in
    // both light and dark themes.
    if (agreed) {
        gdprBox.style.backgroundColor = 'var(--accent)';
        gdprBox.style.borderColor = 'var(--accent)';
        if (icon) icon.classList.remove('hidden');
    } else {
        gdprBox.style.backgroundColor = '';
        gdprBox.style.borderColor = '';
        if (icon) icon.classList.add('hidden');
    }

    submitBtn.disabled = !agreed;
}

function logout() {
    user = null;
    authToken = '';
    localStorage.removeItem('user');
    localStorage.removeItem('candidate_token');
    if (window.google?.accounts?.id) google.accounts.id.disableAutoSelect();
    updateAuthUI();
    renderReviews();
}

// Persist a successful auth (JWT + profile) and refresh UI.
function setSession(token, fullName, email) {
    authToken = token || '';
    user = { displayName: fullName || email || 'User', email: email || '' };
    localStorage.setItem('candidate_token', authToken);
    localStorage.setItem('user', JSON.stringify(user));
    closeAllModals();
    updateAuthUI();
    renderReviews();
}

function showAuthError(msg) {
    const el = document.getElementById('auth-error');
    if (!el) { alert(msg); return; }
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 5000);
}

// On load: if we hold a candidate JWT, verify it against the backend (/auth/me) and
// refresh the profile from the DB. An expired/invalid token clears the session.
async function validateSession() {
    if (!authToken) return;
    try {
        const res = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` },
        });
        if (res.status === 401) { logout(); return; }
        if (!res.ok) return; // transient server error: keep the cached session
        const d = await res.json();
        user = { displayName: d.full_name || d.email || 'User', email: d.email || '' };
        localStorage.setItem('user', JSON.stringify(user));
        updateAuthUI();
        renderReviews();
    } catch (err) {
        console.warn('Session validation skipped (offline):', err);
    }
}

function switchAuthTab(tab) {
    document.querySelectorAll('#auth-tabs [data-auth-tab]').forEach(b => {
        const on = b.dataset.authTab === tab;
        b.classList.toggle('bg-primary', on);
        b.classList.toggle('dark:bg-accent', on);
        b.classList.toggle('text-white', on);
        b.classList.toggle('dark:text-slate-900', on);
        b.classList.toggle('glass', !on);
        b.classList.toggle('text-slate-600', !on);
    });
    document.getElementById('login-form')?.classList.toggle('hidden', tab !== 'login');
    document.getElementById('register-form')?.classList.toggle('hidden', tab !== 'register');
    document.getElementById('auth-error')?.classList.add('hidden');
}

// ── Email/password login ───────────────────────────────────────────────────────
async function handleEmailLogin(e) {
    e.preventDefault();
    // Consent gate: creating a session writes a token to localStorage, so block
    // login (like apply/reviews/Google) until cookies are accepted.
    if (!cookieConsent) { showAuthError(translations[currentLang].cookies.required); return; }
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-pass').value;
    if (!email || !password) return;
    try {
        const res = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        if (res.status === 401) { showAuthError('Incorrect email or password.'); return; }
        if (res.status === 429) { showAuthError('Too many attempts. Try again shortly.'); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const d = await res.json();
        setSession(d.access_token, d.full_name, d.email);
    } catch (err) {
        console.error('Login error:', err);
        showAuthError('Server unavailable. Please try again.');
    }
}

// ── Registration (18+ enforced both client- and server-side) ───────────────────
async function handleRegister(e) {
    e.preventDefault();
    // Same consent gate as login — no registration before cookies are accepted.
    if (!cookieConsent) { showAuthError(translations[currentLang].cookies.required); return; }
    const full_name = document.getElementById('reg-name').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-pass').value;
    const birthdate = document.getElementById('reg-birth').value; // "YYYY-MM-DD"
    if (!full_name || !email || !password || !birthdate) { showAuthError('Please fill in all fields.'); return; }
    if (password.length < 6) { showAuthError('Password must be at least 6 characters.'); return; }
    if (computeAge(birthdate) < 18) { showAuthError('Registration is allowed from age 18.'); return; }
    try {
        const res = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name, email, password, birthdate }),
        });
        if (res.status === 400) { showAuthError('Registration is allowed from age 18.'); return; }
        if (res.status === 409) { showAuthError('This email is already registered.'); return; }
        if (res.status === 429) { showAuthError('Too many attempts. Try again shortly.'); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const d = await res.json();
        setSession(d.access_token, d.full_name, d.email);
    } catch (err) {
        console.error('Register error:', err);
        showAuthError('Server unavailable. Please try again.');
    }
}

function computeAge(isoDate) {
    const b = new Date(isoDate);
    if (isNaN(b.getTime())) return 0;
    const t = new Date();
    let age = t.getFullYear() - b.getFullYear();
    if (t.getMonth() < b.getMonth() || (t.getMonth() === b.getMonth() && t.getDate() < b.getDate())) age--;
    return age;
}

// ── Google Identity Services (server-verified) ─────────────────────────────────
function googleClientId() {
    const id = window.APP_CONFIG && window.APP_CONFIG.GOOGLE_CLIENT_ID;
    return (id && !id.startsWith('YOUR_GOOGLE_CLIENT_ID')) ? id : null;
}

// GIS gives us an ID token; we send it to the backend, which verifies it with
// Google and returns our own candidate JWT. We never trust the token client-side.
async function handleGoogleCredential(response) {
    if (!cookieConsent) { alert(translations[currentLang].cookies.required); return; }
    try {
        const res = await fetch(`${API_BASE_URL}/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_token: response.credential }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const d = await res.json();
        setSession(d.access_token, d.full_name, d.email);
    } catch (err) {
        console.error('Google login error:', err);
        showAuthError('Google sign-in failed. Please try again.');
    }
}

function initGoogleAuth() {
    const clientId = googleClientId();
    if (!clientId || !window.google?.accounts?.id) return;
    google.accounts.id.initialize({ client_id: clientId, callback: handleGoogleCredential, auto_select: false });
    const container = document.getElementById('google-signin-btn');
    if (container) {
        container.innerHTML = '';
        google.accounts.id.renderButton(container, { theme: 'outline', size: 'large', text: 'signin_with', shape: 'pill', width: 280 });
    }
}
window.onGoogleLibraryLoad = initGoogleAuth;

function updateAuthUI() {
    const desktop = document.getElementById('auth-status-desktop');
    if (user) {
        const firstName = (user.displayName || user.email || '').split(' ')[0];
        desktop.innerHTML = `
            <div class="flex items-center gap-3 border-l border-slate-200 dark:border-slate-800 pl-6">
               <span class="text-slate-600 dark:text-slate-400 capitalize font-bold">Hi, ${escHtml(firstName)}</span>
               <button data-action="my-apps" title="${escHtml(translations[currentLang].myapps.button)}" class="text-primary dark:text-accent hover:text-accent transition-colors cursor-pointer">
                 <i data-lucide="clipboard-list" class="w-3.5 h-3.5"></i>
               </button>
               <button data-action="logout" class="text-primary dark:text-accent hover:text-red-500 transition-colors cursor-pointer">
                 <i data-lucide="log-out" class="w-3.5 h-3.5"></i>
               </button>
             </div>
        `;
    } else {
        desktop.innerHTML = `
            <button data-action="open-auth" class="flex items-center gap-1.5 text-primary dark:text-accent hover:text-accent transition-colors border-l border-slate-200 dark:border-slate-800 pl-6 cursor-pointer">
                <i data-lucide="log-in" class="w-3 h-3"></i>
                <span data-i18n="auth.login">${translations[currentLang].auth.login}</span>
            </button>
        `;
    }
    lucide.createIcons();
}

// FIX: single delegated listener on the container — survives innerHTML re-renders
document.getElementById('auth-status-desktop').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    if (btn.dataset.action === 'logout') logout();
    if (btn.dataset.action === 'open-auth') openModal(document.getElementById('auth-modal'));
    if (btn.dataset.action === 'my-apps') openMyApplications();
});

// ── Job alerts: email subscribe ───────────────────────────────────────────────
(function initSubscribe() {
    const form = document.getElementById('subscribe-form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('subscribe-email');
        const msg = document.getElementById('subscribe-msg');
        const t = translations[currentLang].alerts;
        const email = (input.value || '').trim();
        if (!email) return;
        msg.classList.remove('hidden');
        try {
            const res = await fetch(`${API_BASE_URL}/subscribe`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, site: SITE_KEY, lang: currentLang }),
            });
            msg.textContent = res.ok ? t.success : t.error;
            msg.className = 'text-sm mt-3 font-bold ' + (res.ok ? 'text-green-600 dark:text-green-400' : 'text-red-500');
            if (res.ok) input.value = '';
        } catch (err) {
            msg.textContent = t.error;
            msg.className = 'text-sm mt-3 font-bold text-red-500';
        }
    });
})();

// ── "My applications": logged-in candidate's submissions + their status ────────
async function openMyApplications() {
    const t = translations[currentLang];
    let modal = document.getElementById('myapps-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'myapps-modal';
        modal.className = 'fixed inset-0 z-[1000] flex items-center justify-center p-4 hidden';
        modal.innerHTML =
            '<div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" data-close></div>' +
            '<div class="relative w-full max-w-lg max-h-[80vh] overflow-hidden rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col">' +
              '<div class="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-800">' +
                '<h3 class="font-black uppercase tracking-tight text-primary dark:text-white" data-myapps="title"></h3>' +
                '<button data-close class="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"><i data-lucide="x" class="w-4 h-4"></i></button>' +
              '</div>' +
              '<div data-myapps="body" class="p-5 overflow-y-auto space-y-3 text-sm"></div>' +
            '</div>';
        document.body.appendChild(modal);
        modal.querySelectorAll('[data-close]').forEach((el) =>
            el.addEventListener('click', () => { modal.classList.add('hidden'); modal.classList.remove('flex'); })
        );
    }
    modal.querySelector('[data-myapps="title"]').textContent = t.myapps.title;
    const body = modal.querySelector('[data-myapps="body"]');
    body.innerHTML = '<div class="text-center text-slate-400 py-10"><i data-lucide="loader-2" class="w-6 h-6 inline animate-spin"></i></div>';
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    lucide.createIcons();

    try {
        const res = await fetch(`${API_BASE_URL}/my-applications`, {
            headers: { 'Authorization': `Bearer ${authToken}` },
        });
        if (!res.ok) throw new Error('http ' + res.status);
        const data = await res.json();
        const apps = data.applications || [];
        if (!apps.length) {
            body.innerHTML = `<p class="text-center text-slate-400 py-10">${escHtml(t.myapps.empty)}</p>`;
            return;
        }
        const badge = {
            received:  'bg-blue-500/15 text-blue-600 dark:text-blue-400',
            reviewing: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
            processed: 'bg-green-500/15 text-green-600 dark:text-green-400',
        };
        body.innerHTML = apps.map((a) => {
            const st = a.status || 'received';
            let date = '';
            try { date = a.created_at ? new Date(String(a.created_at).replace(' ', 'T')).toLocaleDateString() : ''; } catch (e) {}
            return '<div class="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-800">' +
                `<div><div class="font-bold text-primary dark:text-white">${escHtml(a.profession || '—')}</div>` +
                `<div class="text-xs text-slate-400">${escHtml(date)}</div></div>` +
                `<span class="text-[10px] font-bold px-2.5 py-1 rounded-full ${badge[st] || badge.received}">${escHtml(t.myapps[st] || st)}</span>` +
            '</div>';
        }).join('');
    } catch (e) {
        body.innerHTML = `<p class="text-center text-red-500 py-10">${escHtml(t.myapps.error)}</p>`;
    }
}

// Jobs
function initJobFilters() {
    const container = document.getElementById('job-filters');
    if (!container) return;
    // "All" + the admin-managed categories (localized labels).
    const categories = [
        { id: 'All', label: { ua: 'Всі', cz: 'Vše', en: 'All' } },
        ...categoriesData.map(c => ({ id: c.id, label: c.label || {} })),
    ];

    container.innerHTML = categories.map(cat => `
        <button data-filter="${escHtml(cat.id)}" class="px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${activeFilter === cat.id ? 'bg-primary dark:bg-accent text-white dark:text-slate-900 shadow-lg' : 'glass-card border-none text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800'}">
            ${escHtml(cat.label[currentLang] || cat.label.en || cat.id)}
        </button>
    `).join('');

    container.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
            activeFilter = btn.getAttribute('data-filter');
            initJobFilters();
            renderJobs();
        });
    });
}

// Deep-link support: a Google Jobs result points at <site>/#job-<id>. When the
// page loads with such a hash (and the job exists), open its details modal.
function openJobFromHash() {
    const m = (location.hash || '').match(/^#job-(.+)$/);
    if (!m) return;
    const id = decodeURIComponent(m[1]);
    if (Array.isArray(jobsData) && jobsData.some(j => String(j.id) === String(id))) {
        openJobDetails(id);
    }
}

// ── Google for Jobs: JobPosting structured data (JSON-LD) ───────────────────
// Built in the browser from the jobs we already fetched — no extra backend call.
// Google executes JS and reads dynamically-injected JSON-LD, so this is enough to
// make our vacancies eligible for the Google Jobs rich result.
function injectJobPostingsLD() {
    const prev = document.getElementById('jobposting-ld');
    if (prev) prev.remove();
    if (!Array.isArray(jobsData) || !jobsData.length) return;

    const cfg = window.APP_CONFIG || {};
    const brand = cfg.BRAND || document.title || 'Konstanta';
    const siteUrl = (cfg.SITE_URL || location.origin).replace(/\/$/, '');
    const logoUrl = cfg.LOGO_URL || '';

    const toISO = (s) => {
        if (!s) return undefined;
        const d = new Date(String(s).replace(' ', 'T'));
        return isNaN(d.getTime()) ? undefined : d.toISOString();
    };
    const plusDays = (iso, n) => {
        const d = iso ? new Date(iso) : new Date();
        d.setDate(d.getDate() + n);
        return d.toISOString();
    };
    // Best-effort salary → MonetaryAmount (only when confidently numeric).
    const parseSalary = (s) => {
        if (!s) return undefined;
        const txt = String(s);
        const nums = (txt.match(/\d[\d\s.,]*/g) || [])
            .map(x => parseFloat(x.replace(/\s/g, '').replace(',', '.')))
            .filter(n => !isNaN(n) && n > 0);
        if (!nums.length) return undefined;
        const unit = /hod|год|hour|\/\s*h\b/i.test(txt) ? 'HOUR'
                   : /měs|mes|month|міс/i.test(txt) ? 'MONTH'
                   : undefined;
        const currency = /eur|€/i.test(txt) ? 'EUR' : 'CZK';
        const value = nums.length >= 2
            ? { '@type': 'QuantitativeValue', minValue: Math.min(...nums), maxValue: Math.max(...nums) }
            : { '@type': 'QuantitativeValue', value: nums[0] };
        if (unit) value.unitText = unit;
        return { '@type': 'MonetaryAmount', currency, value };
    };

    const lang = currentLang;
    const postings = jobsData.map((job) => {
        const title = (job.title && (job.title[lang] || job.title.cz || job.title.en || job.title.ua)) || '';
        if (!title) return null;
        const cityNames = (Array.isArray(job.cities) && job.cities.length)
            ? job.cities.map(c => c && c.name).filter(Boolean)
            : (job.location ? [job.location] : []);
        const datePosted = toISO(job.created_at) || new Date().toISOString();
        const desc = (job.description && job.description.trim())
            ? job.description
            : `${title}${cityNames.length ? ' — ' + cityNames.join(', ') : ''}${job.salary ? '. ' + job.salary : ''}`;
        const jobLocation = cityNames.length
            ? cityNames.map(name => ({ '@type': 'Place', address: { '@type': 'PostalAddress', addressLocality: name, addressCountry: 'CZ' } }))
            : [{ '@type': 'Place', address: { '@type': 'PostalAddress', addressCountry: 'CZ' } }];

        const org = { '@type': 'Organization', name: brand, sameAs: siteUrl };
        if (logoUrl) org.logo = logoUrl;

        const posting = {
            '@context': 'https://schema.org/',
            '@type': 'JobPosting',
            title,
            description: desc,
            datePosted,
            validThrough: plusDays(datePosted, 60),
            employmentType: 'FULL_TIME',
            hiringOrganization: org,
            jobLocation,
            identifier: { '@type': 'PropertyValue', name: brand, value: String(job.id) },
            url: `${siteUrl}/#job-${encodeURIComponent(job.id)}`,
            directApply: true,
        };
        const salary = parseSalary(job.salary);
        if (salary) posting.baseSalary = salary;
        if (job.image_url) posting.image = job.image_url;
        return posting;
    }).filter(Boolean);

    if (!postings.length) return;
    const el = document.createElement('script');
    el.type = 'application/ld+json';
    el.id = 'jobposting-ld';
    el.textContent = JSON.stringify(postings);
    document.head.appendChild(el);
}

function renderJobs() {
    injectJobPostingsLD();
    const container = document.getElementById('job-container');
    const t = translations[currentLang];

    // Filter by `type` — the field that drives the filter buttons.
    // (`category` kept as a fallback for any legacy records.)
    const filtered = activeFilter === 'All'
        ? jobsData
        : jobsData.filter(j => (j.type || j.category) === activeFilter);

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="col-span-full glass border border-dashed border-slate-300 dark:border-slate-700 p-12 rounded-2xl text-center text-slate-500 font-bold transition-colors">
                ${t.jobs.empty}
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map((job) => {
        const title = (job.title && (job.title[currentLang] || job.title.en)) || '';
        const type  = categoryLabelFor(job.type || job.category);
        const cities = Array.isArray(job.cities) ? job.cities : [];
        const citiesHtml = cities.length
            ? `<div class="mt-1 space-y-1">${cities.map(c => `
                <div class="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 transition-colors">
                    <i data-lucide="map-pin" class="w-3.5 h-3.5 text-accent"></i>
                    <span class="text-sm font-semibold">${escHtml(c.name || '')}</span>
                    <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-full ${c.housing ? 'bg-green-500/15 text-green-600 dark:text-green-400' : 'bg-slate-400/15 text-slate-500 dark:text-slate-400'}">${c.housing ? '🏠 ' + escHtml(t.jobs.housing) : escHtml(t.jobs.noHousing)}</span>
                </div>`).join('')}</div>`
            : `<div class="flex items-center gap-1 text-slate-500 dark:text-slate-400 mt-1 transition-colors">
                    <i data-lucide="map-pin" class="w-3.5 h-3.5 text-accent"></i>
                    <span class="text-sm font-semibold">${escHtml(job.location || '')}</span>
                </div>`;
        const salaryHtml = job.salary ? `
                <div class="flex items-center gap-2 mt-4 text-primary dark:text-accent font-bold">
                    <i data-lucide="banknote" class="w-4 h-4 text-accent"></i>
                    <span class="text-sm">${escHtml(job.salary)}</span>
                </div>` : '';
        const descHtml = job.description ? `
                <p class="text-sm text-slate-600 dark:text-slate-400 mt-4 leading-relaxed line-clamp-3 transition-colors">${escHtml(job.description)}</p>` : '';
        const imageHtml = job.image_url ? `
                <img src="${escHtml(job.image_url)}" alt="${escHtml(title)}" loading="lazy" class="w-full h-44 object-cover">` : '';
        return `
        <div class="glass-card overflow-hidden group cursor-pointer border-slate-200 dark:border-slate-800" data-job-id="${escHtml(String(job.id ?? ''))}">
            ${imageHtml}
            <div class="p-6">
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <div class="text-[10px] font-black text-accent uppercase tracking-[0.2em] mb-1">${escHtml(type)}</div>
                        <h3 class="text-xl font-bold text-primary dark:text-white group-hover:text-accent transition-colors">
                            ${escHtml(title)}
                        </h3>
                        ${citiesHtml}
                    </div>
                    <button class="text-slate-400 dark:text-slate-500 hover:text-accent transition-colors p-2 glass rounded-lg group-hover:bg-accent/10">
                        <i data-lucide="external-link" class="w-5 h-5"></i>
                    </button>
                </div>
                ${salaryHtml}
                ${descHtml}

                <div class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 flex justify-between items-center text-[10px] uppercase font-black tracking-widest text-slate-500 dark:text-slate-400 transition-colors">
                    <span class="flex items-center gap-1.5">
                        ${job.new ? '<div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>' : ''}
                        <span data-i18n="jobs.new">${t.jobs.new}</span>
                    </span>
                </div>
            </div>
        </div>`;
    }).join('');

    // Click a card (or its top-right button) → open the full-details modal.
    container.querySelectorAll('[data-job-id]').forEach(card => {
        card.addEventListener('click', () => openJobDetails(card.dataset.jobId));
    });

    lucide.createIcons();
}

// Full vacancy info in a modal (the card shows a truncated preview).
function openJobDetails(jobId) {
    const job = jobsData.find(j => String(j.id) === String(jobId));
    if (!job) return;
    const t = translations[currentLang];
    const el = document.getElementById('job-details-content');
    if (!el) return;

    const title = (job.title && (job.title[currentLang] || job.title.en)) || '';
    const cat   = categoryLabelFor(job.type || job.category);
    const cities = Array.isArray(job.cities) ? job.cities : [];
    const citiesHtml = cities.length
        ? `<div class="space-y-1.5 mb-5">${cities.map(c => `
            <div class="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                <i data-lucide="map-pin" class="w-4 h-4 text-accent"></i>
                <span class="text-sm font-semibold">${escHtml(c.name || '')}</span>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${c.housing ? 'bg-green-500/15 text-green-600 dark:text-green-400' : 'bg-slate-400/15 text-slate-500 dark:text-slate-400'}">${c.housing ? '🏠 ' + escHtml(t.jobs.housing) : escHtml(t.jobs.noHousing)}</span>
            </div>`).join('')}</div>`
        : (job.location ? `<div class="flex items-center gap-2 text-slate-600 dark:text-slate-300 mb-5">
                <i data-lucide="map-pin" class="w-4 h-4 text-accent"></i>
                <span class="text-sm font-semibold">${escHtml(job.location)}</span>
            </div>` : '');
    const imageHtml = job.image_url
        ? `<img src="${escHtml(job.image_url)}" alt="${escHtml(title)}" class="w-full h-56 object-cover">` : '';
    const salaryHtml = job.salary
        ? `<div class="flex items-center gap-2 mb-5 text-primary dark:text-accent font-bold">
                <i data-lucide="banknote" class="w-5 h-5 text-accent"></i>
                <span>${escHtml(job.salary)}</span>
            </div>` : '';
    const descHtml = job.description
        ? `<p class="text-sm text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">${escHtml(job.description)}</p>` : '';

    el.innerHTML = `
        ${imageHtml}
        <div class="p-8 sm:p-10">
            <div class="text-[10px] font-black text-accent uppercase tracking-[0.2em] mb-1">${escHtml(cat)}</div>
            <h2 class="text-2xl font-black text-primary dark:text-white mb-4 transition-colors">${escHtml(title)}</h2>
            ${citiesHtml}
            ${salaryHtml}
            ${descHtml}
            <button id="details-apply-btn" class="mt-8 w-full bg-primary dark:bg-accent text-white dark:text-slate-900 py-4 rounded-xl font-bold uppercase tracking-widest text-xs hover:opacity-90 transition-all shadow-lg active:scale-95">
                ${escHtml(t.apply.submit)}
            </button>
        </div>`;

    // Apply button: close details, then trigger the existing apply flow (cookie/auth checks).
    el.querySelector('#details-apply-btn')?.addEventListener('click', () => {
        closeAllModals();
        document.querySelector('.btn-job-modal')?.click();
    });

    openModal(document.getElementById('job-details-modal'));
    lucide.createIcons();
}

// Reviews
function renderReviews() {
    const container = document.getElementById('reviews-container');
    const formContainer = document.getElementById('review-form-container');
    const t = translations[currentLang];

    if (comments.length === 0) {
        container.innerHTML = `
            <div class="glass border border-dashed border-slate-300 dark:border-slate-700 p-12 rounded-2xl text-center text-slate-500 font-bold">
                 ${t.reviews.noReviews}
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="columns-1 md:columns-2 gap-6 space-y-6">
                ${comments.map(review => `
                    <div class="break-inside-avoid glass-card p-6 relative overflow-hidden group text-left border-slate-200 dark:border-slate-800 animate-fade-in-up">
                        <div class="flex items-center gap-3 mb-4">
                            <div class="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center text-accent font-bold">
                                ${(review.userName?.[0] || '?').toUpperCase()}
                            </div>
                            <div>
                                <div class="font-bold text-primary dark:text-white text-sm transition-colors">${escHtml(review.userName)}</div>
                                <div class="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-black tracking-widest transition-colors">
                                    ${new Date(review.createdAt).toLocaleDateString()}
                                </div>
                            </div>
                        </div>
                        <p class="text-slate-700 dark:text-slate-300 text-sm leading-relaxed font-medium transition-colors">"${escHtml(review.text)}"</p>
                    </div>
                `).join('')}
            </div>
        `;
    }

    if (user) {
        formContainer.innerHTML = `
            <form id="review-form" class="space-y-4 text-left">
                <div>
                    <input type="text" disabled value="${escHtml(user.displayName || user.email)}" class="w-full glass border border-slate-300 dark:border-slate-800 rounded-lg px-4 py-2.5 text-sm text-slate-600 dark:text-slate-400 font-bold">
                </div>
                <textarea required id="review-text" placeholder="${cookieConsent ? t.reviews.textPlaceholder : t.cookies.required}" rows="4" class="w-full glass border border-slate-300 dark:border-slate-800 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 transition-all shadow-inner text-slate-900 dark:text-white font-medium ${!cookieConsent ? 'opacity-50 cursor-not-allowed' : ''}"></textarea>
                <button type="submit" id="btn-submit-review" class="w-full bg-primary dark:bg-accent text-white dark:text-slate-900 py-3 rounded-xl font-bold uppercase tracking-widest text-xs hover:bg-slate-800 dark:hover:bg-accent-light disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-lg active:scale-95">
                    <i data-lucide="send" class="w-3.5 h-3.5"></i> <span data-i18n="reviews.submit">${t.reviews.submit}</span>
                </button>
            </form>
        `;
        document.getElementById('review-form').addEventListener('submit', handleReviewSubmit);
    } else {
        formContainer.innerHTML = `
            <div class="text-center py-6">
                <p class="text-slate-500 dark:text-slate-400 text-sm mb-6 transition-colors">${t.reviews.loginRequired}</p>
                <button id="btn-review-login" class="bg-primary dark:bg-accent text-white dark:text-slate-900 px-8 py-3 rounded-full text-xs font-bold uppercase tracking-widest hover:bg-slate-800 dark:hover:bg-accent-light transition-all shadow-lg active:scale-95">
                    ${t.auth.login}
                </button>
            </div>
        `;
        // FIX(W6): #btn-login-header is destroyed by updateAuthUI() on load, so the old
        // inline onclick threw on null. Open the auth modal directly instead.
        document.getElementById('btn-review-login')?.addEventListener('click', () => {
            openModal(document.getElementById('auth-modal'));
        });
    }
    lucide.createIcons();
}

async function handleReviewSubmit(e) {
    e.preventDefault();
    if (!cookieConsent) return;
    const textEl = document.getElementById('review-text');
    const text = textEl.value.trim();
    if (!text) return;

    const btn = document.getElementById('btn-submit-review');
    btn.disabled = true;
    btn.innerText = '...';

    try {
        const payload = {
            userName: user.displayName || user.email,
            text,
            createdAt: new Date().toISOString(),
            site: SITE_KEY,
        };

        const reviewHeaders = { 'Content-Type': 'application/json' };
        if (authToken) reviewHeaders['Authorization'] = `Bearer ${authToken}`;
        const response = await fetch(`${API_BASE_URL}/reviews`, {
            method: 'POST',
            headers: reviewHeaders,
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(`API error ${response.status}`);

        // Re-fetch from the server so the list reflects what was actually persisted
        // (and picks up the server-assigned id). No optimistic local insert — a failed
        // save must not leave a "ghost" review that vanishes on the next reload.
        textEl.value = '';
        await fetchReviews();
    } catch (err) {
        console.error('Review submit failed:', err);
        const t = translations[currentLang];
        const formEl = document.getElementById('review-form');
        const errMsg = document.createElement('p');
        errMsg.className = 'text-red-500 text-xs font-bold text-center mt-2';
        errMsg.textContent = (t.reviews && t.reviews.error) || 'Could not submit your review. Please try again.';
        formEl?.appendChild(errMsg);
        setTimeout(() => errMsg.remove(), 4000);
    } finally {
        btn.disabled = false;
        lucide.createIcons();
    }
}

// Branches & Legal Info
function renderBranches() {
    const list = document.getElementById('branch-list');
    const t = translations[currentLang];
    const locs = ["Praha", "Brno", "Ostrava", "Plzeň", "Liberec"];
    const branchText = currentLang === 'ua' ? 'Філія' : currentLang === 'cz' ? 'Pobočka' : 'Branch';
    
    document.getElementById('branch-map-title').innerText = t.contact.branchMap;

    list.innerHTML = locs.map(loc => `
        <div class="flex items-center gap-2 text-slate-700 dark:text-slate-300 text-xs font-bold uppercase transition-colors">
            <i data-lucide="chevron-right" class="w-3.5 h-3.5 text-accent"></i> <span>${branchText}: ${loc}</span>
        </div>
    `).join('');
    lucide.createIcons();
}

function renderLegalInfo() {
    const container = document.getElementById('legal-info');
    const t = translations[currentLang];
    container.innerHTML = `
        <p class="font-bold text-slate-200 uppercase tracking-widest text-[10px] mb-2">${t.legal.title}</p>
        <p>${t.legal.address}</p>
        <p>${t.legal.ico} | ${t.legal.dic}</p>
        <p class="italic opacity-80">${t.legal.reg}</p>
    `;
}

function updateProfessions() {
    const search = document.getElementById('apply-profession-search');
    const hidden = document.getElementById('apply-profession');
    const list = document.getElementById('apply-profession-list');
    if (!search || !hidden || !list) return;
    const t = translations[currentLang];
    search.placeholder = t.apply.select;

    // Options = the currently active vacancies (title in the current language), de-duplicated.
    const titles = [...new Set(
        jobsData
            .map(j => ((j.title && (j.title[currentLang] || j.title.en)) || '').trim())
            .filter(Boolean)
    )];

    // Drop a previously picked value that is no longer among the active vacancies.
    if (hidden.value && !titles.includes(hidden.value)) {
        hidden.value = '';
        search.value = '';
    }

    const render = (filter) => {
        const f = (filter || '').trim().toLowerCase();
        const matches = titles.filter(x => x.toLowerCase().includes(f));
        list.innerHTML = matches.length
            ? matches.map(x => `<li data-value="${escHtml(x)}" class="px-4 py-2.5 cursor-pointer text-sm text-slate-700 dark:text-slate-200 hover:bg-accent/10">${escHtml(x)}</li>`).join('')
            : `<li class="px-4 py-2.5 text-sm text-slate-400">${t.jobs.empty}</li>`;
    };

    // Re-bind cleanly (runs again on language change / jobs reload): assignment, not
    // addEventListener, so handlers never stack up.
    search.oninput = () => { hidden.value = ''; render(search.value); list.classList.remove('hidden'); };
    search.onfocus = () => { render(''); list.classList.remove('hidden'); };
    search.onblur  = () => setTimeout(() => list.classList.add('hidden'), 150); // let an option click land first
    list.onmousedown = (e) => {
        const li = e.target.closest('li[data-value]');
        if (!li) return;
        e.preventDefault();                  // keep focus; stops blur from racing the click
        hidden.value = li.dataset.value;
        search.value = li.dataset.value;
        list.classList.add('hidden');
    };

    render('');
}

// Stats Animation
function initCounters() {
    const numbers = document.querySelectorAll('.animated-number');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = parseInt(entry.target.getAttribute('data-value'));
                animateValue(entry.target, 0, target, 2000);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    numbers.forEach(num => observer.observe(num));
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Cookie Consent
function initCookieConsent() {
    if (!cookieConsent) {
        document.getElementById('cookie-consent').classList.remove('hidden');
    }

    document.getElementById('btn-cookie-accept').addEventListener('click', () => {
        cookieConsent = true;
        localStorage.setItem('cookie-consent', 'true');
        document.getElementById('cookie-consent').classList.add('hidden');
        renderReviews(); // Re-render to update inputs
    });

    document.getElementById('btn-cookie-decline').addEventListener('click', () => {
        document.getElementById('cookie-consent').classList.add('hidden');
    });
}

// Mocking initial content
renderBranches();
renderLegalInfo();
updateProfessions();
