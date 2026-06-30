/* ═══════════════════════════════════════════════════════════════════════════
   KONSTANTA CRM — admin.js
   Full Kanban Manager Panel with WebSocket real-time sync
════════════════════════════════════════════════════════════════════════════ */

'use strict';

// API/WS URLs come from config.js (window.APP_CONFIG), which auto-detects local
// vs production. Falls back to localhost only if config.js failed to load.
const API_BASE  = (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) || 'http://localhost:8000';
const WS_URL    = (window.APP_CONFIG && window.APP_CONFIG.WS_URL) || 'ws://localhost:8000/ws/managers';
const WS_RECONNECT_DELAY_MS     = 5000;   // base reconnect delay
const WS_RECONNECT_MAX_DELAY_MS = 60000;  // cap for exponential backoff

// Shared inner-HTML for the "Take to Work" button — used by createTicketCard,
// handleTakeToWork's error restore, and resetTakeWorkButtons (single source of truth).
const TAKE_WORK_BTN_HTML = `
    <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 8 16 12 12 16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
    Take to Work
`;

const COMPLETE_BTN_HTML = `
    <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
    Виконати
`;

// Job categories are now admin-managed (loaded from GET /categories into
// `categoriesList`) instead of a hardcoded list. See fetchCategories().

// Candidate sites a job can be published on. `key` must match the backend KNOWN_SITES
// and each site's config.js SITE_KEY; `label` is what admins see. An empty selection
// in the DB means "everywhere" (legacy jobs), but the form requires at least one.
const JOB_SITES = [
    { key: 'konstanta', label: 'Konstanta' },
    { key: 'robota',    label: 'Чехія Робота' },
];

// ── Runtime state ────────────────────────────────────────────────────────────
let managerName    = '';          // staff username (from the login JWT)
let staffRole      = '';          // 'admin' | 'worker' — gates the Jobs tab
let authToken      = '';          // staff JWT; sent as Authorization: Bearer.
                                  // Held in memory + sessionStorage (cleared on logout / tab close).
let ws             = null;        // WebSocket instance
let wsReconnectTimer = null;      // setTimeout handle for reconnect loop
let wsReconnectDelay = WS_RECONNECT_DELAY_MS; // current backoff delay (grows on repeated failures)
let wsIntentionalClose = false;   // prevents reconnect on deliberate logout

// In-memory card registry: application_id (number) → HTMLElement
const cardRegistry = new Map();

// ── DOM refs (populated after DOMContentLoaded) ──────────────────────────────
let loginOverlay, dashboard;
let loginNameInput, loginPasswordInput, loginError, loginErrorText, btnLogin;
let adminHeader, clockEl, connectionBadge, connectionLabel, connectionDot;
let managerDisplayName, managerAvatar;
let btnLogout, btnRefresh, syncIndicator;
let totalCountEl;
let colNew, colProcessing, colCompleted;
let countNew, countProcessing, countCompleted;
let toastContainer;

// Tabs + Jobs Management refs
let tabBtns, tabApplications, tabJobs, tabCategories;
let jobsListEl, jobsTotalCountEl, btnAddJob;
let jobModalOverlay, jobModalTitle, jobForm, jobFormError, btnJobSave;
let jobIdInput, jobTitleUa, jobTitleCz, jobTitleEn, jobType, jobSalary, jobDescription, jobIsNew, jobImage;
let jobSiteKonstanta, jobSiteRobota;
let jobCitiesEl, btnAddCity;

// Categories management refs
let categoriesListEl, categoriesTotalCountEl, btnAddCategory;
let categoryModalOverlay, categoryModalTitle, categoryForm, categoryFormError, btnCategorySave;
let categoryIdInput, catLabelUa, catLabelCz, catLabelEn;

// ════════════════════════════════════════════════════════════════════════════
// BOOT
// ════════════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    bindDomRefs();
    lucide.createIcons();
    startClock();
    checkAuth();

    btnLogin.addEventListener('click', handleLogin);
    btnLogout.addEventListener('click', handleLogout);
    btnRefresh.addEventListener('click', () => syncDatabase(true));

    // Allow Enter key in login form
    [loginNameInput, loginPasswordInput].forEach(el => {
        el.addEventListener('keydown', e => { if (e.key === 'Enter') handleLogin(); });
    });

    // Tabs
    tabBtns.forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));

    // Jobs management
    btnAddJob.addEventListener('click', () => openJobModal(null));
    jobForm.addEventListener('submit', handleJobSubmit);
    btnAddCity.addEventListener('click', () => addCityRow());
    document.getElementById('job-modal-close').addEventListener('click', closeJobModal);
    document.getElementById('job-cancel').addEventListener('click', closeJobModal);
    jobModalOverlay.addEventListener('click', e => { if (e.target === jobModalOverlay) closeJobModal(); });

    // Categories management
    btnAddCategory.addEventListener('click', () => openCategoryModal(null));
    categoryForm.addEventListener('submit', handleCategorySubmit);
    document.getElementById('category-modal-close').addEventListener('click', closeCategoryModal);
    document.getElementById('category-cancel').addEventListener('click', closeCategoryModal);
    categoryModalOverlay.addEventListener('click', e => { if (e.target === categoryModalOverlay) closeCategoryModal(); });

    document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        if (!jobModalOverlay.classList.contains('hidden')) closeJobModal();
        if (!categoryModalOverlay.classList.contains('hidden')) closeCategoryModal();
    });
});

