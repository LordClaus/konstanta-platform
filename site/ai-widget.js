/* ═══════════════════════════════════════════════════════════════════════════
   AI assistant chat widget (candidate sites).

   A self-contained floating chat. Talks to the backend's thin /ai/chat proxy
   (which forwards to Gemini). The jobs context is read from window.__candidateJobs
   (published by script.js) so neither the widget nor the server re-queries the DB.

   Only mounts when APP_CONFIG.AI_ENABLED is true — flip that on once GEMINI_API_KEY
   is set on the backend. Classic script (not a module): loaded after config.js.
═══════════════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    var cfg = window.APP_CONFIG || {};
    if (!cfg.AI_ENABLED) return;

    var API = cfg.API_BASE_URL;
    var BRAND = cfg.BRAND || 'Konstanta';

    var I18N = {
        ua: { title: 'Онлайн-помічник', sub: 'Запитайте про роботу', greet: 'Вітаю! Я допоможу обрати вакансію та підкажу, як подати анкету. Що вас цікавить?', ph: 'Напишіть повідомлення…', err: 'Помічник тимчасово недоступний. Спробуйте пізніше або зв’яжіться з нами.', open: 'Чат-помічник' },
        cz: { title: 'Online asistent', sub: 'Zeptejte se na práci', greet: 'Dobrý den! Pomohu vám vybrat pozici a poradím s přihláškou. Co vás zajímá?', ph: 'Napište zprávu…', err: 'Asistent je dočasně nedostupný. Zkuste to později nebo nás kontaktujte.', open: 'Chat asistent' },
        en: { title: 'Online assistant', sub: 'Ask about jobs', greet: 'Hi! I can help you pick a vacancy and guide you through applying. What are you looking for?', ph: 'Type a message…', err: 'The assistant is temporarily unavailable. Please try later or contact us.', open: 'Chat assistant' }
    };

    function lang() {
        var l = localStorage.getItem('lang') || 'ua';
        return I18N[l] ? l : 'ua';
    }
    function t() { return I18N[lang()]; }
    function esc(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    var messages = [];       // { role: 'user'|'assistant', content }
    var open = false, busy = false, greeted = false;

    // ── DOM ──────────────────────────────────────────────────────────────────
    var fab = document.createElement('button');
    fab.setAttribute('aria-label', t().open);
    fab.className = 'fixed bottom-6 right-6 z-[80] w-14 h-14 rounded-full bg-accent text-white shadow-xl flex items-center justify-center hover:scale-105 active:scale-95 transition-transform';
    fab.innerHTML = '<i data-lucide="message-circle" class="w-6 h-6"></i>';

    var panel = document.createElement('div');
    panel.className = 'fixed bottom-24 right-6 z-[80] w-[calc(100vw-3rem)] sm:w-[22rem] max-h-[70vh] rounded-2xl overflow-hidden shadow-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex-col hidden';
    panel.innerHTML =
        '<div class="bg-primary text-white px-4 py-3 flex items-center justify-between">' +
            '<div class="flex items-center gap-2">' +
                '<span class="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center"><i data-lucide="sparkles" class="w-4 h-4 text-accent"></i></span>' +
                '<div class="leading-tight"><div class="font-bold text-sm" data-ai="title"></div><div class="text-[10px] text-slate-300" data-ai="sub"></div></div>' +
            '</div>' +
            '<button data-ai="close" class="p-1.5 rounded-lg hover:bg-white/10 transition-colors"><i data-lucide="x" class="w-4 h-4"></i></button>' +
        '</div>' +
        '<div data-ai="messages" class="flex-1 overflow-y-auto p-4 space-y-3 text-sm bg-slate-50 dark:bg-slate-950"></div>' +
        '<form data-ai="form" class="p-2.5 border-t border-slate-200 dark:border-slate-800 flex items-end gap-2 bg-white dark:bg-slate-900">' +
            '<textarea data-ai="input" rows="1" class="flex-1 resize-none max-h-28 px-3 py-2 rounded-xl text-sm bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-accent/30"></textarea>' +
            '<button type="submit" data-ai="send" class="shrink-0 w-10 h-10 rounded-xl bg-accent text-white flex items-center justify-center hover:opacity-90 active:scale-95 transition disabled:opacity-50"><i data-lucide="send" class="w-4 h-4"></i></button>' +
        '</form>';

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    var elMsgs = panel.querySelector('[data-ai="messages"]');
    var elInput = panel.querySelector('[data-ai="input"]');
    var elForm = panel.querySelector('[data-ai="form"]');
    var elSend = panel.querySelector('[data-ai="send"]');

    function applyStrings() {
        panel.querySelector('[data-ai="title"]').textContent = t().title;
        panel.querySelector('[data-ai="sub"]').textContent = t().sub;
        elInput.placeholder = t().ph;
        fab.setAttribute('aria-label', t().open);
    }

    function icons() { if (window.lucide) window.lucide.createIcons(); }

    function bubble(role, html) {
        var mine = role === 'user';
        return '<div class="flex ' + (mine ? 'justify-end' : 'justify-start') + '">' +
            '<div class="max-w-[85%] px-3 py-2 rounded-2xl ' +
            (mine ? 'bg-accent text-white rounded-br-sm' : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-bl-sm') +
            '">' + html + '</div></div>';
    }

    function renderMessages() {
        elMsgs.innerHTML = messages.map(function (m) {
            return bubble(m.role, esc(m.content).replace(/\n/g, '<br>'));
        }).join('');
        scrollDown();
    }

    var typingEl = null;
    function showTyping(on) {
        if (on) {
            typingEl = document.createElement('div');
            typingEl.innerHTML = bubble('assistant', '<span class="inline-flex gap-1"><span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"></span><span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay:.15s"></span><span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay:.3s"></span></span>');
            elMsgs.appendChild(typingEl.firstChild);
            scrollDown();
        } else if (typingEl) {
            var last = elMsgs.lastChild;
            if (last) elMsgs.removeChild(last);
            typingEl = null;
        }
    }

    function scrollDown() { elMsgs.scrollTop = elMsgs.scrollHeight; }

    function compactJobs() {
        var jobs = window.__candidateJobs || [];
        var L = lang();
        return jobs.slice(0, 40).map(function (j) {
            var title = (j.title && (j.title[L] || j.title.cz || j.title.en || j.title.ua)) || '';
            var loc = '';
            if (Array.isArray(j.cities) && j.cities.length) {
                loc = j.cities.map(function (c) { return c && c.name; }).filter(Boolean).join(', ');
            } else { loc = j.location || ''; }
            return { title: title, type: j.type || j.category || '', location: loc, salary: j.salary || '' };
        }).filter(function (x) { return x.title; });
    }

    function send(text) {
        if (busy || !text.trim()) return;
        busy = true; elSend.disabled = true;
        messages.push({ role: 'user', content: text.trim() });
        renderMessages();
        showTyping(true);
        fetch(API + '/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lang: lang(), brand: BRAND, jobs: compactJobs(), messages: messages.slice(-12) })
        }).then(function (res) {
            return res.json().catch(function () { return {}; }).then(function (data) {
                return { ok: res.ok, data: data };
            });
        }).then(function (r) {
            showTyping(false);
            messages.push({ role: 'assistant', content: (r.ok && r.data.reply) ? r.data.reply : t().err });
            renderMessages();
        }).catch(function () {
            showTyping(false);
            messages.push({ role: 'assistant', content: t().err });
            renderMessages();
        }).then(function () {
            busy = false; elSend.disabled = false;
        });
    }

    function toggle(force) {
        open = (typeof force === 'boolean') ? force : !open;
        panel.classList.toggle('hidden', !open);
        panel.classList.toggle('flex', open);
        if (open) {
            applyStrings();
            if (!greeted) { greeted = true; messages.push({ role: 'assistant', content: t().greet }); renderMessages(); }
            icons();
            setTimeout(function () { elInput.focus(); }, 50);
        }
    }

    fab.addEventListener('click', function () { toggle(); });
    panel.querySelector('[data-ai="close"]').addEventListener('click', function () { toggle(false); });
    elForm.addEventListener('submit', function (e) { e.preventDefault(); var v = elInput.value; elInput.value = ''; elInput.style.height = 'auto'; send(v); });
    elInput.addEventListener('input', function () { elInput.style.height = 'auto'; elInput.style.height = Math.min(elInput.scrollHeight, 112) + 'px'; });
    elInput.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); elForm.requestSubmit(); } });

    applyStrings();
    icons();
})();
