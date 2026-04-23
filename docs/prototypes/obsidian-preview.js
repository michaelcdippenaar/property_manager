// Obsidian vault markdown preview server
// Serves any .md file from the Klikk Proerty Manager vault as styled HTML.
// Usage: node obsidian-preview.js  (default port 8007)
//   http://localhost:8007/               → Tenant/Mobile App.md (default)
//   http://localhost:8007/Projects/Property_Manager/Agent/states.md
//   http://localhost:8007/_tree          → directory index

const http = require('http');
const fs = require('fs');
const path = require('path');

const VAULT = '/Users/mcdippenaar/PycharmProjects/tremly_property_manager/Klikk Proerty Manager';
const PORT = process.env.PORT || 8007;
const DEFAULT_FILE = '/Projects/Property_Manager/Tenant/Mobile App.md';

function walk(dir, base = '') {
  const out = [];
  for (const name of fs.readdirSync(dir)) {
    if (name.startsWith('.')) continue;
    const p = path.join(dir, name);
    const rel = base ? base + '/' + name : name;
    const st = fs.statSync(p);
    if (st.isDirectory()) out.push(...walk(p, rel));
    else if (name.endsWith('.md')) out.push('/' + rel);
  }
  return out;
}

function shell(title, body) {
  return `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--navy:#2B2D6E;--accent:#FF3D7F;--ink:#1A1A2E;--paper:#FAFAFC;--line:#EFEFF5;--muted:#6B6D82;--code-bg:#F4F4FA}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--paper);color:var(--ink);font-family:'DM Sans',system-ui,sans-serif;line-height:1.6}
body{display:grid;grid-template-columns:260px 1fr;min-height:100vh}
aside{position:sticky;top:0;height:100vh;overflow-y:auto;background:#fff;border-right:1px solid var(--line);padding:24px 16px;font-size:13px}
aside h2{font-family:'Fraunces',serif;font-size:15px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:0.08em;margin:16px 0 8px}
aside h2:first-child{margin-top:0}
aside a{display:block;padding:6px 10px;color:var(--ink);text-decoration:none;border-radius:6px;margin-bottom:2px;word-break:break-word}
aside a:hover{background:var(--line)}
aside a.active{background:var(--navy);color:#fff}
main{padding:48px 64px;max-width:920px}
main h1{font-family:'Fraunces',serif;font-size:40px;font-weight:700;color:var(--navy);margin:0 0 8px;line-height:1.15}
main h2{font-family:'Fraunces',serif;font-size:28px;font-weight:600;color:var(--navy);margin:40px 0 12px;padding-top:24px;border-top:1px solid var(--line)}
main h2:first-of-type{border-top:none;padding-top:0}
main h3{font-family:'Fraunces',serif;font-size:20px;font-weight:600;color:var(--ink);margin:28px 0 8px}
main h4{font-size:15px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;color:var(--muted);margin:20px 0 6px}
main blockquote{margin:16px 0;padding:12px 20px;border-left:3px solid var(--accent);background:#fff5f9;color:var(--ink);font-style:italic;border-radius:0 8px 8px 0}
main blockquote p{margin:0}
main p{margin:10px 0}
main a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(255,61,127,0.3)}
main a:hover{border-bottom-color:var(--accent)}
main ul,main ol{padding-left:24px}
main li{margin:4px 0}
main input[type=checkbox]{margin-right:8px;accent-color:var(--accent);transform:translateY(1px)}
main table{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px;background:#fff;border-radius:8px;overflow:hidden;border:1px solid var(--line)}
main th{background:var(--navy);color:#fff;text-align:left;padding:10px 14px;font-weight:500;font-size:13px}
main td{padding:10px 14px;border-top:1px solid var(--line);vertical-align:top}
main tr:nth-child(even) td{background:var(--paper)}
main code{background:var(--code-bg);padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px;color:var(--navy)}
main pre{background:#1A1A2E;color:#E5E7F0;padding:16px 20px;border-radius:8px;overflow-x:auto;font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px;line-height:1.5}
main pre code{background:none;color:inherit;padding:0}
main hr{border:none;border-top:1px solid var(--line);margin:40px 0}
main strong{color:var(--navy);font-weight:600}
.badge{display:inline-block;background:var(--accent);color:#fff;padding:2px 10px;border-radius:100px;font-size:12px;font-weight:500;margin-left:8px;vertical-align:middle}
.breadcrumb{font-size:13px;color:var(--muted);margin-bottom:24px}
.breadcrumb a{color:var(--muted)}
.meta{color:var(--muted);font-size:13px;margin-bottom:32px;font-family:'JetBrains Mono',monospace}
@media(max-width:900px){body{grid-template-columns:1fr}aside{display:none}main{padding:32px 24px}}
</style>
</head><body>${body}</body></html>`;
}