function bindDomRefs() {
    loginOverlay        = document.getElementById('login-overlay');
    dashboard           = document.getElementById('dashboard');
    loginNameInput      = document.getElementById('login-name');
    loginPasswordInput  = document.getElementById('login-password');
    loginError          = document.getElementById('login-error');
    loginErrorText      = document.getElementById('login-error-text');
    btnLogin            = document.getElementById('btn-login');
    clockEl             = document.getElementById('clock');
    connectionBadge     = document.getElementById('connection-badge');
    connectionLabel     = document.getElementById('connection-label');
    connectionDot       = connectionBadge.querySelector('.connection-dot');
    managerDisplayName  = document.getElementById('manager-display-name');
    managerAvatar       = document.getElementById('manager-avatar');
    btnLogout           = document.getElementById('btn-logout');
    btnRefresh          = document.getElementById('btn-refresh');
    syncIndicator       = document.getElementById('sync-indicator');
    totalCountEl        = document.getElementById('total-count');
    colNew              = document.getElementById('col-new');
    colProcessing       = document.getElementById('col-processing');
    colCompleted        = document.getElementById('col-completed');
    countNew            = document.getElementById('count-new');
    countProcessing     = document.getElementById('count-processing');
    countCompleted      = document.getElementById('count-completed');
    toastContainer      = document.getElementById('toast-container');

    // Tabs
    tabBtns             = document.querySelectorAll('.tab-btn');
    tabApplications     = document.getElementById('tab-applications');
    tabJobs             = document.getElementById('tab-jobs');
    tabCategories       = document.getElementById('tab-categories');

    // Jobs management
    jobsListEl          = document.getElementById('jobs-list');
    jobsTotalCountEl    = document.getElementById('jobs-total-count');
    btnAddJob           = document.getElementById('btn-add-job');
    jobModalOverlay     = document.getElementById('job-modal-overlay');
    jobModalTitle       = document.getElementById('job-modal-title');
    jobForm             = document.getElementById('job-form');
    jobFormError        = document.getElementById('job-form-error');
    btnJobSave          = document.getElementById('job-save');
    jobIdInput          = document.getElementById('job-id');
    jobTitleUa          = document.getElementById('job-title-ua');
    jobTitleCz          = document.getElementById('job-title-cz');
    jobTitleEn          = document.getElementById('job-title-en');
    jobType             = document.getElementById('job-type');
    jobSalary           = document.getElementById('job-salary');
    jobDescription      = document.getElementById('job-description');
    jobIsNew            = document.getElementById('job-is-new');
    jobImage            = document.getElementById('job-image');
    jobSiteKonstanta    = document.getElementById('job-site-konstanta');
    jobSiteRobota       = document.getElementById('job-site-robota');
    jobCitiesEl         = document.getElementById('job-cities');
    btnAddCity          = document.getElementById('btn-add-city');

    // Categories management
    categoriesListEl    = document.getElementById('categories-list');
    categoriesTotalCountEl = document.getElementById('categories-total-count');
    btnAddCategory      = document.getElementById('btn-add-category');
    categoryModalOverlay = document.getElementById('category-modal-overlay');
    categoryModalTitle  = document.getElementById('category-modal-title');
    categoryForm        = document.getElementById('category-form');
    categoryFormError   = document.getElementById('category-form-error');
    btnCategorySave     = document.getElementById('category-save');
    categoryIdInput     = document.getElementById('category-id');
    catLabelUa          = document.getElementById('category-label-ua');
    catLabelCz          = document.getElementById('category-label-cz');
    catLabelEn          = document.getElementById('category-label-en');
}

// Map site key → its checkbox element (single source for read/write of placement).
function siteCheckbox(key) {
    return key === 'konstanta' ? jobSiteKonstanta
         : key === 'robota'    ? jobSiteRobota
         : null;
}

// ════════════════════════════════════════════════════════════════════════════
// AUTH
// ════════════════════════════════════════════════════════════════════════════
function checkAuth() {
    // The staff JWT + identity live in sessionStorage (cleared when the tab closes),
    // so a staff member re-authenticates once per browser session.
    const savedToken = sessionStorage.getItem('crm_token');
    const savedName  = sessionStorage.getItem('crm_username');
    const savedRole  = sessionStorage.getItem('crm_role');
    if (savedToken && savedName) {
        authToken   = savedToken;
        managerName = savedName;
        staffRole   = savedRole || 'worker';
        bootDashboard();
    } else {
        loginOverlay.style.display = 'flex';
        dashboard.classList.add('hidden');
        // Convenience: prefill the last-used username (non-secret) without auto-login.
        const lastName = localStorage.getItem('crm_last_username');
        if (lastName && loginNameInput) loginNameInput.value = lastName;
    }
}

