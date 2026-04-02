import { z } from 'zod';
import { apiGet, apiPost } from '../http-client.mjs';

export function registerESigningTools(server) {
  server.tool(
    'esigning_list',
    'List all e-signing submissions',
    {},
    async () => {
      const result = await apiGet('esigning/submissions/');
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_create',
    'Create a new e-signing submission',
    {
      lease_id: z.number(),
      signers: z.array(z.object({
        name: z.string(),
        email: z.string(),
        role: z.string().optional(),
      })),
      signing_mode: z.string().optional(),
    },
    async (args) => {
      const result = await apiPost('esigning/submissions/', args);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_get',
    'Get e-signing submission detail by ID',
    { id: z.number() },
    async ({ id }) => {
      const result = await apiGet(`esigning/submissions/${id}/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_signer_status',
    'Check signer status for a submission',
    { id: z.number() },
    async ({ id }) => {
      const result = await apiGet(`esigning/submissions/${id}/signer-status/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_resend',
    'Resend e-signing invite for a submission',
    { id: z.number() },
    async ({ id }) => {
      const result = await apiPost(`esigning/submissions/${id}/resend/`, {});
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_public_link',
    'Create a public signing link for a submitter',
    { id: z.number(), submitter_id: z.number() },
    async ({ id, submitter_id }) => {
      const result = await apiPost(`esigning/submissions/${id}/public-link/`, { submitter_id });
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_webhook_info',
    'Get webhook configuration info',
    {},
    async () => {
      const result = await apiGet('esigning/webhook/info/');
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );
}
