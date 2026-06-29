/* ═══════════════════════════════════════════════════════════════════════════
   Legal pages renderer (shared by all four legal documents).

   Reads which document to show from <body data-doc="…">, the language from the
   same localStorage key the main site uses ('lang'), and renders the matching
   text from window.LEGAL (legal-content.js). Language + theme toggles mirror the
   main site so the visitor's choice carries over.
═══════════════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    const LANGS = ['cz', 'ua', 'en'];
    const BACK = { cz: 'Zpět na web', ua: 'Назад на сайт', en: 'Back to site' };

    const docKey = document.body.dataset.doc;
    const data = window.LEGAL && window.LEGAL.docs[docKey];
    const meta = (window.LEGAL && window.LEGAL.meta) || {};

    let lang = localStorage.getItem('lang') || 'ua';
    if (!LANGS.includes(lang)) lang = 'ua';

    // Respect the theme chosen on the main site (the page's <html> class is the default).
    (function applyTheme() {
        const t = localStorage.getItem('theme');
        if (t === 'dark') document.documentElement.classList.add('dark');
        else if (t === 'light') document.documentElement.classList.remove('dark');
    })();

    function render() {
        if (!data) return;
        document.documentElement.lang = lang === 'cz' ? 'cs' : lang;
        const title = data.title[lang] || data.title.en;
        document.title = title + (meta.brand ? ' — ' + meta.brand : '');

        const h1 = document.getElementById('legal-title');
        if (h1) h1.textContent = title;

        const body = document.getElementById('legal-body');
        if (body) body.innerHTML = data.body[lang] || data.body.en;

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