async function handleLogin() {
    const username = loginNameInput.value.trim();
    const pass = loginPasswordInput.value;

    loginError.style.display = 'none';

    if (!username || username.length < 3) {
        showLoginError('Please enter your username (min 3 characters).');
        loginNameInput.focus();
        return;
    }
    if (!pass) {
        showLoginError('Please enter the password.');
        loginPasswordInput.focus();
        return;
    }

    // Authenticate against the backend; on success we receive a staff JWT + role.
    btnLogin.disabled = true;
    let result;
    try {
        const res = await fetch(`${API_BASE}/auth/staff/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password: pass }),
        });
        if (res.status === 200) {
            result = { ok: true, data: await res.json() };
        } else if (res.status === 401) {
            result = { ok: false, kind: 'bad' };
        } else if (res.status === 429) {
            result = { ok: false, kind: 'ratelimited' };
        } else {
            result = { ok: false, kind: 'error' };
        }
    } catch (err) {
        console.error('Login failed:', err);
        result = { ok: false, kind: 'unreachable' };
    } finally {
        btnLogin.disabled = false;
    }

    if (!result.ok) {
        if (result.kind === 'bad') {
            showLoginError('Incorrect username or password. Please try again.');
            loginPasswordInput.value = '';
            loginPasswordInput.focus();
            loginPasswordInput.classList.add('ring-2');
            loginPasswordInput.style.borderColor = 'rgba(239,68,68,0.6)';
            setTimeout(() => {
                loginPasswordInput.classList.remove('ring-2');
                loginPasswordInput.style.borderColor = '';
            }, 2000);
        } else if (result.kind === 'ratelimited') {
            showLoginError('Too many attempts. Please wait a minute and try again.');
        } else {
            showLoginError('Server unreachable. Check your connection and try again.');
        }
        return;
    }

    authToken   = result.data.access_token;
    managerName = result.data.username || username;
    staffRole   = result.data.role || 'worker';
    sessionStorage.setItem('crm_token', authToken);
    sessionStorage.setItem('crm_username', managerName);
    sessionStorage.setItem('crm_role', staffRole);
    localStorage.setItem('crm_last_username', managerName); // non-secret convenience prefill
    loginPasswordInput.value = '';
    bootDashboard();
}

function showLoginError(msg) {
    loginErrorText.textContent = msg;
    loginError.style.display = 'block';
    lucide.createIcons();
}

function handleLogout() {
    wsIntentionalClose = true;
    if (ws) { ws.close(); ws = null; }
    if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null; }
    sessionStorage.removeItem('crm_token');
    sessionStorage.removeItem('crm_username');
    sessionStorage.removeItem('crm_role');
    authToken = '';
    managerName = '';
    staffRole = '';
    cardRegistry.clear();
    clearColumns();
    dashboard.classList.add('hidden');
    loginOverlay.style.display = 'flex';
    loginNameInput.value = '';
    loginPasswordInput.value = '';
    loginError.style.display = 'none';
    setConnectionStatus('disconnected');
}

// ════════════════════════════════════════════════════════════════════════════
// DASHBOARD BOOT
// ════════════════════════════════════════════════════════════════════════════
function bootDashboard() {
    loginOverlay.style.display = 'none';
    dashboard.classList.remove('hidden');

    // Update header UI
    managerDisplayName.textContent = managerName;
    managerAvatar.textContent = (managerName[0] || '?').toUpperCase();

    // Role-based UI: only admins manage vacancies. Hide the Jobs tab for workers
    // and force the Applications tab if a worker somehow lands on Jobs.
    applyRoleVisibility();

    lucide.createIcons();

    wsIntentionalClose = false;
    syncDatabase(false);
    initWebSocket();

    // Categories drive the job-type dropdown + the website filters; load them once
    // on boot so the job modal's category <select> is populated (admins only).
    if (isAdmin()) fetchCategories();
}

function isAdmin() {
    return staffRole === 'admin';
}

function applyRoleVisibility() {
    // The Jobs/Categories tabs are admin-only; hide them for workers.
    document.querySelectorAll('.tab-btn[data-tab="jobs"], .tab-btn[data-tab="categories"]').forEach(btn => {
        btn.classList.toggle('hidden', !isAdmin());
    });
    if (!isAdmin()) switchTab('applications');
}

// ════════════════════════════════════════════════════════════════════════════
// CLOCK
// ════════════════════════════════════════════════════════════════════════════
function startClock() {
    function tick() {
        const now = new Date();
        const h = String(now.getHours()).padStart(2, '0');
        const m = String(now.getMinutes()).padStart(2, '0');
        const s = String(now.getSeconds()).padStart(2, '0');
        if (clockEl) clockEl.textContent = `${h}:${m}:${s}`;
    }
    tick();
    setInterval(tick, 1000);
}

// ════════════════════════════════════════════════════════════════════════════
// DATABASE SYNC (GET /sync-db)
// ════════════════════════════════════════════════════════════════════════════
async function syncDatabase(showToast = false) {
    syncIndicator.classList.remove('hidden');
    lucide.createIcons();

    try {
        // Page through the bounded /sync-db endpoint until a short page ends it,
        // so the panel shows every application (not just the newest page).
        const PAGE_SIZE = 500;
        const applications = [];
        for (let offset = 0; ; offset += PAGE_SIZE) {
            const res = await fetch(`${API_BASE}/sync-db?limit=${PAGE_SIZE}&offset=${offset}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
            if (res.status === 401) { handleAuthExpired(); return; }
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const page = await res.json();
            applications.push(...page);
            if (page.length < PAGE_SIZE) break;
        }

        clearColumns();
        cardRegistry.clear();

        // Sort oldest-first so newest lands on top after prepending
        const sorted = [...applications].sort((a, b) => {
            const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
            const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
            return ta - tb;
        });

        sorted.forEach(app => renderTicketToColumn(app, false));
        updateCounts();

        if (showToast) showToast_('Database synced successfully.', 'success');
    } catch (err) {
        console.error('syncDatabase error:', err);
        if (showToast) showToast_(`Sync failed: ${err.message}`, 'error');
    } finally {
        syncIndicator.classList.add('hidden');
    }
}

function clearColumns() {
    [colNew, colProcessing, colCompleted].forEach(col => {
        col.innerHTML = '';
        renderEmptyState(col, col.id);
    });
    updateCounts();
}

function renderEmptyState(columnEl, colId) {
    if (columnEl.querySelector('.ticket-card')) return; // has cards, skip
    const icons = { 'col-new': '📋', 'col-processing': '⚙️', 'col-completed': '✅' };
    const msgs  = { 'col-new': 'No new applications', 'col-processing': 'Nothing in progress', 'col-completed': 'No completed applications' };
    const existing = columnEl.querySelector('.column-empty');
    if (!existing) {
        const el = document.createElement('div');
        el.className = 'column-empty';
        el.innerHTML = `<div class="column-empty-icon">${icons[colId] || '📭'}</div><span>${msgs[colId] || 'Empty'}</span>`;
        columnEl.appendChild(el);
    }
}

// ════════════════════════════════════════════════════════════════════════════
// TICKET CARD CREATION
// ════════════════════════════════════════════════════════════════════════════

/**
 * Build a ticket card DOM element from an application record.
 * @param {Object} app - application object from /sync-db or WS new_application event
 * @param {string|null} lockedBy - if set, renders locked badge instead of action button
 * @returns {HTMLElement}
 */
function createTicketCard(app, lockedBy = null) {
    const id          = app.id ?? app.application_id ?? '?';
    const name        = app.name || '—';
    const phone       = app.phone || '—';
    const email       = app.email || null;
    const profession  = app.profession || null;
    const comment     = app.comment || null;
    const platform    = (app.platform || 'website').toLowerCase();
    const rawTs       = app.created_at || app.timestamp || null;
    const timeStr     = rawTs ? formatTimestamp(rawTs) : '—';
    const isOwned     = lockedBy && lockedBy === managerName;
    const isTg        = platform === 'telegram';

    const card = document.createElement('div');
    card.className = `ticket-card${isOwned ? ' owned' : ''}`;
    card.dataset.id = String(id);

    card.innerHTML = `
        <div class="ticket-id"># ${escHtml(String(id))} &nbsp;·&nbsp; ${escHtml(platform.toUpperCase())}</div>
        <div class="ticket-name">${escHtml(name)}</div>

        <div class="ticket-meta">
            <div class="ticket-meta-row">
                <svg class="meta-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13.9 19.79 19.79 0 0 1 1.61 5.18a2 2 0 0 1 1.99-2.18h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 10.91a16 16 0 0 0 6.06 6.06l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                <a href="tel:${escHtml(phone)}">${escHtml(phone)}</a>
            </div>
            ${email ? `
            <div class="ticket-meta-row">
                <svg class="meta-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
                <a href="mailto:${escHtml(email)}">${escHtml(email)}</a>
            </div>` : ''}
            ${profession ? `
            <div class="ticket-meta-row">
                <svg class="meta-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="7" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                <span>${escHtml(profession)}</span>
            </div>` : ''}
        </div>

        ${comment ? `<div class="ticket-comment">"${escHtml(comment)}"</div>` : ''}

        <div class="ticket-footer">
            <span class="ticket-time">${timeStr}</span>
            <div class="flex items-center gap-2" style="display:flex;align-items:center;gap:0.5rem;">
                <span class="platform-badge ${isTg ? 'tg' : ''}">${isTg ? '✈ TG' : '🌐 WEB'}</span>
                <div class="ticket-actions"></div>
            </div>
        </div>
    `;

    const actionsEl = card.querySelector('.ticket-actions');
    const cardStatus = (app.status || (lockedBy ? 'processing' : 'new')).toLowerCase();

    if (cardStatus === 'completed') {
        // Done — no actions, just a finished badge.
        const done = document.createElement('div');
        done.className = 'locked-badge done';
        done.innerHTML = '✅ Виконано';
        actionsEl.appendChild(done);
    } else if (cardStatus === 'processing') {
        // Already claimed: show WHO has it. Never "Take to Work". "Виконати" appears
        // ONLY to the manager who claimed it (owner) — and the backend enforces the
        // same in SQL, so no one else (not even an admin) can close another's ticket.
        if (lockedBy) {
            const badge = document.createElement('div');
            badge.className = 'locked-badge';
            badge.innerHTML = `🔒 ${escHtml(lockedBy)}`;
            actionsEl.appendChild(badge);
        }
        if (isOwned) {
            const done = document.createElement('button');
            done.className = 'btn-complete';
            done.setAttribute('data-app-id', String(id));
            done.innerHTML = COMPLETE_BTN_HTML;
            done.addEventListener('click', () => handleComplete(done, Number(id)));
            actionsEl.appendChild(done);
        }
    } else {
        // NEW → "Take to Work"
        const btn = document.createElement('button');
        btn.className = 'btn-take-work';
        btn.setAttribute('data-app-id', String(id));
        btn.innerHTML = TAKE_WORK_BTN_HTML;
        btn.addEventListener('click', () => handleTakeToWork(btn, Number(id)));
        actionsEl.appendChild(btn);
    }

    return card;
}

