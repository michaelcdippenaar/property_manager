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

  // ── Native signing tools ────────────────────────────────────────────

  server.tool(
    'esigning_public_sign_info',
    'Get public signing page info (no auth required). Returns signing_backend, signer info.',
    { uuid: z.string().describe('Public link UUID') },
    async ({ uuid }) => {
      const result = await fetch(
        `${process.env.TREMLY_API_URL || 'http://localhost:8000/api/v1/'}esigning/public-sign/${uuid}/`,
        { headers: { Accept: 'application/json' } }
      );
      const data = await result.json();
      return { content: [{ type: 'text', text: JSON.stringify({ ok: result.ok, status: result.status, data }, null, 2) }] };
    }
  );

  server.tool(
    'esigning_public_document',
    'Get the filled lease HTML + signing fields for a native signing link (no auth required)',
    { uuid: z.string().describe('Public link UUID') },
    async ({ uuid }) => {
      const result = await fetch(
        `${process.env.TREMLY_API_URL || 'http://localhost:8000/api/v1/'}esigning/public-sign/${uuid}/document/`,
        { headers: { Accept: 'application/json' } }
      );
      const data = await result.json();
      // Truncate HTML for readability
      if (data.html) data.html = `[${data.html.length} chars]`;
      return { content: [{ type: 'text', text: JSON.stringify({ ok: result.ok, status: result.status, data }, null, 2) }] };
    }
  );

  server.tool(
    'esigning_native_signing_test',
    'Composite test: create native submission, verify document endpoint returns fields, validate signer roles match. Requires lease_id and at least one signer.',
    {
      lease_id: z.number(),
      signers: z.array(z.object({
        name: z.string(),
        email: z.string(),
        role: z.string(),
      })),
    },
    async (args) => {
      const results = { steps: [], pass: true };

      // Step 1: Create submission
      const createRes = await apiPost('esigning/submissions/', {
        lease_id: args.lease_id,
        signers: args.signers.map(s => ({ ...s, send_email: false })),
        signing_mode: 'sequential',
      });
      if (createRes.error) {
        results.steps.push({ step: 'create_submission', pass: false, error: createRes.error });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }
      const submission = createRes.data || createRes;
      const subId = submission.id;
      results.steps.push({ step: 'create_submission', pass: true, submission_id: subId, signing_backend: submission.signing_backend });

      // Step 2: Check submission is native
      if (submission.signing_backend !== 'native') {
        results.steps.push({ step: 'check_backend', pass: false, error: `Expected native, got ${submission.signing_backend}` });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }
      results.steps.push({ step: 'check_backend', pass: true });

      // Step 3: Get public link for first signer
      const linkRes = await apiPost(`esigning/submissions/${subId}/public-link/`, {
        submitter_id: submission.signers?.[0]?.id || 1,
      });
      const linkData = linkRes.data || linkRes;
      const uuid = linkData.uuid;
      if (!uuid) {
        results.steps.push({ step: 'create_public_link', pass: false, error: 'No UUID returned', data: linkData });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }
      results.steps.push({ step: 'create_public_link', pass: true, uuid });

      // Step 4: Fetch public sign info
      const baseUrl = process.env.TREMLY_API_URL || 'http://localhost:8000/api/v1/';
      const infoRes = await fetch(`${baseUrl}esigning/public-sign/${uuid}/`, { headers: { Accept: 'application/json' } });
      const info = await infoRes.json();
      if (info.signing_backend !== 'native') {
        results.steps.push({ step: 'public_sign_info', pass: false, error: `Expected native, got ${info.signing_backend}` });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }
      results.steps.push({ step: 'public_sign_info', pass: true, signer_role: info.signer_role });

      // Step 5: Fetch document + fields
      const docRes = await fetch(`${baseUrl}esigning/public-sign/${uuid}/document/`, { headers: { Accept: 'application/json' } });
      const doc = await docRes.json();
      const fields = doc.fields || [];
      const htmlLen = (doc.html || '').length;

      if (htmlLen === 0) {
        results.steps.push({ step: 'fetch_document', pass: false, error: 'document_html is empty' });
        results.pass = false;
      } else if (fields.length === 0) {
        results.steps.push({
          step: 'fetch_document', pass: false,
          error: `No fields found for signer_role="${doc.signer_role}". HTML has ${htmlLen} chars. This likely means role mapping is broken — signer role doesn't match field roles in HTML.`,
          signer_role: doc.signer_role,
        });
        results.pass = false;
      } else {
        results.steps.push({
          step: 'fetch_document', pass: true,
          html_length: htmlLen,
          fields_count: fields.length,
          signer_role: doc.signer_role,
          field_types: fields.reduce((acc, f) => { acc[f.fieldType] = (acc[f.fieldType] || 0) + 1; return acc; }, {}),
        });
      }

      // Step 6: Verify all field roles match signer role
      const mismatchedFields = fields.filter(f => f.signerRole !== doc.signer_role);
      if (mismatchedFields.length > 0) {
        results.steps.push({ step: 'role_consistency', pass: false, error: `${mismatchedFields.length} fields have mismatched roles`, mismatched: mismatchedFields.slice(0, 3) });
        results.pass = false;
      } else if (fields.length > 0) {
        results.steps.push({ step: 'role_consistency', pass: true });
      }

      return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
    }
  );
}
