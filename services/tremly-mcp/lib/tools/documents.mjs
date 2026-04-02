import { z } from 'zod';
import { apiPost, apiPostFormData } from '../http-client.mjs';
import { readFile } from 'node:fs/promises';
import { basename } from 'node:path';

export function registerDocumentTools(server) {
  server.tool(
    'document_parse',
    'Parse an uploaded lease document (PDF/DOCX) using AI',
    { file_path: z.string() },
    async ({ file_path }) => {
      try {
        const fileBuffer = await readFile(file_path);
        const fileName = basename(file_path);
        const blob = new Blob([fileBuffer]);

        const formData = new FormData();
        formData.append('file', blob, fileName);

        const result = await apiPostFormData('leases/parse-document/', formData, { timeout: 120000 });
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      } catch (e) {
        return {
          content: [{ type: 'text', text: JSON.stringify({ ok: false, error: e.message, status: 0 }, null, 2) }],
        };
      }
    }
  );

  server.tool(
    'lease_import',
    'Import parsed lease data atomically',
    { data: z.record(z.any()) },
    async ({ data }) => {
      const result = await apiPost('leases/import/', data, { timeout: 60000 });
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    }
  );
}
