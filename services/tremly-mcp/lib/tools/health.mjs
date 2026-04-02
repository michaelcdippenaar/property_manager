import { z } from 'zod';
import { apiGet, isAuthenticated } from '../http-client.mjs';

const ENDPOINTS = [
  { name: 'leases', path: 'leases/', auth: true },
  { name: 'templates', path: 'leases/templates/', auth: true },
  { name: 'clauses', path: 'leases/clauses/', auth: true },
  { name: 'builder_drafts', path: 'leases/builder/drafts/', auth: true },
  { name: 'esigning', path: 'esigning/submissions/', auth: true },
  { name: 'calendar', path: 'leases/calendar/', auth: true },
  { name: 'webhook_info', path: 'esigning/webhook/info/', auth: true },
  { name: 'auth_me', path: 'auth/me/', auth: true },
];

export function registerHealthTools(server) {
  server.tool(
    'health_check',
    'Ping all backend API endpoints and return a status table',
    { include_auth: z.boolean().optional().default(true) },
    async ({ include_auth }) => {
      const results = [];
      for (const ep of ENDPOINTS) {
        if (ep.auth && !include_auth) continue;
        if (ep.auth && !isAuthenticated()) {
          results.push({ endpoint: ep.name, path: ep.path, status: 'SKIP', code: 0, note: 'Not authenticated' });
          continue;
        }
        try {
          const res = await apiGet(ep.path);
          results.push({
            endpoint: ep.name,
            path: ep.path,
            status: res.ok ? 'OK' : 'ERROR',
            code: res.status,
          });
        } catch (e) {
          results.push({
            endpoint: ep.name,
            path: ep.path,
            status: 'FAIL',
            code: 0,
            note: e.message,
          });
        }
      }

      const output = { ok: true, data: { results, authenticated: isAuthenticated() }, status: 200 };
      return { content: [{ type: 'text', text: JSON.stringify(output, null, 2) }] };
    }
  );
}
