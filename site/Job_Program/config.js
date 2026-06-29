/* ═══════════════════════════════════════════════════════════════════════════
   KONSTANTA CRM — runtime frontend configuration (manager admin panel)

   No build step → detect the environment at runtime:
     • localhost / 127.0.0.1  → local FastAPI on :8000 (development)
     • any other host         → PRODUCTION_API_URL below

   ⚠️ BEFORE GOING LIVE: set PRODUCTION_API_URL to your Serv00 backend, e.g.
       const PRODUCTION_API_URL = 'https://konstanta.serv00.net';
   Must be https:// so the derived WebSocket URL becomes wss:// (secure) —
   GitHub Pages is https and browsers block insecure ws:// from an https page.

   Loaded as a plain <script> BEFORE admin.js so window.APP_CONFIG exists first.
═══════════════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    // Production backend origin (no trailing slash) — the Koyeb service URL.
    const PRODUCTION_API_URL = 'https://immense-ailina-7557-850b69ec.koyeb.app';

    const host = window.location.hostname;
    const isLocal =
        host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0' || host === '';

    const apiBase = isLocal ? 'http://localhost:8000' : PRODUCTION_API_URL;

    if (!isLocal && apiBase.includes('YOUR-BACKEND-DOMAIN')) {
        console.error(
            '[config] PRODUCTION_API_URL is not set — API/WS calls will fail. ' +
            'Edit Job_Program/config.js and set your Serv00 backend URL.'
        );
    }

    window.APP_CONFIG = Object.freeze({
        API_BASE_URL: apiBase,
        WS_URL: apiBase.replace(/^http/, 'ws') + '/ws/managers',
    });
})();
