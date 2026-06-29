/* ═══════════════════════════════════════════════════════════════════════════
   Content pages renderer (About / How it works / FAQ).

   Reads which page to show from <body data-page="…">, the language from the same
   localStorage key the main site uses ('lang'), and renders from window.PAGES
   (pages-content.js). FAQ additionally emits FAQPage JSON-LD (Google rich result).
   Language + theme toggles mirror the main site.
═══════════════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    const LANGS = ['cz', 'ua', 'en'];
    const BACK = { cz: 'Zpět na web', ua: 'Назад на сайт', en: 'Back to site' };

    const pageKey = document.body.dataset.page;
    const data = window.PAGES && window.PAGES.pages[pageKey];
    const meta = (window.PAGES && window.PAGES.meta) || {};

    let lang = localStorage.getItem('lang') || 'ua';
    if (!LANGS.includes(lang)) lang = 'ua';

    (function applyTheme() {
        const t = localStorage.getItem('theme');
        if (t === 'dark') document.documentElement.classList.add('dark');
        else if (t === 'light') document.documentElement.classList.remove('dark');
    })();

    const escAttr = (s) => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

    function renderFaqLD(items) {
        const old = document.getElementById('faq-ld');
        if (old) old.remove();
        if (!items || !items.length) return;
        const ld = {
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: items.map((it) => ({
                '@type': 'Question',
                name: it.q,
                acceptedAnswer: { '@type': 'Answer', text: it.a },
            })),
        };
        const el = document.createElement('script');
        el.type = 'application/ld+json';
        el.id = 'faq-ld';
        el.textContent = JSON.stringify(ld);
        document.head.appendChild(el);
    }

    function render() {
        if (!data) return;
        document.documentElement.lang = lang === 'cz' ? 'cs' : lang;
        const title = data.title[lang] || data.title.en;
        document.title = title + (meta.brand ? ' — ' + meta.brand : '');

        const h1 = document.getElementById('page-title');
        if (h1) h1.textContent = title;

        const body = document.getElementById('page-body');
        if (body) {
            if (pageKey === 'faq') {
                const items = (data.items && (data.items[lang] || data.items.en)) || [];
                body.innerHTML = items.map((it) => `
                    <details class="faq-item">
                        <summary>${escAttr(it.q)}</summary>
                        <div class="faq-answer">${escAttr(it.a)}</div>
                    </details>`).join('');
                renderFaqLD(items);
            } else {
                body.innerHTML = data.body[lang] || data.body.en;
            }
        }

        document.querySelectorAll('[data-legal="back"]').forEach((el) => {
            el.textContent = '← ' + (BACK[lang] || BACK.en);
        });
        document.querySelectorAll('[data-setlang]').forEach((btn) => {
            btn.classList.toggle('legal-lang-active', btn.dataset.setlang === lang);
        });

        if (window.lucide) lucide.createIcons();
    }

    document.querySelectorAll('[data-setlang]').forEach((btn) => {
        btn.addEventListener('click', () => {
            lang = btn.dataset.setlang;
            localStorage.setItem('lang', lang);
            render();
            window.scrollTo({ top: 0 });
        });
    });

    const themeBtn = document.getElementById('legal-theme');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const dark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('theme', dark ? 'dark' : 'light');
            if (window.lucide) lucide.createIcons();
        });
    }

    render();
})();
