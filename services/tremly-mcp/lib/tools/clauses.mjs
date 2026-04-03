import { z } from 'zod';
import { apiGet, apiPost, apiDelete } from '../http-client.mjs';

export function registerClauseTools(server) {
  server.tool(
    'clause_list',
    'List all reusable lease clauses',
    {},
    async () => {
      const result = await apiGet('leases/clauses/');
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'clause_create',
    'Create a new reusable clause',
    {
      title: z.string(),
      category: z.string(),
      html: z.string(),
      tags: z.array(z.string()).optional(),
    },
    async (args) => {
      const result = await apiPost('leases/clauses/', args);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'clause_delete',
    'Delete a clause by ID',
    { id: z.coerce.number() },
    async ({ id }) => {
      const result = await apiDelete(`leases/clauses/${id}/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'clause_use',
    'Mark a clause as used (increment usage count)',
    { id: z.coerce.number() },
    async ({ id }) => {
      const result = await apiPost(`leases/clauses/${id}/use/`, {});
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'clause_generate',
    'AI-generate a clause from a prompt',
    { prompt: z.string() },
    async ({ prompt }) => {
      const result = await apiPost('leases/clauses/generate/', { prompt }, { timeout: 60000 });
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'clause_extract',
    'Extract clauses from HTML content',
    { html: z.string() },
    async ({ html }) => {
      const result = await apiPost('leases/clauses/extract/', { html }, { timeout: 60000 });
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );
}
