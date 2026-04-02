import { z } from 'zod';
import { apiGet, apiPost, apiPatch, apiDelete } from '../http-client.mjs';

export function registerLeaseTools(server) {
  server.tool(
    'lease_list',
    'List leases with optional status filter and pagination',
    { status: z.string().optional(), page: z.number().optional() },
    async ({ status, page }) => {
      const params = new URLSearchParams();
      if (status) params.set('status', status);
      if (page) params.set('page', String(page));
      const qs = params.toString();
      const path = qs ? `leases/?${qs}` : 'leases/';
      const result = await apiGet(path);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'lease_get',
    'Get a single lease by ID',
    { id: z.number() },
    async ({ id }) => {
      const result = await apiGet(`leases/${id}/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'lease_create',
    'Create a new lease',
    {
      unit_id: z.number(),
      primary_tenant_id: z.number(),
      start_date: z.string(),
      end_date: z.string(),
      monthly_rent: z.string().or(z.number()),
      deposit: z.string().or(z.number()).optional(),
      status: z.string().optional(),
      notes: z.string().optional(),
    },
    async (args) => {
      const result = await apiPost('leases/', args);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'lease_update',
    'Update fields on an existing lease',
    {
      id: z.number(),
      status: z.string().optional(),
      monthly_rent: z.string().or(z.number()).optional(),
      deposit: z.string().or(z.number()).optional(),
      start_date: z.string().optional(),
      end_date: z.string().optional(),
      notes: z.string().optional(),
    },
    async ({ id, ...fields }) => {
      // Remove undefined fields
      const body = Object.fromEntries(Object.entries(fields).filter(([, v]) => v !== undefined));
      const result = await apiPatch(`leases/${id}/`, body);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'lease_delete',
    'Delete a lease by ID',
    { id: z.number() },
    async ({ id }) => {
      const result = await apiDelete(`leases/${id}/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'lease_calendar',
    'Get lease calendar data',
    {},
    async () => {
      const result = await apiGet('leases/calendar/');
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );
}