/**
 * Route a card to the correct column based on application status.
 * @param {Object} app
 * @param {boolean} prepend - if true, insert at TOP (for live WS new cards)
 */
function renderTicketToColumn(app, prepend = true) {
    const status = (app.status || 'new').toLowerCase();
    const columnEl = status === 'processing' ? colProcessing
                   : status === 'completed'  ? colCompleted
                   : colNew;

    // Remove empty state placeholder
    const empty = columnEl.querySelector('.column-empty');
    if (empty) empty.remove();

    const lockedBy = status === 'processing' ? (app.manager_name || null) : null;
    const card = createTicketCard(app, lockedBy);
    cardRegistry.set(Number(app.id ?? app.application_id), card);

    if (prepend) {
        columnEl.insertBefore(card, columnEl.firstChild);
    } else {
        columnEl.appendChild(card);
    }
}

// ════════════════════════════════════════════════════════════════════════════
// COLUMN COUNTS
// ════════════════════════════════════════════════════════════════════════════
function updateCounts() {
    const nNew  = colNew.querySelectorAll('.ticket-card').length;
    const nProc = colProcessing.querySelectorAll('.ticket-card').length;
    const nDone = colCompleted.querySelectorAll('.ticket-card').length;
    countNew.textContent        = nNew;
    countProcessing.textContent = nProc;
    countCompleted.textContent  = nDone;
    totalCountEl.textContent    = nNew + nProc + nDone;

    // Ensure empty states are shown for empty columns
    [{ el: colNew, id: 'col-new' }, { el: colProcessing, id: 'col-processing' }, { el: colCompleted, id: 'col-completed' }]
        .forEach(({ el, id }) => {
            const cards = el.querySelectorAll('.ticket-card');
            if (cards.length === 0) renderEmptyState(el, id);
        });
}

// ════════════════════════════════════════════════════════════════════════════
// "TAKE TO WORK" ACTION
// ════════════════════════════════════════════════════════════════════════════
function handleTakeToWork(btn, appId) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast_('WebSocket is not connected. Reconnecting…', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `
        <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>
        Sending…
    `;

    try {
        ws.send(JSON.stringify({
            action:         'lock_ticket',
            application_id: appId,
            manager_name:   managerName,
        }));
    } catch (err) {
        console.error('WS send error:', err);
        showToast_('Failed to send lock command.', 'error');
        btn.disabled = false;
        btn.innerHTML = TAKE_WORK_BTN_HTML;
    }
}

// ════════════════════════════════════════════════════════════════════════════
// "ВИКОНАТИ" (COMPLETE) ACTION
// ════════════════════════════════════════════════════════════════════════════
function handleComplete(btn, appId) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast_('WebSocket is not connected. Reconnecting…', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `
        <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>
        …
    `;

    try {
        ws.send(JSON.stringify({ action: 'complete_ticket', application_id: appId }));
    } catch (err) {
        console.error('WS send error:', err);
        showToast_('Failed to send complete command.', 'error');
        btn.disabled = false;
        btn.innerHTML = COMPLETE_BTN_HTML;
    }
}

/**
 * Re-enable a "Take to Work" button stuck in the "Sending…" state after a
 * server REJECTION — the card must remain in place, so we only restore the button.
 * @param {number|string|null} appId - if given, reset only that ticket's button;
 *                                      otherwise (legacy errors) reset all stuck buttons.
 */
function resetTakeWorkButtons(appId = null) {
    const selector = (appId !== null && appId !== undefined)
        ? `.btn-take-work[disabled][data-app-id="${CSS.escape(String(appId))}"]`
        : '.btn-take-work[disabled]';
    document.querySelectorAll(selector).forEach(btn => {
        btn.disabled = false;
        btn.innerHTML = TAKE_WORK_BTN_HTML;
    });
}

// ════════════════════════════════════════════════════════════════════════════
// WEBSOCKET
// ════════════════════════════════════════════════════════════════════════════
function initWebSocket() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

    setConnectionStatus('reconnecting');

    try {
        ws = new WebSocket(WS_URL);
    } catch (err) {
        console.error('WebSocket constructor failed:', err);
        scheduleReconnect();
        return;
    }

    ws.addEventListener('open', () => {
        console.info('[WS] Connected to', WS_URL);
        // Auth handshake: the hub requires the first frame to carry the staff JWT.
        try {
            ws.send(JSON.stringify({ action: 'auth', token: authToken }));
        } catch (err) {
            console.error('[WS] Failed to send auth handshake:', err);
        }
        setConnectionStatus('connected');
        if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null; }
        wsReconnectDelay = WS_RECONNECT_DELAY_MS; // reset backoff after a successful connect
        showToast_('Real-time connection established.', 'success');
    });

    ws.addEventListener('message', e => {
        try {
            const msg = JSON.parse(e.data);
            handleWsMessage(msg);
        } catch (err) {
            console.warn('[WS] Non-JSON message received:', e.data);
        }
    });

    ws.addEventListener('close', e => {
        console.warn('[WS] Connection closed:', e.code, e.reason);
        ws = null;
        setConnectionStatus('disconnected');
        if (!wsIntentionalClose) {
            showToast_(`Connection lost. Reconnecting in ${Math.round(wsReconnectDelay / 1000)}s…`, 'warning');
            scheduleReconnect();
        }
    });

    ws.addEventListener('error', err => {
        console.error('[WS] Error:', err);
        // close event fires after error, so reconnect is handled there
    });
}

