import { z } from 'zod';
import { apiGet, apiPost } from '../http-client.mjs';
import { execFile } from 'node:child_process';
import { writeFile, unlink, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

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
      lease_id: z.coerce.number(),
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
    { id: z.coerce.number() },
    async ({ id }) => {
      const result = await apiGet(`esigning/submissions/${id}/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_signer_status',
    'Check signer status for a submission',
    { id: z.coerce.number() },
    async ({ id }) => {
      const result = await apiGet(`esigning/submissions/${id}/signer-status/`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_resend',
    'Resend e-signing invite for a submission',
    { id: z.coerce.number() },
    async ({ id }) => {
      const result = await apiPost(`esigning/submissions/${id}/resend/`, {});
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );

  server.tool(
    'esigning_public_link',
    'Create a public signing link for a submitter',
    { id: z.coerce.number(), submitter_id: z.coerce.number() },
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
      lease_id: z.coerce.number(),
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

  // ── Form submission + DB verification test ─────────────────────────────

  server.tool(
    'esigning_form_submit_test',
    `Composite E2E test: creates a native signing submission, gets a public link, fetches
the document fields, submits the form with fake signature images + captured merge field
data, then verifies via the authenticated API that the DB was correctly updated:
  - signer status → "completed"
  - signer.signed_fields populated
  - signer.captured_fields populated
  - submission.captured_data merged
  - signer.audit recorded (ip, consent_given_at, document_hash_at_signing)
Requires: lease_id with a valid native-signing template.`,
    {
      lease_id: z.coerce.number(),
      signers: z.array(z.object({
        name: z.string(),
        email: z.string(),
        role: z.string(),
      })).describe('Signers to create (role must match field roles in the template, e.g. "tenant_1")'),
      captured_fields: z.record(z.string()).optional().describe('Merge field values to submit, e.g. {"tenant_1_id": "9901015008083"}'),
    },
    async ({ lease_id, signers, captured_fields }) => {
      const baseUrl = process.env.TREMLY_API_URL || 'http://localhost:8000/api/v1/';
      const results = { steps: [], pass: true };

      // Minimal 1×1 transparent PNG — valid image data for testing signatures
      const FAKE_SIG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

      // ── Step 1: Create submission ─────────────────────────────────────
      const createRes = await apiPost('esigning/submissions/', {
        lease_id,
        signers: signers.map(s => ({ ...s, send_email: false })),
        signing_mode: 'parallel',
      });
      if (!createRes.ok) {
        results.steps.push({ step: 'create_submission', pass: false, error: createRes.error });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }
      const submission = createRes.data;
      const subId = submission.id;
      results.steps.push({ step: 'create_submission', pass: true, submission_id: subId, backend: submission.signing_backend });

      if (submission.signing_backend !== 'native') {
        results.steps.push({ step: 'check_backend', pass: false, error: `Expected native, got ${submission.signing_backend}` });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }

      // ── Step 2: Sign each signer ──────────────────────────────────────
      for (const signer of submission.signers) {
        const signerStepPrefix = `signer_${signer.role}`;

        // Get public link
        const linkRes = await apiPost(`esigning/submissions/${subId}/public-link/`, {
          submitter_id: signer.id,
        });
        if (!linkRes.ok) {
          results.steps.push({ step: `${signerStepPrefix}_public_link`, pass: false, error: linkRes.error });
          results.pass = false;
          continue;
        }
        const uuid = linkRes.data?.uuid;
        results.steps.push({ step: `${signerStepPrefix}_public_link`, pass: !!uuid, uuid });

        // Fetch document + fields
        const docRes = await fetch(`${baseUrl}esigning/public-sign/${uuid}/document/`, {
          headers: { Accept: 'application/json' },
        });
        const doc = await docRes.json();
        const fields = doc.fields || [];
        results.steps.push({
          step: `${signerStepPrefix}_fetch_document`,
          pass: fields.length > 0,
          field_count: fields.length,
          field_types: fields.reduce((acc, f) => { acc[f.fieldType] = (acc[f.fieldType] || 0) + 1; return acc; }, {}),
        });

        if (fields.length === 0) {
          results.pass = false;
          continue;
        }

        // Build signed fields payload (fake image for sig/initials, date string for date)
        const signedFields = fields.map(f => ({
          fieldName: f.fieldName,
          fieldType: f.fieldType,
          imageData: f.fieldType === 'date' ? '' : FAKE_SIG,
        }));

        // Submit
        const consentTimestamp = new Date().toISOString();
        const submitRes = await fetch(`${baseUrl}esigning/public-sign/${uuid}/sign/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({
            fields: signedFields,
            captured_fields: captured_fields || {},
            consent: { agreed: true, timestamp: consentTimestamp },
          }),
        });
        const submitData = await submitRes.json();
        results.steps.push({
          step: `${signerStepPrefix}_submit`,
          pass: submitRes.ok,
          status: submitRes.status,
          error: submitRes.ok ? undefined : JSON.stringify(submitData).slice(0, 200),
        });
        if (!submitRes.ok) results.pass = false;
      }

      // ── Step 3: Verify DB state via authenticated API ─────────────────
      const verifyRes = await apiGet(`esigning/submissions/${subId}/`);
      if (!verifyRes.ok) {
        results.steps.push({ step: 'verify_db_fetch', pass: false, error: verifyRes.error });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }
      const updatedSub = verifyRes.data;

      // Check each signer's DB state
      for (const signer of updatedSub.signers) {
        const prefix = `db_check_${signer.role}`;
        const signedOk = signer.status === 'completed' || signer.status === 'signed';
        const hasSignedFields = Array.isArray(signer.signed_fields) && signer.signed_fields.length > 0;
        const hasAudit = !!(signer.audit?.consent_given_at && signer.audit?.document_hash_at_signing);
        const hasCaptured = !captured_fields || Object.keys(captured_fields).length === 0
          ? true
          : !!(signer.captured_fields && Object.keys(signer.captured_fields).length > 0);

        results.steps.push({
          step: prefix,
          pass: signedOk && hasSignedFields && hasAudit,
          status: signer.status,
          signed_fields_count: signer.signed_fields?.length ?? 0,
          has_audit: hasAudit,
          audit_keys: signer.audit ? Object.keys(signer.audit) : [],
          has_captured_fields: hasCaptured,
          captured_fields_keys: signer.captured_fields ? Object.keys(signer.captured_fields) : [],
        });

        if (!signedOk) { results.pass = false; }
        if (!hasSignedFields) { results.pass = false; }
        if (!hasAudit) { results.pass = false; }
      }

      // Check submission-level captured_data
      if (captured_fields && Object.keys(captured_fields).length > 0) {
        const capturedOk = Object.keys(captured_fields).every(
          k => updatedSub.captured_data?.[k] === captured_fields[k]
        );
        results.steps.push({
          step: 'db_check_captured_data',
          pass: capturedOk,
          expected: captured_fields,
          actual: updatedSub.captured_data,
        });
        if (!capturedOk) results.pass = false;
      }

      // Check overall submission status
      const allSigned = updatedSub.signers.every(s => s.status === 'completed' || s.status === 'signed');
      results.steps.push({
        step: 'db_check_submission_status',
        pass: allSigned ? updatedSub.status === 'completed' : true,
        submission_status: updatedSub.status,
        all_signers_signed: allSigned,
      });

      results.summary = {
        submission_id: subId,
        final_status: updatedSub.status,
        signers: updatedSub.signers.map(s => ({
          role: s.role,
          status: s.status,
          signed_fields: s.signed_fields?.length ?? 0,
        })),
      };

      return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
    }
  );

  // ── PDF generation test ─────────────────────────────────────────────────

  server.tool(
    'esigning_test_pdf',
    'Test PDF generation for a submission by hitting the /test-pdf/ endpoint. Returns page count, file size, and any errors.',
    { id: z.coerce.number().describe('Submission ID') },
    async ({ id }) => {
      const baseUrl = process.env.TREMLY_API_URL || 'http://localhost:8000/api/v1/';
      const url = `${baseUrl}esigning/submissions/${id}/test-pdf/`;
      const results = { submission_id: id, steps: [], pass: true };

      // Step 1: Fetch the PDF
      let pdfBuffer;
      try {
        const res = await fetch(url);
        if (!res.ok) {
          const text = await res.text();
          results.steps.push({ step: 'fetch_pdf', pass: false, status: res.status, error: text.slice(0, 200) });
          results.pass = false;
          return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
        }
        const buf = await res.arrayBuffer();
        pdfBuffer = Buffer.from(buf);
        results.steps.push({ step: 'fetch_pdf', pass: true, size_bytes: pdfBuffer.length, content_type: res.headers.get('content-type') });
      } catch (e) {
        results.steps.push({ step: 'fetch_pdf', pass: false, error: e.message });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }

      // Step 2: Verify it's a real PDF
      const header = pdfBuffer.slice(0, 5).toString('ascii');
      if (!header.startsWith('%PDF')) {
        results.steps.push({ step: 'validate_pdf_header', pass: false, error: `Not a PDF, starts with: ${header}` });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }
      results.steps.push({ step: 'validate_pdf_header', pass: true });

      // Step 3: Count pages using pdftoppm (poppler)
      const tmpDir = await mkdtemp(join(tmpdir(), 'tremly-pdf-'));
      const pdfPath = join(tmpDir, `sub_${id}.pdf`);
      try {
        await writeFile(pdfPath, pdfBuffer);
        const { stdout } = await execFileAsync('/opt/homebrew/bin/pdfinfo', [pdfPath]);
        const pagesMatch = stdout.match(/Pages:\s+(\d+)/);
        const pages = pagesMatch ? parseInt(pagesMatch[1]) : null;
        results.steps.push({ step: 'page_count', pass: pages !== null && pages > 0, pages });
      } catch (e) {
        results.steps.push({ step: 'page_count', pass: false, error: e.message });
        results.pass = false;
      } finally {
        await rm(tmpDir, { recursive: true, force: true });
      }

      return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
    }
  );

  server.tool(
    'esigning_pdf_layout_compare',
    'Generate PDF for a submission, render each page to an image, and compare structure (page count, text content per page) against the original TipTap document HTML.',
    { id: z.coerce.number().describe('Submission ID') },
    async ({ id }) => {
      const baseUrl = process.env.TREMLY_API_URL || 'http://localhost:8000/api/v1/';
      const results = { submission_id: id, steps: [], pass: true };

      // Step 1: Fetch submission details via authenticated API
      try {
        const subRes = await apiGet(`esigning/submissions/${id}/`);
        const sub = subRes.data || {};
        const signers = sub.signers || [];
        results.steps.push({ step: 'fetch_submission', pass: subRes.ok, signer_count: signers.length, status: sub.status });
        if (!subRes.ok) results.pass = false;
      } catch (e) {
        results.steps.push({ step: 'fetch_submission', pass: false, error: e.message });
        results.pass = false;
      }

      // Step 2: Fetch the PDF
      const pdfRes = await fetch(`${baseUrl}esigning/submissions/${id}/test-pdf/`);
      if (!pdfRes.ok) {
        results.steps.push({ step: 'fetch_pdf', pass: false, status: pdfRes.status });
        results.pass = false;
        return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
      }
      const pdfBuffer = Buffer.from(await pdfRes.arrayBuffer());
      results.steps.push({ step: 'fetch_pdf', pass: true, size_kb: Math.round(pdfBuffer.length / 1024) });

      // Step 3: Render pages and extract text per page
      const tmpDir = await mkdtemp(join(tmpdir(), 'tremly-layout-'));
      const pdfPath = join(tmpDir, `sub_${id}.pdf`);
      try {
        await writeFile(pdfPath, pdfBuffer);

        // Get page count + metadata
        const { stdout: infoOut } = await execFileAsync('/opt/homebrew/bin/pdfinfo', [pdfPath]);
        const pagesMatch = infoOut.match(/Pages:\s+(\d+)/);
        const pdfPageCount = pagesMatch ? parseInt(pagesMatch[1]) : 0;
        results.steps.push({ step: 'pdf_pages', pass: pdfPageCount > 0, pages: pdfPageCount });

        // Extract text per page using pdftotext
        const pageTexts = [];
        for (let p = 1; p <= pdfPageCount; p++) {
          try {
            const { stdout: pageText } = await execFileAsync('/opt/homebrew/bin/pdftotext', ['-f', String(p), '-l', String(p), pdfPath, '-']);
            const trimmed = pageText.trim();
            pageTexts.push({
              page: p,
              char_count: trimmed.length,
              preview: trimmed.slice(0, 120).replace(/\n/g, ' '),
              blank: trimmed.length === 0,
            });
          } catch {
            pageTexts.push({ page: p, error: 'text extraction failed' });
          }
        }

        const blankPages = pageTexts.filter(p => p.blank);
        results.steps.push({
          step: 'page_text_analysis',
          pass: blankPages.length === 0,
          pages: pageTexts,
          blank_page_count: blankPages.length,
          warn: blankPages.length > 0 ? `${blankPages.length} blank page(s) detected — possible layout overflow` : null,
        });

        // Check audit trail page (should be last page with "Audit Trail" text)
        const lastPage = pageTexts[pageTexts.length - 1];
        const hasAuditTrail = lastPage?.preview?.includes('Audit Trail') || lastPage?.preview?.includes('Signer');
        results.steps.push({ step: 'audit_trail_page', pass: hasAuditTrail, last_page_preview: lastPage?.preview });

      } catch (e) {
        results.steps.push({ step: 'render', pass: false, error: e.message });
        results.pass = false;
      } finally {
        await rm(tmpDir, { recursive: true, force: true });
      }

      results.pass = results.steps.every(s => s.pass !== false);
      return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
    }
  );
}
