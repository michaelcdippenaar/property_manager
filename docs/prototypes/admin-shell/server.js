// Admin SPA shell mockup — static server
// Serves docs/prototypes/admin-shell/ on port 8008.
// Usage: node server.js
const http = require('http');
const fs   = require('fs');
const path = require('path');

const ROOT = __dirname;
const PORT = process.env.PORT || 8008;
const TYPES = { '.html':'text/html', '.css':'text/css', '.js':'application/javascript', '.svg':'image/svg+xml', '.png':'image/png', '.jpg':'image/jpeg', '.json':'application/json' };

http.createServer((req, res) => {
  let u = decodeURIComponent(req.url.split('?')[0]);
  if (u === '/') u = '/index.html';
  const f = path.join(ROOT, u);
  if (!f.startsWith(ROOT)) { res.writeHead(403); return res.end('Forbidden'); }
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); return res.end('Not found: ' + u); }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(f).toLowerCase()] || 'text/plain' });
    res.end(data);
  });
}).listen(PORT, () => console.log(`Admin shell mockup on http://localhost:${PORT}`));