function scheduleReconnect() {
    if (wsReconnectTimer) return;
    const delay = wsReconnectDelay;
    wsReconnectTimer = setTimeout(() => {
        wsReconnectTimer = null;
        if (!wsIntentionalClose) initWebSocket();
    }, delay);
    // Exponential backoff (×1.5) capped at the max, so a down server isn't hammered.
    wsReconnectDelay = Math.min(Math.round(wsReconnectDelay * 1.5), WS_RECONNECT_MAX_DELAY_MS);
}

// ════════════════════════════════════════════════════════════════════════════
// WS EVENT HANDLERS
// ════════════════════════════════════════════════════════════════════════════
function handleWsMessage(msg) {
    // ── error (server rejection) ─────────────────────────────────────────────
    // Backend sends {action:'error', message}. Legacy {event:'error'} also handled.
    if (msg.action === 'error' || msg.event === 'error') {
        showToast_(msg.message || 'An error occurred.', 'error');
        // Re-enable only the rejected ticket's "Sending…" button (falls back to all
        // if the error carries no application_id). The rejected card stays in place.
        resetTakeWorkButtons(msg.application_id);
        return;
    }

    const event = msg.event;

    // ── new_application ───────────────────────────────────────────────────
    if (event === 'new_application') {
        const appId   = msg.application_id;
        const data    = msg.data   || {};
        const ts      = msg.timestamp || new Date().toISOString();

        const appObj = {
            id:         appId,
            name:       data.name       || '—',
            phone:      data.phone      || '—',
            email:      data.email      || null,
            profession: data.profession || null,
            comment:    data.comment    || null,
            platform:   data.platform   || 'website',
            status:     'new',
            created_at: ts,
        };

        // Remove any existing card with same id (safety guard)
        const existing = cardRegistry.get(Number(appId));
        if (existing) existing.remove();

        // Remove empty placeholder from NEW column
        const emptyEl = colNew.querySelector('.column-empty');
        if (emptyEl) emptyEl.remove();

        const card = createTicketCard(appObj, null);
        cardRegistry.set(Number(appId), card);
        colNew.insertBefore(card, colNew.firstChild);
        updateCounts();

        showToast_(`New application from ${appObj.name} (#${appId})`, 'info');
        return;
    }

    // ── ticket_locked ─────────────────────────────────────────────────────
    if (event === 'ticket_locked') {
        const appId    = Number(msg.application_id);
        const lockedBy = msg.manager_name || 'unknown';
        handleTicketLocked(appId, lockedBy);
        return;
    }

    // ── ticket_completed ──────────────────────────────────────────────────
    if (event === 'ticket_completed') {
        handleTicketCompleted(Number(msg.application_id));
        return;
    }

    console.debug('[WS] Unhandled event:', event);
}

function handleTicketLocked(appId, lockedBy) {
    const card = cardRegistry.get(appId);
    if (!card) {
        console.warn('ticket_locked: no card found for id', appId);
        return;
    }

    // FIX: compare the locking manager against the logged-in manager (was a
    // self-comparison `managerName === managerName` that was always true).
    const isOwned = lockedBy === managerName;

    // Remove card from registry immediately to prevent duplicate-animation race
    // If another ticket_locked event arrives within 260ms, cardRegistry.get(appId) will return null
    cardRegistry.delete(appId);

    // Animate out of NEW and into PROCESSING
    card.style.transition = 'opacity 0.25s, transform 0.25s';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.96)';

    setTimeout(() => {
        card.remove();

        // Rebuild card in locked state
        const appId_n = Number(appId);
        const existingData = extractCardData(card);

        const lockedCard = createTicketCard({ ...existingData, status: 'processing' }, lockedBy);
        if (isOwned) lockedCard.classList.add('owned');

        const emptyEl = colProcessing.querySelector('.column-empty');
        if (emptyEl) emptyEl.remove();

        lockedCard.style.opacity = '0';
        lockedCard.style.transform = 'translateY(-6px)';
        colProcessing.insertBefore(lockedCard, colProcessing.firstChild);
        cardRegistry.set(appId_n, lockedCard);

        // Animate in
        requestAnimationFrame(() => {
            lockedCard.style.transition = 'opacity 0.3s, transform 0.3s';
            lockedCard.style.opacity = '1';
            lockedCard.style.transform = 'translateY(0)';
        });

        updateCounts();

        const toastMsg = isOwned
            ? `You locked ticket #${appId}.`
            : `Ticket #${appId} locked by ${lockedBy}.`;
        showToast_(toastMsg, isOwned ? 'success' : 'warning');

    }, 260);
}

function handleTicketCompleted(appId) {
    const card = cardRegistry.get(appId);
    if (!card) { console.warn('ticket_completed: no card for id', appId); return; }

    const data = extractCardData(card);   // read fields before detaching the node
    cardRegistry.delete(appId);

    card.style.transition = 'opacity 0.25s, transform 0.25s';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.96)';

    setTimeout(() => {
        card.remove();
        const doneCard = createTicketCard({ ...data, status: 'completed' }, null);
        const emptyEl = colCompleted.querySelector('.column-empty');
        if (emptyEl) emptyEl.remove();

        doneCard.style.opacity = '0';
        doneCard.style.transform = 'translateY(-6px)';
        colCompleted.insertBefore(doneCard, colCompleted.firstChild);
        cardRegistry.set(Number(appId), doneCard);

        requestAnimationFrame(() => {
            doneCard.style.transition = 'opacity 0.3s, transform 0.3s';
            doneCard.style.opacity = '1';
            doneCard.style.transform = 'translateY(0)';
        });

        updateCounts();
        showToast_(`Заявку #${appId} завершено.`, 'success');
    }, 260);
}

/** Pull field values back out of a rendered card for re-render after move */
function extractCardData(card) {
    return {
        id:         card.dataset.id,
        name:       card.querySelector('.ticket-name')?.textContent?.trim() || '—',
        phone:      card.querySelector('a[href^="tel:"]')?.textContent || '—',
        email:      card.querySelector('a[href^="mailto:"]')?.textContent || null,
        profession: (() => {
            const rows = card.querySelectorAll('.ticket-meta-row');
            for (const row of rows) {
                const a = row.querySelector('a');
                if (!a) return row.querySelector('span')?.textContent || null;
            }
            return null;
        })(),
        comment:    card.querySelector('.ticket-comment')?.textContent?.replace(/^"|"$/g, '').trim() || null,
        platform:   card.querySelector('.platform-badge')?.textContent?.includes('TG') ? 'telegram' : 'website',
        created_at: card.querySelector('.ticket-time')?.textContent || null,
    };
}

