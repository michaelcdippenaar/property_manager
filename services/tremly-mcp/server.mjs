import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

import { registerAuthTools } from './lib/tools/auth.mjs';
import { registerHealthTools } from './lib/tools/health.mjs';
import { registerLeaseTools } from './lib/tools/leases.mjs';
import { registerTemplateTools } from './lib/tools/templates.mjs';
import { registerBuilderTools } from './lib/tools/builder.mjs';
import { registerClauseTools } from './lib/tools/clauses.mjs';
import { registerESigningTools } from './lib/tools/esigning.mjs';
import { registerDocumentTools } from './lib/tools/documents.mjs';

const server = new McpServer({
  name: 'tremly-e2e',
  version: '1.0.0',
  description: 'MCP testing server for Tremly Property Manager backend API (E2E)',
});

// Register all tool groups
registerAuthTools(server);
registerHealthTools(server);
registerLeaseTools(server);
registerTemplateTools(server);
registerBuilderTools(server);
registerClauseTools(server);
registerESigningTools(server);
registerDocumentTools(server);

// Start with stdio transport
const transport = new StdioServerTransport();
await server.connect(transport);
