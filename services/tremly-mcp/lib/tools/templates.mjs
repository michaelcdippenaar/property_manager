import { z } from 'zod';
import { apiGet, apiPost, apiPatch, apiDelete } from '../http-client.mjs';

export function registerTemplateTools(server) {
  server.tool(
    'template_list',
    'List all active lease templates',
    {},
    async () => {
      const result = await apiGet('leases/templates/');
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'template_get',
    'Get a template with full content by ID',
    { id: z.number() },
    async ({ id }) => {
      const result = await apiGet(`leases/templates/${id}/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'template_create',
    'Create a new lease template',
    {
      name: z.string(),
      content_html: z.string().optional(),
      header_html: z.string().optional(),
      footer_html: z.string().optional(),
      description: z.string().optional(),
      category: z.string().optional(),
    },
    async (args) => {
      const result = await apiPost('leases/templates/', args);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'template_update',
    'Update (patch) a lease template',
    {
      id: z.number(),
      name: z.string().optional(),
      content_html: z.string().optional(),
      header_html: z.string().optional(),
      footer_html: z.string().optional(),
      description: z.string().optional(),
      category: z.string().optional(),
    },
    async ({ id, ...fields }) => {
      const body = Object.fromEntries(Object.entries(fields).filter(([, v]) => v !== undefined));
      const result = await apiPatch(`leases/templates/${id}/`, body);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'template_preview',
    'Get template preview data',
    { id: z.number() },
    async ({ id }) => {
      const result = await apiGet(`leases/templates/${id}/preview/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'template_ai_chat',
    'Send a message to the template AI chat assistant',
    { id: z.number(), message: z.string() },
    async ({ id, message }) => {
      const result = await apiPost(`leases/templates/${id}/ai-chat/`, { message }, { timeout: 60000 });
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'template_tiptap_roundtrip',
    'Composite test: create a template with v2 TipTap JSON envelope, refetch, verify integrity, then clean up',
    { name: z.string().optional() },
    async ({ name }) => {
      const templateName = name || `TipTap Roundtrip Test ${Date.now()}`;
      const envelope = {
        v: 2,
        html: '<p>Test merge field: {{tenant_name}}</p>',
        tiptapJson: {
          type: 'doc',
          content: [
            {
              type: 'paragraph',
              content: [
                { type: 'text', text: 'Test merge field: ' },
                { type: 'mergeField', attrs: { fieldName: 'tenant_name' } },
              ],
            },
          ],
        },
        fields: [{ fieldName: 'tenant_name', fieldType: 'text' }],
      };

      const checks = [];
      let templateId = null;

      // Step 1: Create template
      const createRes = await apiPost('leases/templates/', {
        name: templateName,
        content_html: JSON.stringify(envelope),
      });
      if (!createRes.ok) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ ok: false, error: 'Failed to create template', detail: createRes.error, status: createRes.status }, null, 2) }],
        };
      }
      templateId = createRes.data.id;
      checks.push({ step: 'create', passed: true });

      // Step 2: Re-fetch
      const getRes = await apiGet(`leases/templates/${templateId}/`);
      if (!getRes.ok) {
        checks.push({ step: 'refetch', passed: false, error: getRes.error });
        // Cleanup
        await apiDelete(`leases/templates/${templateId}/`);
        return { content: [{ type: 'text', text: JSON.stringify({ ok: false, data: { checks }, status: getRes.status }, null, 2) }] };
      }
      checks.push({ step: 'refetch', passed: true });

      // Step 3: Parse and verify
      let parsed;
      try {
        parsed = JSON.parse(getRes.data.content_html);
      } catch (e) {
        checks.push({ step: 'parse_json', passed: false, error: 'content_html is not valid JSON' });
        await apiDelete(`leases/templates/${templateId}/`);
        return { content: [{ type: 'text', text: JSON.stringify({ ok: false, data: { checks }, status: 200 }, null, 2) }] };
      }
      checks.push({ step: 'parse_json', passed: true });

      checks.push({ step: 'version_check', passed: parsed.v === 2, expected: 2, actual: parsed.v });
      checks.push({ step: 'html_intact', passed: typeof parsed.html === 'string' && parsed.html.includes('{{tenant_name}}'), actual: parsed.html });
      checks.push({ step: 'tiptapJson_intact', passed: !!parsed.tiptapJson && Array.isArray(parsed.tiptapJson.content), hasContent: !!parsed.tiptapJson?.content });
      checks.push({ step: 'fields_intact', passed: Array.isArray(parsed.fields) && parsed.fields.length > 0, fieldCount: parsed.fields?.length });

      // Step 4: Cleanup
      const delRes = await apiDelete(`leases/templates/${templateId}/`);
      checks.push({ step: 'cleanup', passed: delRes.ok || delRes.status === 204 });

      const allPassed = checks.every((c) => c.passed);
      return {
        content: [{ type: 'text', text: JSON.stringify({ ok: allPassed, data: { checks, templateId }, status: 200 }, null, 2) }],
      };
    }
  );
}