function sidebar(files, currentPath) {
  const groups = {};
  for (const f of files) {
    const parts = f.replace(/^\//, '').split('/');
    const top = parts[0] || 'root';
    const key = parts.length > 2 ? parts.slice(0, -1).join('/') : top;
    (groups[key] = groups[key] || []).push(f);
  }
  const orderedKeys = Object.keys(groups).sort();
  let html = '<aside>';
  for (const k of orderedKeys) {
    html += `<h2>${k.replace(/^Projects\/Property_Manager\/?/, '') || 'Root'}</h2>`;
    for (const f of groups[k].sort()) {
      const name = f.split('/').pop().replace('.md', '');
      const active = f === currentPath ? ' class="active"' : '';
      html += `<a href="${encodeURI(f)}"${active}>${name}</a>`;
    }
  }
  html += '</aside>';
  return html;
}

// minimal markdown renderer — enough for our notes
function md2html(src) {
  // code blocks first (placeholder replace)
  const codeBlocks = [];
  src = src.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    codeBlocks.push(`<pre><code class="lang-${lang}">${code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`);
    return `\u0001CODE${codeBlocks.length - 1}\u0001`;
  });

  // escape html in the rest
  src = src.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // headings
  src = src.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  src = src.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  src = src.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  src = src.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // horizontal rule
  src = src.replace(/^---+$/gm, '<hr>');

  // blockquotes
  src = src.replace(/^&gt; ?(.+)$/gm, '<blockquote><p>$1</p></blockquote>');
  src = src.replace(/<\/blockquote>\n<blockquote>/g, '\n');

  // tables — detect ---|--- rows
  src = src.replace(/^\|(.+)\|\n\|([-:|\s]+)\|\n((?:\|.+\|\n?)+)/gm, (_, header, _align, rows) => {
    const hCells = header.split('|').map(c => c.trim()).filter((_, i, a) => i < a.length);
    const rowLines = rows.trim().split('\n');
    let t = '<table><thead><tr>';
    for (const c of hCells) t += `<th>${c}</th>`;
    t += '</tr></thead><tbody>';
    for (const r of rowLines) {
      const cells = r.replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      t += '<tr>';
      for (const c of cells) t += `<td>${c}</td>`;
      t += '</tr>';
    }
    t += '</tbody></table>';
    return t;
  });

  // inline formatting
  src = src.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, (_, p, label) => `<a href="/${encodeURI(p.trim())}.md">${label}</a>`);
  src = src.replace(/\[\[([^\]]+)\]\]/g, (_, p) => {
    const name = p.split('/').pop();
    return `<a href="/Projects/Property_Manager/${encodeURI(p)}.md">${name}</a>`;
  });
  src = src.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  src = src.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  src = src.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');
  src = src.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // task list items
  src = src.replace(/^- \[ \] (.+)$/gm, '<li><input type="checkbox" disabled> $1</li>');
  src = src.replace(/^- \[x\] (.+)$/gmi, '<li><input type="checkbox" checked disabled> $1</li>');
  // bullets
  src = src.replace(/^- (.+)$/gm, '<li>$1</li>');
  // ordered
  src = src.replace(/^\d+\.\s+(.+)$/gm, '<li class="ol">$1</li>');

  // wrap consecutive <li> into <ul> (or <ol>)
  src = src.replace(/(<li class="ol">[\s\S]*?<\/li>(?:\n<li class="ol">[\s\S]*?<\/li>)*)/g, m => `<ol>${m.replace(/ class="ol"/g, '')}</ol>`);
  src = src.replace(/(<li>[\s\S]*?<\/li>(?:\n<li>[\s\S]*?<\/li>)*)/g, m => `<ul>${m}</ul>`);

  // paragraphs — lines not already wrapped become <p>
  src = src.split('\n\n').map(block => {
    if (/^\s*<(h[1-6]|ul|ol|li|pre|blockquote|table|hr)/.test(block.trim())) return block;
    if (!block.trim()) return '';
    return `<p>${block.trim().replace(/\n/g, ' ')}</p>`;
  }).join('\n\n');

  // restore code blocks
  src = src.replace(/\u0001CODE(\d+)\u0001/g, (_, i) => codeBlocks[+i]);
  return src;
}

http.createServer((req, res) => {
  let u = decodeURIComponent(req.url.split('?')[0]);
  if (u === '/' || u === '/index') u = DEFAULT_FILE;

  if (u === '/_tree') {
    const files = walk(VAULT);
    res.writeHead(200, { 'Content-Type': 'text/html' });
    return res.end(shell('Vault tree', sidebar(files, null) + '<main><h1>Vault tree</h1><p>Click any note in the sidebar.</p></main>'));
  }

  if (!u.endsWith('.md')) {
    res.writeHead(404); return res.end('Only .md files supported.');
  }

  const filePath = path.join(VAULT, u);
  fs.readFile(filePath, 'utf8', (err, content) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      return res.end('Not found: ' + u);
    }
    const files = walk(VAULT);
    const title = u.split('/').pop().replace('.md', '');
    const breadcrumb = `<div class="breadcrumb">${u.split('/').filter(Boolean).slice(0, -1).join(' / ')}</div>`;
    const body = sidebar(files, u) + `<main>${breadcrumb}${md2html(content)}</main>`;
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(shell(title + ' — Klikk vault', body));
  });
}).listen(PORT, () => {
  console.log(`Obsidian preview on http://localhost:${PORT}`);
  console.log(`Default: ${DEFAULT_FILE}`);
});
