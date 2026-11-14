# Frontend scaffold

The application entry point is `src/main.tsx`. `src/App.tsx` composes `src/pages/DashboardPage.tsx`, while `src/hooks/useDashboardData.ts` owns loading/error/refresh behavior for the local API. Reusable UI is in `src/components/`, API calls and TypeScript contracts are in `src/services/` and `src/types/`, and the Nightwatch theme is in `src/styles.css`.

The Vite development server binds to loopback and proxies `/api` requests to `http://127.0.0.1:8001` by default. Set `VITE_API_PROXY_TARGET` to override the backend URL. The command center supports scenario replay, service status, telemetry/evidence filters, local model availability, investigation, approval-gated simulated remediation, recovery verification, reports, and live lifecycle events. Risky and unsafe actions are visibly gated or blocked.

Install packages with `npm install`, start with `npm run dev -- --host 127.0.0.1`, and run `npm test` plus `npm run build` before committing frontend changes.