// ════════════════════════════════════════════════════════════════════════════
// TABS
// ════════════════════════════════════════════════════════════════════════════
function switchTab(tab) {
    tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    tabApplications.classList.toggle('hidden', tab !== 'applications');
    tabJobs.classList.toggle('hidden', tab !== 'jobs');
    tabCategories.classList.toggle('hidden', tab !== 'categories');
    if (tab === 'jobs') fetchJobsList();
    if (tab === 'categories') fetchCategories();
    lucide.createIcons();
}

// ════════════════════════════════════════════════════════════════════════════
// JOBS MANAGEMENT (CRUD against FastAPI)
// ════════════════════════════════════════════════════════════════════════════
let jobsList = [];

function adminHeaders() {
    // Admin/worker write routes require the staff JWT issued at login.
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
    };
}

/** Called when the backend rejects the JWT (expired/invalid). Force re-login. */
function handleAuthExpired() {
    showToast_('Session expired — please log in again.', 'warning');
    handleLogout();
}

async function fetchJobsList() {
    try {
        const res = await fetch(`${API_BASE}/jobs`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        jobsList = await res.json();
    } catch (err) {
        console.error('fetchJobsList error:', err);
        showToast_(`Failed to load jobs: ${err.message}`, 'error');
        jobsList = [];
    }
    renderJobsList();
}

function renderJobsList() {
    if (!jobsListEl) return;
    if (jobsTotalCountEl) jobsTotalCountEl.textContent = jobsList.length;

    if (!jobsList.length) {
        jobsListEl.innerHTML = `<div class="jobs-empty">No job openings yet. Click "Add Job" to create the first one.</div>`;
        return;
    }

    jobsListEl.innerHTML = jobsList.map(job => {
        const title  = (job.title && (job.title.en || job.title.ua || job.title.cz)) || '—';
        const type   = categoryLabel(job.type || job.category);
        const loc    = job.location || '—';
        const salary = job.salary || '';
        const sitesArr = Array.isArray(job.sites) ? job.sites : [];
        const sitesLabel = sitesArr.length
            ? sitesArr.map(k => (JOB_SITES.find(s => s.key === k)?.label || k)).join(' · ')
            : 'Всі сайти';
        return `
        <div class="job-card">
            <div class="job-card-top">
                <span class="job-card-type">${escHtml(type)}</span>
                ${job.new ? '<span class="job-card-new">● New</span>' : ''}
            </div>
            <div class="job-card-title">${escHtml(title)}</div>
            <div class="job-card-sites">📍 ${escHtml(sitesLabel)}</div>
            <div class="job-card-meta">
                <div class="job-card-meta-row">
                    <i data-lucide="map-pin" class="meta-ic"></i><span>${escHtml(loc)}</span>
                </div>
                ${salary ? `<div class="job-card-meta-row"><i data-lucide="banknote" class="meta-ic"></i><span>${escHtml(salary)}</span></div>` : ''}
            </div>
            <div class="job-card-actions">
                <button class="job-btn edit" data-id="${escHtml(job.id)}"><i data-lucide="pencil" class="w-3 h-3"></i> Edit</button>
                <button class="job-btn delete" data-id="${escHtml(job.id)}"><i data-lucide="trash-2" class="w-3 h-3"></i> Delete</button>
            </div>
        </div>`;
    }).join('');

    jobsListEl.querySelectorAll('.job-btn.edit').forEach(btn =>
        btn.addEventListener('click', () => openJobModal(btn.dataset.id)));
    jobsListEl.querySelectorAll('.job-btn.delete').forEach(btn =>
        btn.addEventListener('click', () => handleJobDelete(btn.dataset.id)));

    lucide.createIcons();
}

/** English label for a category id (admin UI). Falls back to the raw id. */
function categoryLabel(id) {
    if (!id) return '—';
    const c = categoriesList.find(c => c.id === id);
    return c ? (c.label?.en || c.label?.ua || c.id) : id;
}

/**
 * Rebuild the job-type <select> from the admin-managed categories (value=id,
 * text=EN label). A legacy/unknown value on the job is preserved as an extra
 * option so editing never silently re-types it. Rebuilt on each open.
 */
function populateJobTypeOptions(selected) {
    const opts = categoriesList.map(c => ({ id: c.id, label: c.label?.en || c.label?.ua || c.id }));
    if (selected && !opts.some(o => o.id === selected)) {
        opts.push({ id: selected, label: categoryLabel(selected) });
    }
    jobType.innerHTML = opts
        .map(o => `<option value="${escHtml(o.id)}">${escHtml(o.label)}</option>`)
        .join('');
    if (selected && opts.some(o => o.id === selected)) jobType.value = selected;
    else if (opts.length) jobType.value = opts[0].id;
}

/**
 * Tick the placement checkboxes from a job's `sites` array. An empty/missing list
 * means the job is published everywhere (legacy), so all boxes are checked.
 */
function applySitesToForm(sites) {
    const list = Array.isArray(sites) ? sites : [];
    const all  = list.length === 0;
    JOB_SITES.forEach(({ key }) => {
        const box = siteCheckbox(key);
        if (box) box.checked = all || list.includes(key);
    });
}

/** Read the checked placement boxes back into an array of site keys. */
function collectSelectedSites() {
    return JOB_SITES.filter(({ key }) => siteCheckbox(key)?.checked).map(({ key }) => key);
}

// ── Cities editor (dynamic rows: city name + "housing" checkbox) ─────────────
/** Append one city row; optionally prefilled (used on edit). */
function addCityRow(name = '', housing = false) {
    const row = document.createElement('div');
    row.className = 'city-row';
    row.innerHTML = `
        <input type="text" class="form-input city-name" placeholder="Praha" value="${escHtml(name)}">
        <label class="city-housing"><input type="checkbox" class="city-housing-box" ${housing ? 'checked' : ''}> housing</label>
        <button type="button" class="city-remove" aria-label="Remove">
            <i data-lucide="x" class="w-3.5 h-3.5"></i>
        </button>
    `;
    row.querySelector('.city-remove').addEventListener('click', () => row.remove());
    jobCitiesEl.appendChild(row);
    lucide.createIcons();
    return row;
}

/** Rebuild the cities editor from a job's cities array (≥1 empty row by default). */
function applyCitiesToForm(cities) {
    jobCitiesEl.innerHTML = '';
    const list = Array.isArray(cities) ? cities : [];
    if (!list.length) { addCityRow(); return; }
    list.forEach(c => addCityRow(c?.name || '', !!c?.housing));
}

/** Collect city rows → [{name, housing}], dropping blank names. */
function collectCities() {
    return [...jobCitiesEl.querySelectorAll('.city-row')].map(row => ({
        name: row.querySelector('.city-name').value.trim(),
        housing: row.querySelector('.city-housing-box').checked,
    })).filter(c => c.name);
}

function openJobModal(jobId = null) {
    jobForm.reset();
    hideJobError();

    if (jobId) {
        const job = jobsList.find(j => String(j.id) === String(jobId));
        if (!job) { showToast_('Job not found — try re-syncing.', 'error'); return; }
        jobModalTitle.textContent = 'Edit Job';
        jobIdInput.value     = job.id;
        jobTitleUa.value     = job.title?.ua || '';
        jobTitleCz.value     = job.title?.cz || '';
        jobTitleEn.value     = job.title?.en || '';
        populateJobTypeOptions(job.type || job.category);
        jobSalary.value      = job.salary || '';
        jobDescription.value = job.description || '';
        jobIsNew.checked     = !!job.new;
        applySitesToForm(job.sites);
        // Edit: prefill cities; legacy jobs (no cities) seed one row from `location`.
        applyCitiesToForm(job.cities && job.cities.length
            ? job.cities
            : (job.location ? [{ name: job.location, housing: false }] : []));
    } else {
        jobModalTitle.textContent = 'Add Job';
        jobIdInput.value = '';
        populateJobTypeOptions(null);
        jobIsNew.checked = true;
        applySitesToForm(null);   // new job defaults to "everywhere" (all checked)
        applyCitiesToForm(null);  // one empty city row
    }

    jobModalOverlay.classList.remove('hidden');
    lucide.createIcons();
    jobTitleUa.focus();
}

function closeJobModal() {
    jobModalOverlay.classList.add('hidden');
    hideJobError();
}

function showJobError(message) {
    jobFormError.textContent = message;
    jobFormError.classList.add('show');
}

function hideJobError() {
    jobFormError.textContent = '';
    jobFormError.classList.remove('show');
}

async function handleJobSubmit(e) {
    e.preventDefault();
    hideJobError();

    const sites = collectSelectedSites();
    const cities = collectCities();

    const payload = {
        title_ua:    jobTitleUa.value.trim(),
        title_cz:    jobTitleCz.value.trim(),
        title_en:    jobTitleEn.value.trim(),
        type:        jobType.value,
        salary:      jobSalary.value.trim() || null,
        description: jobDescription.value.trim() || null,
        is_new:      jobIsNew.checked,
        sites,
        cities,
    };

    if (!payload.title_ua || !payload.title_cz || !payload.title_en) {
        showJobError('All three title languages (UA / CZ / EN) are required.');
        return;
    }
    if (!payload.type) {
        showJobError('Select a category (create one in the Categories tab first).');
        return;
    }
    if (!cities.length) {
        showJobError('Add at least one city.');
        return;
    }
    if (!sites.length) {
        showJobError('Оберіть хоча б один сайт для розміщення.');
        return;
    }

    const id     = jobIdInput.value;
    const isEdit = !!id;
    const url    = isEdit ? `${API_BASE}/jobs/${encodeURIComponent(id)}` : `${API_BASE}/jobs`;
    const method = isEdit ? 'PUT' : 'POST';

    btnJobSave.disabled = true;

    try {
        const res = await fetch(url, {
            method,
            headers: adminHeaders(),
            body: JSON.stringify(payload),
        });
        if (res.status === 401) { handleAuthExpired(); return; }
        if (res.status === 403) { showJobError('Only administrators can manage vacancies.'); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const result = await res.json().catch(() => ({}));
        const jobId = isEdit ? id : (result.id || '');

        // Upload the photo (if one was chosen) to R2 via the backend.
        const file = jobImage && jobImage.files && jobImage.files[0];
        if (file && jobId) {
            await uploadJobImage(jobId, file);
        }

        closeJobModal();
        showToast_(isEdit ? 'Job updated successfully.' : 'Job created successfully.', 'success');
        await fetchJobsList();
    } catch (err) {
        console.error('handleJobSubmit error:', err);
        showJobError(`Save failed: ${err.message}`);
    } finally {
        btnJobSave.disabled = false;
    }
}

/**
 * Upload a job photo to the backend (which stores it in Cloudflare R2 and returns
 * the public URL). Sent as multipart/form-data — note we must NOT set Content-Type
 * manually so the browser adds the multipart boundary.
 */
async function uploadJobImage(jobId, file) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/image`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` },
        body: fd,
    });
    if (res.status === 401) { handleAuthExpired(); throw new Error('Session expired'); }
    if (res.status === 413) throw new Error('Image too large (max 5 MB)');
    if (res.status === 415) throw new Error('Unsupported image type (JPEG/PNG/WebP only)');
    if (res.status === 503) throw new Error('Image storage not configured on the server');
    if (!res.ok) throw new Error(`Image upload failed (HTTP ${res.status})`);
    return res.json();
}

