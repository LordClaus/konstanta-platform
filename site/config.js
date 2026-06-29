/* ═══════════════════════════════════════════════════════════════════════════
   KONSTANTA — runtime frontend configuration (candidate site)

   This static site has no build step, so the backend URL can't be injected at
   build time. Instead we detect the environment at runtime:
     • localhost / 127.0.0.1  → local FastAPI on :8000 (development)
     • any other host         → PRODUCTION_API_URL below

   ⚠️ BEFORE GOING LIVE: set PRODUCTION_API_URL to your Serv00 backend, e.g.
       const PRODUCTION_API_URL = 'https://konstanta.serv00.net';
   Must be https:// — GitHub Pages is served over https and browsers block
   mixed (http) content.

   Loaded as a plain <script> BEFORE script.js so window.APP_CONFIG exists first.
═══════════════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    // Production backend origin (no trailing slash) — the Koyeb service URL.
    const PRODUCTION_API_URL = 'https://immense-ailina-7557-850b69ec.koyeb.app';

    // Google OAuth 2.0 Web Client ID (candidate sign-in). The site origin
    // (https://www.konstanta-agency.cz) must be in the OAuth client's
    // "Authorized JavaScript origins" in Google Cloud Console.
    const GOOGLE_CLIENT_ID = '23498790575-k0iquvqga3v0nb5jrrca5745uobd7155.apps.googleusercontent.com';

    const host = window.location.hostname;
    const isLocal =
        host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0' || host === '';

    const apiBase = isLocal ? 'http://localhost:8000' : PRODUCTION_API_URL;

    if (!isLocal && apiBase.includes('YOUR-BACKEND-DOMAIN')) {
        console.error(
            '[config] PRODUCTION_API_URL is not set — API calls will fail. ' +
            'Edit config.js and set your Koyeb backend URL.'
        );
    }

    // Identifies which candidate site this is. The backend filters /jobs?site=<key>
    // so this site shows only jobs the admin assigned to it (plus legacy "everywhere"
    // jobs). Must match a key in the backend KNOWN_SITES + the admin panel JOB_SITES.
    const SITE_KEY = 'konstanta';

    // Public identity — used for Google for Jobs / Organization structured data.
    const BRAND = 'Konstanta';
    const SITE_URL = 'https://www.konstanta-agency.cz';
    const LOGO_URL = '';

    // AI assistant widget. Flip to true ONLY after GEMINI_API_KEY is set on the
    // backend (Koyeb) — otherwise the chat button would appear but not work.
    const AI_ENABLED = false;

    window.APP_CONFIG = Object.freeze({
        API_BASE_URL: apiBase,
        WS_URL: apiBase.replace(/^http/, 'ws') + '/ws/managers',
        GOOGLE_CLIENT_ID,
        SITE_KEY,
        BRAND,
        SITE_URL,
        LOGO_URL,
        AI_ENABLED,
    });
})();
