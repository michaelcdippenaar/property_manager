import { z } from 'zod';
import { apiGet, apiPost, apiPatch } from '../http-client.mjs';

export function registerBuilderTools(server) {
  server.tool(
    'builder_session_create',
    'Create a new lease builder session',
    { template_id: z.coerce.number().optional() },
    async (args) => {
      const body = {};
      if (args.template_id !== undefined) body.template_id = args.template_id;
      const result = await apiPost('leases/builder/sessions/', body);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'builder_session_message',
    'Send a chat message to a builder session (may take 10-30s for AI response)',
    { session_id: z.coerce.number(), message: z.string() },
    async ({ session_id, message }) => {
      const result = await apiPost(
        `leases/builder/sessions/${session_id}/message/`,
        { message },
        { timeout: 60000 }
      );
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'builder_session_finalize',
    'Finalize a builder session into a lease',
    { session_id: z.coerce.number() },
    async ({ session_id }) => {
      const result = await apiPost(`leases/builder/sessions/${session_id}/finalize/`, {});
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'builder_draft_list',
    'List all builder drafts',
    {},
    async () => {
      const result = await apiGet('leases/builder/drafts/');
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'builder_draft_create',
    'Create a new builder draft',
    {
      name: z.string().optional(),
      template_id: z.coerce.number().optional(),
      data: z.record(z.any()).optional(),
    },
    async (args) => {
      const result = await apiPost('leases/builder/drafts/new/', args);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'builder_draft_update',
    'Update an existing builder draft',
    {
      id: z.coerce.number(),
      name: z.string().optional(),
      data: z.record(z.any()).optional(),
    },
    async ({ id, ...fields }) => {
      const body = Object.fromEntries(Object.entries(fields).filter(([, v]) => v !== undefined));
      const result = await apiPatch(`leases/builder/drafts/${id}/`, body);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );
}