async function handleJobDelete(jobId) {
    const job = jobsList.find(j => String(j.id) === String(jobId));
    const label = job ? (job.title?.en || job.title?.ua || job.title?.cz || 'this job') : 'this job';
    if (!window.confirm(`Delete "${label}"?\nThis removes it from the public website.`)) return;

    try {
        const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`, {
            method: 'DELETE',
            headers: adminHeaders(),
        });
        if (res.status === 401) { handleAuthExpired(); return; }
        if (res.status === 403) { showToast_('Only administrators can delete vacancies.', 'error'); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        showToast_('Job deleted.', 'success');
        await fetchJobsList();
    } catch (err) {
        console.error('handleJobDelete error:', err);
        showToast_(`Delete failed: ${err.message}`, 'error');
    }
}

// ════════════════════════════════════════════════════════════════════════════
// CATEGORIES MANAGEMENT (CRUD against FastAPI)
// ════════════════════════════════════════════════════════════════════════════
let categoriesList = [];

async function fetchCategories() {
    try {
        const res = await fetch(`${API_BASE}/categories`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        categoriesList = await res.json();
    } catch (err) {
        console.error('fetchCategories error:', err);
        showToast_(`Failed to load categories: ${err.message}`, 'error');
        categoriesList = [];
    }
    renderCategoriesList();
}

function renderCategoriesList() {
    if (!categoriesListEl) return;
    if (categoriesTotalCountEl) categoriesTotalCountEl.textContent = categoriesList.length;

    if (!categoriesList.length) {
        categoriesListEl.innerHTML = `<div class="jobs-empty">No categories yet. Click "Add Category" to create the first one.</div>`;
        return;
    }

    categoriesListEl.innerHTML = categoriesList.map(cat => `
        <div class="job-card">
            <div class="job-card-title">${escHtml(cat.label?.ua || cat.label?.en || cat.id)}</div>
            <div class="category-langs">
                🇺🇦 ${escHtml(cat.label?.ua || '—')} · 🇨🇿 ${escHtml(cat.label?.cz || '—')} · 🇬🇧 ${escHtml(cat.label?.en || '—')}
            </div>
            <div class="job-card-actions">
                <button class="job-btn edit" data-id="${escHtml(cat.id)}"><i data-lucide="pencil" class="w-3 h-3"></i> Edit</button>
                <button class="job-btn delete" data-id="${escHtml(cat.id)}"><i data-lucide="trash-2" class="w-3 h-3"></i> Delete</button>
            </div>
        </div>`).join('');

    categoriesListEl.querySelectorAll('.job-btn.edit').forEach(btn =>
        btn.addEventListener('click', () => openCategoryModal(btn.dataset.id)));
    categoriesListEl.querySelectorAll('.job-btn.delete').forEach(btn =>
        btn.addEventListener('click', () => handleCategoryDelete(btn.dataset.id)));

    lucide.createIcons();
}

function openCategoryModal(catId = null) {
    categoryForm.reset();
    hideCategoryError();
    if (catId) {
        const cat = categoriesList.find(c => c.id === catId);
        if (!cat) { showToast_('Category not found — try re-syncing.', 'error'); return; }
        categoryModalTitle.textContent = 'Edit Category';
        categoryIdInput.value = cat.id;
        catLabelUa.value = cat.label?.ua || '';
        catLabelCz.value = cat.label?.cz || '';
        catLabelEn.value = cat.label?.en || '';
    } else {
        categoryModalTitle.textContent = 'Add Category';
        categoryIdInput.value = '';
    }
    categoryModalOverlay.classList.remove('hidden');
    lucide.createIcons();
    catLabelUa.focus();
}

function closeCategoryModal() {
    categoryModalOverlay.classList.add('hidden');
    hideCategoryError();
}

function showCategoryError(message) {
    categoryFormError.textContent = message;
    categoryFormError.classList.add('show');
}

function hideCategoryError() {
    categoryFormError.textContent = '';
    categoryFormError.classList.remove('show');
}

async function handleCategorySubmit(e) {
    e.preventDefault();
    hideCategoryError();

    const payload = {
        label_ua: catLabelUa.value.trim(),
        label_cz: catLabelCz.value.trim(),
        label_en: catLabelEn.value.trim(),
    };
    if (!payload.label_ua || !payload.label_cz || !payload.label_en) {
        showCategoryError('All three names (UA / CZ / EN) are required.');
        return;
    }

    const id     = categoryIdInput.value;
    const isEdit = !!id;
    const url    = isEdit ? `${API_BASE}/categories/${encodeURIComponent(id)}` : `${API_BASE}/categories`;
    const method = isEdit ? 'PUT' : 'POST';

    btnCategorySave.disabled = true;
    try {
        const res = await fetch(url, { method, headers: adminHeaders(), body: JSON.stringify(payload) });
        if (res.status === 401) { handleAuthExpired(); return; }
        if (res.status === 403) { showCategoryError('Only administrators can manage categories.'); return; }
        if (res.status === 409) { showCategoryError('A category with this name already exists.'); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        closeCategoryModal();
        showToast_(isEdit ? 'Category updated.' : 'Category created.', 'success');
        await fetchCategories();
    } catch (err) {
        console.error('handleCategorySubmit error:', err);
        showCategoryError(`Save failed: ${err.message}`);
    } finally {
        btnCategorySave.disabled = false;
    }
}

async function handleCategoryDelete(catId) {
    const cat = categoriesList.find(c => c.id === catId);
    const label = cat ? (cat.label?.en || cat.label?.ua || catId) : catId;
    if (!window.confirm(`Delete category "${label}"?`)) return;
    try {
        const res = await fetch(`${API_BASE}/categories/${encodeURIComponent(catId)}`, {
            method: 'DELETE', headers: adminHeaders(),
        });
        if (res.status === 401) { handleAuthExpired(); return; }
        if (res.status === 403) { showToast_('Only administrators can delete categories.', 'error'); return; }
        if (res.status === 409) { showToast_('Category is in use by some jobs — reassign them first.', 'error'); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        showToast_('Category deleted.', 'success');
        await fetchCategories();
    } catch (err) {
        console.error('handleCategoryDelete error:', err);
        showToast_(`Delete failed: ${err.message}`, 'error');
    }
}

// ════════════════════════════════════════════════════════════════════════════
// CONNECTION STATUS
// ════════════════════════════════════════════════════════════════════════════
function setConnectionStatus(state) {
    connectionBadge.className = `connection-badge ${state}`;
    const labels = { connected: '🟢 Connected', disconnected: '🔴 Offline', reconnecting: '🟡 Reconnecting…' };
    connectionLabel.textContent = labels[state] || state;
}

// ════════════════════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ════════════════════════════════════════════════════════════════════════════
const TOAST_ICONS = {
    success: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    error:   '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    info:    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    warning: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
};

function showToast_(message, type = 'info', duration = 4500) {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${TOAST_ICONS[type] || TOAST_ICONS.info}</span>
        <span>${escHtml(message)}</span>
        <button class="toast-dismiss" aria-label="Dismiss">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
    `;
    toast.querySelector('.toast-dismiss').addEventListener('click', () => removeToast(toast));
    toastContainer.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => removeToast(toast), duration);
    }
}

function removeToast(toast) {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(16px)';
    toast.style.transition = 'opacity 0.2s, transform 0.2s';
    setTimeout(() => toast.remove(), 220);
}

// ════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ════════════════════════════════════════════════════════════════════════════
function escHtml(str) {
    if (!str && str !== 0) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatTimestamp(ts) {
    try {
        const d = new Date(ts);
        if (isNaN(d.getTime())) return String(ts);
        return d.toLocaleString('uk-UA', {
            day:    '2-digit',
            month:  '2-digit',
            year:   'numeric',
            hour:   '2-digit',
            minute: '2-digit',
        });
    } catch {
        return String(ts);
    }
}
