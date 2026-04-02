import { z } from 'zod';
import { login, apiGet, isAuthenticated, getCurrentUser, getTokens } from '../http-client.mjs';

export function registerAuthTools(server) {
  server.tool(
    'auth_login',
    'Authenticate with the Tremly backend API using email and password',
    { email: z.string(), password: z.string() },
    async ({ email, password }) => {
      const result = await login(email, password);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'auth_whoami',
    'Get the current authenticated user info',
    {},
    async () => {
      if (!isAuthenticated()) {
        return { content: [{ type: 'text', text: JSON.stringify({ ok: false, error: 'Not authenticated. Call auth_login first.', status: 0 }) }] };
      }
      const result = await apiGet('auth/me/');
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'auth_status',
    'Check current auth state and token validity',
    {},
    async () => {
      const authenticated = isAuthenticated();
      const user = getCurrentUser();
      const tokens = getTokens();
      const status = {
        ok: true,
        data: {
          authenticated,
          user: user || null,
          hasAccessToken: !!tokens.access,
          hasRefreshToken: !!tokens.refresh,
        },
        status: 200,
      };
      return { content: [{ type: 'text', text: JSON.stringify(status, null, 2) }] };
    }
  );
}
