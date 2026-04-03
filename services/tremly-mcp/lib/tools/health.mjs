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

// Merge field audit rules
const ROW_RULES = [
  { rowPattern: /email/i,           fieldMustContain: 'email',  fieldMustNotContain: 'phone' },
  { rowPattern: /phone|contact no/i, fieldMustContain: 'phone', fieldMustNotContain: 'email' },
];
const LABEL_RULES = [
  { labelContains: 'email', fieldMustContain: 'email' },
  { labelContains: 'phone', fieldMustContain: 'phone' },
];

async function auditTemplateMergeFields() {
  const listRes = await apiGet('leases/templates/');
  const templates = listRes.data?.results ?? listRes.data ?? [];
  const templateResults = [];

  for (const tmpl of templates) {
    const detail = await apiGet(`leases/templates/${tmpl.id}/`);
    const contentHtml = detail.data?.content_html || '';
    let html = contentHtml;
    try { const p = JSON.parse(contentHtml); if (p?.html) html = p.html; } catch {}
    if (!html) { templateResults.push({ id: tmpl.id, name: tmpl.name, issues: [], note: 'no content' }); continue; }

    const issues = [];

    // Row context check: email row must not use a phone field, and vice versa
    for (const rule of ROW_RULES) {
      const re = new RegExp(rule.rowPattern.source + '[^<]{0,20}<span[^>]+data-field-name="([^"]+)"', 'gi');
      let m;
      while ((m = re.exec(html)) !== null) {
        const fn = m[1];
        if (rule.fieldMustNotContain && fn.includes(rule.fieldMustNotContain)) {
          issues.push({ type: 'row_mismatch', rowContext: m[0].slice(0, 80), fieldName: fn, expected: `contains "${rule.fieldMustContain}"` });
        }
      }
    }

    // Label vs field-name check
    const spanRe = /data-label="([^"]+)"[^>]*data-field-name="([^"]+)"|data-field-name="([^"]+)"[^>]*data-label="([^"]+)"/g;
    let sm;
    while ((sm = spanRe.exec(html)) !== null) {
      const label = (sm[1] || sm[4] || '').toLowerCase();
      const fieldName = (sm[2] || sm[3] || '').toLowerCase();
      for (const lr of LABEL_RULES) {
        if (label.includes(lr.labelContains) && !fieldName.includes(lr.fieldMustContain)) {
          issues.push({ type: 'label_mismatch', label: sm[1] || sm[4], fieldName: sm[2] || sm[3], expected: `field containing "${lr.fieldMustContain}"` });
        }
      }
    }

    templateResults.push({ id: tmpl.id, name: tmpl.name, pass: issues.length === 0, issues });
  }

  return templateResults;
}

export function registerHealthTools(server) {
  server.tool(
    'health_check',
    'Ping all backend API endpoints and run template merge field audit. Returns a full status table.',
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
          results.push({ endpoint: ep.name, path: ep.path, status: res.ok ? 'OK' : 'ERROR', code: res.status });
        } catch (e) {
          results.push({ endpoint: ep.name, path: ep.path, status: 'FAIL', code: 0, note: e.message });
        }
      }

      // Template merge field audit (only when authenticated)
      let templateAudit = null;
      if (isAuthenticated()) {
        try {
          const auditResults = await auditTemplateMergeFields();
          const auditPass = auditResults.every(r => r.pass !== false);
          const failingTemplates = auditResults.filter(r => r.issues?.length > 0);
          templateAudit = {
            status: auditPass ? 'OK' : 'FAIL',
            templates_checked: auditResults.length,
            templates_with_issues: failingTemplates.length,
            issues: failingTemplates,
          };
        } catch (e) {
          templateAudit = { status: 'ERROR', note: e.message };
        }
      }

      const allEndpointsOk = results.every(r => r.status === 'OK' || r.status === 'SKIP');
      const auditOk = !templateAudit || templateAudit.status === 'OK';
      const output = {
        ok: allEndpointsOk && auditOk,
        data: { results, authenticated: isAuthenticated(), template_merge_field_audit: templateAudit },
        status: 200,
      };
      return { content: [{ type: 'text', text: JSON.stringify(output, null, 2) }] };
    }
  );
}
