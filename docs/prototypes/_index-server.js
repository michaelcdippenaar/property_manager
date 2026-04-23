// Static server for Klikk prototypes + design-system workbench
// Launched via .claude/launch.json → "Prototypes Index"
const http = require('http');
const fs = require('fs');
const path = require('path');

const port = process.env.PORT || 8006;
const root = __dirname;

const mime = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.md': 'text/markdown; charset=utf-8',
};

/* ---------- Mockup catalogue ---------- */
const categories = [
  {
    title: 'Admin (web app)',
    subtitle: 'Desktop-first workspace for agents, owners, suppliers',
    items: [
      { file: 'agent-dashboard.html', label: 'Agent dashboard', note: '15-stage lifecycle · Tasks / Board / Properties' },
      { file: 'agent-portfolio-timeline.html', label: 'Portfolio timeline', note: 'State › Stage › Property × Months · 12mo / 1mo toggle' },
    ],
  },
  {
    title: 'Agent mobile app',
    subtitle: '“I’m at a property” — site tool, offline-first',
    items: [
      { file: 'agent-mobile.html', label: 'Agent mobile — 12 frames', note: 'Now · Inspect · Sign · Log' },
    ],
  },
  {
    title: 'Tenant mobile app',
    subtitle: 'The home you live in, the problems you need fixed',
    items: [
      { file: 'tenant-home.html', label: 'Home tab', note: 'Landing · property · lease · payments' },
      { file: 'tenant-support.html', label: 'Problems tab — 12 frames', note: 'Report · thread · resolution' },
      { file: 'tenant-calendar.html', label: 'Calendar tab — 9 frames', note: 'Rent · inspections · renewal · notices' },
    ],
  },
  {
    title: 'Sales / marketing',
    subtitle: 'Landing pages and demo assets',
    items: [
      { file: 'sales-klikk-passport.html', label: 'Klikk Passport', note: 'Tenant identity / verification pitch' },
      { file: 'sales-tenant-app.html', label: 'Tenant app sales page', note: 'Public-facing overview' },
    ],
  },
];

/* ---------- Design tokens (single source of truth for the /design page) ---------- */
const tokens = {
  brand: [
    { name: 'navy',            hex: '#2B2D6E', use: 'Primary — text, headings, accents' },
    { name: 'accent',          hex: '#FF3D7F', use: 'Accent — CTAs, focus, elevated tab' },
    { name: 'surface',         hex: '#F5F5F8', use: 'App background' },
    { name: 'surface-secondary', hex: '#F0EFF8', use: 'Card alt, hover, pressed' },
    { name: 'white',           hex: '#FFFFFF', use: 'Card surface' },
  ],
  semantic: [
    { name: 'success',         hex: '#16A34A', use: 'Paid, active, confirmed' },
    { name: 'warning',         hex: '#D97706', use: 'Due soon, pending action' },
    { name: 'danger',          hex: '#DC2626', use: 'Overdue, emergency, error' },
    { name: 'info',            hex: '#2563EB', use: 'Informational, neutral link' },
  ],
  grays: [
    { name: 'ink',             hex: '#2B2D6E', use: 'Primary text' },
    { name: 'ink-soft',        hex: '#6c6e92', use: 'Secondary text' },
    { name: 'ink-muted',       hex: '#8a8ca8', use: 'Meta, captions' },
    { name: 'border',          hex: '#EFEFF5', use: 'Dividers, hairlines' },
    { name: 'border-soft',     hex: '#F0EFF8', use: 'Inset separators' },
  ],
};

const shadows = [
  { name: 'shadow-soft',   value: '0 1px 3px rgba(43,45,110,.06), 0 4px 10px -4px rgba(43,45,110,.08)', use: 'Cards at rest' },
  { name: 'shadow-lifted', value: '0 4px 12px rgba(43,45,110,.10), 0 16px 32px -10px rgba(43,45,110,.18)', use: 'Hover, elevated content' },
  { name: 'shadow-phone',  value: '0 20px 40px -18px rgba(43,45,110,.25), 0 40px 80px -30px rgba(43,45,110,.30)', use: 'Phone mockups' },
];

const typography = {
  prototype: {
    display: `'Fraunces', serif — weight 600/700, letter-spacing -.02em`,
    body: `'DM Sans', sans-serif — weight 400/500/600`,
    scale: [
      { role: 'Page title', size: '40px', line: '1.05', weight: 700, family: 'Fraunces' },
      { role: 'Section title', size: '22px', line: '1.2', weight: 600, family: 'Fraunces' },
      { role: 'Body', size: '15px', line: '1.45', weight: 400, family: 'DM Sans' },
      { role: 'Meta', size: '12.5px', line: '1.3', weight: 400, family: 'DM Sans' },
    ],
  },
  production: {
    note: 'Admin SPA + mobile apps use Inter 15px base. Fraunces is ONLY for the prototype workbench and marketing site. Do not ship Fraunces inside the product.',
  },
};

const phoneSpec = {
  width: 320,
  height: 658,
  frame: 10,
  statusBar: 44,
  tabBar: 78,
  radius: 40,
  notes: 'Used across agent-mobile.html, tenant-support.html, tenant-calendar.html. Retina screenshots via headless Chrome at --force-device-scale-factor=2.',
};

const iconSpec = {
  library: 'Phosphor Icons',
  packages: '@phosphor-icons/vue · @phosphor-icons/react · @phosphor-icons/web',
  weights: ['thin', 'light', 'regular', 'bold', 'fill', 'duotone'],
  defaultWeight: 'regular',
  size: '18px inline · 22–24px standalone (controlled via font-size)',
  colorRule: 'currentColor — inherit from parent, never hard-coded',
  license: 'MIT · 9,000+ icons · no paid tier',
  forbidden: 'No emoji in product UI. Emoji are allowed only in marketing copy and user-generated content.',
};

/* ---------- Agent lifecycle (15 stages — from content/product/lifecycle.yaml)
   `legal` field anchors the stage to POPIA / RHA / FICA / ECTA references
   (skill: klikk-legal-POPIA-RHA). Pills render on stage cards. ---------- */
const agentLifecycle = [
  { step: 1,  phase: 'pre',       title: 'Notice',         desc: 'Tenant or landlord gives 2-month written notice — triggers marketing', protos: ['tenant-calendar.html', 'agent-dashboard.html'],
    legal: [
      { act: 'rha',   ref: 's5(2)(b)',     note: 'Notice of termination must be in writing' },
    ] },
  { step: 2,  phase: 'pre',       title: 'Market',         desc: 'List vacancy on Property24, Private Property, social media',         protos: ['agent-dashboard.html'],
    legal: [
      { act: 'popia', ref: 's69',          note: 'Direct marketing to past leads needs Form 4 consent or existing-customer carve-out' },
    ] },
  { step: 3,  phase: 'pre',       title: 'Viewings',       desc: 'Schedule and conduct viewings while previous tenant occupies',        protos: ['agent-mobile.html', 'agent-dashboard.html'],
    legal: [
      { act: 'popia', ref: 's11(1)(b)',    note: 'Lawful basis: pre-contract steps' },
      { act: 'popia', ref: 's18',          note: 'Notify viewing visitor at point of collection (privacy notice)' },
    ] },
  { step: 4,  phase: 'pre',       title: 'Screen',         desc: 'AI scores applicants: credit, criminal, ID, employment, rental history', protos: ['agent-mobile.html', 'agent-dashboard.html'],
    legal: [
      { act: 'popia', ref: 's27 + s35',    note: 'Criminal record is special PI — requires explicit consent' },
      { act: 'popia', ref: 's20–21',       note: 'Credit bureau (TransUnion etc.) is an Operator — DPA required' },
      { act: 'popia', ref: 's71',          note: 'AI scoring may be automated decision-making — disclose + allow human review' },
    ] },
  { step: 5,  phase: 'pre',       title: 'Lease',          desc: 'AI generates RHA-compliant lease, e-sign from any device',           protos: ['agent-mobile.html', 'agent-dashboard.html'],
    legal: [
      { act: 'rha',   ref: 's5(3)',        note: 'Mandatory lease terms — name/address/deposit/rules/inspection schedule' },
      { act: 'rha',   ref: 's5(6)',        note: 'Tenant entitled to written copy on demand, free of charge' },
      { act: 'ecta',  ref: 's13',          note: 'E-signature legally valid in SA (advanced e-sig not required for residential lease)' },
    ] },
  { step: 6,  phase: 'pre',       title: 'Invoicing',      desc: 'Configure recurring rent schedule, escalation, payment method',      protos: ['agent-dashboard.html'],
    legal: [
      { act: 'popia', ref: 's11(1)(b)',    note: 'Lawful basis: contract performance' },
      { act: 'rha',   ref: 's4A(2)(b)',    note: 'No charging admin fees beyond what the lease lists (unfair practice if hidden)' },
    ] },
  { step: 7,  phase: 'pre',       title: 'Deposit',        desc: 'Collect deposit + first month; lodge in interest-bearing account',   protos: ['agent-dashboard.html'],
    legal: [
      { act: 'rha',   ref: 's5(3)(b)–(c)', note: 'Deposit must be lodged in interest-bearing account; interest accrues for tenant from lodge date' },
      { act: 'rha',   ref: 's16(a)',       note: 'Commingling deposit with operating funds is a criminal offence' },
    ] },
  { step: 8,  phase: 'turnaround',title: 'Move-Out',       desc: 'Joint outgoing inspection, photos, signed report, keys returned',    protos: ['agent-mobile.html'],
    legal: [
      { act: 'rha',   ref: 's5(3)(g)',     note: 'Joint outgoing inspection within 3 days of expiry — failure = waiver of damage claims' },
    ] },
  { step: 9,  phase: 'turnaround',title: 'Repairs',        desc: 'Overnight contractors work from snag list — clean, paint, fix',     protos: ['tenant-support.html', 'agent-mobile.html'],
    legal: [
      { act: 'popia', ref: 's20–21',       note: 'Each supplier receiving tenant contact = Operator. DPA required.' },
    ] },
  { step: 10, phase: 'turnaround',title: 'Move-In',        desc: 'Joint incoming inspection with photo evidence, signed report',       protos: ['agent-mobile.html'],
    legal: [
      { act: 'rha',   ref: 's5(3)(e)–(f)', note: 'Joint incoming inspection within 7 days of move-in — defects noted, not later disputed' },
    ] },
  { step: 11, phase: 'turnaround',title: 'Onboard',        desc: 'Keys, utilities transfer, welcome pack, tenant portal setup',        protos: ['tenant-home.html'],
    legal: [
      { act: 'popia', ref: 's18',          note: 'Privacy notice to tenant at point of full data collection' },
    ] },
  { step: 12, phase: 'active',    title: 'Rent',           desc: 'Monthly invoices, payment tracking, receipts on request',            protos: ['tenant-home.html', 'agent-dashboard.html'],
    legal: [
      { act: 'rha',   ref: 's5(3)(d)',     note: 'Receipt required on demand — date, amount, period, property' },
      { act: 'fica',  ref: 's21A',         note: 'Payment records retained 5 years (FICA outranks POPIA s14 here)' },
    ] },
  { step: 13, phase: 'active',    title: 'Maintain',       desc: 'AI triage, supplier matching, dispatch, tenant app tickets',         protos: ['tenant-support.html', 'agent-mobile.html'],
    legal: [
      { act: 'popia', ref: 's20–21',       note: 'Suppliers receive tenant PI (name, phone, address, photos) — Operator agreement applies' },
      { act: 'rha',   ref: 's4A(2)(c)',    note: 'Failure to maintain in habitable condition is an unfair practice' },
    ] },
  { step: 14, phase: 'active',    title: 'Renew / Notice', desc: 'Renewal at 80 biz days; renew, month-to-month, or vacate → stage 1', protos: ['tenant-calendar.html', 'agent-dashboard.html'],
    legal: [
      { act: 'rha',   ref: 's4A(2)(d)',    note: 'Late renewal notice = unfair practice (Tribunal jurisdiction)' },
      { act: 'cpa',   ref: 's14',          note: '20 business days notice if month-to-month per CPA fixed-term rules' },
    ] },
  { step: 15, phase: 'closeout',  title: 'Refund',         desc: 'Itemised deposit refund with all accrued interest within 7/14/21 days', protos: [],
    legal: [
      { act: 'rha',   ref: 's5(3)(g)–(i)', note: '7 days (no damage) · 14 days (after repairs) · 21 days (no inspection done)' },
      { act: 'rha',   ref: 's16(a)',       note: 'Failure to refund or pay interest = criminal offence' },
    ] },
];

const agentPhases = {
  pre:        { label: 'Pre-tenancy',   hue: '#2B2D6E', soft: '#F0EFF8', desc: 'Stages 1–7 · previous tenant still occupies' },
  turnaround: { label: 'Turnaround',    hue: '#FF3D7F', soft: '#FFE4EF', desc: 'Stages 8–11 · overnight, PM move-out → AM move-in' },
  active:     { label: 'Active tenancy',hue: '#16A34A', soft: '#E6F4EB', desc: 'Stages 12–14 · 12-month contract' },
  closeout:   { label: 'Closeout',      hue: '#D97706', soft: '#FDF3E0', desc: 'Stage 15 · deposit refund with interest' },
};

/* ---------- Tenant lifecycle (14 stages, tenant POV) ---------- */
const tenantLifecycle = [
  { step: 1,  phase: 'finding',    title: 'Search',         desc: 'Browse listings, find a place that fits budget and area',                protos: [] },
  { step: 2,  phase: 'finding',    title: 'View',           desc: 'Attend viewing, meet the agent, ask about the property',                 protos: [] },
  { step: 3,  phase: 'finding',    title: 'Apply',          desc: 'Submit application — ID, payslips, bank statements, references',        protos: ['sales-klikk-passport.html'] },
  { step: 4,  phase: 'moving-in',  title: 'Sign lease',     desc: 'Review and e-sign lease from phone. No paper, no office visit',         protos: [] },
  { step: 5,  phase: 'moving-in',  title: 'Pay deposit',    desc: 'EFT or DebiCheck: deposit + first month rent',                          protos: [] },
  { step: 6,  phase: 'moving-in',  title: 'Move-in',        desc: 'Joint incoming inspection with agent — photos as proof of condition',   protos: [] },
  { step: 7,  phase: 'moving-in',  title: 'Settle in',      desc: 'Utilities transferred, welcome pack, tenant portal access',             protos: ['tenant-home.html'] },
  { step: 8,  phase: 'living',     title: 'Pay rent',       desc: 'Monthly rent on time — tracked, receipts on demand',                    protos: ['tenant-home.html', 'tenant-calendar.html'] },
  { step: 9,  phase: 'living',     title: 'Report problem', desc: 'Something broke — report via app with photo, track repair progress',    protos: ['tenant-support.html'] },
  { step: 10, phase: 'living',     title: 'Communicate',    desc: 'Ask questions, request permission (pets, roommate change, guests)',     protos: ['tenant-support.html'] },
  { step: 11, phase: 'moving-on',  title: 'Renewal offer',  desc: 'At 80 biz days: accept renewal, negotiate, go month-to-month, or leave', protos: ['tenant-calendar.html'] },
  { step: 12, phase: 'moving-on',  title: 'Give notice',    desc: '2-month written notice if vacating — formal, in the app',                protos: ['tenant-calendar.html'] },
  { step: 13, phase: 'moving-on',  title: 'Move-out',       desc: 'Joint outgoing inspection — photos compared to move-in evidence',        protos: [] },
  { step: 14, phase: 'moving-on',  title: 'Deposit back',   desc: 'Itemised refund within 7/14/21 days — interest included',               protos: [] },
];

const tenantPhases = {
  finding:    { label: 'Finding a home', hue: '#2B2D6E', soft: '#F0EFF8', desc: 'Stages 1–3 · search, view, apply' },
  'moving-in':{ label: 'Moving in',      hue: '#FF3D7F', soft: '#FFE4EF', desc: 'Stages 4–7 · sign → keys in hand' },
  living:     { label: 'Living here',    hue: '#16A34A', soft: '#E6F4EB', desc: 'Stages 8–10 · the quiet 12 months' },
  'moving-on':{ label: 'Moving on',      hue: '#D97706', soft: '#FDF3E0', desc: 'Stages 11–14 · renewal, notice, move-out, refund' },
};

/* ---------- Owner lifecycle (11 stages, owner POV) ---------- */
const ownerLifecycle = [
  { step: 1,  phase: 'onboarding',  title: 'Onboard',             desc: 'Sign mandate with Klikk. FICA, title deed, bond statement, banking',   protos: [] },
  { step: 2,  phase: 'per-tenant',  title: 'Approve listing',     desc: 'Review marketing copy, photos, asking rent before it goes live',      protos: [] },
  { step: 3,  phase: 'per-tenant',  title: 'Approve tenant',      desc: 'Review screening results on shortlisted applicants — pick 1',          protos: [] },
  { step: 4,  phase: 'per-tenant',  title: 'Approve lease',       desc: 'Review lease terms, escalation %, special clauses. Countersign',      protos: [] },
  { step: 5,  phase: 'per-tenant',  title: 'Move-in confirmed',   desc: 'Deposit lodged in trust, signed inspection report, keys handed',      protos: [] },
  { step: 6,  phase: 'operating',   title: 'Monthly statement',   desc: 'Rent collected → commission + fees deducted → payout to bank account', protos: [] },
  { step: 7,  phase: 'operating',   title: 'Approve repairs',     desc: 'Any maintenance above threshold (default R2,500) needs your OK',       protos: [] },
  { step: 8,  phase: 'transitions', title: 'Annual inspection',   desc: 'Routine condition check — dashboard summary with photos',              protos: [] },
  { step: 9,  phase: 'transitions', title: 'Renewal decision',    desc: 'Renew, escalate rent, go month-to-month, or replace tenant',           protos: [] },
  { step: 10, phase: 'transitions', title: 'Move-out review',     desc: 'Approve deposit deductions based on outgoing inspection',              protos: [] },
  { step: 11, phase: 'transitions', title: 'Turnaround spend',    desc: 'Approve refurb, painting, deep clean for next tenancy',                protos: [] },
];

const ownerPhases = {
  onboarding:   { label: 'Onboarding',  hue: '#2B2D6E', soft: '#F0EFF8', desc: 'Stage 1 · bring property into Klikk' },
  'per-tenant': { label: 'Per-tenant',  hue: '#FF3D7F', soft: '#FFE4EF', desc: 'Stages 2–5 · 4 approvals, once per tenancy' },
  operating:    { label: 'Operating',   hue: '#16A34A', soft: '#E6F4EB', desc: 'Stages 6–7 · monthly rhythm' },
  transitions:  { label: 'Transitions', hue: '#D97706', soft: '#FDF3E0', desc: 'Stages 8–11 · year-end + turnaround' },
};

/* ---------- Handoff moments — where roles converge ---------- */
const roleStyle = {
  agent:  { label: 'Agent',  hue: '#2B2D6E' },
  tenant: { label: 'Tenant', hue: '#16A34A' },
  owner:  { label: 'Owner',  hue: '#D97706' },
};

const handoffMoments = [
  {
    title: 'Tenant selection',
    when: 'Pre-tenancy · stage 4',
    who: ['agent', 'owner'],
    agent:  'Screen applicants, rank, shortlist top 1–3 with recommendation',
    owner:  'Review shortlist, approve the pick',
    tenant: 'Waits quietly — no visibility yet',
  },
  {
    title: 'Lease signing',
    when: 'Pre-tenancy · stage 5',
    who: ['agent', 'owner', 'tenant'],
    agent:  'Draft RHA-compliant lease, trigger e-signing flow',
    owner:  'Review terms, countersign',
    tenant: 'Review, e-sign from phone',
  },
  {
    title: 'Move-in inspection',
    when: 'Turnaround · stage 10',
    who: ['agent', 'tenant'],
    agent:  'Lead inspection, capture photos, document condition',
    tenant: 'Walk property with agent, sign report',
    owner:  'Receives signed PDF in dashboard — no action needed',
  },
  {
    title: 'Monthly rent',
    when: 'Active · stage 12 (×12)',
    who: ['tenant', 'agent', 'owner'],
    agent:  'Reconcile payment, deduct fees, disburse',
    owner:  'Receive payout + statement in bank',
    tenant: 'Pay via EFT, DebiCheck, or in-app',
  },
  {
    title: 'Routine maintenance',
    when: 'Active · stage 13',
    who: ['tenant', 'agent', 'owner'],
    agent:  'Triage ticket, match supplier, dispatch (or escalate if &gt; R2,500)',
    owner:  'Approve spend if above threshold',
    tenant: 'Report problem with photo, track progress',
  },
  {
    title: 'Emergency',
    when: 'Active · any time',
    who: ['tenant', 'agent'],
    agent:  'Dispatch trusted supplier immediately, no approval needed',
    tenant: 'Hit emergency button, document damage',
    owner:  'Informed after the fact with invoice',
  },
  {
    title: 'Renewal decision',
    when: 'Active · stage 14, at 80 biz days',
    who: ['owner', 'agent', 'tenant'],
    owner:  'Set renewal terms, escalation %',
    agent:  'Draft renewal, send to tenant',
    tenant: 'Accept, counter-offer, or give notice',
  },
  {
    title: 'Notice period',
    when: 'Active → pre-tenancy · stages 1–3',
    who: ['tenant', 'agent'],
    tenant: 'Give 2-month notice, arrange viewing access',
    agent:  'Re-list, schedule viewings, screen next applicants',
    owner:  'Notified, previews incoming applicants',
  },
  {
    title: 'Move-out',
    when: 'Turnaround · stage 8',
    who: ['agent', 'tenant', 'owner'],
    agent:  'Lead outgoing inspection, compare to move-in evidence',
    tenant: 'Walk property, sign report, return keys',
    owner:  'Review proposed deductions',
  },
  {
    title: 'Deposit refund',
    when: 'Closeout · stage 15',
    who: ['agent', 'owner', 'tenant'],
    agent:  'Itemise deductions, calculate interest',
    owner:  'Approve final amount',
    tenant: 'Receive refund + itemised breakdown',
  },
];

/* ---------- Icon library (Phosphor icon names — rendered via @phosphor-icons/web CDN) ---------- */
const iconGroups = [
  {
    title: 'Navigation & structure',
    icons: ['house', 'calendar-blank', 'chat-circle', 'gear-six', 'list', 'magnifying-glass', 'bell', 'user-circle'],
  },
  {
    title: 'Actions & controls',
    icons: ['plus', 'check', 'x', 'caret-right', 'caret-down', 'arrow-right', 'dots-three', 'funnel'],
  },
  {
    title: 'Property & places',
    icons: ['house-line', 'buildings', 'key', 'door-open', 'map-pin', 'map-trifold', 'storefront', 'garage'],
  },
  {
    title: 'People & identity',
    icons: ['user', 'users', 'user-plus', 'identification-card', 'identification-badge', 'hand-shake', 'seal-check'],
  },
  {
    title: 'Documents & forms',
    icons: ['file-text', 'clipboard-text', 'pen', 'signature', 'paperclip', 'scroll', 'files', 'note-pencil'],
  },
  {
    title: 'Money & billing',
    icons: ['credit-card', 'wallet', 'money', 'receipt', 'coin', 'bank', 'currency-circle-dollar', 'invoice'],
  },
  {
    title: 'Status & alerts',
    icons: ['check-circle', 'x-circle', 'warning-circle', 'warning', 'clock', 'clock-countdown', 'seal-check', 'info'],
  },
  {
    title: 'Media & capture',
    icons: ['camera', 'image-square', 'images', 'upload-simple', 'download-simple', 'paperclip', 'qr-code'],
  },
  {
    title: 'Maintenance & trades',
    icons: ['wrench', 'hammer', 'toolbox', 'lightning', 'drop', 'flame', 'paint-roller', 'broom'],
  },
  {
    title: 'Communication',
    icons: ['phone', 'phone-call', 'envelope', 'envelope-simple', 'chat-text', 'chat-teardrop-text', 'paper-plane-tilt', 'whatsapp-logo'],
  },
];

const iconWeights = [
  { key: 'thin',    stroke: 'Ultra-thin 1px — ghost affordances, dense panels' },
  { key: 'light',   stroke: 'Light 1.25px — secondary meta, low-emphasis rails' },
  { key: 'regular', stroke: 'Default 1.5px — body UI, most screens' },
  { key: 'bold',    stroke: 'Heavy 2px — primary CTAs, emphasis, alerts' },
  { key: 'fill',    stroke: 'Solid fill — active nav, selected state, badges' },
  { key: 'duotone', stroke: 'Accent + outline — illustration, empty states' },
];

const weightUsage = [
  { role: 'Inactive bottom-tab',   weight: 'regular', why: 'Quiet, present, not demanding' },
  { role: 'Active bottom-tab',     weight: 'fill',    why: 'Pairs with the elevated pink cushion — solid mass reads clearly at 28px' },
  { role: 'Primary CTA buttons',   weight: 'bold',    why: 'Matches DM Sans 600 label weight' },
  { role: 'Inline body icons',     weight: 'regular', why: 'Reads at 18px next to 15px text without overpowering' },
  { role: 'Meta rows, timestamps', weight: 'light',   why: 'De-emphasises, lets text carry meaning' },
  { role: 'Status chips',          weight: 'fill',    why: 'Small canvas (14px) — fill survives the downscale' },
  { role: 'Empty-state hero',      weight: 'duotone', why: 'Navy outline + pink accent for illustrative moments' },
  { role: 'Destructive actions',   weight: 'bold',    why: 'Pairs with danger-600 for serious affordance' },
];

/* ---------- Page rendering ---------- */
function layout(activeKey, title, inner) {
  const navGroups = [
    {
      label: 'Product',
      items: [
        { key: 'overview',   href: '/app',        label: 'Overview',    icon: 'book'   },
        { key: 'datamodel',  href: '/data-model', label: 'Data model',  icon: 'cube'   },
        { key: 'ia',         href: '/ia',         label: 'IA & routes', icon: 'sitemap'},
        { key: 'api',        href: '/api',        label: 'API',         icon: 'plug'   },
        { key: 'rbac',       href: '/rbac',       label: 'RBAC',        icon: 'lock'   },
        { key: 'rules',      href: '/rules',      label: 'Business rules', icon: 'gavel' },
        { key: 'integrations', href: '/integrations', label: 'Integrations', icon: 'wires' },
        { key: 'tests',      href: '/tests',      label: 'Tests',       icon: 'flask'  },
        { key: 'env',        href: '/env',        label: 'Environment', icon: 'server' },
        { key: 'copy',       href: '/copy',       label: 'Copy library',icon: 'quote'  },
      ],
    },
    {
      label: 'Design Pack',
      items: [
        { key: 'mockups',    href: '/',           label: 'Mockups',       icon: 'monitor' },
        { key: 'design',     href: '/design',     label: 'Design system', icon: 'palette' },
        { key: 'components', href: '/components', label: 'Components',    icon: 'stack'   },
        { key: 'logos',      href: '/logos',      label: 'Logos',         icon: 'logo'    },
        { key: 'icons',      href: '/icons',      label: 'Icons',         icon: 'shapes'  },
      ],
    },
    {
      label: 'Strategy',
      items: [
        { key: 'flows',   href: '/flows',   label: 'Flows',         icon: 'route'   },
        { key: 'data',    href: '/data',    label: 'Data flow',     icon: 'shield'  },
      ],
    },
  ];
  const icons = {
    monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
    palette: '<circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
    route:   '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    shapes:  '<path d="M8.3 10a.7.7 0 0 1-.626-1.079L11.4 3a.7.7 0 0 1 1.198-.043L16.3 8.9a.7.7 0 0 1-.572 1.1Z"/><rect x="3" y="14" width="7" height="7" rx="1"/><circle cx="17.5" cy="17.5" r="3.5"/>',
    logo:    '<rect x="3" y="3" width="18" height="18" rx="4"/><text x="9" y="16" font-family="Inter,sans-serif" font-size="10" font-weight="700" fill="currentColor" stroke="none">K</text><circle cx="16" cy="15" r="1.4" fill="currentColor" stroke="none"/>',
    shield:  '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    book:    '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    stack:   '<path d="M12 2 2 7l10 5 10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    cube:    '<path d="m21 16-9 5-9-5V8l9-5 9 5v8Z"/><path d="m3.27 6.96 8.73 5.05 8.73-5.05"/><path d="M12 22.08V12"/>',
    sitemap: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><path d="M10 6.5h4M6.5 10v4M17.5 10v4"/>',
    plug:    '<path d="M9 2v4M15 2v4"/><path d="M7 6h10v4a5 5 0 0 1-10 0V6Z"/><path d="M12 15v7"/>',
    lock:    '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    gavel:   '<path d="m14 12-8 8a2.83 2.83 0 1 1-4-4l8-8"/><path d="m15 13 6-6"/><path d="m9 7 6-6 6 6-6 6z"/><path d="M3 21h18"/>',
    wires:   '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M6 8v4a4 4 0 0 0 4 4h4a4 4 0 0 1 4 4"/>',
    flask:   '<path d="M9 2v6L3.5 18A2 2 0 0 0 5.24 21h13.52a2 2 0 0 0 1.74-3L15 8V2"/><path d="M9 2h6"/><path d="M7 14h10"/>',
    server:  '<rect x="2" y="4" width="20" height="7" rx="2"/><rect x="2" y="13" width="20" height="7" rx="2"/><line x1="6" y1="7.5" x2="6.01" y2="7.5"/><line x1="6" y1="16.5" x2="6.01" y2="16.5"/>',
    quote:   '<path d="M3 21c3 0 7-1 7-8V5c0-1.25-.76-2.02-2-2H4c-1.25 0-2 .75-2 1.97V11c0 1.25.75 2 2 2h3"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.76-2.02-2-2h-4c-1.25 0-2 .75-2 1.97V11c0 1.25.75 2 2 2h3"/>',
  };
  const renderItem = n => `
    <a href="${n.href}" class="nav-item ${n.key === activeKey ? 'active' : ''}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${icons[n.icon]}</svg>
      <span>${n.label}</span>
    </a>`;
  const navHtml = navGroups.map(g => `
    <div class="nav-label">${g.label}</div>
    ${g.items.map(renderItem).join('')}
  `).join('');

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Klikk Prototypes — ${title}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:#F5F5F8;color:#2B2D6E;font-family:'DM Sans',-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
  a{color:inherit}
  /* Layout shell */
  .shell{display:grid;grid-template-columns:240px 1fr;min-height:100vh}
  aside{position:sticky;top:0;height:100vh;background:#fff;border-right:1px solid #EFEFF5;padding:28px 16px;display:flex;flex-direction:column;gap:6px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#D5D6E2 transparent}
  aside::-webkit-scrollbar{width:6px}
  aside::-webkit-scrollbar-thumb{background:#D5D6E2;border-radius:3px}
  aside::-webkit-scrollbar-thumb:hover{background:#B7B9CE}
  aside::-webkit-scrollbar-track{background:transparent}
  .brand{padding:4px 10px 20px;display:flex;align-items:center;gap:10px}
  .brand-mark{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,#2B2D6E,#FF3D7F);display:flex;align-items:center;justify-content:center;color:#fff;font-family:'Fraunces',serif;font-weight:700;font-size:14px}
  .brand-name{font-family:'Fraunces',serif;font-weight:700;font-size:17px;letter-spacing:-.01em}
  .nav-label{font-size:11px;font-weight:600;letter-spacing:.08em;color:#8a8ca8;text-transform:uppercase;padding:14px 10px 6px}
  .nav-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:10px;text-decoration:none;color:#6c6e92;font-size:14px;font-weight:500;transition:all .12s}
  .nav-item svg{width:18px;height:18px;flex-shrink:0}
  .nav-item:hover{background:#FAFAFE;color:#2B2D6E}
  .nav-item.active{background:#F0EFF8;color:#2B2D6E}
  aside .bottom{margin-top:auto;padding:12px 10px;font-size:11px;color:#b0b2cc}
  aside .bottom code{font-family:ui-monospace,Menlo,monospace;color:#8a8ca8}
  main{padding:56px 48px 96px;min-width:0}
  .page{max-width:860px;margin:0 auto}
  h1{font-family:'Fraunces',serif;font-weight:700;font-size:40px;letter-spacing:-.02em;margin:0 0 6px}
  .lede{color:#6c6e92;font-size:15px;margin:0 0 40px}
  h2{font-family:'Fraunces',serif;font-weight:600;font-size:22px;letter-spacing:-.01em;margin:0 0 2px;color:#2B2D6E}
  h3{font-family:'DM Sans',sans-serif;font-weight:600;font-size:14px;letter-spacing:.02em;color:#6c6e92;text-transform:uppercase;margin:0 0 10px}
  section{margin-bottom:40px}
  section > header{margin-bottom:14px;padding:0 4px}
  section > header p{margin:0;color:#8a8ca8;font-size:13px}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;background:#F0EFF8;padding:1.5px 6px;border-radius:4px;color:#2B2D6E}
  @media (max-width:820px){
    .shell{grid-template-columns:1fr}
    aside{position:static;height:auto;border-right:0;border-bottom:1px solid #EFEFF5;padding:16px}
    aside .bottom{display:none}
    main{padding:32px 20px 80px}
  }
</style>
</head>
<body>
<div class="shell">
  <aside>
    <div class="brand">
      <div class="brand-mark">K</div>
      <div class="brand-name">Klikk</div>
    </div>
    ${navHtml}
    <div class="bottom">
      <div>Static server</div>
      <code>docs/prototypes/</code>
    </div>
  </aside>
  <main>
    <div class="page">${inner}</div>
  </main>
</div>
</body>
</html>`;
}

function pageMockups() {
  const existing = new Set(fs.readdirSync(root).filter(f => f.endsWith('.html')));
  const cataloged = new Set();
  categories.forEach(c => c.items.forEach(i => cataloged.add(i.file)));
  const orphans = [...existing].filter(f => !cataloged.has(f)).sort();

  const sections = categories.map(c => {
    const rows = c.items
      .filter(i => existing.has(i.file))
      .map(i => `
        <a class="row" href="/${i.file}">
          <div class="row-main">
            <div class="row-label">${i.label}</div>
            <div class="row-note">${i.note}</div>
          </div>
          <div class="row-file">${i.file}</div>
          <svg class="row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
        </a>`).join('');
    return `
      <section>
        <header>
          <h2>${c.title}</h2>
          <p>${c.subtitle}</p>
        </header>
        <div class="group">${rows}</div>
      </section>`;
  }).join('');

  const orphanBlock = orphans.length ? `
    <section>
      <header><h2>Uncategorized</h2><p>Files found but not yet grouped — edit <code>_index-server.js</code></p></header>
      <div class="group">${orphans.map(f => `<a class="row" href="/${f}"><div class="row-main"><div class="row-label">${f}</div></div><svg class="row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg></a>`).join('')}</div>
    </section>` : '';

  const css = `
    <style>
      .group{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(43,45,110,.06),0 8px 24px -12px rgba(43,45,110,.12)}
      .row{display:flex;align-items:center;gap:14px;padding:16px 18px;color:#2B2D6E;text-decoration:none;border-bottom:1px solid #EFEFF5;transition:background .12s}
      .row:last-child{border-bottom:none}
      .row:hover{background:#FAFAFE}
      .row-main{flex:1;min-width:0}
      .row-label{font-weight:500;font-size:15px;line-height:1.2}
      .row-note{color:#8a8ca8;font-size:12.5px;margin-top:3px;font-weight:400}
      .row-file{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;color:#b0b2cc;white-space:nowrap;margin-right:4px}
      .row-arrow{width:16px;height:16px;color:#c7c9dd;flex-shrink:0}
      .row:hover .row-arrow{color:#FF3D7F;transform:translateX(2px);transition:all .14s}
      @media (max-width:520px){.row-file{display:none}}
    </style>`;

  return css + `
    <h1>Mockups</h1>
    <p class="lede">Static HTML prototypes grouped by product surface.</p>
    ${sections}
    ${orphanBlock}`;
}

function pageDesign() {
  const swatch = t => `
    <div class="swatch">
      <div class="chip" style="background:${t.hex}"></div>
      <div class="swatch-body">
        <div class="swatch-name">${t.name}</div>
        <div class="swatch-meta"><code>${t.hex}</code></div>
        <div class="swatch-use">${t.use}</div>
      </div>
    </div>`;

  const shadowRow = s => `
    <div class="shadow-row">
      <div class="shadow-demo" style="box-shadow:${s.value}"></div>
      <div class="shadow-body">
        <div class="swatch-name">${s.name}</div>
        <div class="swatch-use">${s.use}</div>
        <code class="shadow-val">${s.value}</code>
      </div>
    </div>`;

  const typeRow = t => `
    <div class="type-row">
      <div class="type-sample" style="font-family:${t.family==='Fraunces'?"'Fraunces',serif":"'DM Sans',sans-serif"};font-size:${t.size};line-height:${t.line};font-weight:${t.weight};letter-spacing:${t.family==='Fraunces'?'-.01em':'0'}">${t.role}</div>
      <div class="type-meta"><code>${t.family}</code> · ${t.size} · ${t.weight}</div>
    </div>`;

  const css = `
    <style>
      .card{background:#fff;border-radius:16px;padding:24px;box-shadow:0 1px 3px rgba(43,45,110,.06),0 8px 24px -12px rgba(43,45,110,.12);margin-bottom:16px}
      .grid-swatch{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
      .swatch{display:flex;gap:12px;padding:12px;background:#FAFAFE;border-radius:12px;align-items:center}
      .chip{width:52px;height:52px;border-radius:10px;flex-shrink:0;border:1px solid rgba(43,45,110,.06)}
      .swatch-body{min-width:0}
      .swatch-name{font-weight:600;font-size:14px;color:#2B2D6E}
      .swatch-meta{margin:3px 0}
      .swatch-use{font-size:12px;color:#8a8ca8;line-height:1.35}
      .shadow-row{display:grid;grid-template-columns:96px 1fr;gap:18px;align-items:center;padding:14px 0;border-bottom:1px solid #EFEFF5}
      .shadow-row:last-child{border-bottom:0}
      .shadow-demo{width:72px;height:56px;background:#fff;border-radius:10px;margin:8px 0}
      .shadow-val{display:block;margin-top:6px;font-size:11px;color:#8a8ca8;word-break:break-all;background:none;padding:0}
      .shadow-body{min-width:0}
      .type-row{display:grid;grid-template-columns:1fr auto;gap:20px;align-items:baseline;padding:14px 0;border-bottom:1px solid #EFEFF5}
      .type-row:last-child{border-bottom:0}
      .type-sample{color:#2B2D6E}
      .type-meta{color:#8a8ca8;font-size:12px;white-space:nowrap}
      .kv{display:grid;grid-template-columns:180px 1fr;gap:10px 20px;font-size:14px}
      .kv dt{color:#8a8ca8;font-weight:500}
      .kv dd{margin:0;color:#2B2D6E}
      .callout{background:#F0EFF8;border-left:3px solid #FF3D7F;padding:12px 16px;border-radius:0 10px 10px 0;font-size:13.5px;color:#2B2D6E;line-height:1.5}
      .phone-diagram{display:flex;gap:28px;align-items:center;flex-wrap:wrap}
      .phone-box{width:168px;height:342px;background:#111;border-radius:28px;padding:6px;position:relative;flex-shrink:0;box-shadow:0 20px 40px -18px rgba(43,45,110,.25)}
      .phone-box .screen{position:absolute;inset:6px;background:#F5F5F8;border-radius:22px;overflow:hidden}
      .phone-box .sb{height:22px;background:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 10px;font-size:9px;color:#2B2D6E;font-weight:600}
      .phone-box .tb{position:absolute;left:0;right:0;bottom:0;height:40px;background:#fff;border-top:1px solid #EFEFF5}
      .phone-box .content{padding:10px;font-size:10px;color:#6c6e92}
      .tab-demo{display:flex;justify-content:space-around;align-items:center;height:100%;padding:0 12px}
      .tab-demo .t{width:14px;height:14px;border-radius:3px;background:#E0DFEA}
      .tab-demo .elev{width:22px;height:22px;border-radius:50%;background:#2B2D6E;position:relative;transform:translateY(-10px);box-shadow:0 6px 14px rgba(255,61,127,.35)}
      .tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;letter-spacing:.02em}
      .tag-proto{background:#F0EFF8;color:#2B2D6E}
      .tag-prod{background:#FFE4EF;color:#FF3D7F}
    </style>`;

  return css + `
    <h1>Design system</h1>
    <p class="lede">Tokens, typography, spacing, and component primitives driving every Klikk surface.</p>

    <section>
      <header><h2>Brand colors</h2><p>Navy + accent pink. Everything else is derived.</p></header>
      <div class="card"><div class="grid-swatch">${tokens.brand.map(swatch).join('')}</div></div>
    </section>

    <section>
      <header><h2>Semantic colors</h2><p>Status communication — never use these decoratively.</p></header>
      <div class="card"><div class="grid-swatch">${tokens.semantic.map(swatch).join('')}</div></div>
    </section>

    <section>
      <header><h2>Text & surface grays</h2><p>Ink scale + hairline borders.</p></header>
      <div class="card"><div class="grid-swatch">${tokens.grays.map(swatch).join('')}</div></div>
    </section>

    <section>
      <header><h2>Typography</h2><p>Two stacks: prototype (editorial) and production (functional).</p></header>
      <div class="card">
        <h3>Prototype stack <span class="tag tag-proto">workbench only</span></h3>
        <p style="margin:4px 0 16px;font-size:13px;color:#6c6e92">Display: <code>Fraunces</code> · Body: <code>DM Sans</code></p>
        ${typography.prototype.scale.map(typeRow).join('')}
      </div>
      <div class="card">
        <h3>Production stack <span class="tag tag-prod">ship this</span></h3>
        <div class="callout">${typography.production.note}</div>
      </div>
    </section>

    <section>
      <header><h2>Shadows</h2><p>Three tiers — rest, lifted, phone. Nothing else.</p></header>
      <div class="card">${shadows.map(shadowRow).join('')}</div>
    </section>

    <section>
      <header><h2>Phone mockup spec</h2><p>Dimensions used across every mobile prototype. Captured at 2x.</p></header>
      <div class="card">
        <div class="phone-diagram">
          <div class="phone-box">
            <div class="screen">
              <div class="sb"><span>9:41</span><span>●●●</span></div>
              <div class="content">
                <div style="font-family:'Fraunces',serif;font-size:14px;font-weight:700;margin-bottom:4px;color:#2B2D6E">Quiet morning</div>
                <div>No events · 2 drafts</div>
              </div>
              <div class="tb"><div class="tab-demo"><div class="elev"></div><div class="t"></div><div class="t"></div><div class="t"></div></div></div>
            </div>
          </div>
          <dl class="kv">
            <dt>Canvas</dt><dd>${phoneSpec.width} × ${phoneSpec.height}px</dd>
            <dt>Frame (bezel)</dt><dd>${phoneSpec.frame}px, radius ${phoneSpec.radius}px</dd>
            <dt>Status bar</dt><dd>${phoneSpec.statusBar}px, white, 9am / signal / battery</dd>
            <dt>Tab bar</dt><dd>${phoneSpec.tabBar}px, 4 tabs, elevated-active pattern</dd>
            <dt>Capture</dt><dd>Headless Chrome <code>--force-device-scale-factor=2</code></dd>
          </dl>
        </div>
        <div class="callout" style="margin-top:18px">${phoneSpec.notes}</div>
      </div>
    </section>

    <section>
      <header><h2>Icons</h2><p>One library, six weights, one color rule.</p></header>
      <div class="card">
        <dl class="kv">
          <dt>Library</dt><dd>${iconSpec.library}</dd>
          <dt>Packages</dt><dd><code>${iconSpec.packages}</code></dd>
          <dt>Weights</dt><dd>${iconSpec.weights.map(w => `<code>${w}</code>`).join(' · ')}</dd>
          <dt>Default weight</dt><dd><code>${iconSpec.defaultWeight}</code></dd>
          <dt>Size</dt><dd>${iconSpec.size}</dd>
          <dt>Color</dt><dd>${iconSpec.colorRule}</dd>
          <dt>License</dt><dd>${iconSpec.license}</dd>
        </dl>
        <div class="callout" style="margin-top:14px">${iconSpec.forbidden}</div>
        <p style="margin:14px 0 0;font-size:13px;color:#6c6e92">Full catalogue and weight-usage table: <a href="/icons" style="color:#FF3D7F;font-weight:500">Icons →</a></p>
      </div>
    </section>

    <section>
      <header><h2>Component primitives</h2><p>Patterns that appear in multiple prototypes — treat as the canonical source.</p></header>
      <div class="card">
        <h3>Elevated-active tab</h3>
        <p style="margin:0 0 10px;font-size:13.5px;color:#2B2D6E;line-height:1.5">Bottom nav uses a 36×36 navy circle nested inside a 54×54 pink radial-gradient cushion, translated up 10px. Inactive tabs sit flat. This is the Klikk mobile signature — do not substitute Material / iOS defaults.</p>
        <h3 style="margin-top:20px">Status dots</h3>
        <p style="margin:0;font-size:13.5px;color:#2B2D6E;line-height:1.5">8px solid dot: red (danger-600), amber (warning-600), green (success-600). Never standalone — always paired with a label.</p>
        <h3 style="margin-top:20px">Property card</h3>
        <p style="margin:0;font-size:13.5px;color:#2B2D6E;line-height:1.5">White surface, 14px radius, <code>shadow-soft</code>, address line in Fraunces semibold, meta row in DM Sans 13px. The only card density we use.</p>
      </div>
    </section>

    <section>
      <header><h2>References</h2><p>Where to find deeper specs when you need them.</p></header>
      <div class="card">
        <dl class="kv">
          <dt>Admin UI</dt><dd>Skill: <code>klikk-design-standard</code></dd>
          <dt>Mobile UX</dt><dd>Skill: <code>klikk-design-mobile-ux</code> (iOS HIG + Android MD3)</dd>
          <dt>Taste guide</dt><dd>Skill: <code>klikk-design-frontend-taste</code></dd>
          <dt>Marketing site</dt><dd>Skill: <code>klikk-marketing-website</code></dd>
        </dl>
      </div>
    </section>
  `;
}

/* ---------- Shared flow CSS + tab nav ---------- */
const flowsCss = `
  <style>
    .card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 1px 3px rgba(43,45,110,.06),0 8px 24px -12px rgba(43,45,110,.12)}
    .flow-tabs{display:flex;gap:4px;background:#fff;border-radius:12px;padding:4px;margin-bottom:32px;box-shadow:0 1px 3px rgba(43,45,110,.06);width:fit-content}
    .flow-tab{padding:8px 16px;border-radius:8px;font-size:13px;font-weight:500;color:#6c6e92;text-decoration:none;transition:all .12s;display:flex;align-items:center;gap:8px}
    .flow-tab:hover{background:#FAFAFE;color:#2B2D6E}
    .flow-tab.active{background:#2B2D6E;color:#fff}
    .flow-tab .dot{width:7px;height:7px;border-radius:50%}
    .phase{margin-bottom:40px}
    .phase-header{background:var(--soft);border-radius:16px;padding:18px 20px;margin-bottom:14px}
    .phase-header h2{margin:6px 0 2px}
    .phase-header p{margin:0;color:#6c6e92;font-size:13.5px}
    .phase-pill{display:inline-block;background:var(--hue);color:#fff;font-size:11px;font-weight:600;letter-spacing:.06em;padding:3px 10px;border-radius:999px;text-transform:uppercase}
    .phase-stages{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
    .stage{position:relative;background:#fff;border-radius:14px;padding:16px 16px 16px 56px;box-shadow:0 1px 3px rgba(43,45,110,.06);border-left:3px solid var(--hue);min-height:120px}
    .stage-num{position:absolute;left:14px;top:14px;width:30px;height:30px;border-radius:50%;background:var(--soft);color:var(--hue);font-family:'Fraunces',serif;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:14px}
    .stage-title{font-family:'Fraunces',serif;font-weight:600;font-size:17px;color:#2B2D6E;letter-spacing:-.01em}
    .stage-desc{font-size:12.5px;color:#6c6e92;line-height:1.4;margin:4px 0 10px}
    .stage-protos{display:flex;flex-wrap:wrap;gap:5px}
    .stage-link{font-size:11px;padding:3px 8px;background:#F0EFF8;color:#2B2D6E;border-radius:6px;text-decoration:none;font-weight:500;font-family:ui-monospace,Menlo,monospace}
    .stage-link:hover{background:#FF3D7F;color:#fff}
    .stage-gap{font-size:11px;color:#c23b3b;background:#FFE4EF;padding:3px 8px;border-radius:6px;font-weight:500}
    .stage-legal{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;padding-top:8px;border-top:1px dashed #EFEFF5}
    .legal-pill{font-size:10px;padding:2px 7px;border-radius:5px;font-family:ui-monospace,Menlo,monospace;font-weight:500;border:1px solid;cursor:help;letter-spacing:.01em}
    .legal-pill[data-act="popia"]{background:#E6F0FE;color:#1E4FB8;border-color:#D5E2FB}
    .legal-pill[data-act="rha"]  {background:#FFE4EF;color:#9C1D4F;border-color:#FFD4E5}
    .legal-pill[data-act="fica"] {background:#FDF3E0;color:#9A5800;border-color:#FAE5BD}
    .legal-pill[data-act="ecta"] {background:#E6F4EB;color:#15803D;border-color:#CFEAD7}
    .legal-pill[data-act="cpa"]  {background:#F0EFF8;color:#5B5E8C;border-color:#E0DFEE}
    .legal-legend{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px;padding:12px 14px;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(43,45,110,.06)}
    .legal-legend .ll-title{font-size:11px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-right:4px;align-self:center}
    .gap-row{display:grid;grid-template-columns:30px 140px 1fr;gap:14px;padding:10px 0;border-bottom:1px solid #EFEFF5;align-items:baseline}
    .gap-row:last-child{border-bottom:0}
    .gap-num{font-family:'Fraunces',serif;font-weight:700;color:#D97706;font-size:16px}
    .gap-title{font-weight:600;color:#2B2D6E;font-size:14px}
    .gap-desc{font-size:12.5px;color:#6c6e92;line-height:1.4}
    .intro-strip{display:flex;gap:8px;margin-bottom:28px;flex-wrap:wrap}
    .intro-strip .chip-phase{display:flex;align-items:center;gap:6px;padding:6px 10px;background:#fff;border-radius:8px;font-size:12px;color:#6c6e92;box-shadow:0 1px 3px rgba(43,45,110,.06)}
    .intro-strip .dot{width:8px;height:8px;border-radius:50%}
  </style>`;

function flowTabs(activeKey) {
  const tabs = [
    { key: 'agent',    href: '/flows',          label: 'Agent',    dot: '#2B2D6E' },
    { key: 'tenant',   href: '/flows/tenant',   label: 'Tenant',   dot: '#16A34A' },
    { key: 'owner',    href: '/flows/owner',    label: 'Owner',    dot: '#D97706' },
    { key: 'together', href: '/flows/together', label: 'Together', dot: '#FF3D7F' },
  ];
  return `
    <div class="flow-tabs">
      ${tabs.map(t => `<a class="flow-tab ${t.key===activeKey?'active':''}" href="${t.href}"><span class="dot" style="background:${t.dot}"></span>${t.label}</a>`).join('')}
    </div>`;
}

function renderLifecycle(lifecycle, phases, phaseOrder) {
  const byPhase = Object.fromEntries(phaseOrder.map(p => [p, []]));
  lifecycle.forEach(s => byPhase[s.phase].push(s));

  const stageCard = s => {
    const meta = phases[s.phase];
    const protoChips = s.protos && s.protos.length
      ? s.protos.map(p => `<a class="stage-link" href="/${p}">${p.replace('.html','')}</a>`).join('')
      : `<span class="stage-gap">no prototype yet</span>`;
    const legal = (s.legal && s.legal.length)
      ? `<div class="stage-legal">${s.legal.map(l => `<span class="legal-pill" data-act="${l.act}" title="${l.note.replace(/"/g,'&quot;')}">${l.act.toUpperCase()} ${l.ref}</span>`).join('')}</div>`
      : '';
    return `
      <article class="stage" style="--hue:${meta.hue};--soft:${meta.soft}">
        <div class="stage-num">${s.step}</div>
        <div class="stage-body">
          <div class="stage-title">${s.title}</div>
          <div class="stage-desc">${s.desc}</div>
          <div class="stage-protos">${protoChips}</div>
          ${legal}
        </div>
      </article>`;
  };

  const phaseBlock = key => {
    const meta = phases[key];
    const stages = byPhase[key].map(stageCard).join('');
    const range = byPhase[key].map(s => s.step);
    const header = `Stages ${range[0]}${range.length>1?'–'+range[range.length-1]:''}`;
    return `
      <section class="phase">
        <header class="phase-header" style="--hue:${meta.hue};--soft:${meta.soft}">
          <div class="phase-pill">${header}</div>
          <h2 style="color:${meta.hue}">${meta.label}</h2>
          <p>${meta.desc}</p>
        </header>
        <div class="phase-stages">${stages}</div>
      </section>`;
  };

  const strip = `
    <div class="intro-strip">
      ${phaseOrder.map(k => `<div class="chip-phase"><span class="dot" style="background:${phases[k].hue}"></span>${phases[k].label}</div>`).join('')}
    </div>`;

  const gaps = lifecycle.filter(s => !s.protos || s.protos.length === 0);
  const gapBlock = gaps.length ? `
    <section>
      <header><h2>Coverage gaps</h2><p>Stages not yet represented by any prototype.</p></header>
      <div class="card">
        ${gaps.map(s => `<div class="gap-row"><span class="gap-num">${s.step}</span><span class="gap-title">${s.title}</span><span class="gap-desc">${s.desc}</span></div>`).join('')}
      </div>
    </section>` : '';

  return strip + phaseOrder.map(phaseBlock).join('') + gapBlock;
}

function pageFlowsAgent() {
  const legalLegend = `
    <div class="legal-legend">
      <span class="ll-title">Legal layer</span>
      <span class="legal-pill" data-act="popia">POPIA</span>
      <span class="legal-pill" data-act="rha">RHA</span>
      <span class="legal-pill" data-act="fica">FICA</span>
      <span class="legal-pill" data-act="ecta">ECTA</span>
      <span class="legal-pill" data-act="cpa">CPA</span>
      <span style="font-size:11.5px;color:#8a8ca8;margin-left:auto;align-self:center">Hover a pill for the rule. See <a href="/data" style="color:#2B2D6E;text-decoration:underline">Data flow</a> for PI inventory.</span>
    </div>`;
  return flowsCss + `
    <h1>Agent flow</h1>
    <p class="lede">The 15-stage rental lifecycle — the agent orchestrates every handoff. Each stage carries the SA legal anchors that govern it.</p>
    ${flowTabs('agent')}
    ${legalLegend}
    ${renderLifecycle(agentLifecycle, agentPhases, ['pre', 'turnaround', 'active', 'closeout'])}
  `;
}

function pageFlowsTenant() {
  return flowsCss + `
    <h1>Tenant flow</h1>
    <p class="lede">14 stages from the tenant's point of view — <em>"this is my home"</em>.</p>
    ${flowTabs('tenant')}
    ${renderLifecycle(tenantLifecycle, tenantPhases, ['finding', 'moving-in', 'living', 'moving-on'])}
  `;
}

function pageFlowsOwner() {
  return flowsCss + `
    <h1>Owner flow</h1>
    <p class="lede">11 stages from the owner's point of view — <em>"my properties are being handled"</em>. Mostly reviews + approvals, not action.</p>
    ${flowTabs('owner')}
    ${renderLifecycle(ownerLifecycle, ownerPhases, ['onboarding', 'per-tenant', 'operating', 'transitions'])}
  `;
}

function pageFlowsTogether() {
  const roleChip = key => {
    const s = roleStyle[key];
    return `<span class="role-chip" style="--hue:${s.hue}">${s.label}</span>`;
  };

  const moment = m => {
    const actions = ['agent', 'tenant', 'owner'].map(role => {
      const active = m.who.includes(role);
      const action = m[role];
      const s = roleStyle[role];
      return `
        <div class="mo-lane ${active?'active':'passive'}" style="--hue:${s.hue}">
          <div class="mo-lane-label">${s.label}</div>
          <div class="mo-lane-body">${action || '<em>not involved</em>'}</div>
        </div>`;
    }).join('');
    return `
      <article class="moment">
        <header class="mo-head">
          <div class="mo-title">${m.title}</div>
          <div class="mo-when">${m.when}</div>
        </header>
        <div class="mo-who">${m.who.map(roleChip).join('')}</div>
        <div class="mo-lanes">${actions}</div>
      </article>`;
  };

  const css = `
    <style>
      .moment{background:#fff;border-radius:16px;padding:20px;box-shadow:0 1px 3px rgba(43,45,110,.06),0 8px 24px -12px rgba(43,45,110,.12);margin-bottom:14px}
      .mo-head{display:flex;justify-content:space-between;align-items:baseline;gap:16px;margin-bottom:10px}
      .mo-title{font-family:'Fraunces',serif;font-weight:600;font-size:19px;color:#2B2D6E;letter-spacing:-.01em}
      .mo-when{font-size:11.5px;color:#8a8ca8;font-family:ui-monospace,Menlo,monospace;white-space:nowrap}
      .mo-who{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
      .role-chip{display:inline-block;padding:3px 10px;border-radius:999px;background:var(--hue);color:#fff;font-size:11px;font-weight:600;letter-spacing:.02em}
      .mo-lanes{display:grid;gap:6px}
      .mo-lane{display:grid;grid-template-columns:90px 1fr;gap:14px;padding:10px 14px;border-radius:10px;border-left:3px solid var(--hue)}
      .mo-lane.active{background:#FAFAFE}
      .mo-lane.passive{background:transparent;opacity:.45}
      .mo-lane-label{font-size:11px;font-weight:600;letter-spacing:.06em;color:var(--hue);text-transform:uppercase;padding-top:1px}
      .mo-lane-body{font-size:13.5px;color:#2B2D6E;line-height:1.5}
      .mo-lane-body em{color:#b0b2cc;font-style:normal}
      .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:28px}
      .stat{background:#fff;border-radius:14px;padding:18px;box-shadow:0 1px 3px rgba(43,45,110,.06);border-left:3px solid var(--hue)}
      .stat-num{font-family:'Fraunces',serif;font-weight:700;font-size:34px;color:var(--hue);line-height:1;letter-spacing:-.02em}
      .stat-label{margin-top:6px;font-size:12px;color:#6c6e92;text-transform:uppercase;letter-spacing:.06em;font-weight:500}
      .stat-sub{font-size:12.5px;color:#8a8ca8;margin-top:4px}
      .legend{background:#fff;border-radius:14px;padding:16px 20px;box-shadow:0 1px 3px rgba(43,45,110,.06);margin-bottom:20px}
      .legend-title{font-family:'Fraunces',serif;font-weight:600;font-size:15px;color:#2B2D6E;margin-bottom:6px}
      .legend-body{font-size:13px;color:#6c6e92;line-height:1.5}
      .legend-body strong{color:#2B2D6E}
      @media (max-width:640px){.stats{grid-template-columns:1fr}.mo-lane{grid-template-columns:1fr;gap:4px}}
    </style>`;

  const stats = `
    <div class="stats">
      <div class="stat" style="--hue:#2B2D6E"><div class="stat-num">15</div><div class="stat-label">Agent stages</div><div class="stat-sub">Orchestrator</div></div>
      <div class="stat" style="--hue:#16A34A"><div class="stat-num">14</div><div class="stat-label">Tenant stages</div><div class="stat-sub">Resident</div></div>
      <div class="stat" style="--hue:#D97706"><div class="stat-num">11</div><div class="stat-label">Owner stages</div><div class="stat-sub">Decision-maker</div></div>
    </div>`;

  const legend = `
    <div class="legend">
      <div class="legend-title">Reading this page</div>
      <div class="legend-body">Every row below is a <strong>moment of convergence</strong> — a point in the tenancy where two or three roles must interact. Filled lanes are the roles active at that moment; faded lanes are informed-only. The three lifecycles run in parallel tracks; these are the points where they touch.</div>
    </div>`;

  return flowsCss + css + `
    <h1>Together</h1>
    <p class="lede">Three lifecycles, one tenancy. These are the ${handoffMoments.length} moments where they converge.</p>
    ${flowTabs('together')}
    ${stats}
    ${legend}
    ${handoffMoments.map(moment).join('')}
  `;
}

/* ---------- Data flow (POPIA / RHA / FICA lens) ────────────────
   Sourced from skill: klikk-legal-POPIA-RHA. Three lenses:
   1. PI inventory by lifecycle stage — what gets collected, basis, retention, location
   2. Sub-processors / Operators (POPIA s20–21) — third parties + safeguards
   3. Data subject rights touchpoints (POPIA s23–s25, s11(3), s69(3))
   ─────────────────────────────────────────────────────────────── */
const piInventory = [
  { stage: 4, label: 'Application & screening', items: [
    { item: 'ID number, full name, DOB',         basis: 'POPIA s11(1)(b) — pre-contract',  retention: '5 yrs post-decision (FICA)', location: 'PostgreSQL · af-south-1' },
    { item: 'Credit report (TransUnion)',        basis: 'POPIA s11(1)(b) + Operator DPA',  retention: 'Bureau-side per NCR rules', location: 'TransUnion API (no copy stored)' },
    { item: 'Criminal record (where consented)', basis: 'POPIA s27 + s35 — special PI',    retention: 'Delete on rejection',        location: 'Encrypted blob, S3 af-south-1' },
    { item: 'Payslips, bank statements',         basis: 'POPIA s11(1)(b) + FICA s21A',     retention: '5 yrs (FICA)',               location: 'S3 af-south-1, KMS-encrypted' },
    { item: 'Employment + reference contacts',   basis: 'POPIA s11(1)(b)',                 retention: '5 yrs',                       location: 'PostgreSQL' },
  ] },
  { stage: 5, label: 'Lease execution', items: [
    { item: 'Signed lease PDF',                  basis: 'POPIA s11(1)(b) + ECTA s13',      retention: '5 yrs post-termination',     location: 'S3 af-south-1' },
    { item: 'Signature image + audit trail',     basis: 'POPIA s11(1)(b)',                 retention: '5 yrs post-termination',     location: 'PostgreSQL + S3' },
    { item: 'Witness names + IDs (if any)',      basis: 'POPIA s11(1)(b)',                 retention: '5 yrs',                       location: 'PostgreSQL' },
  ] },
  { stage: 7, label: 'Deposit', items: [
    { item: 'Trust account number + balances',   basis: 'RHA s5(3)(b)–(c)',                retention: 'Until refund + 3 yrs',       location: 'Banking partner (FNB/Standard Bank)' },
    { item: 'Interest accrual ledger',           basis: 'RHA s5(3)(c)',                    retention: 'Until refund + 3 yrs',       location: 'PostgreSQL + bank statement' },
  ] },
  { stage: 11, label: 'Onboarding', items: [
    { item: 'Tenant phone + email',              basis: 'POPIA s11(1)(b)',                 retention: '5 yrs post-termination',     location: 'PostgreSQL' },
    { item: 'Emergency contact',                 basis: 'POPIA s11(1)(a) — consent',       retention: '5 yrs post-termination',     location: 'PostgreSQL' },
    { item: 'Utility account numbers',           basis: 'POPIA s11(1)(b)',                 retention: 'Until move-out',             location: 'PostgreSQL' },
  ] },
  { stage: 12, label: 'Active tenancy', items: [
    { item: 'Payment history + receipts',        basis: 'POPIA s11(1)(b) + Prescription Act', retention: '5 yrs (FICA)',           location: 'PostgreSQL' },
    { item: 'Communication logs (in-app)',       basis: 'POPIA s11(1)(b)',                 retention: '5 yrs',                       location: 'PostgreSQL + S3 attachments' },
    { item: 'Payment failures + flags',          basis: 'POPIA s11(1)(b)',                 retention: '5 yrs',                       location: 'PostgreSQL' },
  ] },
  { stage: 13, label: 'Maintenance', items: [
    { item: 'Photos of damage / repairs',        basis: 'POPIA s11(1)(b) + RHA s5(3)',     retention: '5 yrs post-termination',     location: 'S3 af-south-1' },
    { item: 'Tenant location for site visit',    basis: 'POPIA s11(1)(b)',                 retention: 'Visit complete + 30 days',   location: 'In-memory only (not persisted)' },
    { item: 'Supplier-shared contact details',   basis: 'POPIA s20–21 Operator',           retention: 'Per supplier DPA',           location: 'Supplier system' },
  ] },
  { stage: 8, label: 'Move-out & inspection', items: [
    { item: 'Outgoing inspection report + photos', basis: 'RHA s5(3)(g)',                  retention: '5 yrs post-termination',     location: 'S3 af-south-1' },
    { item: 'Damage list + cost estimates',      basis: 'RHA s5(3)(g) + s5A',              retention: '5 yrs',                       location: 'PostgreSQL' },
  ] },
  { stage: 15, label: 'Refund', items: [
    { item: 'Tenant refund banking details',     basis: 'POPIA s11(1)(b)',                 retention: 'Until refund + 3 yrs',       location: 'PostgreSQL (encrypted)' },
    { item: 'Itemised deduction statement',      basis: 'RHA s5(3)(g)–(i)',                retention: '5 yrs',                       location: 'S3 (PDF) + PostgreSQL' },
  ] },
];

const subProcessors = [
  { name: 'TransUnion / Experian / Compuscan', purpose: 'Credit + ITC checks',          shares: 'ID, full name, DOB, address',                  region: 'South Africa',          dpa: 'Required (POPIA s20–21)', risk: 'medium' },
  { name: 'Banking partner (FNB / Standard Bank)', purpose: 'Trust account + payments', shares: 'Tenant name, banking, payment amounts',        region: 'South Africa',          dpa: 'Bank acts as Responsible Party (own basis)', risk: 'low' },
  { name: 'AWS S3 + RDS',                       purpose: 'Storage of documents + DB',   shares: 'All PI at rest',                               region: 'af-south-1 (Cape Town)', dpa: 'AWS DPA in place. No cross-border under POPIA s72.', risk: 'low' },
  { name: 'Email gateway (AWS SES / Mailgun)',  purpose: 'Transactional emails',        shares: 'Email address, name, message body',            region: 'eu-west-1 / SA',         dpa: 'Required. Cross-border safeguards if EU.', risk: 'medium' },
  { name: 'SMS gateway (Clickatell)',           purpose: 'SMS notifications',           shares: 'Phone number, message body',                   region: 'South Africa',          dpa: 'Required',                  risk: 'low' },
  { name: 'Suppliers (plumbers, electricians)', purpose: 'On-site repairs',             shares: 'Tenant name, phone, address, repair photos',   region: 'South Africa',          dpa: 'Required per supplier (often informal — gap)', risk: 'high' },
  { name: 'Property24 / Private Property',      purpose: 'Vacancy listing distribution', shares: 'Property data only — no tenant PI',           region: 'South Africa',          dpa: 'N/A — Klikk is publisher',  risk: 'low' },
  { name: 'Anthropic Claude API',               purpose: 'AI lease drafting + screening', shares: 'Lease drafts, applicant fields (anonymised where possible)', region: 'United States (cross-border)', dpa: 'Anthropic DPA. POPIA s72 safeguards via SCCs / Anthropic enterprise agreement.', risk: 'medium' },
  { name: 'Gotenberg (self-hosted Docker)',     purpose: 'HTML→PDF conversion',         shares: 'Lease HTML processed in-memory',               region: 'Klikk infra',           dpa: 'N/A — runs in own VPC',     risk: 'low' },
];

const dsarRights = [
  { right: 'Access',           section: 'POPIA s23 + PAIA Form 2', summary: 'Tenant requests a copy of all PI Klikk holds about them.', sla: '30 days', surface: 'Tenant app → "Data & privacy" → Request my data' },
  { right: 'Correction',       section: 'POPIA s24',               summary: 'Tenant disputes inaccurate PI (e.g. wrong ID number, address typo).', sla: '30 days', surface: 'Tenant app → Profile → Edit (or formal request)' },
  { right: 'Deletion',         section: 'POPIA s24(1)(b)',         summary: 'Tenant requests removal once retention period expires or basis lapses.', sla: '30 days · subject to FICA / RHA retention overrides', surface: 'Tenant app → "Data & privacy" → Delete account' },
  { right: 'Object',           section: 'POPIA s11(3)',            summary: 'Tenant objects to specific processing (e.g. AI scoring).', sla: '30 days', surface: 'Email DPO + ticketing flag' },
  { right: 'Marketing opt-out',section: 'POPIA s69(3)',            summary: 'Every electronic comm carries an unsubscribe link / STOP keyword.', sla: 'Immediate (next send)', surface: 'Email footer + SMS reply STOP' },
  { right: 'Complain',         section: 'POPIA s74',               summary: 'Tenant lodges complaint with Information Regulator.', sla: 'Regulator-driven', surface: 'External — inforegulator.org.za' },
];

/* Vault33 — the compliance engine. Sourced from docs/system/vault33-system-document.md */
const vault33 = {
  summary: {
    name: 'Vault33',
    purpose: 'Encrypt, audit, and gate access to all regulated personal information so POPIA / FICA / RHA compliance is automatic, not aspirational.',
    location: 'backend/apps/the_volt/',
    surface: 'Django 5 + DRF app · REST API · 23-tool MCP server (stdio + HTTP-streamable) · Gateway module',
    consumers: 'Claude (MCP) · Admin SPA (REST) · External parties — conveyancers, banks (Gateway)',
    productLines: 'Rentals (live) · Real Estate (roadmap) · BI (roadmap)',
    ingestionSkill: 'klikk-vault31-ingestion (legacy name — the ingestion pipeline INTO Vault33)',
    version: 'v1.0 draft scoping · 2026-04-17',
  },
  concept: {
    headline: 'The library model — data belongs to the data subject.',
    body: 'Klikk and its sub-processors never own tenant data. Vault33 treats every record as a book on a shelf that belongs to the person it describes. When a conveyancer, bank, supplier, or even a Klikk agent needs to see something, they <em>check it out</em> — a time-bounded, scope-bounded, audit-logged borrow. The checkout has an expiry, a stated purpose, and a return receipt. When it ends, access is revoked and the book goes back to the shelf.',
    mapping: [
      ['The library',     'Vault33 (the Django app + encrypted blob store + audit log)'],
      ['The librarian',   'The Gateway module — enforces consent, records every loan, issues recall notices'],
      ['The book',        'An Entity or Document — encrypted at rest, signed on loan'],
      ['The owner',       'The data subject (tenant, owner, beneficial owner) — POPIA calls them the "data subject"'],
      ['The borrower',    'Any third party — conveyancer, bank, SARS, supplier, Klikk agent — a DataSubscriber'],
      ['The library card','OTP-gated consent artifact (POPIA s11 lawful basis + s20–21 operator agreement)'],
      ['The loan slip',   'Checkout record — scope, purpose, expiry, HMAC-signed package'],
      ['The return',      'Revocation at expiry · audit entry closes the loop · downstream caches must purge'],
      ['The late fee',    'POPIA s107 offences · Information Regulator fines up to R10m · civil claims'],
    ],
    why: [
      'It makes the default "no access". A stranger walking into the library doesn\'t get the book — the owner has to issue a card first.',
      'Every read is accountable. You can always answer "who has my data and why?" because every loan is logged.',
      'Expiries are enforced in code. A conveyancer who needed FICA docs for a transfer does not retain them indefinitely.',
      'POPIA s23 (DSAR) is trivial: hand the owner the loan ledger for their book. s24 (correction / deletion) is trivial: recall all loans, update the book, re-issue.',
    ],
  },
  entities: [
    { t: 'personal',         icon: 'ph-user',              d: 'Natural persons — tenants, owners, beneficial owners, signatories' },
    { t: 'trust',            icon: 'ph-scales',            d: 'SA trusts with trustee / beneficiary chains' },
    { t: 'company',          icon: 'ph-buildings',         d: '(Pty) Ltd, Ltd — full CIPC directorship graph' },
    { t: 'close_corporation',icon: 'ph-building-office',   d: 'Legacy CC members' },
    { t: 'sole_proprietary', icon: 'ph-user-rectangle',    d: 'Individual-trading-as — linked to a personal entity' },
    { t: 'asset',            icon: 'ph-house-line',        d: 'Immovable / movable — erven, vehicles, equipment' },
  ],
  storage: [
    { layer: 'PostgreSQL',        scope: 'Entities · document metadata · audit log · relationships · checkouts', path: '15+ models · 10 migrations' },
    { layer: 'Local filesystem',  scope: 'Encrypted document blobs (.enc)',                                       path: 'backend/media/vault/' },
    { layer: 'ChromaDB (SQLite)', scope: 'Vector embeddings — hybrid graph + semantic search',                    path: 'rag_chroma/chroma.sqlite3' },
  ],
  encryption: [
    ['Cipher',            'Fernet (AES-128-CBC + HMAC-SHA256)'],
    ['Key derivation',    'PBKDF2-HMAC-SHA256 · 100,000 iterations'],
    ['Key material',      'Django SECRET_KEY + owner-ID salt (per-owner symmetric key)'],
    ['Integrity',         'HMAC signing on every blob + gateway checkout package'],
    ['Known gap',         'No key rotation · no HSM · no envelope encryption — single point of failure on SECRET_KEY'],
  ],
  ingestion: [
    { path: 'REST API',              how: 'Admin SPA / bulk tenant onboarding POST entities + documents',           state: 'live' },
    { path: 'MCP write tools',       how: 'Claude calls upsert_* / attach_document / link_entities — idempotent',   state: 'live' },
    { path: 'Classification engine', how: 'Auto-index documents to ChromaDB · extract fields per doc-type skill',   state: 'partial · Smart ID only' },
    { path: 'Email inbound',         how: 'Patterns seeded (email_subject_patterns, email_sender_patterns); no handler', state: 'future' },
  ],
  mcpRead: [
    'ensure_vault', 'list_entities', 'find_entity', 'get_entity',
    'list_documents', 'list_document_types', 'list_relationship_types',
    'download_document', 'get_api_schema', 'POST /entities/query/ (hybrid search)',
  ],
  mcpWrite: [
    'upsert_owner', 'upsert_property', 'upsert_tenant',
    'attach_document', 'link_entities', 'update_entity',
    'deactivate_entity', 'create_checkout', 'approve_checkout',
    'revoke_checkout', 'add_subscriber', 'grant_access', 'extract_fields',
  ],
  popiaCoverage: [
    { ref: 's17',    obligation: 'Processing records',            delivery: 'VaultWriteAudit — append-only log of every mutation (before/after snapshots)' },
    { ref: 's19',    obligation: 'Security safeguards',           delivery: 'Fernet encryption at rest + HMAC signing' },
    { ref: 's20–21', obligation: 'Operator agreements',           delivery: 'DataSubscriber model + OTP-gated consent flow via Gateway' },
    { ref: 's23',    obligation: 'Subject access (DSAR)',         delivery: 'get_entity MCP tool + download_document — returns full record + decrypted blobs' },
    { ref: 's24',    obligation: 'Correction / deletion',         delivery: 'update_entity for correction · deactivate_entity (soft) · hard delete blocked by retention' },
    { ref: 'FICA s21A', obligation: 'Enhanced CDD · BO chain',    delivery: 'Entity schemas enforce ID + address + multi-hop relationship graph' },
    { ref: 'RHA s5(3)', obligation: 'Deposit & inspection records', delivery: 'Asset entity + financial / inspection document types · 5-yr retention' },
  ],
  status: [
    { area: 'Data models · REST API · MCP server', state: 'built' },
    { area: 'Fernet encryption + per-owner keys',  state: 'built' },
    { area: 'Audit log · relationship graph',      state: 'built' },
    { area: 'Document-type catalogue (85 SA types)', state: 'built' },
    { area: 'Gateway consent flow',                state: 'built' },
    { area: 'Classification extraction (per doc type)', state: 'partial' },
    { area: 'ChromaDB hybrid query UX',            state: 'partial' },
    { area: 'Admin SPA / tenant DSAR self-service', state: 'pending' },
    { area: 'Production deployment',               state: 'pending' },
  ],
  seeded: [
    ['Entities', '90 (78 personal + 12 assets)'],
    ['Documents', '0'],
    ['Relationships', '0'],
    ['Document types catalogued', '85'],
    ['Relationship types', '10'],
    ['Migrations', '10'],
  ],
  gaps: [
    { t: 'Key rotation',              d: 'Not implemented; key derivation from SECRET_KEY is a single point of failure.' },
    { t: 'MCP rate limiting',         d: 'No per-caller throttle — potential data-exfiltration vector if an MCP token leaks.' },
    { t: 'E2E encryption of Gateway', d: 'Checkout packages are HMAC-signed but not end-to-end ciphered.' },
    { t: 'Anomalous-access alerts',   d: 'Audit log exists but no rules or alerting on bulk reads / off-hours access.' },
    { t: 'Envelope encryption / HSM', d: 'Not designed — single key per owner, no KMS wrapping.' },
    { t: 'Email ingestion pipeline',  d: 'Classification patterns seeded; no inbound email handler yet.' },
    { t: 'Tenant DSAR self-service',  d: 'No self-service UI for tenants to download / correct / delete their data.' },
  ],
};

const dataFlowCss = `
  <style>
    .df-tabs{display:flex;gap:6px;background:#fff;padding:6px;border-radius:12px;margin-bottom:26px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;position:sticky;top:12px;z-index:5;flex-wrap:wrap}
    .df-tab{flex:1 1 0;min-width:130px;text-align:center;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:600;color:#6c6e92;text-decoration:none;transition:all .12s;cursor:pointer;border:1px solid transparent}
    .df-tab:hover{background:#FAFAFE;color:#2B2D6E}
    .df-tab.active{background:linear-gradient(135deg,#2B2D6E,#3a3d8a);color:#fff;box-shadow:0 2px 8px -2px rgba(43,45,110,.3)}
    .df-tab .t-num{font-size:10.5px;font-weight:600;opacity:.7;margin-right:6px;letter-spacing:.04em}
    .df-section{margin-bottom:42px}
    .df-section{scroll-margin-top:90px}
    .df-section > header{margin-bottom:14px}
    .df-section > header h2{font-family:'Fraunces',serif;font-weight:600;font-size:22px;color:#2B2D6E;margin:0}
    .df-section > header p{margin:4px 0 0;color:#6c6e92;font-size:13px}
    .stage-block{background:#fff;border-radius:14px;box-shadow:0 1px 3px rgba(43,45,110,.06);margin-bottom:14px;overflow:hidden}
    .sb-head{display:flex;align-items:center;gap:12px;padding:14px 18px;background:#FAFAFE;border-bottom:1px solid #EFEFF5}
    .sb-num{width:28px;height:28px;border-radius:50%;background:#F0EFF8;color:#2B2D6E;font-family:'Fraunces',serif;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:13px}
    .sb-title{font-family:'Fraunces',serif;font-weight:600;font-size:16px;color:#2B2D6E}
    .sb-count{margin-left:auto;font-size:11px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
    .pi-row{display:grid;grid-template-columns:2fr 2.5fr 1.5fr 1.5fr;gap:14px;padding:11px 18px;border-bottom:1px solid #F4F4F9;font-size:12.5px;align-items:start}
    .pi-row:last-child{border-bottom:0}
    .pi-row > div:first-child{font-weight:600;color:#2B2D6E}
    .pi-row > div:nth-child(2),.pi-row > div:nth-child(3){color:#5b5e8c}
    .pi-row > div:last-child{color:#8a8ca8;font-family:ui-monospace,Menlo,monospace;font-size:11.5px}
    .pi-head{background:#FCFCFE;font-size:10.5px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
    .pi-head > div{color:#8a8ca8 !important;font-weight:600 !important;font-family:'DM Sans',sans-serif !important}
    .sp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
    .sp-card{background:#fff;border-radius:14px;padding:16px 18px;box-shadow:0 1px 3px rgba(43,45,110,.06);border-left:3px solid #ccc}
    .sp-card[data-risk="low"]{border-left-color:#16A34A}
    .sp-card[data-risk="medium"]{border-left-color:#D97706}
    .sp-card[data-risk="high"]{border-left-color:#DC2626}
    .sp-name{font-family:'Fraunces',serif;font-weight:600;font-size:16px;color:#2B2D6E;letter-spacing:-.01em}
    .sp-purpose{font-size:12px;color:#6c6e92;margin:2px 0 10px;line-height:1.4}
    .sp-meta{font-size:11.5px;color:#5b5e8c;line-height:1.6}
    .sp-meta strong{color:#8a8ca8;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;display:block;margin-top:6px}
    .sp-risk{display:inline-block;font-size:10px;padding:2px 7px;border-radius:5px;margin-top:8px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
    .sp-risk[data-risk="low"]{background:#E6F4EB;color:#15803D}
    .sp-risk[data-risk="medium"]{background:#FDF3E0;color:#9A5800}
    .sp-risk[data-risk="high"]{background:#FFE4EF;color:#9C1D4F}
    .ds-row{display:grid;grid-template-columns:160px 1fr 200px;gap:18px;padding:14px 18px;background:#fff;border-radius:12px;margin-bottom:10px;box-shadow:0 1px 3px rgba(43,45,110,.06);align-items:start}
    .ds-right{font-family:'Fraunces',serif;font-weight:600;font-size:16px;color:#2B2D6E}
    .ds-section{font-size:11px;color:#8a8ca8;font-family:ui-monospace,Menlo,monospace;margin-top:2px;display:block}
    .ds-summary{font-size:13px;color:#5b5e8c;line-height:1.5}
    .ds-surface{font-size:11.5px;color:#6c6e92;line-height:1.5;border-left:2px solid #EFEFF5;padding-left:12px}
    .ds-surface strong{color:#8a8ca8;font-size:10px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;display:block;margin-bottom:2px}
    .df-banner{background:linear-gradient(135deg,#F0EFF8 0%,#FFE4EF 100%);border-radius:14px;padding:18px 22px;margin-bottom:32px}
    .df-banner h3{font-family:'Fraunces',serif;font-weight:600;font-size:18px;color:#2B2D6E;margin:0 0 4px}
    .df-banner p{margin:0;font-size:13.5px;color:#5b5e8c;line-height:1.5}
    /* Vault33 styles */
    .v33-hero{background:linear-gradient(135deg,#2B2D6E 0%,#3a3d8a 50%,#FF3D7F 100%);color:#fff;border-radius:16px;padding:28px 32px;margin-bottom:22px;display:grid;grid-template-columns:1fr 160px;gap:24px;align-items:center}
    .v33-hero h3{font-family:'Fraunces',serif;font-weight:700;font-size:28px;margin:0 0 8px;letter-spacing:-.01em}
    .v33-hero p{margin:0;font-size:14.5px;line-height:1.55;color:rgba(255,255,255,.9)}
    .v33-hero .v33-lock{width:100%;aspect-ratio:1;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:64px;color:#fff}
    .v33-spec{background:#fff;border-radius:14px;padding:22px 26px;box-shadow:0 1px 3px rgba(43,45,110,.06);margin-bottom:18px;border:1px solid #EFEFF5}
    .v33-spec h4{font-family:'Fraunces',serif;font-weight:600;font-size:17px;color:#2B2D6E;margin:0 0 6px;display:flex;align-items:center;gap:10px}
    .v33-spec h4 .ph{font-size:20px;color:#FF3D7F}
    .v33-spec .kick{color:#6c6e92;font-size:12.5px;margin:0 0 16px;line-height:1.5}
    .v33-dl{display:grid;grid-template-columns:180px 1fr;gap:0;font-size:13px}
    .v33-dl > dt{padding:8px 0;color:#8a8ca8;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid #F4F4F9}
    .v33-dl > dd{padding:8px 0;margin:0;color:#3a3c5f;line-height:1.5;border-bottom:1px solid #F4F4F9}
    .v33-dl > dt:last-of-type,.v33-dl > dd:last-of-type{border-bottom:0}
    .v33-dl code{font-family:ui-monospace,Menlo,monospace;font-size:12px;background:#F5F5F8;padding:1px 6px;border-radius:4px;color:#2B2D6E}
    .v33-entities{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
    .v33-ent{background:#FAFAFE;border:1px solid #EFEFF5;border-radius:10px;padding:14px 16px;transition:all .12s}
    .v33-ent:hover{border-color:#FF3D7F;background:#fff}
    .v33-ent .h{display:flex;align-items:center;gap:10px;font-weight:600;color:#2B2D6E;font-size:13.5px;margin-bottom:4px;font-family:ui-monospace,Menlo,monospace}
    .v33-ent .h .ph{font-size:20px;color:#FF3D7F}
    .v33-ent .d{font-size:12px;color:#6c6e92;line-height:1.45}
    .v33-storage{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
    .v33-store{background:#FAFAFE;border-radius:10px;padding:14px 16px;border:1px solid #EFEFF5}
    .v33-store .layer{font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;font-size:14.5px;margin-bottom:4px}
    .v33-store .scope{font-size:12px;color:#6c6e92;line-height:1.5;margin-bottom:6px}
    .v33-store .path{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#8a8ca8;background:#fff;padding:2px 6px;border-radius:4px;display:inline-block}
    .v33-chan{display:grid;grid-template-columns:180px 1fr 110px;gap:14px;padding:10px 0;border-bottom:1px solid #F4F4F9;font-size:13px;align-items:center}
    .v33-chan:last-child{border-bottom:0}
    .v33-chan .p{font-weight:600;color:#2B2D6E}
    .v33-chan .h{color:#5b5e8c}
    .v33-state{font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;padding:3px 8px;border-radius:5px;text-align:center}
    .v33-state[data-s="live"]{background:#E6F4EB;color:#15803D}
    .v33-state[data-s="partial"]{background:#FDF3E0;color:#9A5800}
    .v33-state[data-s="future"]{background:#F0F0F4;color:#7a7a9c}
    .v33-state[data-s="pending"]{background:#F0F0F4;color:#7a7a9c}
    .v33-state[data-s="built"]{background:#E6F4EB;color:#15803D}
    .v33-mcp{display:grid;grid-template-columns:1fr 1fr;gap:14px}
    .v33-mcp-side{background:#FAFAFE;border-radius:10px;padding:14px 16px;border:1px solid #EFEFF5}
    .v33-mcp-side h5{font-family:'Fraunces',serif;font-weight:600;font-size:13px;color:#2B2D6E;margin:0 0 8px;display:flex;align-items:center;gap:8px;text-transform:uppercase;letter-spacing:.08em;font-size:11px}
    .v33-mcp-side h5 .badge{font-size:10px;padding:1px 6px;border-radius:4px;letter-spacing:.04em}
    .v33-mcp-side[data-mode="read"] .badge{background:#E5EAFF;color:#3840a8}
    .v33-mcp-side[data-mode="write"] .badge{background:#FFE4EF;color:#9C1D4F}
    .v33-mcp-list{display:flex;flex-wrap:wrap;gap:5px}
    .v33-mcp-tool{font-family:ui-monospace,Menlo,monospace;font-size:11px;background:#fff;padding:3px 8px;border-radius:5px;color:#2B2D6E;border:1px solid #EFEFF5}
    .v33-popia{display:grid;grid-template-columns:100px 1fr 2fr;gap:12px;padding:10px 14px;background:#FAFAFE;border-radius:8px;margin-bottom:6px;font-size:12.5px;align-items:start}
    .v33-popia .ref{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#2B2D6E;background:#fff;padding:2px 8px;border-radius:4px;display:inline-block;font-size:11.5px}
    .v33-popia .ob{color:#3a3c5f;font-weight:500}
    .v33-popia .dv{color:#6c6e92;line-height:1.5}
    .v33-popia.head{background:transparent;padding:4px 14px;font-size:10.5px;color:#8a8ca8;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
    .v33-popia.head > div{color:#8a8ca8}
    .v33-status{display:grid;grid-template-columns:1fr 120px;gap:10px;padding:8px 12px;background:#FAFAFE;border-radius:8px;margin-bottom:4px;font-size:12.5px;align-items:center}
    .v33-status .area{color:#3a3c5f}
    .v33-counts{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px}
    .v33-count{background:#FAFAFE;border-radius:10px;padding:14px 16px;text-align:center}
    .v33-count .n{font-family:'Fraunces',serif;font-weight:700;font-size:22px;color:#2B2D6E;line-height:1}
    .v33-count .k{font-size:11px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-top:4px}
    .v33-gap{display:grid;grid-template-columns:180px 1fr;gap:14px;padding:10px 14px;background:#FFFBEA;border:1px solid #FDF3E0;border-radius:8px;margin-bottom:5px;font-size:12.5px}
    .v33-gap .t{font-weight:600;color:#9A5800}
    .v33-gap .d{color:#6c6e92;line-height:1.5}
    /* Library-checkout concept card */
    .v33-concept{background:linear-gradient(180deg,#FAFAFE 0%,#fff 100%);border-left:3px solid #FF3D7F}
    .v33-concept .lib-headline{font-family:'Fraunces',serif;font-weight:600;font-size:18.5px;color:#2B2D6E;line-height:1.4;margin:4px 0 12px;letter-spacing:-.01em}
    .v33-concept .lib-body{color:#3a3c5f;font-size:13.5px;line-height:1.65;margin:0 0 18px}
    .v33-concept .lib-body em{color:#FF3D7F;font-style:italic}
    .v33-lib-map{background:#fff;border:1px solid #EFEFF5;border-radius:10px;overflow:hidden;margin-bottom:18px}
    .v33-lib-row{display:grid;grid-template-columns:220px 30px 1fr;gap:14px;padding:10px 16px;border-bottom:1px solid #F4F4F9;font-size:13px;align-items:center}
    .v33-lib-row:last-child{border-bottom:0}
    .v33-lib-row .role{font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;font-size:13.5px}
    .v33-lib-row .maps{text-align:center;color:#FF3D7F;font-weight:700;font-size:15px}
    .v33-lib-row .meaning{color:#5b5e8c;line-height:1.5;font-size:12.5px}
    .v33-lib-row.head{background:#FAFAFE;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
    .v33-lib-row.head .role,.v33-lib-row.head .meaning{color:#8a8ca8;font-family:'Inter',sans-serif;font-weight:600;font-size:10.5px}
    .v33-lib-why{background:#FAFAFE;border-radius:10px;padding:14px 18px}
    .v33-lib-why h5{font-family:'Fraunces',serif;font-weight:600;font-size:13px;color:#2B2D6E;margin:0 0 8px;text-transform:uppercase;letter-spacing:.08em;font-size:11px}
    .v33-lib-why ul{margin:0;padding-left:18px;color:#5b5e8c;font-size:12.5px;line-height:1.6}
    .v33-lib-why li{margin-bottom:4px}
    .v33-lib-why li:last-child{margin-bottom:0}
    @media (max-width:820px){.pi-row{grid-template-columns:1fr;gap:4px}.pi-head{display:none}.ds-row{grid-template-columns:1fr;gap:8px}.v33-entities,.v33-storage,.v33-mcp{grid-template-columns:1fr}.v33-hero{grid-template-columns:1fr}.v33-dl{grid-template-columns:1fr}.v33-popia{grid-template-columns:1fr}.v33-chan{grid-template-columns:1fr}.v33-lib-row{grid-template-columns:1fr;gap:4px}.v33-lib-row .maps{display:none}}
  </style>`;

function pageDataFlow() {
  const piByStage = piInventory.map(group => {
    const rows = group.items.map(it => `
      <div class="pi-row">
        <div>${it.item}</div>
        <div>${it.basis}</div>
        <div>${it.retention}</div>
        <div>${it.location}</div>
      </div>`).join('');
    return `
      <div class="stage-block">
        <div class="sb-head">
          <div class="sb-num">${group.stage}</div>
          <div class="sb-title">${group.label}</div>
          <div class="sb-count">${group.items.length} items</div>
        </div>
        <div class="pi-row pi-head">
          <div>PI item</div><div>Lawful basis</div><div>Retention</div><div>Location</div>
        </div>
        ${rows}
      </div>`;
  }).join('');

  const sps = subProcessors.map(sp => `
    <article class="sp-card" data-risk="${sp.risk}">
      <div class="sp-name">${sp.name}</div>
      <div class="sp-purpose">${sp.purpose}</div>
      <div class="sp-meta">
        <strong>Shares</strong>${sp.shares}
        <strong>Region</strong>${sp.region}
        <strong>Operator agreement</strong>${sp.dpa}
      </div>
      <span class="sp-risk" data-risk="${sp.risk}">${sp.risk} risk</span>
    </article>`).join('');

  const dsars = dsarRights.map(d => `
    <div class="ds-row">
      <div>
        <div class="ds-right">${d.right}</div>
        <code class="ds-section">${d.section}</code>
        <div style="font-size:11px;color:#8a8ca8;margin-top:6px">SLA: ${d.sla}</div>
      </div>
      <div class="ds-summary">${d.summary}</div>
      <div class="ds-surface"><strong>Surface in product</strong>${d.surface}</div>
    </div>`).join('');

  const entityTiles = vault33.entities.map(e => `
    <div class="v33-ent">
      <div class="h"><i class="ph ${e.icon}"></i> ${e.t}</div>
      <div class="d">${e.d}</div>
    </div>`).join('');

  const storeTiles = vault33.storage.map(s => `
    <div class="v33-store">
      <div class="layer">${s.layer}</div>
      <div class="scope">${s.scope}</div>
      <div class="path">${s.path}</div>
    </div>`).join('');

  const encDl = vault33.encryption.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');

  const chans = vault33.ingestion.map(c => `
    <div class="v33-chan">
      <div class="p">${c.path}</div>
      <div class="h">${c.how}</div>
      <div><span class="v33-state" data-s="${c.state.split(' ')[0]}">${c.state}</span></div>
    </div>`).join('');

  const mcpReadList = vault33.mcpRead.map(t => `<span class="v33-mcp-tool">${t}</span>`).join('');
  const mcpWriteList = vault33.mcpWrite.map(t => `<span class="v33-mcp-tool">${t}</span>`).join('');

  const popiaRows = vault33.popiaCoverage.map(p => `
    <div class="v33-popia">
      <div><span class="ref">${p.ref}</span></div>
      <div class="ob">${p.obligation}</div>
      <div class="dv">${p.delivery}</div>
    </div>`).join('');

  const statusRows = vault33.status.map(s => `
    <div class="v33-status">
      <div class="area">${s.area}</div>
      <div><span class="v33-state" data-s="${s.state}">${s.state}</span></div>
    </div>`).join('');

  const countTiles = vault33.seeded.map(([k, v]) => `
    <div class="v33-count"><div class="n">${v}</div><div class="k">${k}</div></div>`).join('');

  const gapRows = vault33.gaps.map(g => `
    <div class="v33-gap">
      <div class="t">${g.t}</div>
      <div class="d">${g.d}</div>
    </div>`).join('');

  const sumKV = (k, v) => `<dt>${k}</dt><dd>${v}</dd>`;

  const conceptMap = vault33.concept.mapping.map(([role, meaning]) => `
    <div class="v33-lib-row">
      <div class="role">${role}</div>
      <div class="maps">→</div>
      <div class="meaning">${meaning}</div>
    </div>`).join('');

  const conceptWhy = vault33.concept.why.map(w => `<li>${w}</li>`).join('');

  return flowsCss + dataFlowCss + `
    <h1>Data flow</h1>
    <p class="lede">The same lifecycle, viewed through a POPIA / RHA / FICA lens. What PI gets collected, who shares it, and how data subjects exercise their rights — and where it all persists.</p>

    <nav class="df-tabs" aria-label="Data flow sections">
      <a href="#inventory"  class="df-tab active"><span class="t-num">1</span>PI inventory</a>
      <a href="#processors" class="df-tab"><span class="t-num">2</span>Sub-processors</a>
      <a href="#rights"     class="df-tab"><span class="t-num">3</span>DSAR rights</a>
      <a href="#vault33"    class="df-tab"><span class="t-num">4</span>Vault33</a>
    </nav>

    <div class="df-banner">
      <h3>Why this view exists</h3>
      <p>Klikk processes <strong>special personal information</strong> (criminal record, financial), holds <strong>FICA-grade records</strong> for 5+ years, and shares data with <strong>Operators</strong> under POPIA s20–21. This page is the single source of truth for what we hold, where it lives, who else touches it, how tenants exercise their rights, and — in section 4 — the <strong>Vault33</strong> system that persists every byte of it.</p>
    </div>

    <section class="df-section" id="inventory">
      <header>
        <h2>1 · PI inventory by lifecycle stage</h2>
        <p>What gets collected at each touchpoint, the lawful basis (POPIA s11), retention period, and where it physically lives.</p>
      </header>
      ${piByStage}
    </section>

    <section class="df-section" id="processors">
      <header>
        <h2>2 · Sub-processors &amp; Operators</h2>
        <p>Third parties that process tenant PI on Klikk's behalf. Each one needs an Operator agreement (POPIA s20–21) and, if cross-border, s72 safeguards.</p>
      </header>
      <div class="sp-grid">${sps}</div>
    </section>

    <section class="df-section" id="rights">
      <header>
        <h2>3 · Data subject rights — surfaced in product</h2>
        <p>Tenant rights under POPIA must be exercisable without writing to a lawyer. Each row below names the right, its statute reference, and where it lives in Klikk.</p>
      </header>
      ${dsars}
    </section>

    <section class="df-section" id="vault33">
      <header>
        <h2>4 · Vault33 — the compliance engine</h2>
        <p>The Django app that encrypts, audits, and gates access to every byte of tenant PI. Sections 1–3 describe the <em>policy</em>; this section describes the <em>implementation</em>.</p>
      </header>

      <div class="v33-hero">
        <div>
          <h3>Vault33</h3>
          <p>${vault33.summary.purpose}</p>
        </div>
        <div class="v33-lock"><i class="ph-duotone ph-vault"></i></div>
      </div>

      <div class="v33-spec v33-concept">
        <h4><i class="ph ph-books"></i> Conceptual model — the library</h4>
        <p class="lib-headline">${vault33.concept.headline}</p>
        <p class="lib-body">${vault33.concept.body}</p>
        <div class="v33-lib-map">
          <div class="v33-lib-row head">
            <div class="role">Library metaphor</div>
            <div class="maps"></div>
            <div class="meaning">What it maps to in Vault33</div>
          </div>
          ${conceptMap}
        </div>
        <div class="v33-lib-why">
          <h5>Why this model matters</h5>
          <ul>${conceptWhy}</ul>
        </div>
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-info"></i> What it is</h4>
        <dl class="v33-dl">
          ${sumKV('Name', '<code>' + vault33.summary.name + '</code>')}
          ${sumKV('Location', '<code>' + vault33.summary.location + '</code>')}
          ${sumKV('Surface', vault33.summary.surface)}
          ${sumKV('Consumers', vault33.summary.consumers)}
          ${sumKV('Product lines', vault33.summary.productLines)}
          ${sumKV('Ingestion skill', '<code>' + vault33.summary.ingestionSkill + '</code>')}
          ${sumKV('Version', vault33.summary.version)}
        </dl>
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-users-three"></i> Six entity types</h4>
        <p class="kick">Every person, company, trust, and asset in Klikk is one of six types — linked to others via a directed relationship graph.</p>
        <div class="v33-entities">${entityTiles}</div>
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-database"></i> Storage layers</h4>
        <p class="kick">Three physical stores. Structured data in Postgres, encrypted blobs on disk, vectors in ChromaDB for hybrid search.</p>
        <div class="v33-storage">${storeTiles}</div>
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-lock-key"></i> Encryption at rest</h4>
        <p class="kick">Fernet (AES-128-CBC + HMAC-SHA256) with a per-owner symmetric key. Satisfies POPIA s19 security-safeguards obligation.</p>
        <dl class="v33-dl">${encDl}</dl>
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-arrows-in"></i> Ingestion channels</h4>
        <p class="kick">How data gets IN to the vault. The <code>klikk-vault31-ingestion</code> skill targets the REST API and MCP write tools.</p>
        ${chans}
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-plugs-connected"></i> MCP tools · 23 total</h4>
        <p class="kick">Claude talks to Vault33 through these. Read tools return decrypted data; write tools are idempotent and audit every mutation.</p>
        <div class="v33-mcp">
          <div class="v33-mcp-side" data-mode="read">
            <h5>Read tools <span class="badge">10</span></h5>
            <div class="v33-mcp-list">${mcpReadList}</div>
          </div>
          <div class="v33-mcp-side" data-mode="write">
            <h5>Write tools <span class="badge">13</span></h5>
            <div class="v33-mcp-list">${mcpWriteList}</div>
          </div>
        </div>
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-shield-check"></i> POPIA coverage matrix</h4>
        <p class="kick">Every POPIA obligation that Vault33 directly delivers. Read alongside Section 3 (data subject rights) which surfaces them in product.</p>
        <div class="v33-popia head"><div>Statute</div><div>Obligation</div><div>How Vault33 delivers</div></div>
        ${popiaRows}
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-checks"></i> Status</h4>
        <p class="kick">What's built, what's partial, what's pending — as of v1.0 draft scoping (2026-04-17).</p>
        ${statusRows}
        <div class="v33-counts">${countTiles}</div>
      </div>

      <div class="v33-spec">
        <h4><i class="ph ph-warning"></i> Known gaps</h4>
        <p class="kick">Documented in the system doc as "future" or "not designed" — these are the hardening items before production.</p>
        ${gapRows}
      </div>
    </section>

    <script>
      // Highlight active tab on scroll
      (function(){
        const tabs = document.querySelectorAll('.df-tab');
        const sections = ['inventory','processors','rights','vault33'].map(id => document.getElementById(id));
        function onScroll(){
          const y = window.scrollY + 140;
          let active = 0;
          sections.forEach((s, i) => { if (s && s.offsetTop <= y) active = i; });
          tabs.forEach((t, i) => t.classList.toggle('active', i === active));
        }
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
      })();
    </script>
  `;
}

/* ---------- Logos page ────────────────────────────────────────
   Sourced from live app.klikk.co.za:
   - Favicon (admin/public/favicon.svg) — navy K + pink dot
   - Navbar wordmark (admin/src/components/AppLayout.vue) — text "Klikk" + pink "."
   - Brand mark in this workbench — gradient K square (workbench-only)
   ─────────────────────────────────────────────────────────────── */

/* The canonical favicon mark (lifted verbatim from admin/public/favicon.svg) */
const faviconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="100%" height="100%">
  <text x="14" y="23" font-family="'Inter','Arial',sans-serif" font-size="20" font-weight="700" fill="#2B2D6E" text-anchor="middle" letter-spacing="-0.5">K</text>
  <circle cx="24" cy="23" r="3" fill="#FF3D7F"/>
</svg>`;

/* Inverse / knockout — same construction, white K + pink dot for dark surfaces */
const faviconInverseSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="100%" height="100%">
  <text x="14" y="23" font-family="'Inter','Arial',sans-serif" font-size="20" font-weight="700" fill="#FFFFFF" text-anchor="middle" letter-spacing="-0.5">K</text>
  <circle cx="24" cy="23" r="3" fill="#FF3D7F"/>
</svg>`;

/* Mono — single colour (navy or white) for embossing, single-colour print */
const faviconMonoSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="100%" height="100%">
  <text x="14" y="23" font-family="'Inter','Arial',sans-serif" font-size="20" font-weight="700" fill="currentColor" text-anchor="middle" letter-spacing="-0.5">K</text>
  <circle cx="24" cy="23" r="3" fill="currentColor"/>
</svg>`;

const logosCss = `
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
  <style>
    .lg-banner{background:linear-gradient(135deg,#2B2D6E 0%,#3F4193 100%);color:#fff;border-radius:14px;padding:22px 26px;margin-bottom:32px;display:flex;align-items:center;gap:24px}
    .lg-banner .lg-mark{width:64px;height:64px;background:#fff;border-radius:14px;padding:8px;flex-shrink:0}
    .lg-banner h3{font-family:'Bricolage Grotesque','Fraunces',serif;font-weight:800;font-size:22px;margin:0 0 4px;letter-spacing:-.02em}
    .lg-banner p{margin:0;font-size:13.5px;opacity:.8;line-height:1.5;max-width:540px}
    .lg-section{margin-bottom:42px}
    .lg-section > header{margin-bottom:14px}
    .lg-section > header h2{font-family:'Fraunces',serif;font-weight:600;font-size:22px;color:#2B2D6E;margin:0}
    .lg-section > header p{margin:4px 0 0;color:#6c6e92;font-size:13px}
    .lg-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
    .lg-card{background:#fff;border-radius:14px;padding:0;box-shadow:0 1px 3px rgba(43,45,110,.06),0 8px 24px -12px rgba(43,45,110,.12);overflow:hidden;display:flex;flex-direction:column}
    .lg-canvas{height:160px;display:flex;align-items:center;justify-content:center;padding:20px;border-bottom:1px solid #EFEFF5;position:relative}
    .lg-canvas[data-bg="light"]{background:#FAFAFE}
    .lg-canvas[data-bg="dark"]{background:#2B2D6E}
    .lg-canvas[data-bg="accent"]{background:#FF3D7F}
    .lg-canvas[data-bg="check"]{background-color:#fff;background-image:linear-gradient(45deg,#F0EFF8 25%,transparent 25%,transparent 75%,#F0EFF8 75%),linear-gradient(45deg,#F0EFF8 25%,transparent 25%,transparent 75%,#F0EFF8 75%);background-size:16px 16px;background-position:0 0,8px 8px}
    .lg-mark-32{width:32px;height:32px}
    .lg-mark-64{width:64px;height:64px}
    .lg-mark-96{width:96px;height:96px}
    .lg-wordmark{font-family:'Bricolage Grotesque','Inter',sans-serif;font-weight:800;letter-spacing:-.02em;line-height:1}
    .lg-wordmark[data-size="md"]{font-size:36px}
    .lg-wordmark[data-size="lg"]{font-size:56px}
    .lg-wordmark[data-tone="light"]{color:#2B2D6E}
    .lg-wordmark[data-tone="dark"]{color:#fff}
    .lg-wordmark .accent{color:#FF3D7F}
    .lg-meta{padding:12px 14px}
    .lg-name{font-size:13px;font-weight:600;color:#2B2D6E;font-family:'DM Sans',sans-serif}
    .lg-spec{font-size:11px;color:#8a8ca8;margin-top:2px;font-family:ui-monospace,Menlo,monospace}
    .lg-detail{background:#fff;border-radius:14px;padding:18px 22px;margin-bottom:20px;box-shadow:0 1px 3px rgba(43,45,110,.06)}
    .lg-detail h4{font-family:'Fraunces',serif;font-weight:600;font-size:15px;color:#2B2D6E;margin:0 0 4px}
    .lg-detail dl{display:grid;grid-template-columns:140px 1fr;gap:8px 16px;margin:10px 0 0;font-size:12.5px}
    .lg-detail dt{color:#8a8ca8;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;padding-top:1px}
    .lg-detail dd{margin:0;color:#5b5e8c;font-family:ui-monospace,Menlo,monospace;font-size:11.5px;line-height:1.5}
    .lg-rules{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-top:14px}
    .lg-rule{background:#FAFAFE;border-radius:10px;padding:14px 16px;border-left:3px solid var(--hue,#16A34A)}
    .lg-rule[data-tone="dont"]{border-left-color:#DC2626;background:#FFE4EF}
    .lg-rule h5{font-family:'DM Sans',sans-serif;font-weight:600;font-size:11.5px;color:var(--hue,#15803D);margin:0 0 4px;text-transform:uppercase;letter-spacing:.06em}
    .lg-rule[data-tone="dont"] h5{color:#9C1D4F}
    .lg-rule p{margin:0;font-size:12.5px;color:#5b5e8c;line-height:1.5}
  </style>`;

function pageLogos() {
  /* The mark in three sizes on three canvases — inventory + usage in one glance */
  const markVariants = [
    { name: 'Favicon · default',   spec: '32×32 · navy + pink', svg: faviconSvg,         bg: 'light', size: 32  },
    { name: 'Favicon · dark mode', spec: 'inverse',             svg: faviconInverseSvg,  bg: 'dark',  size: 32  },
    { name: 'App icon · 64',       spec: 'PWA / launcher',      svg: faviconSvg,         bg: 'light', size: 64  },
    { name: 'App icon · 96',       spec: 'high-density',        svg: faviconSvg,         bg: 'light', size: 96  },
    { name: 'Mono · navy',         spec: 'single-colour print', svg: faviconMonoSvg,     bg: 'light', size: 64, color: '#2B2D6E' },
    { name: 'Mono · white',        spec: 'on photography',      svg: faviconMonoSvg,     bg: 'check', size: 64, color: '#2B2D6E' },
    { name: 'Knockout · accent bg',spec: 'avoid in production', svg: faviconInverseSvg,  bg: 'accent',size: 64  },
  ];

  const wordmarkVariants = [
    { name: 'Wordmark · navbar',  spec: '36px · Bricolage 800 · navy on light', tone: 'light', size: 'md', bg: 'light' },
    { name: 'Wordmark · hero',    spec: '56px · Bricolage 800 · navy on light', tone: 'light', size: 'lg', bg: 'light' },
    { name: 'Wordmark · dark',    spec: '36px · Bricolage 800 · white on navy', tone: 'dark',  size: 'md', bg: 'dark'  },
    { name: 'Wordmark · accent',  spec: 'avoid: pink dot disappears',           tone: 'dark',  size: 'md', bg: 'accent', warn: true },
  ];

  const markCards = markVariants.map(v => `
    <article class="lg-card">
      <div class="lg-canvas" data-bg="${v.bg}">
        <div class="lg-mark-${v.size}" ${v.color?`style="color:${v.color}"`:''}>${v.svg}</div>
      </div>
      <div class="lg-meta">
        <div class="lg-name">${v.name}</div>
        <div class="lg-spec">${v.spec}</div>
      </div>
    </article>`).join('');

  const wordmarkCards = wordmarkVariants.map(v => `
    <article class="lg-card">
      <div class="lg-canvas" data-bg="${v.bg}">
        <span class="lg-wordmark" data-size="${v.size}" data-tone="${v.tone}">Klikk<span class="accent">.</span></span>
      </div>
      <div class="lg-meta">
        <div class="lg-name">${v.name}</div>
        <div class="lg-spec">${v.spec}</div>
      </div>
    </article>`).join('');

  const lockup = `
    <article class="lg-card">
      <div class="lg-canvas" data-bg="light" style="gap:14px">
        <div class="lg-mark-64">${faviconSvg}</div>
        <span class="lg-wordmark" data-size="lg" data-tone="light">Klikk<span class="accent">.</span></span>
      </div>
      <div class="lg-meta">
        <div class="lg-name">Lockup · horizontal</div>
        <div class="lg-spec">mark + wordmark · 14px gap</div>
      </div>
    </article>
    <article class="lg-card">
      <div class="lg-canvas" data-bg="dark" style="gap:14px">
        <div class="lg-mark-64">${faviconInverseSvg}</div>
        <span class="lg-wordmark" data-size="lg" data-tone="dark">Klikk<span class="accent">.</span></span>
      </div>
      <div class="lg-meta">
        <div class="lg-name">Lockup · dark</div>
        <div class="lg-spec">white K + white wordmark + pink dot</div>
      </div>
    </article>
    <article class="lg-card">
      <div class="lg-canvas" data-bg="light" style="flex-direction:column;gap:10px">
        <div class="lg-mark-64">${faviconSvg}</div>
        <span class="lg-wordmark" data-size="md" data-tone="light">Klikk<span class="accent">.</span></span>
      </div>
      <div class="lg-meta">
        <div class="lg-name">Lockup · stacked</div>
        <div class="lg-spec">for square footprints</div>
      </div>
    </article>`;

  return logosCss + `
    <h1>Logos</h1>
    <p class="lede">The Klikk brand mark, wordmark, and lockups — pulled from <code>app.klikk.co.za</code> + <code>admin/public/favicon.svg</code>.</p>

    <div class="lg-banner">
      <div class="lg-mark">${faviconSvg}</div>
      <div>
        <h3>Klikk<span style="color:#FF3D7F">.</span></h3>
        <p>One letter, one dot, two colours. The "K" is the consonant landlords say when they describe what they do ("we collect rent"). The dot is the click — confirmation, completion, the pink moment of action.</p>
      </div>
    </div>

    <div class="lg-detail">
      <h4>Construction</h4>
      <dl>
        <dt>Mark file</dt>          <dd>admin/public/favicon.svg · 32×32 viewBox · 340 bytes</dd>
        <dt>K letterform</dt>       <dd>Inter 700 · 20px · letter-spacing −0.5 · text-anchor middle · fill #2B2D6E</dd>
        <dt>Pink dot</dt>           <dd>circle cx=24 cy=23 r=3 · fill #FF3D7F</dd>
        <dt>Wordmark family</dt>    <dd>Bricolage Grotesque 800 (display) · loaded from Google Fonts</dd>
        <dt>Body family</dt>        <dd>Inter 400 / 500 / 600 / 700 (sans body)</dd>
        <dt>Navy</dt>               <dd>#2B2D6E · used for K, body text, navbar</dd>
        <dt>Accent</dt>             <dd>#FF3D7F · used for the dot, the wordmark period, primary CTAs</dd>
      </dl>
    </div>

    <section class="lg-section">
      <header>
        <h2>Mark variants</h2>
        <p>The "K + dot" mark in every legitimate context. Knockout on accent is included to show why you'd avoid it (the pink dot disappears).</p>
      </header>
      <div class="lg-grid">${markCards}</div>
    </section>

    <section class="lg-section">
      <header>
        <h2>Wordmark variants</h2>
        <p>"Klikk." rendered in Bricolage Grotesque 800. The pink full-stop is part of the mark — never substitute a different glyph.</p>
      </header>
      <div class="lg-grid">${wordmarkCards}</div>
    </section>

    <section class="lg-section">
      <header>
        <h2>Lockups</h2>
        <p>Mark + wordmark together. Horizontal is the default; stacked exists for square real estate (app icons, social avatars).</p>
      </header>
      <div class="lg-grid">${lockup}</div>
    </section>

    <section class="lg-section">
      <header>
        <h2>Do &amp; don't</h2>
        <p>Rules to keep the mark consistent across surfaces.</p>
      </header>
      <div class="lg-rules">
        <div class="lg-rule" data-tone="do" style="--hue:#15803D"><h5>Do · clear space</h5><p>Maintain padding equal to the dot's diameter on all sides — never crowd the mark.</p></div>
        <div class="lg-rule" data-tone="do" style="--hue:#15803D"><h5>Do · single accent</h5><p>The pink dot / period is the only accent allowed in the mark itself. Everywhere else: navy.</p></div>
        <div class="lg-rule" data-tone="do" style="--hue:#15803D"><h5>Do · vector only</h5><p>Always use the SVG. Don't rasterise below 64px — the K's letter-spacing breaks.</p></div>
        <div class="lg-rule" data-tone="dont"><h5>Don't · stretch</h5><p>The mark is locked to a 32×32 grid. Aspect ratio is part of the brand.</p></div>
        <div class="lg-rule" data-tone="dont"><h5>Don't · recolour</h5><p>No teal K, no blue dot, no gradient mark. Navy + pink, or single-colour mono.</p></div>
        <div class="lg-rule" data-tone="dont"><h5>Don't · accent background</h5><p>Pink dot disappears on pink. Use the dark or light variants instead.</p></div>
      </div>
    </section>
  `;
}

function pageIcons() {
  const weightClass = w => (w === 'regular' ? 'ph' : `ph-${w}`);
  const icon = (name, weight = 'regular') => `<i class="${weightClass(weight)} ph-${name}"></i>`;

  /* Icon gallery (regular weight by default, hover reveals fill) */
  const cell = name => `
    <div class="ico-cell">
      <div class="ico-swap">
        <span class="ico-default">${icon(name, 'regular')}</span>
        <span class="ico-hover">${icon(name, 'fill')}</span>
      </div>
      <code class="ico-name">${name}</code>
    </div>`;

  const groups = iconGroups.map(g => `
    <section>
      <header><h2>${g.title}</h2><p>${g.icons.length} icons · hover to see <code>fill</code></p></header>
      <div class="card"><div class="ico-grid">${g.icons.map(cell).join('')}</div></div>
    </section>`).join('');

  /* Six-weight comparison using a familiar icon */
  const weightCompare = iconWeights.map(w => `
    <div class="weight-col ${w.key === 'regular' ? 'active' : ''}">
      <div class="weight-demo">${icon('house', w.key)}</div>
      <div class="weight-key"><code>${w.key}</code></div>
      <div class="weight-note">${w.stroke}</div>
    </div>`).join('');

  /* Weight usage table */
  const usageRows = weightUsage.map(u => `
    <div class="usage-row">
      <div class="usage-demo">${icon(u.weight === 'fill' ? 'seal-check' : u.weight === 'bold' ? 'arrow-right' : u.weight === 'duotone' ? 'house-line' : u.weight === 'light' ? 'clock' : 'check-circle', u.weight)}</div>
      <div class="usage-body">
        <div class="usage-role">${u.role}</div>
        <div class="usage-why">${u.why}</div>
      </div>
      <div class="usage-pill"><code>${u.weight}</code></div>
    </div>`).join('');

  const css = `
    <!-- Phosphor web font, all weights -->
    <script src="https://unpkg.com/@phosphor-icons/web@2.1.1"></script>
    <style>
      .card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 1px 3px rgba(43,45,110,.06),0 8px 24px -12px rgba(43,45,110,.12)}
      .ico-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(108px,1fr));gap:4px}
      .ico-cell{display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px 8px;border-radius:10px;transition:background .12s}
      .ico-cell:hover{background:#FAFAFE}
      .ico-swap{position:relative;width:24px;height:24px;color:#2B2D6E;transition:color .14s}
      .ico-swap i{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:24px;line-height:1;transition:opacity .18s}
      .ico-default{opacity:1}
      .ico-hover{opacity:0}
      .ico-cell:hover .ico-swap{color:#FF3D7F;transform:scale(1.08);transition:all .14s}
      .ico-cell:hover .ico-default{opacity:0}
      .ico-cell:hover .ico-hover{opacity:1}
      .ico-name{font-size:11px;color:#8a8ca8;background:none;padding:0;font-family:ui-monospace,Menlo,monospace}
      .spec-card{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}
      .spec-item{padding:14px;background:#FAFAFE;border-radius:10px}
      .spec-item .lbl{font-size:11px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
      .spec-item .val{margin-top:4px;font-size:14px;color:#2B2D6E;font-weight:500}
      .weights{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
      .weight-col{padding:16px 10px;background:#FAFAFE;border-radius:12px;text-align:center;border:2px solid transparent;transition:all .14s}
      .weight-col.active{border-color:#FF3D7F;background:#fff;box-shadow:0 8px 20px -14px rgba(255,61,127,.35)}
      .weight-col:hover{background:#fff;border-color:#EFEFF5}
      .weight-col.active:hover{border-color:#FF3D7F}
      .weight-demo{font-size:34px;color:#2B2D6E;line-height:1;margin-bottom:10px;display:flex;justify-content:center}
      .weight-demo i{display:block}
      .weight-col.active .weight-demo{color:#FF3D7F}
      .weight-key{margin-bottom:6px}
      .weight-key code{font-size:12.5px;padding:2px 8px;background:#fff;font-weight:600;color:#2B2D6E}
      .weight-col.active .weight-key code{background:#FF3D7F;color:#fff}
      .weight-note{font-size:11.5px;color:#6c6e92;line-height:1.35}
      .usage-row{display:grid;grid-template-columns:48px 1fr auto;gap:14px;align-items:center;padding:12px 4px;border-bottom:1px solid #EFEFF5}
      .usage-row:last-child{border-bottom:0}
      .usage-demo{width:40px;height:40px;background:#F0EFF8;border-radius:10px;display:flex;align-items:center;justify-content:center;color:#2B2D6E;font-size:20px}
      .usage-role{font-size:14px;font-weight:500;color:#2B2D6E}
      .usage-why{font-size:12.5px;color:#6c6e92;margin-top:2px;line-height:1.35}
      .usage-pill code{background:#FFE4EF;color:#FF3D7F;font-size:11px;font-weight:600;padding:3px 9px;border-radius:6px}
      .callout{background:#F0EFF8;border-left:3px solid #FF3D7F;padding:12px 16px;border-radius:0 10px 10px 0;font-size:13.5px;color:#2B2D6E;line-height:1.5;margin-top:14px}
      .hero{background:linear-gradient(135deg,#2B2D6E 0%,#1E1F57 100%);color:#fff;border-radius:16px;padding:28px 28px;margin-bottom:16px;display:flex;align-items:center;gap:28px;box-shadow:0 20px 40px -18px rgba(43,45,110,.3)}
      .hero-ico{font-size:72px;color:#FF3D7F;line-height:1}
      .hero-body{flex:1}
      .hero h3{color:#fff;text-transform:none;letter-spacing:-.01em;font-family:'Fraunces',serif;font-weight:600;font-size:22px;margin:0 0 4px}
      .hero p{margin:0;color:rgba(255,255,255,.75);font-size:13.5px;line-height:1.5}
      .hero-stats{display:flex;gap:24px;margin-top:12px}
      .hero-stats > div{font-size:11px;color:rgba(255,255,255,.55);text-transform:uppercase;letter-spacing:.08em}
      .hero-stats strong{display:block;font-family:'Fraunces',serif;font-size:20px;color:#fff;letter-spacing:-.01em;margin-top:2px;font-weight:600;text-transform:none}
      @media (max-width:640px){.weights{grid-template-columns:repeat(3,1fr)}}
    </style>`;

  /* ── Klikk loaders ── motion variants of the K + dot mark ─────── */
  const loadersCss = `
    <style>
      .ldr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin-bottom:16px}
      .ldr-card{background:#fff;border-radius:14px;box-shadow:0 1px 3px rgba(43,45,110,.06);overflow:hidden;display:flex;flex-direction:column}
      .ldr-canvas{height:120px;display:flex;align-items:center;justify-content:center;background:#FAFAFE;border-bottom:1px solid #EFEFF5}
      .ldr-canvas[data-bg="dark"]{background:#2B2D6E}
      .ldr-canvas[data-bg="dark"] .klikk-K{color:#fff}
      .ldr-meta{padding:11px 14px}
      .ldr-name{font-size:12.5px;font-weight:600;color:#2B2D6E;font-family:'DM Sans',sans-serif}
      .ldr-spec{font-size:10.5px;color:#8a8ca8;margin-top:2px;font-family:ui-monospace,Menlo,monospace}
      /* Canonical mark in motion: K (text) + 6px pink dot */
      .klikk-loader{display:inline-flex;align-items:center;gap:5px;font-family:'Inter',sans-serif;font-weight:700;font-size:18px;line-height:1;color:#2B2D6E}
      .klikk-loader.lg{font-size:28px;gap:7px}
      .klikk-loader .klikk-K{}
      .klikk-loader .klikk-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#FF3D7F}
      .klikk-loader.lg .klikk-dot{width:9px;height:9px}
      /* Variant 1 — canonical horizontal bounce (production: PublicSignView) */
      @keyframes klikk-bounce-x{0%,100%{transform:translateX(0)}50%{transform:translateX(4px)}}
      .klikk-loader[data-anim="bounce-x"] .klikk-dot{animation:klikk-bounce-x 0.8s ease-in-out infinite}
      /* Variant 2 — vertical hop */
      @keyframes klikk-bounce-y{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
      .klikk-loader[data-anim="bounce-y"] .klikk-dot{animation:klikk-bounce-y 0.8s ease-in-out infinite}
      /* Variant 3 — pulse / heartbeat */
      @keyframes klikk-pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.6);opacity:.6}}
      .klikk-loader[data-anim="pulse"] .klikk-dot{animation:klikk-pulse 1.0s ease-in-out infinite}
      /* Variant 4 — colour shimmer (cycle navy → pink → navy) */
      @keyframes klikk-shimmer{0%,100%{background:#FF3D7F;transform:scale(1)}50%{background:#2B2D6E;transform:scale(1.3)}}
      .klikk-loader[data-anim="shimmer"] .klikk-dot{animation:klikk-shimmer 1.4s ease-in-out infinite}
      /* Inline label form — used in buttons (e.g. "Submitting") */
      .klikk-inline{display:inline-flex;align-items:center;gap:8px;padding:7px 14px;background:#2B2D6E;color:#fff;border-radius:10px;font-family:'DM Sans',sans-serif;font-size:13px;font-weight:600}
      .klikk-inline .klikk-loader{color:#fff;font-size:13px;gap:4px}
      .klikk-inline .klikk-loader .klikk-dot{width:5px;height:5px}
      .ldr-detail{background:#fff;border-radius:14px;padding:18px 22px;margin-bottom:16px;box-shadow:0 1px 3px rgba(43,45,110,.06)}
      .ldr-detail h4{font-family:'Fraunces',serif;font-weight:600;font-size:15px;color:#2B2D6E;margin:0 0 4px}
      .ldr-detail dl{display:grid;grid-template-columns:140px 1fr;gap:8px 16px;margin:10px 0 0;font-size:12.5px}
      .ldr-detail dt{color:#8a8ca8;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;padding-top:1px}
      .ldr-detail dd{margin:0;color:#5b5e8c;font-family:ui-monospace,Menlo,monospace;font-size:11.5px;line-height:1.5}
    </style>`;

  const loaderVariants = [
    { anim: 'bounce-x', name: 'Bounce-X · canonical', spec: 'translateX(0→4px) · 0.8s · used in lease-signing Submit', size: '', bg: 'light' },
    { anim: 'bounce-y', name: 'Bounce-Y · vertical',  spec: 'translateY(0→-4px) · 0.8s · alt for vertical contexts',  size: '', bg: 'light' },
    { anim: 'pulse',    name: 'Pulse · scale 1→1.6',  spec: 'opacity 1→.6 · 1.0s · for "thinking" states',           size: '', bg: 'light' },
    { anim: 'shimmer',  name: 'Shimmer · navy⇄pink',  spec: 'colour swap + scale · 1.4s · for AI-thinking',         size: '', bg: 'light' },
    { anim: 'bounce-x', name: 'Bounce-X · dark',      spec: 'inverse — white K · 0.8s',                             size: '', bg: 'dark'  },
    { anim: 'bounce-x', name: 'Bounce-X · large',     spec: 'hero loader · 28px',                                    size: 'lg', bg: 'light' },
  ];

  const loaderCard = v => `
    <article class="ldr-card">
      <div class="ldr-canvas" data-bg="${v.bg}">
        <span class="klikk-loader ${v.size}" data-anim="${v.anim}"><span class="klikk-K">K</span><span class="klikk-dot"></span></span>
      </div>
      <div class="ldr-meta">
        <div class="ldr-name">${v.name}</div>
        <div class="ldr-spec">${v.spec}</div>
      </div>
    </article>`;

  const loadersSection = `
    ${loadersCss}
    <section style="margin-bottom:42px">
      <header><h2>Klikk loaders</h2><p>The mark in motion — the dot is what moves. Variants for context, not decoration.</p></header>
      <div class="ldr-grid">${loaderVariants.map(loaderCard).join('')}</div>
      <div class="ldr-detail">
        <h4>Inline form — button labels</h4>
        <p style="font-size:12.5px;color:#6c6e92;margin:0 0 14px;line-height:1.5">In buttons mid-action, the loader replaces the icon and pairs with the verb in present-progressive ("Submitting", "Uploading", "Saving"). The dot bounces at half-size next to the K.</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <span class="klikk-inline"><span class="klikk-loader" data-anim="bounce-x"><span class="klikk-K">K</span><span class="klikk-dot"></span></span><span>Submitting</span></span>
          <span class="klikk-inline"><span class="klikk-loader" data-anim="bounce-x"><span class="klikk-K">K</span><span class="klikk-dot"></span></span><span>Uploading</span></span>
          <span class="klikk-inline" style="background:#FF3D7F"><span class="klikk-loader" data-anim="bounce-x"><span class="klikk-K">K</span><span class="klikk-dot" style="background:#fff"></span></span><span>Saving</span></span>
        </div>
        <dl>
          <dt>Source</dt>            <dd>admin/src/views/signing/PublicSignView.vue lines 374–377, 835–841</dd>
          <dt>K letter</dt>          <dd>Inter 700 · 14–28px · text-white in inline button</dd>
          <dt>Dot</dt>               <dd>5–9px circle · background #FF3D7F · animation: klikk-bounce 0.8s ease-in-out infinite</dd>
          <dt>Cadence</dt>           <dd>0.8s = ~75 BPM (relaxed heartbeat) — feels like progress without urgency</dd>
        </dl>
      </div>
    </section>
  `;

  return css + loadersSection + `
    <h1>Icons</h1>
    <p class="lede">Phosphor is the only icon library. Six weights give you hierarchy for free.</p>

    <div class="hero">
      <div class="hero-ico"><i class="ph-duotone ph-house-line"></i></div>
      <div class="hero-body">
        <h3>Phosphor Icons</h3>
        <p>MIT-licensed, 9,000+ glyphs, six weights. Bigger property vocabulary than Lucide and weight-as-hierarchy without adding color.</p>
        <div class="hero-stats">
          <div>Icons<strong>9,000+</strong></div>
          <div>Weights<strong>6</strong></div>
          <div>License<strong>MIT · free</strong></div>
          <div>Grid<strong>24 px</strong></div>
        </div>
      </div>
    </div>

    <section>
      <header><h2>Specification</h2><p>The rules every icon in the product must follow.</p></header>
      <div class="card">
        <div class="spec-card">
          <div class="spec-item"><div class="lbl">Library</div><div class="val">Phosphor Icons</div></div>
          <div class="spec-item"><div class="lbl">Default weight</div><div class="val">regular</div></div>
          <div class="spec-item"><div class="lbl">Size (inline)</div><div class="val">18 px</div></div>
          <div class="spec-item"><div class="lbl">Size (standalone)</div><div class="val">22 – 24 px</div></div>
          <div class="spec-item"><div class="lbl">Color</div><div class="val">currentColor</div></div>
          <div class="spec-item"><div class="lbl">License</div><div class="val">MIT · free</div></div>
        </div>
        <div class="callout">No emoji in product UI. Emoji are allowed only in marketing copy and user-generated content.</div>
      </div>
    </section>

    <section>
      <header><h2>The six weights</h2><p><strong>Regular</strong> is default. Every other weight is a semantic choice — use them deliberately, not decoratively.</p></header>
      <div class="card"><div class="weights">${weightCompare}</div></div>
    </section>

    <section>
      <header><h2>Weight usage</h2><p>When to reach for each weight in Klikk UI.</p></header>
      <div class="card">${usageRows}</div>
    </section>

    ${groups}

    <section>
      <header><h2>Production integration</h2><p>Packages and snippets by stack.</p></header>
      <div class="card">
        <div class="spec-card">
          <div class="spec-item"><div class="lbl">Vue (admin / tenant / agent)</div><div class="val">@phosphor-icons/vue</div></div>
          <div class="spec-item"><div class="lbl">React (future)</div><div class="val">@phosphor-icons/react</div></div>
          <div class="spec-item"><div class="lbl">Static HTML / prototype</div><div class="val">@phosphor-icons/web (CDN)</div></div>
          <div class="spec-item"><div class="lbl">Flutter (if revived)</div><div class="val">phosphor_flutter</div></div>
        </div>
        <div class="callout" style="margin-top:18px">
          Vue example:&nbsp;<code>&lt;PhHouse :size="22" weight="regular" /&gt;</code>&nbsp;·&nbsp;
          CDN example:&nbsp;<code>&lt;i class="ph ph-house"&gt;&lt;/i&gt;</code>
        </div>
      </div>
    </section>
  `;
}

/* ---------- Data model ---------- */
// Sourced from a fresh Haiku survey of backend/apps/<app>/models.py + signals.py, April 2026.
// This is the canonical schema spec for rebuild-from-cold.
const dataModel = {
  stats: [
    ['Apps',       '13',  'Django apps (excl. the_volt / Vault33)'],
    ['Models',     '75+', 'Concrete Django model classes'],
    ['Signals',    '14',  'post_save / post_delete handlers'],
    ['Status enums','22', 'State machines across the domain'],
    ['Role types', '10',  'User.role values (agent, supplier, owner, tenant, …)'],
    ['Gaps',       '7',   'Known missing models — Invoice, Payment, Inspection, …'],
  ],
  graph: [
    { from: 'User',             to: 'Person',            via: 'linked_user OneToOne · auto-link on signup by email/phone' },
    { from: 'Person',            to: 'Tenant / Landlord', via: 'OneToOne per role' },
    { from: 'Property',          to: 'Unit',               via: '1-to-many (a property has units)' },
    { from: 'Unit',              to: 'Lease',              via: '1-to-many · only one can be ACTIVE at a time' },
    { from: 'Lease',             to: 'Tenant',             via: 'primary_tenant FK + LeaseTenant M2M (co-tenants) + LeaseOccupant + LeaseGuarantor' },
    { from: 'Lease',             to: 'Unit.status',        via: 'signal: sync OCCUPIED / AVAILABLE on every save' },
    { from: 'Lease',             to: 'ESigningSubmission', via: 'one-to-many · signed_pdf_file stored on completion' },
    { from: 'RentalMandate',     to: 'ESigningSubmission', via: 'OneToOne · status synced on completion signal' },
    { from: 'MaintenanceRequest',to: 'Supplier',           via: 'JobDispatch → JobQuoteRequest → Supplier (fan-out quoting)' },
    { from: 'MaintenanceRequest',to: 'SupplierJobAssignment', via: 'scoped access · copies tenant contact fields for POPIA minimisation' },
    { from: 'Tenant',            to: 'TenantUnitAssignment', via: 'temporal: { tenant, unit, start_date, end_date } — current occupancy' },
    { from: 'Property',          to: 'PropertyOwnership',  via: 'temporal: { property, landlord, start_date, end_date, is_current }' },
    { from: 'Property',          to: 'RentalMandate',      via: 'mandate scopes agent access to property' },
    { from: 'Property',          to: 'ComplianceCertificate · MunicipalAccount · InsurancePolicy · PropertyDetail · PropertyPhoto · PropertyDocument', via: 'per-property ancillary records' },
    { from: 'MaintenanceRequest',to: 'MaintenanceActivity', via: 'chat log · vectorized into RAG · broadcast via WebSocket' },
  ],
  apps: [
    {
      name: 'accounts',
      purpose: 'Identity, RBAC, auth audit, agency singleton',
      models: [
        { m: 'User',             p: 'System login account. email is unique. role enum determines portal.', fk: 'agency → Agency', enums: 'role: TENANT | AGENT | ADMIN | SUPPLIER | OWNER | AGENCY_ADMIN | ESTATE_AGENT | MANAGING_AGENT | ACCOUNTANT | VIEWER' },
        { m: 'Person',           p: 'Natural person or company. May or may not have a User.', fk: 'linked_user → User (OneToOne)', enums: 'person_type: INDIVIDUAL | COMPANY' },
        { m: 'PersonDocument',   p: 'ID, proof of address, proof of income, FICA bundle.', fk: 'person → Person', enums: 'document_type: ID_COPY | PROOF_OF_ADDRESS | PROOF_OF_INCOME | FICA | OTHER' },
        { m: 'OTPCode',          p: 'Phone OTP for login.', fk: 'user → User', enums: '—' },
        { m: 'PushToken',        p: 'FCM / APNs device tokens.', fk: 'user → User', enums: 'platform: IOS | ANDROID' },
        { m: 'UserInvite',       p: 'Pending user invite with token.', fk: 'agency, invited_by → User', enums: '—' },
        { m: 'AuthAuditLog',     p: 'Immutable auth trail.', fk: 'user → User', enums: 'event_type: LOGIN_SUCCESS | PASSWORD_CHANGE | OTP_VERIFIED | …' },
        { m: 'Agency',           p: 'Singleton agency record with trust account + FICA fields.', fk: '—', enums: 'account_type: AGENCY | INDIVIDUAL' },
        { m: 'LoginAttempt',     p: 'Rate-limit tracking for failed logins.', fk: '—', enums: '—' },
      ],
    },
    {
      name: 'properties',
      purpose: 'Property, unit, landlord, mandate, compliance, market ops',
      models: [
        { m: 'Property',              p: 'Core property (apartment, house, commercial).', fk: 'owner → Person · agent → User', enums: 'property_type: APARTMENT | HOUSE | TOWNHOUSE | COMMERCIAL' },
        { m: 'Unit',                  p: 'Individual unit within a Property. Status synced by Lease signal.', fk: 'property → Property', enums: 'status: AVAILABLE | OCCUPIED | MAINTENANCE' },
        { m: 'UnitInfo',              p: 'WiFi / parking / utility metadata rows.', fk: 'property, unit', enums: 'icon_type: WIFI | ALARM | GARBAGE | PARKING | ELECTRICITY | WATER | GAS | INTERCOM | LAUNDRY | OTHER' },
        { m: 'PropertyAgentConfig',   p: 'AI agent playbook per property.', fk: 'property (OneToOne)', enums: '—' },
        { m: 'Landlord',              p: 'Owner entity (person, company, trust, CC).', fk: 'person → Person (OneToOne)', enums: 'landlord_type: INDIVIDUAL | COMPANY | TRUST | CC | PARTNERSHIP' },
        { m: 'LandlordDocument',      p: 'CIPC, trust deed, ID.', fk: 'landlord → Landlord', enums: '—' },
        { m: 'BankAccount',           p: 'Landlord bank account(s) for payout.', fk: 'landlord → Landlord', enums: '—' },
        { m: 'LandlordChatMessage',   p: 'Owner-onboarding chat memory.', fk: 'landlord · created_by → User', enums: 'role: USER | ASSISTANT | SYSTEM' },
        { m: 'PropertyOwnership',     p: 'Temporal ownership record (supports transfer).', fk: 'property, landlord', enums: 'owner_type: INDIVIDUAL | COMPANY | TRUST' },
        { m: 'RentalMandate',         p: 'Digitally signed management mandate.', fk: 'property, landlord, esigning_submission (OneToOne), created_by', enums: 'mandate_type: FULL_MANAGEMENT | LETTING_ONLY | RENT_COLLECTION | FINDERS_FEE · exclusivity: SOLE | OPEN · status: DRAFT | SENT | PARTIALLY_SIGNED | ACTIVE | EXPIRED | CANCELLED' },
        { m: 'PropertyGroup',         p: 'Admin grouping (M2M properties).', fk: 'properties (M2M)', enums: '—' },
        { m: 'PropertyDetail',        p: 'Physical & legal details (OneToOne).', fk: 'property (OneToOne)', enums: '—' },
        { m: 'PropertyPhoto',         p: 'Gallery: exterior / interior / flatlet / plans.', fk: 'property, unit', enums: 'category: EXTERIOR | INTERIOR | FLATLET | GARDEN | PLANS | OTHER' },
        { m: 'PropertyDocument',      p: 'Per-property document catalogue (40 doc_type values).', fk: 'property, unit', enums: 'doc_type: TITLE_DEED | ELECTRICAL_COC | MUNICIPAL | TENANT_ID | … (40 types)' },
        { m: 'ComplianceCertificate', p: 'Electrical / pest / gas / plumbing / fence / solar certs with expiry.', fk: 'property', enums: 'cert_type: ELECTRICAL | PEST | GAS | PLUMBING | FENCE | SOLAR | OTHER · status (method): VALID | EXPIRED | PENDING' },
        { m: 'MunicipalAccount',      p: 'Rates / water / electricity / refuse / sewerage account.', fk: 'property', enums: 'account_type: RATES | WATER | ELECTRICITY | REFUSE | SEWERAGE | COMBINED' },
        { m: 'MunicipalBill',         p: 'Monthly bill record (unique per account × month).', fk: 'property, municipal_account', enums: 'payment_status: UNPAID | PAID | OVERDUE | PARTIAL | DISPUTE' },
        { m: 'PropertyValuation',     p: 'Historical valuations (purchase, municipal, bank).', fk: 'property', enums: 'valuation_type: PURCHASE | MUNICIPAL | BANK | AGENT | FORMAL' },
        { m: 'InsurancePolicy',       p: 'Building / contents / combined / liability / landlord.', fk: 'property', enums: 'policy_type: BUILDING | CONTENTS | COMBINED | LIABILITY | LANDLORD | OTHER' },
        { m: 'InsuranceClaim',        p: 'Claim lifecycle.', fk: 'policy, property, unit', enums: 'status: DRAFT | SUBMITTED | ASSESSING | APPROVED | REJECTED | SETTLED | WITHDRAWN' },
        { m: 'PropertyViewing',       p: 'Prospect viewing appointment.', fk: 'property, unit, prospect → Person, agent → User, converted_to_lease → Lease', enums: 'status: SCHEDULED | CONFIRMED | COMPLETED | CANCELLED | CONVERTED' },
        { m: 'PropertyAgentAssignment', p: 'Scopes agent access per property + mandate.', fk: 'property, agent → User, mandate → RentalMandate, assigned_by → User', enums: 'assignment_type: ESTATE | MANAGING · status: ACTIVE | COMPLETED | INACTIVE' },
      ],
    },
    {
      name: 'leases',
      purpose: 'Lease agreements, templates, AI builder, onboarding, inventory',
      models: [
        { m: 'Lease',            p: 'Lease between Unit + primary_tenant. Only ACTIVE occupies.', fk: 'unit, primary_tenant → Person, previous_lease → Lease', enums: 'status: ACTIVE | EXPIRED | TERMINATED | PENDING' },
        { m: 'LeaseTemplate',    p: 'Reusable DOCX/HTML template with merge fields.', fk: '—', enums: '—' },
        { m: 'LeaseBuilderSession', p: 'AI-assisted lease conversation + extracted state + RHA flags.', fk: 'created_by → User, template, lease', enums: 'status: DRAFTING | REVIEW | FINALIZED' },
        { m: 'LeaseTenant',      p: 'Co-tenants (joint & several liability).', fk: 'lease, person', enums: '—' },
        { m: 'LeaseOccupant',    p: 'People physically residing (may differ from signatories).', fk: 'lease, person', enums: '—' },
        { m: 'LeaseGuarantor',   p: 'Surety. covers_tenant indicates which tenant.', fk: 'lease, person, covers_tenant → Person', enums: '—' },
        { m: 'ReusableClause',   p: 'Saved paragraph for insertion into any template.', fk: 'created_by · source_templates (M2M)', enums: 'category: parties | premises | financial | utilities | legal | signatures | general' },
        { m: 'LeaseEvent',       p: 'Auto-generated calendar events for lease dates.', fk: 'lease, completed_by → User', enums: 'event_type: CONTRACT_START | CONTRACT_END | DEPOSIT_DUE | FIRST_RENT | RENT_DUE | INSPECTION_IN | INSPECTION_OUT | INSPECTION_ROUTINE | NOTICE_DEADLINE | RENEWAL_REVIEW | CUSTOM · status: UPCOMING | DUE | COMPLETED | OVERDUE | CANCELLED' },
        { m: 'OnboardingStep',   p: 'Checklist per lease (deposit, signed, id-verified, move-in, keys, invoicing, tenant-app, welcome).', fk: 'lease, completed_by', enums: 'step_type: DEPOSIT_PAYMENT | LEASE_SIGNED | ID_VERIFIED | MOVE_IN_INSPECTION | KEY_HANDOVER | INVOICING_SETUP | TENANT_APP_SETUP | WELCOME_SENT' },
        { m: 'InventoryTemplate',p: 'Preset list of inventory items to copy.', fk: 'created_by', enums: '—' },
        { m: 'InventoryItem',    p: 'Per-lease item with condition_in / condition_out + photos.', fk: 'lease', enums: 'category: APPLIANCE | FURNITURE | FIXTURE | ELECTRONICS | LINEN | KITCHEN | KEYS | OTHER · condition: NEW | GOOD | FAIR | POOR | DAMAGED | MISSING' },
        { m: 'LeaseDocument',    p: 'Supporting docs (signed lease, ID copy).', fk: 'lease, uploaded_by → Person', enums: 'document_type: SIGNED_LEASE | ID_COPY | OTHER' },
      ],
    },
    {
      name: 'esigning',
      purpose: 'Native e-signing backend (ECTA s13 compliant)',
      models: [
        { m: 'ESigningSubmission', p: 'Signing workflow. document_hash + signed_pdf_hash give tamper evidence.', fk: 'lease, mandate, created_by → User', enums: 'signing_backend: NATIVE · status: PENDING | IN_PROGRESS | COMPLETED | DECLINED | EXPIRED · signing_mode: PARALLEL | SEQUENTIAL' },
        { m: 'ESigningAuditEvent',p: 'Immutable audit trail per submission.', fk: 'submission, user → User', enums: 'event_type: LINK_CREATED | DOCUMENT_VIEWED | CONSENT_GIVEN | SIGNATURE_APPLIED | SIGNING_COMPLETED | DOCUMENT_COMPLETED | LINK_EXPIRED | DRAFT_SAVED | SUPPORTING_DOC_UPLOADED | SUPPORTING_DOC_DELETED' },
        { m: 'ESigningPublicLink',p: 'Passwordless signing link (UUID PK).', fk: 'submission', enums: '—' },
        { m: 'SigningDraft',      p: "Tenant's partial progress between sessions.", fk: 'public_link (OneToOne)', enums: '—' },
        { m: 'SupportingDocument',p: 'Documents uploaded by signer during signing.', fk: 'public_link, submission', enums: 'document_type: BANK_STATEMENT | ID_COPY | PROOF_OF_ADDRESS | OTHER' },
      ],
    },
    {
      name: 'maintenance',
      purpose: 'Issues, suppliers, dispatch, quotes, AI triage',
      models: [
        { m: 'Supplier',            p: 'Service provider. ai_profile is AI-enriched for matching.', fk: 'linked_user → User (OneToOne)', enums: '—' },
        { m: 'SupplierTrade',       p: 'Trades offered.', fk: 'supplier', enums: 'trade: PLUMBING | ELECTRICAL | CARPENTRY | PAINTING | ROOFING | HVAC | LOCKSMITH | PEST_CONTROL | LANDSCAPING | APPLIANCE | GENERAL | SECURITY | CLEANING | OTHER' },
        { m: 'SupplierDocument',    p: 'Compliance docs (BEE, CIDB, insurance).', fk: 'supplier', enums: 'document_type: BANK_CONFIRMATION | BEE_CERTIFICATE | INSURANCE | CIDB | COMPANY_REG | TAX_CLEARANCE | OTHER' },
        { m: 'SupplierProperty',    p: 'Preferred supplier ↔ property link.', fk: 'supplier, property', enums: '—' },
        { m: 'MaintenanceRequest',  p: 'Issue lifecycle. Dedup via merged_into FK.', fk: 'unit, tenant → User, supplier, assigned_to → User, merged_into → self', enums: 'priority: LOW | MEDIUM | HIGH | URGENT · category: PLUMBING | ELECTRICAL | ROOF | APPLIANCE | SECURITY | PEST | GARDEN | OTHER · status: OPEN | IN_PROGRESS | RESOLVED | CLOSED' },
        { m: 'MaintenanceSkill',    p: 'KB rows for AI triage (symptom → steps).', fk: '—', enums: 'difficulty: EASY | MEDIUM | HARD' },
        { m: 'AgentQuestion',       p: 'Open question the AI asks staff to close knowledge loops.', fk: 'property, answered_by → User', enums: 'category: PROPERTY | LEASE | MAINTENANCE | TENANT | SUPPLIER | POLICY | OTHER · status: PENDING | ANSWERED | DISMISSED' },
        { m: 'MaintenanceActivity', p: 'Chat log per request (note / status / dispatch / quote / award / system).', fk: 'request, created_by → User', enums: 'activity_type: NOTE | STATUS_CHANGE | SUPPLIER_ASSIGNED | DISPATCH_SENT | QUOTE_RECEIVED | JOB_AWARDED | SYSTEM' },
        { m: 'JobDispatch',         p: 'Quote fan-out wrapper.', fk: 'maintenance_request (OneToOne), dispatched_by → User', enums: 'status: DRAFT | SENT | QUOTING | AWARDED | CANCELLED' },
        { m: 'JobQuoteRequest',     p: 'Quote request to one supplier. match_score is AI-scored fit.', fk: 'dispatch, supplier', enums: 'status: PENDING | VIEWED | QUOTED | DECLINED | AWARDED | EXPIRED' },
        { m: 'JobQuote',            p: "Supplier's quote response.", fk: 'quote_request (OneToOne)', enums: '—' },
        { m: 'AgentTokenLog',       p: 'Log every LLM call for cost tracking.', fk: 'user → User', enums: '—' },
        { m: 'SupplierJobAssignment', p: 'Scoped supplier access. Copies tenant contact fields → POPIA minimisation.', fk: 'supplier → User, maintenance_request, assigned_by', enums: 'status: ASSIGNED | IN_PROGRESS | COMPLETED' },
      ],
    },
    {
      name: 'tenant',
      purpose: 'Canonical tenant record + temporal occupancy',
      models: [
        { m: 'Tenant',              p: 'Bridges Person + User. current_assignment is derived.', fk: 'person (OneToOne), linked_user → User', enums: '—' },
        { m: 'TenantUnitAssignment',p: 'Temporal: { tenant, unit, start_date, end_date }. Source MANUAL or LEASE.', fk: 'tenant, unit (PROTECT), property (PROTECT), lease (SET_NULL), assigned_by', enums: 'source: MANUAL | LEASE' },
      ],
    },
    {
      name: 'ai',
      purpose: 'Tenant-facing chat, intelligence, token accounting',
      models: [
        { m: 'TenantChatSession', p: 'One row per tenant ↔ AI thread. Transcript in messages JSON.', fk: 'user → User, maintenance_request, agent_question', enums: '—' },
        { m: 'TenantIntelligence',p: 'Accumulated profile from chat — facts, complaint score, last_chat_at.', fk: 'user (OneToOne), property_ref, unit_ref', enums: '—' },
      ],
    },
    {
      name: 'notifications',
      purpose: 'Outbound email / SMS / WhatsApp delivery log',
      models: [
        { m: 'NotificationLog', p: 'Single delivery record — provider_message_id, status, error.', fk: '—', enums: 'channel: EMAIL | SMS | WHATSAPP · status: PENDING | SENT | FAILED' },
      ],
    },
    {
      name: 'market_data',
      purpose: 'Scraped P24 / PP listings + AI classification + price stats',
      models: [
        { m: 'ScrapeRun',          p: 'One scrape job. Tracks counts + duration.', fk: '—', enums: 'status: RUNNING | SUCCESS | PARTIAL | FAILED · listing_type: RENT | SALE' },
        { m: 'ListingAgency',      p: 'Agent / agency scraped from source.', fk: '—', enums: 'agent_type: PERSON | AGENCY | PRIVATE' },
        { m: 'MarketListing',      p: 'Scraped listing with AI visual classification + cross-site dedup.', fk: 'agency, scrape_run, canonical_listing (self)', enums: '—' },
        { m: 'MarketListingPhoto', p: 'Photos per listing (downloaded).', fk: 'listing', enums: '—' },
        { m: 'ListingStreetView',  p: 'Google Street View snapshot.', fk: 'listing (OneToOne)', enums: 'api_status: OK | ZERO_RESULTS | NOT_FOUND | QUOTA_EXCEEDED | ERROR' },
        { m: 'ListingNearbyPlace', p: 'Nearby schools / supermarkets / transit / wineries / beaches.', fk: 'listing', enums: '—' },
        { m: 'MarketPriceStats',   p: 'Daily aggregated stats per area × type × bedrooms.', fk: '—', enums: '—' },
        { m: 'MunicipalBylaw',     p: 'Bylaws ingested + vectorized for RAG.', fk: '—', enums: 'municipality: CITY_OF_CAPE_TOWN | STELLENBOSCH | DRAKENSTEIN' },
        { m: 'AreaNewsArticle',    p: 'Area news for market intelligence / RAG.', fk: '—', enums: 'sentiment: POSITIVE | NEUTRAL | NEGATIVE' },
      ],
    },
    {
      name: 'test_hub',
      purpose: 'Self-testing meta-app — tracks test-run history + health',
      models: [
        { m: 'TestRunRecord',       p: 'Historical test-run record per module / tier.', fk: '—', enums: 'tier: UNIT | INTEGRATION | E2E | ALL · phase: RED | GREEN | ALL · triggered_by: MANUAL | AI_AGENT | CI | SCHEDULED' },
        { m: 'TestIssue',           p: 'Bug discovered during manual testing.', fk: '—', enums: 'status: RED | FIXED' },
        { m: 'TestHealthSnapshot',  p: 'Periodic health snapshot — composite score.', fk: '—', enums: '—' },
        { m: 'TestModuleSelfHealth',p: 'Meta: test_hub tests itself (context_files_ok, rag_store_ok, …).', fk: '—', enums: '—' },
      ],
    },
  ],
  enums: [
    { name: 'Lease.status',                 values: 'ACTIVE · EXPIRED · TERMINATED · PENDING', note: 'Only ACTIVE occupies the Unit.' },
    { name: 'Unit.status',                  values: 'AVAILABLE · OCCUPIED · MAINTENANCE',       note: 'Synced by Lease post_save signal.' },
    { name: 'RentalMandate.status',         values: 'DRAFT · SENT · PARTIALLY_SIGNED · ACTIVE · EXPIRED · CANCELLED', note: 'Transitions driven by ESigningSubmission signal.' },
    { name: 'ESigningSubmission.status',    values: 'PENDING · IN_PROGRESS · COMPLETED · DECLINED · EXPIRED', note: 'signed_pdf_file set on COMPLETED.' },
    { name: 'MaintenanceRequest.status',    values: 'OPEN · IN_PROGRESS · RESOLVED · CLOSED',    note: 'Broadcast on every save via WebSocket.' },
    { name: 'MaintenanceRequest.priority',  values: 'LOW · MEDIUM · HIGH · URGENT',              note: 'Drives supplier match_score.' },
    { name: 'MaintenanceRequest.category',  values: 'PLUMBING · ELECTRICAL · ROOF · APPLIANCE · SECURITY · PEST · GARDEN · OTHER', note: 'Used for skill lookup.' },
    { name: 'JobDispatch.status',           values: 'DRAFT · SENT · QUOTING · AWARDED · CANCELLED', note: '—' },
    { name: 'JobQuoteRequest.status',       values: 'PENDING · VIEWED · QUOTED · DECLINED · AWARDED · EXPIRED', note: '—' },
    { name: 'AgentQuestion.status',         values: 'PENDING · ANSWERED · DISMISSED',            note: 'ANSWERED triggers RAG ingestion.' },
    { name: 'ComplianceCertificate (method)', values: 'VALID · EXPIRED · PENDING',               note: 'Derived from expiry_date.' },
    { name: 'MunicipalBill.payment_status', values: 'UNPAID · PAID · OVERDUE · PARTIAL · DISPUTE', note: '—' },
    { name: 'PropertyViewing.status',       values: 'SCHEDULED · CONFIRMED · COMPLETED · CANCELLED · CONVERTED', note: 'CONVERTED sets converted_to_lease.' },
    { name: 'InsuranceClaim.status',        values: 'DRAFT · SUBMITTED · ASSESSING · APPROVED · REJECTED · SETTLED · WITHDRAWN', note: '—' },
    { name: 'ScrapeRun.status',             values: 'RUNNING · SUCCESS · PARTIAL · FAILED',      note: '—' },
    { name: 'NotificationLog.status',       values: 'PENDING · SENT · FAILED',                   note: '—' },
    { name: 'TestIssue.status',             values: 'RED · FIXED',                               note: '—' },
    { name: 'User.role',                    values: 'TENANT · AGENT (legacy) · ADMIN · SUPPLIER · OWNER · AGENCY_ADMIN · ESTATE_AGENT · MANAGING_AGENT · ACCOUNTANT · VIEWER', note: 'Drives portal + routing.' },
    { name: 'Landlord.landlord_type',       values: 'INDIVIDUAL · COMPANY · TRUST · CC · PARTNERSHIP', note: 'Drives FICA doc requirements.' },
    { name: 'PropertyAgentAssignment.status', values: 'ACTIVE · COMPLETED · INACTIVE',           note: 'Combined with assignment_type: ESTATE | MANAGING.' },
    { name: 'TenantUnitAssignment.source',  values: 'MANUAL · LEASE',                            note: 'LEASE means derived from a signed lease.' },
    { name: 'Tenant.is_active',             values: 'true · false',                              note: 'Soft archive flag.' },
  ],
  signals: [
    { app: 'leases',       handler: 'sync_unit_status',              trigger: 'post_save Lease',             effect: 'Recompute Unit.status → OCCUPIED if ACTIVE lease exists, else AVAILABLE' },
    { app: 'leases',       handler: 'sync_unit_status_on_delete',    trigger: 'post_delete Lease',           effect: 'Reset Unit.status' },
    { app: 'leases',       handler: 'broadcast_lease_update',        trigger: 'post_save Lease',             effect: 'WebSocket broadcast to lease_updates group' },
    { app: 'maintenance',  handler: 'broadcast_issue_update',        trigger: 'post_save MaintenanceRequest', effect: 'WebSocket broadcast to maintenance_updates' },
    { app: 'maintenance',  handler: 'vectorize_maintenance_issue',   trigger: 'post_save MaintenanceRequest', effect: 'Ingest into maintenance RAG collection' },
    { app: 'maintenance',  handler: 'broadcast_question_update',     trigger: 'post_save AgentQuestion',     effect: 'WebSocket broadcast' },
    { app: 'maintenance',  handler: 'ingest_answered_question',      trigger: 'post_save AgentQuestion (w/ answer)', effect: 'Ingest into agent_qa RAG' },
    { app: 'maintenance',  handler: 'broadcast_activity_update',     trigger: 'post_save MaintenanceActivity', effect: 'WebSocket broadcast' },
    { app: 'maintenance',  handler: 'log_chat_message',              trigger: 'post_save MaintenanceActivity', effect: 'Append to JSONL log file' },
    { app: 'properties',   handler: 'enqueue_owner_rag_ingestion_on_landlord_save', trigger: 'post_save Landlord (w/ classification_data)', effect: 'Enqueue owner RAG ingestion' },
    { app: 'properties',   handler: 'enqueue_owner_rag_ingestion_on_document_save', trigger: 'post_save LandlordDocument', effect: 'Re-ingest owner RAG' },
    { app: 'properties',   handler: 'enqueue_property_information_rag_ingestion', trigger: 'post_save Property (w/ information_items)', effect: 'Enqueue property-info RAG' },
    { app: 'tenant',       handler: 'link_user_to_tenant',           trigger: 'post_save User',              effect: 'Auto-match Person by email/phone → link Tenant profile' },
    { app: 'esigning',     handler: 'sync_mandate_status',           trigger: 'post_save ESigningSubmission', effect: 'Sync RentalMandate.status + populate signed_document' },
  ],
  gaps: [
    { t: 'Invoice',     d: 'No Invoice model. Rent due_day lives on Lease only — no line items, no VAT split, no agent commission allocation.' },
    { t: 'Payment',     d: 'No Payment model. No received-rent record, no disbursement-to-landlord trail, no trust-account reconciliation.' },
    { t: 'Inspection',  d: 'Move-in / move-out inspections exist only as LeaseEvent placeholders. No structured inspection form, no damage-per-item record.' },
    { t: 'Dispute / Deduction', d: 'No tracking of landlord deductions from deposit or Rental Housing Tribunal complaints.' },
    { t: 'Notification preferences', d: 'NotificationLog is delivery-only. No User-level channel preferences (email vs. SMS vs. WhatsApp).' },
    { t: 'Credit history', d: 'Person.monthly_income exists — no payment track record, no internal credit score, no TransUnion snapshot persistence.' },
    { t: 'Lock-in / Break clause', d: 'notice_period_days + early_termination_penalty_months on Lease are numeric only — no break-clause schedule or penalty formula.' },
  ],
};

function pageDataModel() {
  const css = `
    <style>
      .dm-tabs{display:flex;gap:6px;background:#fff;padding:6px;border-radius:12px;margin-bottom:26px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;position:sticky;top:12px;z-index:5;flex-wrap:wrap}
      .dm-tab{flex:1 1 0;min-width:130px;text-align:center;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:600;color:#6c6e92;text-decoration:none;transition:all .12s;cursor:pointer;border:1px solid transparent}
      .dm-tab:hover{background:#FAFAFE;color:#2B2D6E}
      .dm-tab.active{background:linear-gradient(135deg,#2B2D6E,#3a3d8a);color:#fff;box-shadow:0 2px 8px -2px rgba(43,45,110,.3)}
      .dm-tab .t-num{font-size:10.5px;font-weight:600;opacity:.7;margin-right:6px;letter-spacing:.04em}

      .dm-stats{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:26px}
      .dm-stat{background:#fff;border-radius:12px;padding:16px 18px;border:1px solid #EFEFF5;box-shadow:0 1px 3px rgba(43,45,110,.05)}
      .dm-stat .n{font-family:'Fraunces',serif;font-weight:700;font-size:26px;color:#2B2D6E;line-height:1}
      .dm-stat .l{font-size:11px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin:6px 0 4px}
      .dm-stat .d{font-size:11.5px;color:#6c6e92;line-height:1.4}

      .dm-section{margin-bottom:40px;scroll-margin-top:90px}
      .dm-section > header{margin-bottom:16px}
      .dm-section > header h2{font-family:'Fraunces',serif;font-weight:600;font-size:22px;color:#2B2D6E;margin:0}
      .dm-section > header p{margin:4px 0 0;color:#6c6e92;font-size:13px}

      .dm-graph{background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5}
      .dm-edge{display:grid;grid-template-columns:230px 30px 230px 1fr;gap:14px;padding:9px 8px;font-size:12.5px;align-items:start;border-bottom:1px dashed #F4F4F9}
      .dm-edge:last-child{border-bottom:0}
      .dm-edge .from,.dm-edge .to{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#2B2D6E;font-size:12px;background:#FAFAFE;padding:3px 8px;border-radius:5px;border:1px solid #EFEFF5}
      .dm-edge .arr{text-align:center;color:#FF3D7F;font-weight:700}
      .dm-edge .via{color:#5b5e8c;line-height:1.5}

      .dm-app{background:#fff;border-radius:14px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;margin-bottom:12px;overflow:hidden}
      .dm-app > summary{padding:14px 18px;cursor:pointer;display:flex;align-items:center;gap:12px;background:#FAFAFE;list-style:none;border-bottom:1px solid #EFEFF5}
      .dm-app > summary::-webkit-details-marker{display:none}
      .dm-app > summary::before{content:'▸';color:#FF3D7F;font-size:12px;transition:transform .15s;margin-right:4px}
      .dm-app[open] > summary::before{transform:rotate(90deg)}
      .dm-app > summary .name{font-family:ui-monospace,Menlo,monospace;font-weight:700;color:#2B2D6E;font-size:14px}
      .dm-app > summary .purpose{font-size:12.5px;color:#6c6e92;margin-left:auto}
      .dm-app > summary .count{font-size:10.5px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;background:#fff;border:1px solid #EFEFF5;padding:3px 8px;border-radius:5px}
      .dm-model{display:grid;grid-template-columns:200px 1fr;gap:14px;padding:12px 18px;border-bottom:1px solid #F4F4F9;font-size:12.5px;align-items:start}
      .dm-model:last-child{border-bottom:0}
      .dm-model .mn{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#2B2D6E;font-size:12.5px}
      .dm-model .mc{color:#5b5e8c;line-height:1.5}
      .dm-model .mc .purpose{color:#3a3c5f;margin-bottom:4px}
      .dm-model .mc .meta{font-size:11.5px;color:#8a8ca8;display:block;margin-top:3px}
      .dm-model .mc .meta strong{color:#6c6e92;font-weight:600;text-transform:uppercase;letter-spacing:.04em;font-size:10.5px;margin-right:6px}
      .dm-model .mc code{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;background:#FAFAFE;padding:1px 5px;border-radius:4px;color:#2B2D6E}

      .dm-enum{display:grid;grid-template-columns:260px 1fr 1.2fr;gap:14px;padding:10px 16px;background:#FAFAFE;border-radius:8px;margin-bottom:5px;font-size:12.5px;align-items:start;border:1px solid #EFEFF5}
      .dm-enum .en{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#2B2D6E;font-size:12px}
      .dm-enum .ev{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:#5b5e8c;line-height:1.5}
      .dm-enum .nt{color:#8a8ca8;font-size:11.5px;line-height:1.5}
      .dm-enum.head{background:transparent;border:0;padding:4px 16px;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-bottom:2px}
      .dm-enum.head > div{color:#8a8ca8 !important;font-family:'DM Sans',sans-serif !important;font-weight:600 !important;font-size:10.5px !important}

      .dm-sig{display:grid;grid-template-columns:110px 260px 1.2fr 1.4fr;gap:14px;padding:10px 16px;background:#fff;border-radius:8px;margin-bottom:5px;font-size:12.5px;align-items:start;border:1px solid #EFEFF5}
      .dm-sig .app{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#FF3D7F;font-size:11.5px;background:#FFF5F8;padding:2px 8px;border-radius:5px;display:inline-block}
      .dm-sig .handler{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#2B2D6E;font-size:12px}
      .dm-sig .trigger{color:#5b5e8c;font-size:12px}
      .dm-sig .effect{color:#6c6e92;font-size:12px;line-height:1.5}
      .dm-sig.head{background:transparent;border:0;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
      .dm-sig.head > div{color:#8a8ca8 !important;font-family:'DM Sans',sans-serif !important;font-weight:600 !important;font-size:10.5px !important}

      .dm-gap{display:grid;grid-template-columns:200px 1fr;gap:14px;padding:11px 16px;background:#FFFBEA;border:1px solid #FDF3E0;border-radius:8px;margin-bottom:6px;font-size:12.5px}
      .dm-gap .t{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#9A5800}
      .dm-gap .d{color:#6c6e92;line-height:1.5}

      .dm-banner{background:linear-gradient(135deg,#2B2D6E 0%,#3a3d8a 100%);color:#fff;border-radius:14px;padding:22px 26px;margin-bottom:26px}
      .dm-banner h3{font-family:'Fraunces',serif;font-weight:600;font-size:18px;margin:0 0 8px;letter-spacing:-.01em}
      .dm-banner p{margin:0;color:rgba(255,255,255,.88);font-size:13.5px;line-height:1.55}
      .dm-banner code{font-family:ui-monospace,Menlo,monospace;font-size:12px;background:rgba(255,255,255,.12);padding:1px 6px;border-radius:4px}

      @media (max-width:960px){.dm-stats{grid-template-columns:repeat(3,1fr)}}
      @media (max-width:820px){.dm-stats{grid-template-columns:repeat(2,1fr)}.dm-edge{grid-template-columns:1fr;gap:4px}.dm-edge .arr{display:none}.dm-model{grid-template-columns:1fr;gap:6px}.dm-enum,.dm-sig,.dm-gap{grid-template-columns:1fr;gap:4px}}
    </style>
  `;

  const stats = dataModel.stats.map(([n, v, d]) => `
    <div class="dm-stat"><div class="n">${v}</div><div class="l">${n}</div><div class="d">${d}</div></div>
  `).join('');

  const graph = dataModel.graph.map(g => `
    <div class="dm-edge">
      <div class="from">${g.from}</div>
      <div class="arr">→</div>
      <div class="to">${g.to}</div>
      <div class="via">${g.via}</div>
    </div>
  `).join('');

  const apps = dataModel.apps.map(a => `
    <details class="dm-app" open>
      <summary>
        <span class="name">${a.name}</span>
        <span class="purpose">${a.purpose}</span>
        <span class="count">${a.models.length} models</span>
      </summary>
      ${a.models.map(m => `
        <div class="dm-model">
          <div class="mn">${m.m}</div>
          <div class="mc">
            <div class="purpose">${m.p}</div>
            ${m.fk && m.fk !== '—' ? `<span class="meta"><strong>FK</strong><code>${m.fk}</code></span>` : ''}
            ${m.enums && m.enums !== '—' ? `<span class="meta"><strong>Enum</strong>${m.enums}</span>` : ''}
          </div>
        </div>
      `).join('')}
    </details>
  `).join('');

  const enums = dataModel.enums.map(e => `
    <div class="dm-enum">
      <div class="en">${e.name}</div>
      <div class="ev">${e.values}</div>
      <div class="nt">${e.note}</div>
    </div>
  `).join('');

  const signals = dataModel.signals.map(s => `
    <div class="dm-sig">
      <div><span class="app">${s.app}</span></div>
      <div class="handler">${s.handler}</div>
      <div class="trigger">${s.trigger}</div>
      <div class="effect">${s.effect}</div>
    </div>
  `).join('');

  const gaps = dataModel.gaps.map(g => `
    <div class="dm-gap">
      <div class="t">${g.t}</div>
      <div class="d">${g.d}</div>
    </div>
  `).join('');

  return css + `
    <h1>Data model</h1>
    <p class="lede">Every Django model in the backend — the schema an agent would need to rebuild Klikk cold. Sourced from a fresh survey of <code>backend/apps/*/models.py</code> + <code>signals.py</code>. Vault33 (<code>apps/the_volt/</code>) is documented separately on the <a href="/data#vault33" style="color:#FF3D7F">Data flow</a> page.</p>

    <nav class="dm-tabs" aria-label="Data model sections">
      <a href="#stats"  class="dm-tab active"><span class="t-num">1</span>At a glance</a>
      <a href="#graph"  class="dm-tab"><span class="t-num">2</span>Relationships</a>
      <a href="#apps"   class="dm-tab"><span class="t-num">3</span>Models by app</a>
      <a href="#enums"  class="dm-tab"><span class="t-num">4</span>State machines</a>
      <a href="#signals" class="dm-tab"><span class="t-num">5</span>Signals</a>
      <a href="#gaps"   class="dm-tab"><span class="t-num">6</span>Known gaps</a>
    </nav>

    <div class="dm-banner">
      <h3>How to read this page</h3>
      <p>The <strong>At-a-glance</strong> counters give you the shape of the system. <strong>Relationships</strong> is the mental model — follow an edge to understand what a save triggers. <strong>Models by app</strong> is the verbatim schema. <strong>State machines</strong> is where business rules hide: every <code>.status</code> enum here is a state machine, and the transitions are enforced by serializers + signals. <strong>Signals</strong> is where side-effects live (unit-status sync, RAG ingestion, WebSocket broadcasts). <strong>Known gaps</strong> is the honest list of what's NOT modeled yet.</p>
    </div>

    <section class="dm-section" id="stats">
      <header>
        <h2>1 · At a glance</h2>
        <p>The shape of the system in one row.</p>
      </header>
      <div class="dm-stats">${stats}</div>
    </section>

    <section class="dm-section" id="graph">
      <header>
        <h2>2 · Relationships — the edges that matter</h2>
        <p>The 15 relationships an agent must understand before touching a model. <code>→</code> is "this entity links to / creates / triggers that one".</p>
      </header>
      <div class="dm-graph">${graph}</div>
    </section>

    <section class="dm-section" id="apps">
      <header>
        <h2>3 · Models by app — ${dataModel.apps.length} apps, ${dataModel.apps.reduce((n, a) => n + a.models.length, 0)} models</h2>
        <p>Click any app to inspect its models. Each model lists its purpose, FK relations, and inline enum values.</p>
      </header>
      ${apps}
    </section>

    <section class="dm-section" id="enums">
      <header>
        <h2>4 · State machines</h2>
        <p>Every <code>.status</code> enum in the system. Transitions are enforced by serializer validators + signals — never mutate status directly in a migration.</p>
      </header>
      <div class="dm-enum head"><div>Enum</div><div>Values</div><div>Notes</div></div>
      ${enums}
    </section>

    <section class="dm-section" id="signals">
      <header>
        <h2>5 · Signals — where side-effects live</h2>
        <p>Every Django signal handler in the codebase. If you ever wonder "why did this happen on save?" — the answer is probably here.</p>
      </header>
      <div class="dm-sig head"><div>App</div><div>Handler</div><div>Trigger</div><div>Effect</div></div>
      ${signals}
    </section>

    <section class="dm-section" id="gaps">
      <header>
        <h2>6 · Known gaps</h2>
        <p>Models that don't exist yet — but should, before the platform handles real trust-account money at scale.</p>
      </header>
      ${gaps}
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.dm-tab');
        const ids = ['stats','graph','apps','enums','signals','gaps'];
        const sections = ids.map(id => document.getElementById(id));
        function onScroll(){
          const y = window.scrollY + 140;
          let active = 0;
          sections.forEach((s, i) => { if (s && s.offsetTop <= y) active = i; });
          tabs.forEach((t, i) => t.classList.toggle('active', i === active));
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- IA & routes ---------- */
// Sourced from a Haiku survey of admin/src/router/index.ts and layouts.
const ia = {
  stats: [
    ['Routes',       '47', 'Total routes incl. redirects + nested'],
    ['Canonical',    '42', 'Non-redirect routes'],
    ['Views',        '64', 'Concrete .vue view files'],
    ['Layouts',       '3', 'AppLayout · OwnerLayout · SupplierLayout'],
    ['Portals',       '3', 'Agent/admin · Owner · Supplier'],
    ['Role-gated',   '35', 'Routes requiring requiresAuth: true'],
  ],
  roles: [
    { role: 'admin',          type: 'System admin',       staff: true,  home: '/',        scope: 'Everything + /testing + /admin/devops' },
    { role: 'agency_admin',   type: 'Agency admin',       staff: true,  home: '/agency',  scope: 'All agency operations + /admin/users + /admin/agency' },
    { role: 'agent',          type: 'Field agent',        staff: true,  home: '/agent',   scope: 'Agent-portal: properties, tenants, leases, maintenance' },
    { role: 'estate_agent',   type: 'Estate agent',       staff: true,  home: '/agent',   scope: 'Same as agent (sales-focused)' },
    { role: 'managing_agent', type: 'Managing agent',     staff: true,  home: '/agent',   scope: 'Same as agent (rentals-focused)' },
    { role: 'accountant',     type: 'Accountant',         staff: true,  home: '/',        scope: 'Read-heavy + trust account views (module_access gated)' },
    { role: 'viewer',         type: 'Read-only',          staff: true,  home: '/',        scope: 'Scoped by module_access JSON list on User' },
    { role: 'supplier',       type: 'Service provider',    staff: false, home: '/jobs',    scope: 'Only own dispatched jobs — POPIA data-minimised' },
    { role: 'owner',          type: 'Landlord / owner',   staff: false, home: '/owner',   scope: 'Only own properties, leases, statements' },
    { role: 'tenant',         type: 'Renter',             staff: false, home: '(mobile)', scope: 'Uses Flutter/Quasar tenant app — not admin SPA' },
  ],
  portals: [
    {
      name: 'Public (no layout)',
      layout: 'none',
      purpose: 'Auth + passwordless signing. No sidebar.',
      routes: [
        { path: '/login',           name: 'login',           view: 'auth/LoginView.vue',            meta: 'public: true', purpose: 'Email + password sign-in' },
        { path: '/register',        name: 'register',        view: 'auth/RegisterView.vue',         meta: 'public: true', purpose: 'Self-service account creation' },
        { path: '/forgot-password', name: 'forgot-password', view: 'auth/ForgotPasswordView.vue',   meta: 'public: true', purpose: 'Reset request' },
        { path: '/reset-password',  name: 'reset-password',  view: 'auth/ResetPasswordView.vue',    meta: 'public: true', purpose: 'Token-based reset form' },
        { path: '/accept-invite',   name: 'accept-invite',   view: 'auth/AcceptInviteView.vue',     meta: 'public · allowWhenAuthenticated', purpose: 'Accept team invite' },
        { path: '/sign/:token',     name: 'public-sign',     view: 'signing/PublicSignView.vue',    meta: 'public · allowWhenAuthenticated', purpose: 'E-signature flow (passwordless link)' },
      ],
    },
    {
      name: 'Agent / admin portal',
      layout: 'AppLayout',
      purpose: 'The primary workbench for agency staff. Roles: admin, agency_admin, agent, estate_agent, managing_agent, accountant, viewer.',
      routes: [
        { path: '/',                    name: 'dashboard',          view: 'dashboard/DashboardView.vue',         meta: 'requiresAuth', purpose: 'General dashboard (default home)' },
        { path: '/agency',              name: 'agency-dashboard',   view: 'dashboard/AgencyDashboardView.vue',   meta: 'requiresAuth', purpose: 'Agency-level KPIs' },
        { path: '/agent',               name: 'agent-dashboard',    view: 'dashboard/AgentDashboardView.vue',    meta: 'requiresAuth', purpose: 'Individual agent KPIs' },

        { path: '/properties',          name: 'properties',         view: 'properties/PropertiesView.vue',       meta: 'requiresAuth', purpose: 'List properties' },
        { path: '/properties/:id',      name: 'property-detail',    view: 'properties/PropertyDetailView.vue',   meta: 'requiresAuth', purpose: 'Single property + units + docs' },
        { path: '/landlords',           name: 'landlords',          view: 'properties/LandlordsView.vue',        meta: 'requiresAuth', purpose: 'List owners' },
        { path: '/landlords/:id',       name: 'landlord-detail',    view: 'properties/LandlordDetailView.vue',   meta: 'requiresAuth', purpose: 'Owner profile + statements' },

        { path: '/tenants',             name: 'tenants',            view: 'tenants/TenantsView.vue',             meta: 'requiresAuth', purpose: 'List active + former tenants' },
        { path: '/tenants/:id',         name: 'tenant-detail',      view: 'tenants/TenantDetailView.vue',        meta: 'requiresAuth', purpose: 'Tenant profile + lease chain' },

        { path: '/leases/overview',     name: 'lease-overview',     view: 'leases/LeaseOverviewView.vue',        meta: 'requiresAuth', purpose: 'Portfolio-wide status' },
        { path: '/leases',              name: 'leases',             view: 'leases/LeasesView.vue',               meta: 'requiresAuth', purpose: 'All leases' },
        { path: '/leases/templates',    name: 'lease-templates',    view: 'leases/LeaseTemplatesView.vue',       meta: 'requiresAuth', purpose: 'Reusable templates' },
        { path: '/leases/templates/:id/edit', name: 'lease-template-edit', view: 'leases/TiptapEditorView.vue',  meta: 'requiresAuth', purpose: 'TipTap template editor' },
        { path: '/leases/build',        name: 'lease-builder',      view: 'leases/LeaseBuilderView.vue',         meta: 'requiresAuth', purpose: 'AI-assisted lease builder' },
        { path: '/leases/calendar',     name: 'lease-calendar',     view: 'leases/LeaseCalendarView.vue',        meta: 'requiresAuth', purpose: 'Timeline: start / renewal / expiry' },

        { path: '/maintenance/issues',  name: 'maintenance-issues', view: 'maintenance/RequestsView.vue',        meta: 'requiresAuth', purpose: 'Maintenance tickets' },
        { path: '/maintenance/issues/:id', name: 'maintenance-detail', view: 'maintenance/MaintenanceDetailView.vue', meta: 'requiresAuth', purpose: 'Ticket detail + dispatch' },
        { path: '/maintenance/suppliers', name: 'maintenance-suppliers', view: 'maintenance/SuppliersView.vue', meta: 'requiresAuth', purpose: 'Approved suppliers' },
        { path: '/maintenance/questions', name: 'maintenance-questions', view: 'maintenance/QuestionsView.vue', meta: 'requiresAuth', purpose: 'AgentQuestion inbox' },

        { path: '/suppliers',           name: 'suppliers',          view: 'suppliers/DirectoryView.vue',         meta: 'requiresAuth', purpose: 'Supplier registry' },
        { path: '/suppliers/dispatch',  name: 'dispatch',           view: 'suppliers/DispatchView.vue',          meta: 'requiresAuth', purpose: 'Bulk job assignment' },

        { path: '/property-info/agent',     name: 'property-info-agent',     view: 'properties/PropertyAgentView.vue', meta: 'requiresAuth', purpose: 'AI agent context editor' },
        { path: '/property-info/skills',    name: 'property-info-skills',    view: 'maintenance/SkillLibraryView.vue', meta: 'requiresAuth', purpose: 'Trade skill taxonomy' },
        { path: '/property-info/unit-info', name: 'property-info-unit-info', view: 'properties/UnitTenantInfoView.vue', meta: 'requiresAuth', purpose: 'Unit specs & utilities' },
        { path: '/property-info/monitor',   name: 'property-info-monitor',   view: 'setup/AgentMonitorView.vue',       meta: 'requiresAuth', purpose: 'Agent audit log' },

        { path: '/admin/users',     name: 'admin-users',   view: 'admin/UsersView.vue',           meta: 'requiresAuth · roles: admin, agency_admin', purpose: 'User management' },
        { path: '/admin/agency',    name: 'admin-agency',  view: 'admin/AgencySettingsView.vue',  meta: 'requiresAuth · roles: admin, agency_admin', purpose: 'Agency config' },
        { path: '/admin/devops',    name: 'admin-devops',  view: 'admin/DevOpsView.vue',          meta: 'requiresAuth · roles: admin',                purpose: 'System health' },

        { path: '/testing',                  name: 'TestingDashboard', view: 'testing/TestingDashboard.vue',      meta: 'requiresAuth · roles: admin', purpose: 'QA portal' },
        { path: '/testing/module/:module',   name: 'TestingModule',    view: 'testing/TestingModuleView.vue',     meta: 'requiresAuth · roles: admin', purpose: 'Per-module test runs' },
        { path: '/testing/issues',           name: 'TestingIssues',    view: 'testing/TestingIssuesView.vue',     meta: 'requiresAuth · roles: admin', purpose: 'Known bugs' },
        { path: '/testing/runs',             name: 'TestingRuns',      view: 'testing/TestingRunsView.vue',       meta: 'requiresAuth · roles: admin', purpose: 'Run history' },
        { path: '/testing/selfcheck',        name: 'TestingSelfCheck', view: 'testing/TestingSelfCheckView.vue',  meta: 'requiresAuth · roles: admin', purpose: 'Self-check validator' },

        { path: '/profile',              name: 'profile', view: 'auth/ProfileView.vue', meta: 'requiresAuth', purpose: 'Edit own profile' },
      ],
    },
    {
      name: 'Owner portal',
      layout: 'OwnerLayout',
      purpose: 'Landlord-facing read-only (mostly) portal. Role: owner.',
      routes: [
        { path: '/owner',            name: 'owner-dashboard',    view: 'owner/OwnerDashboard.vue',        meta: 'requiresAuth · roles: owner', purpose: 'Owner summary' },
        { path: '/owner/properties', name: 'owner-properties',   view: 'owner/OwnerPropertiesView.vue',   meta: 'requiresAuth · roles: owner', purpose: 'Owned properties + statements' },
        { path: '/owner/leases',     name: 'owner-lease-builder',view: 'leases/LeaseBuilderView.vue',     meta: 'requiresAuth · roles: owner', purpose: 'Shared lease builder (read/write)' },
      ],
    },
    {
      name: 'Supplier portal',
      layout: 'SupplierLayout',
      purpose: 'Service-provider job inbox. Role: supplier. Scoped access — sees only own jobs.',
      routes: [
        { path: '/jobs',     name: 'supplier-jobs',     view: 'supplier/JobsListView.vue',        meta: 'requiresAuth · roles: supplier', purpose: 'Dispatched jobs (accept / quote / complete)' },
        { path: '/calendar', name: 'supplier-calendar', view: 'supplier/CalendarView.vue',        meta: 'requiresAuth · roles: supplier', purpose: 'Schedule & availability' },
        { path: '/profile',  name: 'supplier-profile',  view: 'supplier/SupplierProfileView.vue', meta: 'requiresAuth · roles: supplier', purpose: 'Business details + certs' },
      ],
    },
  ],
  redirects: [
    ['/leases/status',        '/leases'],
    ['/leases/submit',        '/leases'],
    ['/maintenance',          '/maintenance/issues'],
    ['/property-agent',       '/property-info/agent'],
    ['/unit-tenant-info',     '/property-info/unit-info'],
    ['/skills',               '/property-info/skills'],
    ['/:pathMatch(.*)*',      '/'],
  ],
  layouts: [
    {
      name: 'AppLayout',
      file: 'components/AppLayout.vue',
      roles: 'admin · agency_admin · agent · estate_agent · managing_agent · accountant · viewer',
      sections: [
        { title: 'Header dropdowns', items: [
          'Entities → Properties · Owners · Tenants',
          'Leases → Overview · Leases · Templates · Calendar',
          'Maintenance → Issues (badge) · Questions (badge) · Suppliers',
        ]},
        { title: 'User menu (avatar)', items: [
          'Profile',
          'Admin ⟶ Users · Agency Settings (if agency_admin)',
          'Developer ⟶ Testing · DevOps (admin only)',
          'Knowledge base ⟶ Agent Context · Skill Library · Property Info · Agent Monitor',
          'Logout',
        ]},
        { title: 'Real-time', items: [
          'WebSocket: ws://{host}/ws/maintenance/updates/',
          'Badges poll /maintenance/badges/ every 60s as fallback',
          'Toast container mounted at layout root',
        ]},
        { title: 'Performance', items: [
          'KeepAlive on main RouterView (excludes: TiptapEditorView, TemplateEditorView, LeaseBuilderView)',
          'Mobile hamburger at sm breakpoint',
          'Max-width 1400px content container',
          'Floating AI-assistant FAB → /property-info/agent',
        ]},
      ],
    },
    {
      name: 'OwnerLayout',
      file: 'components/OwnerLayout.vue',
      roles: 'owner',
      sections: [
        { title: 'Header nav', items: ['Dashboard', 'Properties', 'Leases', 'Avatar · Logout'] },
        { title: 'Mobile', items: ['Hamburger toggle for nav items'] },
      ],
    },
    {
      name: 'SupplierLayout',
      file: 'components/SupplierLayout.vue',
      roles: 'supplier',
      sections: [
        { title: 'Header nav', items: ['Jobs', 'Calendar', 'Profile', 'Avatar · Logout'] },
        { title: 'Mobile', items: ['Hamburger toggle for nav items'] },
      ],
    },
  ],
  guards: [
    { step: 1, name: 'Public gate',       logic: 'If to.meta.public === true: allow when unauthenticated. If authenticated and allowWhenAuthenticated !== true → redirect to homeRoute.' },
    { step: 2, name: 'Auth gate',         logic: 'If no access token: redirect to /login. If user missing in store: await auth.fetchMe() (401 → logout + redirect).' },
    { step: 3, name: 'Role gate',         logic: 'If to.meta.roles is set: check auth.user.role ∈ roles. Denied → redirect to auth.homeRoute.' },
    { step: 4, name: 'Home redirect',     logic: 'If navigating to / and homeRoute !== /: redirect (e.g. supplier → /jobs, owner → /owner).' },
    { step: 5, name: 'JWT lifecycle',     logic: 'access_token + refresh_token in localStorage. Logout blacklists refresh token server-side (best-effort), clears local storage.' },
  ],
  flows: [
    { scenario: 'Tenant submits maintenance',
      steps: ['Tenant app → POST /maintenance/requests/', 'MaintenanceRequest created → signal vectorizes + broadcasts', 'Agent sees badge tick up on /maintenance/issues', 'Open issue → dispatch to suppliers → JobQuoteRequest × N', 'Award → SupplierJobAssignment → supplier sees job on /jobs'] },
    { scenario: 'Owner onboarding',
      steps: ['Invite sent → /accept-invite?token=…', 'User created with role=owner', 'Redirect to /owner', 'Owner completes Person + Landlord record', 'RentalMandate drafted → e-sign → status ACTIVE', 'Properties unlocked in /owner/properties'] },
    { scenario: 'Lease signing',
      steps: ['Agent clicks /leases/build → AI Q&A → Lease draft', 'ESigningSubmission created (status: PENDING)', 'Public links generated: /sign/:token per signer', 'Signer completes → ESigningAuditEvent trail', 'When all signed: status: COMPLETED + signed_pdf_file → RentalMandate.status sync'] },
  ],
};

function pageIA() {
  const css = `
    <style>
      .ia-tabs{display:flex;gap:6px;background:#fff;padding:6px;border-radius:12px;margin-bottom:26px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;position:sticky;top:12px;z-index:5;flex-wrap:wrap}
      .ia-tab{flex:1 1 0;min-width:130px;text-align:center;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:600;color:#6c6e92;text-decoration:none;transition:all .12s;border:1px solid transparent}
      .ia-tab:hover{background:#FAFAFE;color:#2B2D6E}
      .ia-tab.active{background:linear-gradient(135deg,#2B2D6E,#3a3d8a);color:#fff;box-shadow:0 2px 8px -2px rgba(43,45,110,.3)}
      .ia-tab .t-num{font-size:10.5px;font-weight:600;opacity:.7;margin-right:6px;letter-spacing:.04em}

      .ia-stats{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:26px}
      .ia-stat{background:#fff;border-radius:12px;padding:16px 18px;border:1px solid #EFEFF5}
      .ia-stat .n{font-family:'Fraunces',serif;font-weight:700;font-size:26px;color:#2B2D6E;line-height:1}
      .ia-stat .l{font-size:11px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin:6px 0 4px}
      .ia-stat .d{font-size:11.5px;color:#6c6e92;line-height:1.4}

      .ia-section{margin-bottom:40px;scroll-margin-top:90px}
      .ia-section > header{margin-bottom:16px}
      .ia-section > header h2{font-family:'Fraunces',serif;font-weight:600;font-size:22px;color:#2B2D6E;margin:0}
      .ia-section > header p{margin:4px 0 0;color:#6c6e92;font-size:13px}

      .ia-portal{background:#fff;border-radius:14px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;margin-bottom:14px;overflow:hidden}
      .ia-portal > header{padding:16px 20px;background:linear-gradient(180deg,#FAFAFE,#fff);border-bottom:1px solid #EFEFF5;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
      .ia-portal > header .name{font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;font-size:16px}
      .ia-portal > header .layout{font-family:ui-monospace,Menlo,monospace;font-size:11px;background:#FFF5F8;color:#FF3D7F;padding:2px 8px;border-radius:5px;border:1px solid #FFE4EF;font-weight:600}
      .ia-portal > header .count{font-size:10.5px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;background:#FAFAFE;border:1px solid #EFEFF5;padding:3px 8px;border-radius:5px;margin-left:auto}
      .ia-portal > header .purpose{flex-basis:100%;margin:8px 0 0;font-size:12.5px;color:#6c6e92;line-height:1.5}

      .ia-route{display:grid;grid-template-columns:1.4fr 1fr 1.5fr 1.4fr 1.6fr;gap:14px;padding:10px 20px;border-bottom:1px solid #F4F4F9;font-size:12px;align-items:start}
      .ia-route:last-child{border-bottom:0}
      .ia-route .path{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#2B2D6E}
      .ia-route .rname{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:#5b5e8c;background:#FAFAFE;padding:2px 6px;border-radius:4px;display:inline-block}
      .ia-route .view{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:#8a8ca8}
      .ia-route .meta{font-size:11px;color:#6c6e92;line-height:1.45}
      .ia-route .purpose{color:#5b5e8c;line-height:1.5}
      .ia-route.head{background:#FCFCFE;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
      .ia-route.head > div{color:#8a8ca8 !important;font-family:'DM Sans',sans-serif !important}

      .ia-role{display:grid;grid-template-columns:160px 180px 70px 160px 1fr;gap:12px;padding:10px 16px;background:#fff;border:1px solid #EFEFF5;border-radius:8px;margin-bottom:5px;font-size:12.5px;align-items:start}
      .ia-role .role{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#2B2D6E;background:#FAFAFE;padding:2px 8px;border-radius:5px;display:inline-block}
      .ia-role .type{color:#5b5e8c}
      .ia-role .staff{text-align:center}
      .ia-role .staff .pill{font-size:10.5px;font-weight:600;padding:2px 8px;border-radius:5px;letter-spacing:.04em}
      .ia-role .staff .pill.y{background:#E6F4EB;color:#15803D}
      .ia-role .staff .pill.n{background:#F0F0F4;color:#7a7a9c}
      .ia-role .home{font-family:ui-monospace,Menlo,monospace;color:#FF3D7F;font-size:12px}
      .ia-role .scope{color:#6c6e92;line-height:1.5}
      .ia-role.head{background:transparent;border:0;padding:4px 16px;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-bottom:2px}
      .ia-role.head > div{color:#8a8ca8 !important;font-family:'DM Sans',sans-serif !important}

      .ia-layout{background:#fff;border-radius:14px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;margin-bottom:14px;padding:18px 22px}
      .ia-layout > h3{font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;font-size:17px;margin:0 0 4px}
      .ia-layout .file{font-family:ui-monospace,Menlo,monospace;color:#8a8ca8;font-size:11.5px;margin-bottom:6px}
      .ia-layout .roles{font-size:11.5px;color:#5b5e8c;margin-bottom:14px}
      .ia-layout .roles strong{color:#FF3D7F;text-transform:uppercase;letter-spacing:.06em;font-weight:600;font-size:10.5px;margin-right:6px}
      .ia-layout .sec{margin-bottom:12px}
      .ia-layout .sec h4{font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;font-size:13px;margin:0 0 6px}
      .ia-layout .sec ul{margin:0;padding-left:18px;color:#5b5e8c;font-size:12.5px;line-height:1.6}
      .ia-layout .sec li{margin-bottom:2px}

      .ia-guard{display:grid;grid-template-columns:40px 180px 1fr;gap:14px;padding:11px 18px;background:#fff;border:1px solid #EFEFF5;border-radius:8px;margin-bottom:5px;font-size:12.5px;align-items:start}
      .ia-guard .step{font-family:'Fraunces',serif;font-weight:700;color:#FF3D7F;font-size:18px;text-align:center}
      .ia-guard .name{font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;font-size:13.5px}
      .ia-guard .logic{color:#5b5e8c;line-height:1.55}

      .ia-redirect{display:grid;grid-template-columns:1fr 40px 1fr;gap:14px;padding:8px 16px;border-bottom:1px solid #F4F4F9;font-size:12px;align-items:center}
      .ia-redirect:last-child{border-bottom:0}
      .ia-redirect .from,.ia-redirect .to{font-family:ui-monospace,Menlo,monospace;color:#2B2D6E;background:#FAFAFE;padding:3px 8px;border-radius:4px;border:1px solid #EFEFF5}
      .ia-redirect .arr{text-align:center;color:#FF3D7F;font-weight:700}

      .ia-flow{background:#fff;border-radius:14px;padding:18px 22px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;margin-bottom:12px;border-left:3px solid #FF3D7F}
      .ia-flow h4{font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;font-size:15px;margin:0 0 10px}
      .ia-flow ol{margin:0;padding-left:20px;color:#5b5e8c;font-size:12.5px;line-height:1.7}
      .ia-flow ol li{margin-bottom:3px}

      @media (max-width:960px){.ia-stats{grid-template-columns:repeat(3,1fr)}.ia-route{grid-template-columns:1fr;gap:4px}.ia-route.head{display:none}.ia-role{grid-template-columns:1fr;gap:4px}.ia-role.head{display:none}.ia-guard{grid-template-columns:1fr}.ia-redirect{grid-template-columns:1fr;gap:2px}.ia-redirect .arr{display:none}}
      @media (max-width:820px){.ia-stats{grid-template-columns:repeat(2,1fr)}}
    </style>
  `;

  const stats = ia.stats.map(([n, v, d]) => `
    <div class="ia-stat"><div class="n">${v}</div><div class="l">${n}</div><div class="d">${d}</div></div>
  `).join('');

  const roles = ia.roles.map(r => `
    <div class="ia-role">
      <div><span class="role">${r.role}</span></div>
      <div class="type">${r.type}</div>
      <div class="staff"><span class="pill ${r.staff ? 'y' : 'n'}">${r.staff ? 'Staff' : 'External'}</span></div>
      <div class="home">${r.home}</div>
      <div class="scope">${r.scope}</div>
    </div>
  `).join('');

  const portals = ia.portals.map(p => `
    <div class="ia-portal">
      <header>
        <span class="name">${p.name}</span>
        <span class="layout">${p.layout}</span>
        <span class="count">${p.routes.length} routes</span>
        <p class="purpose">${p.purpose}</p>
      </header>
      <div class="ia-route head">
        <div>Path</div><div>Name</div><div>View</div><div>Meta</div><div>Purpose</div>
      </div>
      ${p.routes.map(r => `
        <div class="ia-route">
          <div class="path">${r.path}</div>
          <div><span class="rname">${r.name}</span></div>
          <div class="view">${r.view}</div>
          <div class="meta">${r.meta}</div>
          <div class="purpose">${r.purpose}</div>
        </div>
      `).join('')}
    </div>
  `).join('');

  const redirects = ia.redirects.map(([f, t]) => `
    <div class="ia-redirect">
      <div class="from">${f}</div>
      <div class="arr">→</div>
      <div class="to">${t}</div>
    </div>
  `).join('');

  const layouts = ia.layouts.map(L => `
    <div class="ia-layout">
      <h3>${L.name}</h3>
      <div class="file">${L.file}</div>
      <div class="roles"><strong>Roles</strong>${L.roles}</div>
      ${L.sections.map(s => `
        <div class="sec">
          <h4>${s.title}</h4>
          <ul>${s.items.map(i => `<li>${i}</li>`).join('')}</ul>
        </div>
      `).join('')}
    </div>
  `).join('');

  const guards = ia.guards.map(g => `
    <div class="ia-guard">
      <div class="step">${g.step}</div>
      <div class="name">${g.name}</div>
      <div class="logic">${g.logic}</div>
    </div>
  `).join('');

  const flows = ia.flows.map(f => `
    <div class="ia-flow">
      <h4>${f.scenario}</h4>
      <ol>${f.steps.map(s => `<li>${s}</li>`).join('')}</ol>
    </div>
  `).join('');

  return css + `
    <h1>IA &amp; routes</h1>
    <p class="lede">Every route in the admin SPA, every layout, every role. Sourced from <code>admin/src/router/index.ts</code> + layout components. Tenant app is Flutter / Quasar — not documented here.</p>

    <nav class="ia-tabs" aria-label="IA sections">
      <a href="#stats"     class="ia-tab active"><span class="t-num">1</span>At a glance</a>
      <a href="#roles"     class="ia-tab"><span class="t-num">2</span>Roles</a>
      <a href="#routes"    class="ia-tab"><span class="t-num">3</span>Routes by portal</a>
      <a href="#layouts"   class="ia-tab"><span class="t-num">4</span>Layouts</a>
      <a href="#guards"    class="ia-tab"><span class="t-num">5</span>Route guards</a>
      <a href="#flows"     class="ia-tab"><span class="t-num">6</span>Key flows</a>
    </nav>

    <section class="ia-section" id="stats">
      <header>
        <h2>1 · At a glance</h2>
        <p>The shape of the front-end routing.</p>
      </header>
      <div class="ia-stats">${stats}</div>
    </section>

    <section class="ia-section" id="roles">
      <header>
        <h2>2 · Roles → portals</h2>
        <p>There are 10 role values on User. Staff roles land in AppLayout; supplier lands in SupplierLayout; owner lands in OwnerLayout; tenant uses the mobile app (not the admin SPA).</p>
      </header>
      <div class="ia-role head">
        <div>Role</div><div>Type</div><div>Staff?</div><div>Home route</div><div>Scope</div>
      </div>
      ${roles}
    </section>

    <section class="ia-section" id="routes">
      <header>
        <h2>3 · Routes by portal</h2>
        <p>Canonical routes grouped by layout. Each row gives the view file and meta (auth + role guards).</p>
      </header>
      ${portals}

      <div class="ia-layout" style="margin-top:18px">
        <h3>Redirects &amp; aliases</h3>
        <div class="file">Legacy paths that redirect to canonical routes</div>
        <div style="margin-top:10px">${redirects}</div>
      </div>
    </section>

    <section class="ia-section" id="layouts">
      <header>
        <h2>4 · Layouts</h2>
        <p>Three layouts, one per portal. AppLayout is the complex one — the other two are thin wrappers.</p>
      </header>
      ${layouts}
    </section>

    <section class="ia-section" id="guards">
      <header>
        <h2>5 · Route guards — router.beforeEach</h2>
        <p>The 5 checks every navigation passes through. Each check can redirect.</p>
      </header>
      ${guards}
    </section>

    <section class="ia-section" id="flows">
      <header>
        <h2>6 · Key navigation flows</h2>
        <p>End-to-end flows an agent should understand before modifying routes.</p>
      </header>
      ${flows}
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.ia-tab');
        const ids = ['stats','roles','routes','layouts','guards','flows'];
        const sections = ids.map(id => document.getElementById(id));
        function onScroll(){
          const y = window.scrollY + 140;
          let active = 0;
          sections.forEach((s, i) => { if (s && s.offsetTop <= y) active = i; });
          tabs.forEach((t, i) => t.classList.toggle('active', i === active));
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- API contracts ---------- */
// Sourced from a Haiku survey of backend/config/urls.py + each app's urls.py + views.py.
const api = {
  stats: [
    ['Endpoints',     '~195', 'REST endpoints across 11 apps'],
    ['WebSockets',    '4',    'Live channels (Daphne + channels)'],
    ['Public',        '14',   'AllowAny endpoints (auth + signing + gateway OTP)'],
    ['Rate-limited',  '8',    'Throttled (auth, OTP, chat, drafts)'],
    ['ViewSets',      '34',   'DRF routers (each expands to list/detail/+actions)'],
    ['Base path',     '/api/v1/', 'Versioned prefix — never nested'],
  ],
  auth: [
    { m: 'POST',        p: '/auth/register/',              v: 'Self-register (agency bootstrap only)',       auth: 'AllowAny', th: 'AuthAnonThrottle' },
    { m: 'POST',        p: '/auth/login/',                 v: 'Email + password → JWT access + refresh',     auth: 'AllowAny', th: 'AuthAnonThrottle' },
    { m: 'POST',        p: '/auth/google/',                v: 'OAuth2 Google SSO',                           auth: 'AllowAny', th: '—' },
    { m: 'GET · PATCH', p: '/auth/me/',                    v: 'Get / update current user',                   auth: 'IsAuthenticated', th: '—' },
    { m: 'POST',        p: '/auth/token/refresh/',         v: 'Refresh JWT access token',                    auth: 'AllowAny', th: '—' },
    { m: 'POST',        p: '/auth/otp/send/',              v: 'Send OTP to registered phone',                auth: 'AllowAny', th: 'OTPSendThrottle' },
    { m: 'POST',        p: '/auth/otp/verify/',            v: 'Verify OTP → JWT',                            auth: 'AllowAny', th: 'OTPVerifyThrottle' },
    { m: 'POST',        p: '/auth/change-password/',       v: 'Change password (requires current pwd)',     auth: 'IsAuthenticated', th: '—' },
    { m: 'POST',        p: '/auth/logout/',                v: 'Blacklist refresh token',                     auth: 'IsAuthenticated', th: '—' },
    { m: 'POST',        p: '/auth/password-reset/',        v: 'Request reset email',                         auth: 'AllowAny', th: 'AuthAnonThrottle' },
    { m: 'POST',        p: '/auth/password-reset/confirm/',v: 'Confirm reset with token',                    auth: 'AllowAny', th: 'AuthAnonThrottle' },
    { m: 'POST',        p: '/auth/accept-invite/',         v: 'Accept user invite via token',                auth: 'AllowAny', th: 'AuthAnonThrottle' },
    { m: 'POST · DELETE',p:'/auth/push-token/',             v: 'Register / unregister FCM / APNs token',      auth: 'IsAuthenticated', th: '—' },
    { m: 'GET',         p: '/auth/lookup/',                v: 'Cross-entity lookup by ID / CIPC number',     auth: 'IsAgentOrAdmin', th: '—' },
  ],
  apps: [
    {
      name: 'accounts',
      base: '/api/v1/auth/',
      purpose: 'Identity, RBAC, user invites, agency singleton',
      endpoints: [
        { m: 'GET · POST',       p: '/users/',                       v: 'UserListView',           auth: 'IsAgentOrAdmin', purpose: 'List / invite users' },
        { m: 'GET · PATCH · DELETE', p: '/users/<id>/',              v: 'UserDetailView',         auth: 'IsAgentOrAdmin', purpose: 'Get / update / suspend user' },
        { m: 'GET',              p: '/users/invites/',               v: 'PendingInvitesView',     auth: 'IsAgentOrAdmin', purpose: 'Pending invites' },
        { m: 'DELETE',           p: '/users/invites/<id>/',          v: 'CancelInviteView',       auth: 'IsAgentOrAdmin', purpose: 'Cancel sent invite' },
        { m: 'POST',             p: '/users/invites/<id>/resend/',   v: 'ResendInviteView',       auth: 'IsAgentOrAdmin', purpose: 'Resend invite email' },
        { m: 'GET · PATCH',      p: '/agency/',                      v: 'AgencySettingsView',     auth: 'IsAgentOrAdmin', purpose: 'Singleton agency config' },
        { m: 'GET',              p: '/tenants/',                     v: 'TenantsListView',        auth: 'IsAgentOrAdmin', purpose: 'List agency tenants' },
        { m: 'GET · POST',       p: '/persons/',                     v: 'PersonViewSet',          auth: 'IsAgentOrAdmin', purpose: 'CRUD persons (landlord / tenant / occupant)' },
        { m: 'GET · PUT · DELETE', p: '/persons/<id>/',              v: 'PersonDetailView',       auth: 'IsAgentOrAdmin', purpose: 'Person detail' },
        { m: 'GET · POST',       p: '/persons/<id>/documents/',      v: 'PersonDocumentListCreate', auth: 'IsAgentOrAdmin', purpose: 'ID / POA / POI / FICA uploads' },
        { m: 'GET · DELETE',     p: '/persons/<id>/documents/<doc_id>/', v: 'PersonDocumentDetail', auth: 'IsAgentOrAdmin', purpose: 'Individual person doc' },
      ],
    },
    {
      name: 'properties',
      base: '/api/v1/properties/',
      purpose: 'Property, unit, landlord, mandate, compliance (scoped by PropertyAgentAssignment)',
      endpoints: [
        { m: 'GET · POST',           p: '/',                                   v: 'PropertyViewSet',           auth: 'IsAgentOrAdmin', purpose: 'CRUD properties (agent-scoped)' },
        { m: 'GET · PUT · DELETE',   p: '/<id>/',                              v: 'PropertyViewSet',           auth: 'IsAgentOrAdmin', purpose: 'Property detail' },
        { m: 'GET · POST · PATCH · DELETE', p: '/<id>/photos/',                v: 'photos action',             auth: 'IsAgentOrAdmin', purpose: 'Gallery (auto-thumbnail)' },
        { m: 'GET · POST · DELETE',  p: '/<id>/documents/',                    v: 'documents action',          auth: 'IsAgentOrAdmin', purpose: 'Per-property docs (title deed, rates, insurance)' },
        { m: 'GET · POST',           p: '/landlords/',                         v: 'LandlordViewSet',           auth: 'IsAgentOrAdmin', purpose: 'CRUD landlord entities' },
        { m: 'GET · PUT · DELETE',   p: '/landlords/<id>/',                    v: 'LandlordViewSet',           auth: 'IsAgentOrAdmin', purpose: 'Landlord detail' },
        { m: 'POST',                 p: '/landlords/<id>/classify/',           v: 'LandlordClassifyView',      auth: 'IsAgentOrAdmin', purpose: 'AI-classify (POPIA / tax / entity type)' },
        { m: 'POST',                 p: '/landlords/<id>/classify-registration/', v: 'LandlordClassifyRegistrationView', auth: 'IsAgentOrAdmin', purpose: 'AI-parse CIPC / BRN' },
        { m: 'POST',                 p: '/landlords/<id>/chat/',               v: 'LandlordChatView',          auth: 'IsAgentOrAdmin', purpose: 'Agentic owner-onboarding chat' },
        { m: 'GET · POST',           p: '/ownerships/',                        v: 'PropertyOwnershipViewSet',  auth: 'IsAgentOrAdmin', purpose: 'Temporal ownership records' },
        { m: 'GET · PUT · DELETE',   p: '/ownerships/<id>/',                   v: 'PropertyOwnershipViewSet',  auth: 'IsAgentOrAdmin', purpose: 'Detail' },
        { m: 'GET · POST · PUT · DELETE', p: '/units/…',                       v: 'UnitViewSet',               auth: 'IsAgentOrAdmin', purpose: 'Unit CRUD' },
        { m: 'GET · POST · PUT · DELETE', p: '/unit-info/…',                   v: 'UnitInfoViewSet',           auth: 'IsAgentOrAdmin', purpose: 'WiFi / parking / utilities' },
        { m: 'GET · POST · PUT · DELETE', p: '/compliance-certs/…',            v: 'ComplianceCertificateViewSet', auth: 'IsAgentOrAdmin', purpose: 'Electrical / gas / pest / plumbing certs' },
        { m: 'GET · POST · PUT · DELETE', p: '/insurance-policies/…',          v: 'InsurancePolicyViewSet',    auth: 'IsAgentOrAdmin', purpose: 'Building / contents / combined' },
        { m: 'GET · POST · PUT · DELETE', p: '/valuations/…',                  v: 'PropertyValuationViewSet',  auth: 'IsAgentOrAdmin', purpose: 'Market / municipal / bank valuations' },
        { m: 'GET · POST · PUT · DELETE', p: '/bank-accounts/…',               v: 'BankAccountViewSet',        auth: 'IsAgentOrAdmin', purpose: 'Landlord payout accounts' },
        { m: 'GET · POST · PUT · DELETE', p: '/agent-assignments/…',           v: 'PropertyAgentAssignmentViewSet', auth: 'IsAgentOrAdmin', purpose: 'Managing / estate agent scoping' },
        { m: 'GET · POST · PUT · DELETE', p: '/agent-config/…',                v: 'PropertyAgentConfigViewSet',auth: 'IsAgentOrAdmin', purpose: 'Per-property AI playbook' },
        { m: 'GET · POST · PUT · DELETE', p: '/mandates/…',                    v: 'RentalMandateViewSet',      auth: 'IsAgentOrAdmin', purpose: 'Rental management mandates' },
        { m: 'POST',                 p: '/<property_id>/mandates/parse-document/', v: 'ParseMandateDocumentView', auth: 'IsAgentOrAdmin', purpose: 'AI-parse mandate PDF' },
        { m: 'GET · POST · PUT · DELETE', p: '/viewings/…',                    v: 'PropertyViewingViewSet',    auth: 'IsAgentOrAdmin', purpose: 'Prospect viewings' },
        { m: 'GET · POST · PUT · DELETE', p: '/groups/…',                      v: 'PropertyGroupViewSet',      auth: 'IsAgentOrAdmin', purpose: 'Portfolio groups' },
        { m: 'POST',                 p: '/parse-municipal-bill/',              v: 'ParseMunicipalBillView',    auth: 'IsAgentOrAdmin', purpose: 'AI-OCR municipal bill' },
        { m: 'GET',                  p: '/owner/dashboard/',                   v: 'OwnerDashboardView',        auth: 'owner role',     purpose: 'Owner portal home' },
        { m: 'GET',                  p: '/owner/properties/',                  v: 'OwnerPropertiesView',       auth: 'owner role',     purpose: 'Owner properties list' },
      ],
    },
    {
      name: 'leases',
      base: '/api/v1/leases/',
      purpose: 'Lease CRUD, templates, AI builder, clause library, tenant lists',
      endpoints: [
        { m: 'GET · POST',             p: '/',                                  v: 'LeaseViewSet',                      auth: 'IsAuthenticated', purpose: 'CRUD leases (accessible_property_ids scoped)' },
        { m: 'GET · PUT · PATCH · DELETE', p: '/<id>/',                         v: 'LeaseViewSet',                      auth: 'IsAuthenticated', purpose: 'Lease detail' },
        { m: 'GET',                    p: '/calendar/',                         v: 'LeaseCalendarAPIView',              auth: 'IsAuthenticated', purpose: 'Renewals / expiries / rent reviews' },
        { m: 'POST',                   p: '/parse-document/',                   v: 'ParseLeaseDocumentView',            auth: 'IsAuthenticated', purpose: 'AI-extract lease from PDF' },
        { m: 'POST',                   p: '/import/',                           v: 'ImportLeaseView',                   auth: 'IsAuthenticated', purpose: 'Bulk import leases + tenants' },
        { m: 'GET · POST',             p: '/templates/',                        v: 'LeaseTemplateListView',             auth: 'IsAuthenticated', purpose: 'CRUD templates' },
        { m: 'GET · PUT · DELETE',     p: '/templates/<id>/',                   v: 'LeaseTemplateDetailView',           auth: 'IsAuthenticated', purpose: 'Template detail (TipTap HTML)' },
        { m: 'GET',                    p: '/templates/<id>/preview/',           v: 'LeaseTemplatePreviewView',          auth: 'IsAuthenticated', purpose: 'Preview with sample merge data' },
        { m: 'POST',                   p: '/templates/<id>/ai-chat/',           v: 'LeaseTemplateAIChatView',           auth: 'IsAuthenticated', purpose: 'Multi-turn refine template' },
        { m: 'GET',                    p: '/templates/<id>/export.pdf/',        v: 'ExportTemplatePDFView',             auth: 'IsAuthenticated', purpose: 'Export template as PDF (Gotenberg)' },
        { m: 'POST',                   p: '/generate/',                         v: 'GenerateLeaseDocumentView',         auth: 'IsAuthenticated', purpose: 'Generate final lease PDF' },
        { m: 'GET',                    p: '/builder/drafts/',                   v: 'LeaseBuilderDraftListView',         auth: 'IsAuthenticated', purpose: 'List saved drafts' },
        { m: 'POST',                   p: '/builder/drafts/new/',               v: 'LeaseBuilderDraftSaveView',         auth: 'IsAuthenticated', purpose: 'Create draft' },
        { m: 'PUT',                    p: '/builder/drafts/<id>/',              v: 'LeaseBuilderDraftSaveView',         auth: 'IsAuthenticated', purpose: 'Checkpoint save' },
        { m: 'POST',                   p: '/builder/sessions/',                 v: 'LeaseBuilderSessionCreateView',     auth: 'IsAuthenticated', purpose: 'Start builder session' },
        { m: 'POST',                   p: '/builder/sessions/<id>/message/',    v: 'LeaseBuilderChatView',              auth: 'IsAuthenticated', purpose: 'Send AI chat message (Claude)' },
        { m: 'POST',                   p: '/builder/sessions/<id>/finalize/',   v: 'LeaseBuilderFinalizeView',          auth: 'IsAuthenticated', purpose: 'Session → LeaseTemplate' },
        { m: 'GET · POST',             p: '/clauses/',                          v: 'ReusableClauseListCreateView',      auth: 'IsAuthenticated', purpose: 'Reusable clause library' },
        { m: 'DELETE',                 p: '/clauses/<id>/',                     v: 'ReusableClauseDestroyView',         auth: 'IsAuthenticated', purpose: 'Delete clause' },
        { m: 'POST',                   p: '/clauses/<id>/use/',                 v: 'ReusableClauseUseView',             auth: 'IsAuthenticated', purpose: 'Mark used (usage count)' },
        { m: 'POST',                   p: '/clauses/generate/',                 v: 'GenerateClauseView',                auth: 'IsAuthenticated', purpose: 'AI-generate clause from prompt' },
        { m: 'POST',                   p: '/clauses/extract/',                  v: 'ExtractClausesView',                auth: 'IsAuthenticated', purpose: 'AI-extract clauses from HTML' },
        { m: 'GET · POST',             p: '/co-tenants/',                       v: 'LeaseTenantList',                   auth: 'IsAuthenticated', purpose: 'Co-tenants (M2M)' },
        { m: 'GET · POST',             p: '/occupants/',                        v: 'LeaseOccupantList',                 auth: 'IsAuthenticated', purpose: 'Non-signing occupants' },
        { m: 'GET · POST',             p: '/guarantors/',                       v: 'LeaseGuarantorList',                auth: 'IsAuthenticated', purpose: 'Surety / co-signers' },
        { m: 'GET · POST · PUT · DELETE', p: '/inventory-templates/…',          v: 'InventoryTemplateViewSet',          auth: 'IsAuthenticated', purpose: 'Inventory presets' },
      ],
    },
    {
      name: 'esigning',
      base: '/api/v1/esigning/',
      purpose: 'Native e-signing (ECTA s13). Public signer links + staff admin.',
      endpoints: [
        { m: 'GET',      p: '/public-sign/<uuid>/',                          v: 'ESigningPublicSignDetailView',        auth: 'AllowAny',       purpose: 'Signing page state' },
        { m: 'GET',      p: '/public-sign/<uuid>/document/',                 v: 'ESigningPublicDocumentView',          auth: 'AllowAny',       purpose: 'Filled lease HTML + field positions' },
        { m: 'GET',      p: '/public-sign/<uuid>/documents/',                v: 'ESigningPublicDocumentsView',         auth: 'AllowAny',       purpose: 'All docs in submission' },
        { m: 'DELETE',   p: '/public-sign/<uuid>/documents/<doc_id>/',      v: 'ESigningPublicDocumentDeleteView',    auth: 'AllowAny',       purpose: 'Delete draft doc' },
        { m: 'POST',     p: '/public-sign/<uuid>/draft/',                    v: 'ESigningPublicDraftView',             auth: 'AllowAny',       purpose: 'Save draft state' },
        { m: 'POST',     p: '/public-sign/<uuid>/sign/',                     v: 'ESigningPublicSubmitSignatureView',   auth: 'AllowAny',       purpose: '⚠ Submit signature + audit (IP, UA, consent)' },
        { m: 'GET · POST', p: '/submissions/',                               v: 'ESigningSubmissionListCreateView',    auth: 'IsAuthenticated',purpose: 'List / create submissions' },
        { m: 'GET',      p: '/submissions/<id>/',                            v: 'ESigningSubmissionDetailView',        auth: 'IsAuthenticated',purpose: 'Submission detail + audit' },
        { m: 'GET',      p: '/submissions/<id>/documents/',                  v: 'ESigningSubmissionDocumentsView',     auth: 'IsAuthenticated',purpose: 'Manage submission docs' },
        { m: 'GET',      p: '/submissions/<id>/download/',                   v: 'ESigningDownloadSignedView',          auth: 'IsAgentOrAdmin', purpose: '⚠ Download signed PDF (verify hash)' },
        { m: 'GET',      p: '/submissions/<id>/test-pdf/',                   v: 'ESigningTestPdfView',                 auth: 'AllowAny',       purpose: 'Gotenberg health + test PDF' },
        { m: 'POST',     p: '/submissions/<id>/resend/',                     v: 'ESigningResendView',                  auth: 'IsAgentOrAdmin', purpose: 'Resend invite to next signer' },
        { m: 'GET',      p: '/submissions/<id>/signer-status/',              v: 'ESigningSignerStatusView',            auth: 'IsAgentOrAdmin', purpose: 'Per-signer completion' },
        { m: 'POST',     p: '/submissions/<id>/public-link/',                v: 'ESigningCreatePublicLinkView',        auth: 'IsAgentOrAdmin', purpose: 'Generate UUID signing link' },
        { m: 'GET',      p: '/webhook/info/',                                v: 'ESigningWebhookInfoView',             auth: 'IsAgentOrAdmin', purpose: 'Webhook config (HMAC key, URL)' },
        { m: 'GET',      p: '/gotenberg/health/',                            v: 'GotenbergHealthView',                 auth: 'AllowAny',       purpose: 'Gotenberg PDF service health' },
      ],
    },
    {
      name: 'maintenance',
      base: '/api/v1/maintenance/',
      purpose: 'Issues, suppliers, dispatch, quotes, AI triage, supplier portal',
      endpoints: [
        { m: 'GET · POST',              p: '/',                                  v: 'MaintenanceRequestViewSet',      auth: 'IsAuthenticated',    purpose: 'Maintenance requests' },
        { m: 'GET · PUT · DELETE',      p: '/<id>/',                             v: 'MaintenanceRequestViewSet',      auth: 'IsAuthenticated',    purpose: 'Request detail' },
        { m: 'GET · POST · PUT · DELETE', p: '/suppliers/…',                     v: 'SupplierViewSet',                auth: 'IsAuthenticated',    purpose: 'CRUD suppliers' },
        { m: 'GET',                     p: '/quotes/<uuid>/',                    v: 'SupplierQuoteView',              auth: 'AllowAny (token)',   purpose: 'Public quote page' },
        { m: 'POST',                    p: '/quotes/<uuid>/decline/',            v: 'SupplierQuoteDeclineView',       auth: 'AllowAny (token)',   purpose: 'Decline quote' },
        { m: 'GET · POST · PUT · DELETE', p: '/skills/…',                        v: 'MaintenanceSkillViewSet',        auth: 'IsAuthenticated',    purpose: 'Skills KB' },
        { m: 'POST',                    p: '/agent-assist/chat/',                v: 'AgentAssistChatView',            auth: 'IsAgentOrAdmin · 30/min', purpose: 'RAG chat (contracts + skills + Q&A)' },
        { m: 'GET',                     p: '/agent-assist/rag-status/',          v: 'AgentAssistRagStatusView',       auth: 'IsAgentOrAdmin',     purpose: 'RAG indexing status' },
        { m: 'GET',                     p: '/supplier/dashboard/',               v: 'SupplierDashboardView',          auth: 'IsSupplier',         purpose: 'Supplier home' },
        { m: 'GET',                     p: '/supplier/jobs/',                    v: 'SupplierJobsView',               auth: 'IsSupplier',         purpose: 'Assigned jobs' },
        { m: 'GET',                     p: '/supplier/jobs/<id>/',               v: 'SupplierJobDetailView',          auth: 'IsSupplier',         purpose: 'Job detail (scope, contact)' },
        { m: 'POST',                    p: '/supplier/jobs/<id>/quote/',         v: 'SupplierJobQuoteView',           auth: 'IsSupplier',         purpose: 'Submit quote' },
        { m: 'POST',                    p: '/supplier/jobs/<id>/decline/',       v: 'SupplierJobDeclineView',         auth: 'IsSupplier',         purpose: 'Decline job' },
        { m: 'GET · PATCH',             p: '/supplier/profile/',                 v: 'SupplierProfileView',            auth: 'IsSupplier',         purpose: 'Own profile' },
        { m: 'GET · POST',              p: '/supplier/documents/',               v: 'SupplierDocumentsView',          auth: 'IsSupplier',         purpose: 'Compliance docs' },
        { m: 'GET',                     p: '/supplier/calendar/',                v: 'SupplierCalendarView',           auth: 'IsSupplier',         purpose: 'Schedule' },
        { m: 'GET',                     p: '/monitor/dashboard/',                v: 'AgentMonitorDashboardView',      auth: 'IsAgentOrAdmin',     purpose: 'Agent telemetry' },
        { m: 'GET',                     p: '/monitor/token-logs/',               v: 'AgentTokenLogView',              auth: 'IsAgentOrAdmin',     purpose: 'LLM token consumption' },
        { m: 'GET',                     p: '/monitor/health/',                   v: 'AgentHealthCheckView',           auth: 'IsAgentOrAdmin',     purpose: 'Claude + RAG health' },
        { m: 'GET',                     p: '/monitor/tests/',                    v: 'ProgressiveTestView',            auth: 'IsAgentOrAdmin',     purpose: 'Synthetic test results' },
        { m: 'GET',                     p: '/monitor/chat-log/',                 v: 'MaintenanceChatLogView',         auth: 'IsAgentOrAdmin',     purpose: 'Agent chat log' },
        { m: 'GET · POST · PUT · DELETE', p: '/agent-questions/…',               v: 'AgentQuestionViewSet',           auth: 'IsAgentOrAdmin',     purpose: 'Staff Q&A library (→ RAG)' },
        { m: 'GET',                     p: '/dispatches/',                       v: 'JobDispatchListView',            auth: 'IsAgentOrAdmin',     purpose: 'Dispatch queue' },
      ],
    },
    {
      name: 'tenant_portal',
      base: '/api/v1/tenant-portal/',
      purpose: 'Tenant-facing AI chat (conversations, maintenance drafts)',
      endpoints: [
        { m: 'GET · POST', p: '/conversations/',                              v: 'TenantConversationsListCreateView',      auth: 'IsAuthenticated',        purpose: 'Tenant AI conversations' },
        { m: 'GET',        p: '/conversations/<id>/',                         v: 'TenantConversationDetailView',           auth: 'IsAuthenticated',        purpose: 'Conversation thread' },
        { m: 'POST',       p: '/conversations/<id>/messages/',                v: 'TenantConversationMessageCreateView',    auth: 'IsAuthenticated · 30/min', purpose: 'Send message (Claude)' },
        { m: 'POST',       p: '/conversations/<id>/maintenance-draft/',      v: 'TenantConversationMaintenanceDraftView', auth: 'IsAuthenticated · 5/min',  purpose: 'Auto-draft maintenance request' },
      ],
    },
    {
      name: 'tenant',
      base: '/api/v1/tenant/',
      purpose: 'Canonical tenant record + temporal unit assignment',
      endpoints: [
        { m: 'GET · POST · PUT · DELETE', p: '/tenants/…',    v: 'TenantViewSet',              auth: 'IsAuthenticated', purpose: 'Tenant CRUD' },
        { m: 'GET · POST · PUT · DELETE', p: '/assignments/…', v: 'TenantUnitAssignmentViewSet', auth: 'IsAuthenticated', purpose: 'Unit occupancy (temporal)' },
      ],
    },
    {
      name: 'the_volt (Vault33)',
      base: '/api/v1/the-volt/',
      purpose: 'Encrypted vault — owner CRUD + subscriber gateway (OTP-gated consent)',
      endpoints: [
        { m: 'GET',                     p: '/vault/me/',                                  v: 'VaultOwnerMeView',               auth: 'IsAuthenticated',           purpose: "Owner's vault profile" },
        { m: 'GET · POST · PUT · DELETE', p: '/entities/…',                               v: 'VaultEntityViewSet',             auth: 'IsAuthenticated',           purpose: 'CRUD entities (6 types)' },
        { m: 'GET · POST · PUT · DELETE', p: '/relationships/…',                          v: 'EntityRelationshipViewSet',      auth: 'IsAuthenticated',           purpose: 'Relationship graph' },
        { m: 'GET',                     p: '/relationship-types/',                        v: 'RelationshipTypeCatalogueViewSet', auth: 'IsAuthenticated',         purpose: 'Catalogue (10 types)' },
        { m: 'GET · POST · PUT · DELETE', p: '/documents/…',                              v: 'VaultDocumentViewSet',           auth: 'IsAuthenticated',           purpose: 'Encrypted docs (Fernet)' },
        { m: 'GET',                     p: '/schemas/',                                   v: 'EntitySchemaViewSet',            auth: 'IsAuthenticated',           purpose: 'Schema definitions' },
        { m: 'POST',                    p: '/gateway/request/',                           v: 'DataRequestCreateView',          auth: 'VoltApiKeyAuthentication',  purpose: '⚠ Subscriber requests data (X-Volt-API-Key)' },
        { m: 'POST',                    p: '/gateway/checkout/',                          v: 'DataCheckoutView',               auth: 'VoltApiKeyAuthentication',  purpose: 'Get checkout URL' },
        { m: 'GET',                     p: '/gateway/requests/<uuid>/status/',            v: 'DataCheckoutStatusView',         auth: 'VoltApiKeyAuthentication',  purpose: 'Poll request status' },
        { m: 'GET',                     p: '/gateway/requests/',                          v: 'DataRequestListView',            auth: 'IsAuthenticated',           purpose: 'Owner: requests to approve' },
        { m: 'POST',                    p: '/gateway/requests/<uuid>/approve/',           v: 'DataRequestApproveView',         auth: 'IsAuthenticated',           purpose: 'Owner approves request' },
        { m: 'POST',                    p: '/gateway/requests/<uuid>/deny/',              v: 'DataRequestDenyView',            auth: 'IsAuthenticated',           purpose: 'Owner denies request' },
        { m: 'GET',                     p: '/gateway/requests/<uuid>/approval-info/',     v: 'DataRequestApprovalInfoView',    auth: 'AllowAny',                  purpose: 'Public summary (no OTP)' },
        { m: 'POST',                    p: '/gateway/requests/<uuid>/approve-public/',    v: 'DataRequestApprovePublicView',   auth: 'AllowAny (UUID + OTP)',     purpose: '⚠ Approve from email link' },
      ],
    },
    {
      name: 'ai',
      base: '/api/v1/ai/',
      purpose: 'AI skills registry — catalogue of skills, prompts, MCP tools',
      endpoints: [
        { m: 'GET', p: '/registry/',                      v: 'SkillsRegistryView',         auth: 'IsAuthenticated', purpose: 'List available skills' },
        { m: 'GET', p: '/skills/claude/<skill_id>/',      v: 'ClaudeSkillDetailView',      auth: 'IsAuthenticated', purpose: 'Claude skill detail' },
        { m: 'GET', p: '/skills/maintenance/<id>/',       v: 'MaintenanceSkillDetailView', auth: 'IsAuthenticated', purpose: 'Maintenance skill detail' },
        { m: 'GET', p: '/tools/mcp/<tool_id>/',           v: 'MCPToolDetailView',          auth: 'IsAuthenticated', purpose: 'MCP tool detail' },
      ],
    },
    {
      name: 'market_data',
      base: '/api/v1/market-data/',
      purpose: 'Scraped listings, price stats, news, bylaws, semantic search',
      endpoints: [
        { m: 'GET · POST · PUT · DELETE', p: '/listings/…',    v: 'MarketListingViewSet',     auth: 'IsAuthenticated', purpose: 'Market comps (P24 / PP)' },
        { m: 'GET · POST · PUT · DELETE', p: '/stats/…',       v: 'MarketPriceStatsViewSet',  auth: 'IsAuthenticated', purpose: 'Daily price stats by area' },
        { m: 'GET · POST · PUT · DELETE', p: '/scrape-runs/…', v: 'ScrapeRunViewSet',         auth: 'IsAuthenticated', purpose: 'Scraper run history' },
        { m: 'GET · POST · PUT · DELETE', p: '/news/…',        v: 'AreaNewsViewSet',          auth: 'IsAuthenticated', purpose: 'Area news feed' },
        { m: 'GET · POST · PUT · DELETE', p: '/bylaws/…',      v: 'MunicipalBylawViewSet',    auth: 'IsAuthenticated', purpose: 'Municipal bylaws (vectorized)' },
        { m: 'POST',                      p: '/search/',        v: 'SemanticSearchView',       auth: 'IsAuthenticated', purpose: 'Semantic search across corpus' },
        { m: 'POST',                      p: '/map-export/',    v: 'MapExportView',            auth: 'IsAuthenticated', purpose: 'Export as GeoJSON' },
      ],
    },
    {
      name: 'test_hub',
      base: '/api/v1/test-hub/',
      purpose: 'Self-testing meta-app — runs, issues, health, RAG status',
      endpoints: [
        { m: 'GET · POST · PUT · DELETE', p: '/runs/…',           v: 'TestRunRecordViewSet',        auth: 'IsAuthenticated (admin)', purpose: 'Test run records' },
        { m: 'GET',                       p: '/runs/stream/',     v: 'TestRunStreamView',           auth: 'IsAuthenticated (admin)', purpose: 'SSE live test runs' },
        { m: 'GET',                       p: '/runs/stream-frontend/', v: 'FrontendTestStreamView', auth: 'IsAuthenticated (admin)', purpose: 'Frontend test stream' },
        { m: 'GET · POST · PUT · DELETE', p: '/issues/…',         v: 'TestIssueViewSet',            auth: 'IsAuthenticated (admin)', purpose: 'Known bugs' },
        { m: 'GET · POST · PUT · DELETE', p: '/snapshots/…',      v: 'TestHealthSnapshotViewSet',   auth: 'IsAuthenticated (admin)', purpose: 'Health snapshots' },
        { m: 'GET',                       p: '/health/',          v: 'HealthDashboardView',         auth: 'IsAuthenticated (admin)', purpose: 'System health' },
        { m: 'GET',                       p: '/selfcheck/',       v: 'SelfCheckView',               auth: 'IsAuthenticated (admin)', purpose: 'Self-diagnostic' },
        { m: 'GET',                       p: '/rag-status/',      v: 'RAGStatusView',               auth: 'IsAuthenticated (admin)', purpose: 'RAG collection stats' },
        { m: 'POST',                      p: '/rag-reindex/',     v: 'RAGReindexView',              auth: 'IsAuthenticated (admin)', purpose: 'Trigger reindex' },
        { m: 'GET',                       p: '/module/<module>/', v: 'ModuleStatsView',             auth: 'IsAuthenticated (admin)', purpose: 'Per-module stats' },
        { m: 'GET',                       p: '/frontend/stats/',  v: 'FrontendTestStatsView',       auth: 'IsAuthenticated (admin)', purpose: 'Frontend coverage' },
      ],
    },
    {
      name: 'core',
      base: '/api/v1/',
      purpose: 'Top-level health & dashboard',
      endpoints: [
        { m: 'GET', p: '/health/',             v: 'health_check',          auth: 'AllowAny',        purpose: 'Liveness probe (Docker)' },
        { m: 'GET', p: '/stats/',              v: 'StatsView',             auth: 'IsAuthenticated', purpose: 'System statistics' },
        { m: 'GET', p: '/dashboard/portfolio/',v: 'DashboardPortfolioView',auth: 'IsAuthenticated', purpose: 'Portfolio dashboard' },
      ],
    },
  ],
  websockets: [
    { path: 'ws/esigning/<pk>/',              consumer: 'ESigningStatusConsumer',    auth: 'JWT (query param or header)', purpose: 'Real-time signer status updates' },
    { path: 'ws/leases/updates/',             consumer: 'LeaseUpdatesConsumer',      auth: 'JWT',                         purpose: 'Lease change broadcasts (status, tenant)' },
    { path: 'ws/maintenance/<pk>/activity/',  consumer: 'MaintenanceActivityConsumer', auth: 'JWT',                       purpose: 'Job activity stream (quote, status)' },
    { path: 'ws/maintenance/updates/',        consumer: 'MaintenanceListConsumer',   auth: 'JWT',                         purpose: 'Maintenance list refresh' },
  ],
  critical: [
    { name: 'E-sign submit signature', ep: 'POST /esigning/public-sign/<uuid>/sign/', risk: 'PUBLIC · legally binding. Tamper-evident SHA-256 + IP + UA + consent timestamp captured. Audit failure = ECTA non-repudiation broken.' },
    { name: 'E-sign PDF download',     ep: 'GET /esigning/submissions/<id>/download/', risk: 'Signed-PDF hash must verify on every read. Forgery = evidentiary loss.' },
    { name: 'Lease generate PDF',      ep: 'POST /leases/generate/',                   risk: 'Merge field injection could fabricate tenant names, amounts, dates. Server-side validation mandatory.' },
    { name: 'Lease builder finalize',  ep: 'POST /leases/builder/sessions/<id>/finalize/', risk: 'Prompt injection via conversation could insert malicious clauses. Review before save.' },
    { name: 'Agent-assist RAG chat',   ep: 'POST /maintenance/agent-assist/chat/',     risk: 'Prompt injection via stored Q&A. Cross-tenant leakage if agency filter misses.' },
    { name: 'E-sign webhook callback', ep: 'POST /esigning/webhook/ (provider)',       risk: 'HMAC key compromise = forged signature events. Idempotency keys required.' },
    { name: 'User invite',             ep: 'POST /auth/users/ (with role)',            risk: 'Privilege escalation — must block inviter from elevating beyond own role.' },
    { name: 'Vault33 gateway approve', ep: 'POST /the-volt/gateway/requests/<uuid>/approve-public/', risk: 'UUID + OTP only. Consent bypass if OTP not enforced. POPIA s11 breach.' },
    { name: 'User delete',             ep: 'DELETE /auth/users/<id>/',                 risk: 'Cascade delete can orphan tenant / lease records. Soft-delete preferred.' },
    { name: 'Property agent assignment', ep: 'POST /properties/agent-assignments/',    risk: 'Scope escalation — agent could gain visibility of competitor portfolio.' },
  ],
};

function pageAPI() {
  const css = `
    <style>
      .api-tabs{display:flex;gap:6px;background:#fff;padding:6px;border-radius:12px;margin-bottom:26px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;position:sticky;top:12px;z-index:5;flex-wrap:wrap}
      .api-tab{flex:1 1 0;min-width:120px;text-align:center;padding:10px 12px;border-radius:8px;font-size:13px;font-weight:600;color:#6c6e92;text-decoration:none;transition:all .12s;border:1px solid transparent}
      .api-tab:hover{background:#FAFAFE;color:#2B2D6E}
      .api-tab.active{background:linear-gradient(135deg,#2B2D6E,#3a3d8a);color:#fff;box-shadow:0 2px 8px -2px rgba(43,45,110,.3)}
      .api-tab .t-num{font-size:10.5px;font-weight:600;opacity:.7;margin-right:6px;letter-spacing:.04em}

      .api-stats{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:26px}
      .api-stat{background:#fff;border-radius:12px;padding:16px 18px;border:1px solid #EFEFF5}
      .api-stat .n{font-family:'Fraunces',serif;font-weight:700;font-size:24px;color:#2B2D6E;line-height:1}
      .api-stat .l{font-size:11px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin:6px 0 4px}
      .api-stat .d{font-size:11.5px;color:#6c6e92;line-height:1.4}

      .api-section{margin-bottom:40px;scroll-margin-top:90px}
      .api-section > header{margin-bottom:16px}
      .api-section > header h2{font-family:'Fraunces',serif;font-weight:600;font-size:22px;color:#2B2D6E;margin:0}
      .api-section > header p{margin:4px 0 0;color:#6c6e92;font-size:13px}

      .api-app{background:#fff;border-radius:14px;box-shadow:0 1px 3px rgba(43,45,110,.06);border:1px solid #EFEFF5;margin-bottom:12px;overflow:hidden}
      .api-app > summary{padding:14px 18px;cursor:pointer;display:grid;grid-template-columns:160px 220px 1fr 80px;gap:14px;align-items:center;background:#FAFAFE;list-style:none;border-bottom:1px solid #EFEFF5}
      .api-app > summary::-webkit-details-marker{display:none}
      .api-app > summary::before{content:'▸';color:#FF3D7F;font-size:12px;transition:transform .15s}
      .api-app[open] > summary::before{transform:rotate(90deg)}
      .api-app > summary .name{font-family:ui-monospace,Menlo,monospace;font-weight:700;color:#2B2D6E;font-size:14px}
      .api-app > summary .base{font-family:ui-monospace,Menlo,monospace;color:#FF3D7F;font-size:12px;background:#FFF5F8;padding:2px 8px;border-radius:5px;border:1px solid #FFE4EF}
      .api-app > summary .purpose{font-size:12.5px;color:#6c6e92}
      .api-app > summary .count{font-size:10.5px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;background:#fff;border:1px solid #EFEFF5;padding:3px 8px;border-radius:5px;text-align:center}

      .api-row{display:grid;grid-template-columns:160px 2.1fr 1.4fr 1.2fr 1.8fr;gap:12px;padding:9px 18px;border-bottom:1px solid #F4F4F9;font-size:11.5px;align-items:start}
      .api-row:last-child{border-bottom:0}
      .api-row .method{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#FF3D7F;font-size:11px;background:#FFF5F8;padding:2px 6px;border-radius:4px;display:inline-block;border:1px solid #FFE4EF}
      .api-row .path{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#2B2D6E;font-size:11.5px;word-break:break-all}
      .api-row .view{font-family:ui-monospace,Menlo,monospace;color:#8a8ca8;font-size:11px}
      .api-row .auth{color:#5b5e8c;font-size:11px}
      .api-row .purpose{color:#5b5e8c;line-height:1.5}
      .api-row.head{background:#FCFCFE;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
      .api-row.head > div{color:#8a8ca8 !important;font-family:'DM Sans',sans-serif !important;font-weight:600 !important;font-size:10.5px !important}

      .api-ws{display:grid;grid-template-columns:2fr 1.6fr 1.2fr 2fr;gap:14px;padding:10px 18px;background:#fff;border:1px solid #EFEFF5;border-radius:8px;margin-bottom:5px;font-size:12px;align-items:start}
      .api-ws .path{font-family:ui-monospace,Menlo,monospace;font-weight:600;color:#FF3D7F;background:#FFF5F8;padding:2px 8px;border-radius:4px;border:1px solid #FFE4EF;font-size:11.5px;display:inline-block}
      .api-ws .consumer{font-family:ui-monospace,Menlo,monospace;color:#2B2D6E;font-size:11.5px}
      .api-ws .auth{color:#5b5e8c;font-size:11.5px}
      .api-ws .purpose{color:#6c6e92;line-height:1.5;font-size:12px}
      .api-ws.head{background:transparent;border:0;padding:4px 18px;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
      .api-ws.head > div{color:#8a8ca8 !important;font-family:'DM Sans',sans-serif !important}

      .api-crit{background:#FFFBEA;border:1px solid #FDF3E0;border-left:3px solid #FF3D7F;border-radius:10px;padding:14px 18px;margin-bottom:8px}
      .api-crit .head{display:flex;align-items:baseline;gap:12px;margin-bottom:5px;flex-wrap:wrap}
      .api-crit .name{font-family:'Fraunces',serif;font-weight:600;color:#9A5800;font-size:14px}
      .api-crit .ep{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;color:#2B2D6E;background:#fff;padding:2px 8px;border-radius:4px;border:1px solid #EFEFF5}
      .api-crit .risk{color:#6c6e92;font-size:12.5px;line-height:1.55}

      @media (max-width:1000px){.api-stats{grid-template-columns:repeat(3,1fr)}.api-row{grid-template-columns:1fr;gap:4px}.api-row.head{display:none}.api-app > summary{grid-template-columns:1fr;gap:6px}.api-ws{grid-template-columns:1fr;gap:4px}.api-ws.head{display:none}}
      @media (max-width:820px){.api-stats{grid-template-columns:repeat(2,1fr)}}
    </style>
  `;

  const stats = api.stats.map(([n, v, d]) => `
    <div class="api-stat"><div class="n">${v}</div><div class="l">${n}</div><div class="d">${d}</div></div>
  `).join('');

  const authRows = api.auth.map(r => `
    <div class="api-row">
      <div><span class="method">${r.m}</span></div>
      <div class="path">${r.p}</div>
      <div class="view">${r.v}</div>
      <div class="auth">${r.auth}</div>
      <div class="purpose">${r.th}</div>
    </div>
  `).join('');

  const apps = api.apps.map(a => `
    <details class="api-app" open>
      <summary>
        <span class="name">${a.name}</span>
        <span class="base">${a.base}</span>
        <span class="purpose">${a.purpose}</span>
        <span class="count">${a.endpoints.length} endpoints</span>
      </summary>
      <div class="api-row head">
        <div>Method</div><div>Path</div><div>View</div><div>Auth</div><div>Purpose</div>
      </div>
      ${a.endpoints.map(e => `
        <div class="api-row">
          <div><span class="method">${e.m}</span></div>
          <div class="path">${e.p}</div>
          <div class="view">${e.v}</div>
          <div class="auth">${e.auth}</div>
          <div class="purpose">${e.purpose}</div>
        </div>
      `).join('')}
    </details>
  `).join('');

  const wsRows = api.websockets.map(w => `
    <div class="api-ws">
      <div><span class="path">${w.path}</span></div>
      <div class="consumer">${w.consumer}</div>
      <div class="auth">${w.auth}</div>
      <div class="purpose">${w.purpose}</div>
    </div>
  `).join('');

  const critical = api.critical.map(c => `
    <div class="api-crit">
      <div class="head">
        <span class="name">${c.name}</span>
        <span class="ep">${c.ep}</span>
      </div>
      <div class="risk">${c.risk}</div>
    </div>
  `).join('');

  return css + `
    <h1>API contracts</h1>
    <p class="lede">Every REST and WebSocket endpoint in the backend, grouped by Django app. Sourced from a fresh survey of <code>config/urls.py</code> + each app's <code>urls.py</code>. Base path: <code>/api/v1/</code>.</p>

    <nav class="api-tabs" aria-label="API sections">
      <a href="#stats"     class="api-tab active"><span class="t-num">1</span>At a glance</a>
      <a href="#auth"      class="api-tab"><span class="t-num">2</span>Auth</a>
      <a href="#apps"      class="api-tab"><span class="t-num">3</span>By app</a>
      <a href="#websockets" class="api-tab"><span class="t-num">4</span>WebSockets</a>
      <a href="#critical"  class="api-tab"><span class="t-num">5</span>Critical</a>
    </nav>

    <section class="api-section" id="stats">
      <header>
        <h2>1 · At a glance</h2>
        <p>The shape of the API surface.</p>
      </header>
      <div class="api-stats">${stats}</div>
    </section>

    <section class="api-section" id="auth">
      <header>
        <h2>2 · Auth endpoints</h2>
        <p>JWT-based (SimpleJWT). Access token + refresh token. Throttle classes gate anonymous endpoints.</p>
      </header>
      <div class="api-app" style="padding:0">
        <div class="api-row head">
          <div>Method</div><div>Path</div><div>View</div><div>Auth</div><div>Throttle</div>
        </div>
        ${authRows}
      </div>
    </section>

    <section class="api-section" id="apps">
      <header>
        <h2>3 · Endpoints by app</h2>
        <p>${api.apps.length} apps · ~${api.apps.reduce((n, a) => n + a.endpoints.length, 0)} documented endpoints (ViewSets expand into list + detail + extra actions). Click any app to inspect.</p>
      </header>
      ${apps}
    </section>

    <section class="api-section" id="websockets">
      <header>
        <h2>4 · WebSocket channels</h2>
        <p>Django Channels + Daphne. All 4 channels require a JWT token (query param or header). Used for real-time badges, signer status, and maintenance activity streams.</p>
      </header>
      <div class="api-ws head">
        <div>Path</div><div>Consumer</div><div>Auth</div><div>Purpose</div>
      </div>
      ${wsRows}
    </section>

    <section class="api-section" id="critical">
      <header>
        <h2>5 · Critical / sensitive endpoints</h2>
        <p>These need extra scrutiny — legal, financial, or privacy impact. Read alongside the <a href="/data#rights" style="color:#FF3D7F">data rights</a> and <a href="/data#vault33" style="color:#FF3D7F">Vault33</a> sections.</p>
      </header>
      ${critical}
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.api-tab');
        const ids = ['stats','auth','apps','websockets','critical'];
        const sections = ids.map(id => document.getElementById(id));
        function onScroll(){
          const y = window.scrollY + 140;
          let active = 0;
          sections.forEach((s, i) => { if (s && s.offsetTop <= y) active = i; });
          tabs.forEach((t, i) => t.classList.toggle('active', i === active));
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- RBAC matrix (roles × resources × actions) ---------- */
function pageRBAC() {
  const rbac = {
    stats: [
      ['Roles',            '10',   'User.role choices on the User model'],
      ['Permission classes','16',  'Custom DRF BasePermission subclasses'],
      ['Access functions', '1',    'get_accessible_property_ids — single source of truth for property scope'],
      ['Object guards',    '3',    'HasPropertyAccess, IsManagingAgentForProperty, IsOwnerOfProperty'],
      ['Scope model',      'Assignment-based', 'Role + PropertyAgentAssignment.active + ownership chain'],
      ['Source file',      'accounts/permissions.py', '~240 LOC, all guards in one module'],
    ],
    roles: [
      // code, label, bucket, bucket class, scope summary, module access
      { code: 'admin',          label: 'Admin',          bucket: 'Platform', cls: 'p', scope: 'Everything. Superuser bypass + ADMIN role. Manages users, agencies, global config.' },
      { code: 'agency_admin',   label: 'Agency admin',   bucket: 'Agency',   cls: 'a', scope: 'All properties managed by any agent in their agency. Creates agents, sets commissions, views financials.' },
      { code: 'managing_agent', label: 'Managing agent', bucket: 'Agent',    cls: 'g', scope: 'Properties with PropertyAgentAssignment.active AND assignment_type="managing". Day-to-day PM.' },
      { code: 'estate_agent',   label: 'Estate agent',   bucket: 'Agent',    cls: 'g', scope: 'Properties with PropertyAgentAssignment.active AND assignment_type="estate". Lettings/sales only.' },
      { code: 'agent',          label: 'Agent (legacy)', bucket: 'Agent',    cls: 'g', scope: 'Legacy generic managing agent. Property.agent FK fallback. Being phased out in favour of assignments.' },
      { code: 'accountant',     label: 'Accountant',     bucket: 'Finance',  cls: 'f', scope: 'Read access to ALL properties for financial reporting. Cannot edit property data. Ideal for bookkeepers.' },
      { code: 'viewer',         label: 'Viewer',         bucket: 'Agency',   cls: 'a', scope: 'Read-only, scoped to agency. module_access field limits to {inspections|maintenance|properties}. Intern role.' },
      { code: 'owner',          label: 'Owner',          bucket: 'External', cls: 'e', scope: 'Properties reached via Person → Landlord → PropertyOwnership.is_current=True. Sees their own units.' },
      { code: 'supplier',       label: 'Supplier',       bucket: 'External', cls: 'e', scope: 'Maintenance jobs assigned to them. Quotes they submitted. No property-level data.' },
      { code: 'tenant',         label: 'Tenant',         bucket: 'External', cls: 'e', scope: 'Their own active lease(s) via get_tenant_leases(user). Maintenance requests they filed. Payments they owe.' },
    ],
    // Column order for the matrix — each role
    matrixCols: ['admin','agency_admin','managing_agent','estate_agent','agent','accountant','viewer','owner','supplier','tenant'],
    // Each resource row defines permissions per action
    // Legend: F = full CRUD, C = create, R = read, U = update, D = delete, Rs = read own/scoped, Cs = create scoped, — = no access
    resources: [
      // Group: Identity & Access
      { group: 'Identity & Access', resource: 'User accounts',       actions: { admin:'F', agency_admin:'Cs/Rs/Us',      managing_agent:'—', estate_agent:'—', agent:'—', accountant:'—', viewer:'—', owner:'Rs (self)', supplier:'Rs (self)', tenant:'Rs (self)' }, note: 'AGENCY_ADMIN can invite/manage agents within their agency only.' },
      { group: 'Identity & Access', resource: 'Roles & permissions', actions: { admin:'F', agency_admin:'—',              managing_agent:'—', estate_agent:'—', agent:'—', accountant:'—', viewer:'—', owner:'—',       supplier:'—',      tenant:'—' }, note: 'Only ADMIN can change roles. Agency admins cannot promote someone to admin.' },
      { group: 'Identity & Access', resource: 'Agencies',            actions: { admin:'F', agency_admin:'Rs/Us (own)',    managing_agent:'Rs', estate_agent:'Rs', agent:'Rs', accountant:'R', viewer:'Rs', owner:'—', supplier:'—', tenant:'—' }, note: 'Agency admins edit only their own agency record.' },
      // Group: Property graph
      { group: 'Property graph',    resource: 'Properties',          actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'Rs/Us (assigned)', estate_agent:'Rs (assigned)', agent:'Rs/Us (assigned)', accountant:'R', viewer:'R (agency)', owner:'Rs (owned)', supplier:'—', tenant:'—' }, note: 'Scope resolved via access.py → get_accessible_property_ids(user).' },
      { group: 'Property graph',    resource: 'Units',               actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'Rs/Us (assigned)', estate_agent:'Rs (assigned)', agent:'Rs/Us (assigned)', accountant:'R', viewer:'R (agency)', owner:'Rs (owned)', supplier:'—', tenant:'Rs (leased)' }, note: 'Tenant sees only the unit on their active lease.' },
      { group: 'Property graph',    resource: 'Ownership (Landlord/PropertyOwnership)', actions: { admin:'F', agency_admin:'F (agency)', managing_agent:'R (assigned)', estate_agent:'R (assigned)', agent:'R (assigned)', accountant:'R', viewer:'—', owner:'Rs (self)', supplier:'—', tenant:'—' }, note: 'Owner chain is sensitive — FICA docs live here. Viewers cannot see.' },
      { group: 'Property graph',    resource: 'Bank accounts',       actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'R (assigned)',    estate_agent:'—',             agent:'R (assigned)',    accountant:'R', viewer:'—', owner:'Rs (own)',   supplier:'—', tenant:'—' }, note: 'Trust account details — restricted. No tenant visibility.' },
      { group: 'Property graph',    resource: 'Mandates',            actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'Rs (assigned)',    estate_agent:'Rs (assigned)',  agent:'Rs (assigned)',    accountant:'R', viewer:'—', owner:'Rs (own)',   supplier:'—', tenant:'—' }, note: 'RentalMandate ties landlord → property for a defined term.' },
      { group: 'Property graph',    resource: 'Compliance certs',    actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'F (assigned)',     estate_agent:'R (assigned)',   agent:'F (assigned)',     accountant:'R', viewer:'R (agency)', owner:'Rs (own)', supplier:'—', tenant:'Rs (leased)' }, note: 'Tenant sees unit-level certs (elec, gas, lift) for their rental.' },
      // Group: Leases
      { group: 'Leases',            resource: 'Leases',              actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'F (assigned)',     estate_agent:'Cs/Rs/Us (assigned)', agent:'F (assigned)', accountant:'R', viewer:'R (agency)', owner:'Rs (own property)', supplier:'—', tenant:'Rs (own lease)' }, note: 'LeaseViewSet filters by role in get_queryset. Tenants see only leases they are on.' },
      { group: 'Leases',            resource: 'Lease templates',     actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'R',                estate_agent:'R',              agent:'R',                accountant:'—', viewer:'—', owner:'—',         supplier:'—', tenant:'—' }, note: 'Agency admins author lease templates. Agents select from library.' },
      { group: 'Leases',            resource: 'Clauses library',     actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'R',                estate_agent:'R',              agent:'R',                accountant:'—', viewer:'—', owner:'—',         supplier:'—', tenant:'—' }, note: 'AI-generated clauses shared agency-wide.' },
      { group: 'Leases',            resource: 'E-signing submissions', actions: { admin:'F', agency_admin:'F (agency)',   managing_agent:'F (assigned)',     estate_agent:'F (assigned)',   agent:'F (assigned)',     accountant:'R', viewer:'—', owner:'Rs (own property)', supplier:'—', tenant:'Rs + sign (own)' }, note: 'Signing link is OTP-gated. Tenant signs only their own.' },
      // Group: Finance
      { group: 'Finance',           resource: 'Invoices & statements', actions: { admin:'F', agency_admin:'F (agency)',  managing_agent:'F (assigned)',     estate_agent:'R',              agent:'F (assigned)',     accountant:'F',  viewer:'—', owner:'Rs (own)',   supplier:'—', tenant:'Rs (own)' }, note: 'CanViewFinancials composite guard. Tenants see rent invoices issued to them.' },
      { group: 'Finance',           resource: 'Payments',            actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'F (assigned)',     estate_agent:'—',              agent:'F (assigned)',     accountant:'F',  viewer:'—', owner:'Rs (own)',   supplier:'—', tenant:'Cs/Rs (own)' }, note: 'Tenants initiate payments; cannot edit reconciled entries.' },
      { group: 'Finance',           resource: 'Deposits',            actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'F (assigned)',     estate_agent:'—',              agent:'F (assigned)',     accountant:'F',  viewer:'—', owner:'Rs (own)',   supplier:'—', tenant:'Rs (own)' }, note: 'Lodged in interest-bearing account per RHA s5(3)(c). Interest split must be visible to tenant.' },
      { group: 'Finance',           resource: 'Commissions & payouts', actions: { admin:'F', agency_admin:'F (agency)',   managing_agent:'R (own)',          estate_agent:'R (own)',        agent:'R (own)',          accountant:'F',  viewer:'—', owner:'—',         supplier:'—', tenant:'—' }, note: 'Agents see their own splits. Agency admin sees the full pot.' },
      // Group: Maintenance
      { group: 'Maintenance',       resource: 'Maintenance requests',actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'F (assigned)',     estate_agent:'R',              agent:'F (assigned)',     accountant:'—', viewer:'R (agency)', owner:'Rs (own property)', supplier:'Rs (assigned)', tenant:'Cs/Rs (own)' }, note: 'Tenant creates + comments on their own. Supplier sees only jobs they are assigned to.' },
      { group: 'Maintenance',       resource: 'Supplier directory',  actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'R/U (add/approve)', estate_agent:'R',             agent:'R/U',              accountant:'—', viewer:'—', owner:'R (agency)', supplier:'Rs (self)', tenant:'—' }, note: 'Supplier edits their own profile, services, rates.' },
      { group: 'Maintenance',       resource: 'Quotes',              actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'F (assigned)',     estate_agent:'—',              agent:'F (assigned)',     accountant:'R', viewer:'—', owner:'Rs (own)',   supplier:'Cs/Rs (own)', tenant:'—' }, note: 'Supplier posts quote; agent approves; owner sees outcome.' },
      { group: 'Maintenance',       resource: 'Inspection reports',  actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'F (assigned)',     estate_agent:'R',              agent:'F (assigned)',     accountant:'—', viewer:'R (agency)', owner:'Rs (own)', supplier:'—', tenant:'Rs (own lease)' }, note: 'Ingoing + outgoing inspections — RHA s5A(2). Tenant must co-sign.' },
      // Group: Tenants
      { group: 'Tenants',           resource: 'Tenant profiles',     actions: { admin:'F', agency_admin:'F (agency)',     managing_agent:'F (assigned)',     estate_agent:'R (assigned)',   agent:'F (assigned)',     accountant:'R', viewer:'R (agency)', owner:'Rs (own property tenants)', supplier:'—', tenant:'Rs/Us (self)' }, note: 'CanManageTenants composite. Tenant can edit their own contact details.' },
      { group: 'Tenants',           resource: 'Screening (credit/ID)',actions: { admin:'F', agency_admin:'F (agency)',    managing_agent:'F (assigned)',     estate_agent:'F (assigned)',   agent:'F (assigned)',     accountant:'—', viewer:'—', owner:'Rs (results)',supplier:'—', tenant:'Cs (consent) / Rs (own)' }, note: 'POPIA s11 consent from tenant. Results shared with assigned agent + owner only.' },
      { group: 'Tenants',           resource: 'Tenant documents (FICA)', actions: { admin:'F', agency_admin:'F (agency)', managing_agent:'F (assigned)',     estate_agent:'R (assigned)',   agent:'F (assigned)',     accountant:'R', viewer:'—', owner:'—',         supplier:'—', tenant:'Cs/Rs (own)' }, note: 'Owner should NOT see tenant FICA docs — minimisation. Store in Vault33.' },
      // Group: Notifications & portals
      { group: 'Notifications',     resource: 'Notifications (own)', actions: { admin:'F', agency_admin:'Rs (self)',      managing_agent:'Rs (self)',        estate_agent:'Rs (self)',      agent:'Rs (self)',        accountant:'Rs (self)', viewer:'Rs (self)', owner:'Rs (self)', supplier:'Rs (self)', tenant:'Rs (self)' }, note: 'Everyone reads their own queue.' },
      { group: 'Notifications',     resource: 'Broadcast announcements', actions: { admin:'F', agency_admin:'F (agency)', managing_agent:'Cs (to tenants)', estate_agent:'—',              agent:'Cs (to tenants)',  accountant:'—', viewer:'—', owner:'—',         supplier:'—', tenant:'R' }, note: 'Used for rent reminders, load-shedding, community notices.' },
      // Group: Platform
      { group: 'Platform',          resource: 'Agent-assist (RAG)',  actions: { admin:'F', agency_admin:'U',              managing_agent:'U',                estate_agent:'U',              agent:'U',                accountant:'—', viewer:'—', owner:'—',         supplier:'—', tenant:'—' }, note: 'Internal AI chat; scoped to agency data. Not tenant-facing.' },
      { group: 'Platform',          resource: 'Market data (AVM)',   actions: { admin:'F', agency_admin:'R',              managing_agent:'R',                estate_agent:'R',              agent:'R',                accountant:'R', viewer:'—', owner:'R (own properties)', supplier:'—', tenant:'—' }, note: 'Private Property + P24 comps. Rate-limited.' },
      { group: 'Platform',          resource: 'Audit log',           actions: { admin:'R', agency_admin:'R (agency)',     managing_agent:'—',                estate_agent:'—',              agent:'—',                accountant:'R', viewer:'—', owner:'—',         supplier:'—', tenant:'—' }, note: 'Immutable. Only admins and agency admins can review staff actions.' },
      { group: 'Platform',          resource: 'Vault33 gateway',     actions: { admin:'F', agency_admin:'Cs (request checkout)','managing_agent':'Cs (request checkout)', estate_agent:'—', agent:'Cs (request checkout)', accountant:'R (loan slips)', viewer:'—', owner:'F (approve/revoke own data)', supplier:'—', tenant:'F (approve/revoke own data)' }, note: 'Data subject has veto. Staff can request, not unilaterally read.' },
    ],
    // Concrete enforcement examples pulled from code
    enforcement: [
      { file: 'backend/apps/properties/access.py', fn: 'get_accessible_property_ids(user) → QuerySet[UUID]', summary: 'Single source of truth for which property IDs a user can touch. All property-adjacent ViewSets call this in their get_queryset.' },
      { file: 'backend/apps/accounts/permissions.py', fn: 'HasPropertyAccess.has_object_permission(request, view, obj)', summary: 'Resolves obj → property_id, checks against access.py. Allows ADMIN shortcut; denies for SUPPLIER and TENANT on the wrong property.' },
      { file: 'backend/apps/accounts/permissions.py', fn: 'IsManagingAgentForProperty', summary: 'MANAGING_AGENT role + PropertyAgentAssignment(active=True, assignment_type="managing") OR Property.agent == user.' },
      { file: 'backend/apps/accounts/permissions.py', fn: 'IsOwnerOfProperty', summary: 'OWNER role + PropertyOwnership(is_current=True) reached via user.person_profile → Landlord → PropertyOwnership.' },
      { file: 'backend/apps/leases/views.py', fn: 'LeaseViewSet.get_queryset()', summary: 'TENANT → get_tenant_leases(user); ADMIN → Lease.objects.all(); else → leases where unit.property_id in accessible set.' },
      { file: 'backend/apps/esigning/views.py', fn: 'accessible_leases_queryset(user)', summary: 'Same shape as LeaseViewSet; used by every e-signing endpoint. OTP-gated public endpoints bypass this with VoltApiKeyAuthentication-style tokens.' },
      { file: 'backend/apps/maintenance/views.py', fn: 'MaintenanceRequestViewSet.get_queryset()', summary: 'TENANT → requests filed by user; non-ADMIN → requests on accessible properties; SUPPLIER → requests where supplier=user.supplier_profile.' },
      { file: 'backend/apps/the_volt/authentication.py', fn: 'VoltApiKeyAuthentication', summary: 'Subscriber API key → consented scope set. Does NOT grant role; grants time-bounded access to specific entities the data subject approved.' },
    ],
    // Common mistakes and what to review
    pitfalls: [
      { title: 'Never trust request.user.role alone', body: 'Role is necessary but not sufficient. An AGENT without an active PropertyAgentAssignment still has AGENT role — scope checks must combine role with assignment/ownership.' },
      { title: 'Owner ≠ Landlord', body: 'User.role="owner" is the auth identity. Landlord is a legal entity (person or company). Resolution chain: User → Person → Landlord → PropertyOwnership → Property. Break any link and the owner loses access.' },
      { title: 'Tenant scope is per-lease, not per-property', body: 'A person with two active leases sees both units independently. Shared household members are represented as additional Lease.co_tenants, not as owners of the primary record.' },
      { title: 'Accountant is read-only by design', body: 'Role exists specifically so bookkeepers can pull statements without the platform having to run a separate "export" path. Do not add write permissions even if convenient.' },
      { title: 'Viewer.module_access must be honoured', body: 'The VIEWER role carries a JSON field listing allowed modules (inspections, maintenance, properties). A viewer with only ["maintenance"] should get 403 on /api/v1/properties/ — not just a filtered list.' },
      { title: 'FICA separation', body: 'Owner FICA documents (CIPC, ID, proof of address) must never be visible to tenants — and tenant FICA never visible to owners. Both live in Vault33 with separate loan slips.' },
      { title: 'Supplier sees jobs, not properties', body: 'A supplier assigned to a maintenance request gets the address on that request and nothing else. They must not be able to list /api/v1/properties/ even if the API returns their own job list.' },
      { title: 'Agency admin ≠ super admin', body: 'AGENCY_ADMIN can create agents and manage properties within their agency. They cannot promote a user to ADMIN, cannot see other agencies, cannot change system config.' },
    ],
  };

  const cls = v => {
    if (v === 'F') return 'full';
    if (v === 'R') return 'read';
    if (v === '—') return 'none';
    if (v.startsWith('Rs')) return 'readscoped';
    if (v.startsWith('Cs') || v.startsWith('C')) return 'create';
    if (v.startsWith('F (')) return 'full';
    if (v.startsWith('U')) return 'update';
    return 'mixed';
  };

  const statCards = rbac.stats.map(([k,v,h]) => `
    <div class="rbac-stat"><div class="sk">${k}</div><div class="sv">${v}</div><div class="sh">${h}</div></div>
  `).join('');

  const roleCards = rbac.roles.map(r => `
    <div class="rbac-role bucket-${r.cls}">
      <div class="rr-head"><span class="rr-code">${r.code}</span><span class="rr-bucket">${r.bucket}</span></div>
      <h5>${r.label}</h5>
      <p>${r.scope}</p>
    </div>
  `).join('');

  // Build matrix — group resources, collapse by group
  const groups = [...new Set(rbac.resources.map(r => r.group))];
  const colHeads = rbac.matrixCols.map(c => {
    const role = rbac.roles.find(r => r.code === c);
    return `<th class="mc-${role.cls}"><span>${role.label}</span></th>`;
  }).join('');

  const matrixBody = groups.map(g => {
    const rows = rbac.resources.filter(r => r.group === g).map(r => {
      const cells = rbac.matrixCols.map(c => {
        const v = r.actions[c] || '—';
        return `<td class="m-${cls(v)}" title="${r.note || ''}"><code>${v}</code></td>`;
      }).join('');
      return `<tr><td class="mres">${r.resource}<div class="mnote">${r.note || ''}</div></td>${cells}</tr>`;
    }).join('');
    return `
      <tr class="mgroup"><td colspan="${rbac.matrixCols.length + 1}">${g}</td></tr>
      ${rows}
    `;
  }).join('');

  const enforcement = rbac.enforcement.map(e => `
    <div class="rbac-enf">
      <div class="re-file"><i class="ph ph-code"></i> <code>${e.file}</code></div>
      <div class="re-fn"><code>${e.fn}</code></div>
      <p>${e.summary}</p>
    </div>
  `).join('');

  const pitfalls = rbac.pitfalls.map(p => `
    <div class="rbac-pit">
      <h5><i class="ph ph-warning-circle"></i> ${p.title}</h5>
      <p>${p.body}</p>
    </div>
  `).join('');

  const legend = `
    <div class="rbac-legend">
      <span class="m-full"><code>F</code> full CRUD</span>
      <span class="m-read"><code>R</code> read all</span>
      <span class="m-readscoped"><code>Rs</code> read scoped</span>
      <span class="m-create"><code>Cs</code> create scoped</span>
      <span class="m-update"><code>U</code> update only</span>
      <span class="m-none"><code>—</code> no access</span>
    </div>
  `;

  return `
    <style>
      .rbac-tabs{position:sticky;top:0;z-index:10;background:#F5F5F8;padding:12px 0;display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #E5E5EC;margin-bottom:24px}
      .rbac-tabs a{padding:8px 14px;border-radius:20px;background:#fff;font-size:13px;font-weight:500;color:#595B8F;text-decoration:none;border:1px solid #E5E5EC;transition:all .2s}
      .rbac-tabs a.active{background:#2B2D6E;color:#fff;border-color:#2B2D6E}
      .rbac-sec{margin-bottom:48px;scroll-margin-top:72px}
      .rbac-sec h3{font-family:Fraunces,serif;font-weight:700;font-size:28px;margin:0 0 6px;color:#2B2D6E}
      .rbac-sec .sec-sub{color:#595B8F;font-size:14px;margin:0 0 20px}
      .rbac-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .rbac-stat{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px}
      .rbac-stat .sk{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8E90B8}
      .rbac-stat .sv{font-family:Fraunces,serif;font-weight:700;font-size:26px;color:#2B2D6E;line-height:1.1;margin:4px 0}
      .rbac-stat .sh{font-size:12px;color:#595B8F}
      .rbac-roles{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .rbac-role{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px;border-left:4px solid #8E90B8}
      .rbac-role.bucket-p{border-left-color:#2B2D6E}
      .rbac-role.bucket-a{border-left-color:#5B5DC7}
      .rbac-role.bucket-g{border-left-color:#22C55E}
      .rbac-role.bucket-f{border-left-color:#F59E0B}
      .rbac-role.bucket-e{border-left-color:#FF3D7F}
      .rbac-role .rr-head{display:flex;gap:8px;align-items:center;font-size:11px;margin-bottom:4px}
      .rbac-role .rr-code{font-family:ui-monospace,monospace;background:#F0F1F8;color:#595B8F;padding:2px 8px;border-radius:6px}
      .rbac-role .rr-bucket{color:#8E90B8;text-transform:uppercase;letter-spacing:.06em}
      .rbac-role h5{margin:2px 0 6px;font-size:15px;color:#2B2D6E}
      .rbac-role p{font-size:12px;color:#595B8F;line-height:1.55;margin:0}
      .rbac-legend{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px;font-size:12px;color:#595B8F}
      .rbac-legend span code{font-family:ui-monospace,monospace;padding:2px 6px;border-radius:4px;margin-right:4px}
      .rbac-legend .m-full code{background:#22C55E;color:#fff}
      .rbac-legend .m-read code{background:#5B5DC7;color:#fff}
      .rbac-legend .m-readscoped code{background:#C7C9F0;color:#2B2D6E}
      .rbac-legend .m-create code{background:#F59E0B;color:#fff}
      .rbac-legend .m-update code{background:#8B5CF6;color:#fff}
      .rbac-legend .m-none code{background:#F0F1F8;color:#8E90B8}
      .rbac-matrix-wrap{overflow-x:auto;border:1px solid #E5E5EC;border-radius:12px;background:#fff}
      .rbac-matrix{width:100%;border-collapse:collapse;font-size:12px;min-width:1100px}
      .rbac-matrix th{background:#F5F5F8;padding:8px 6px;border-bottom:1px solid #E5E5EC;color:#2B2D6E;font-weight:600;text-align:center;white-space:nowrap;position:sticky;top:0}
      .rbac-matrix th:first-child{text-align:left;padding-left:14px;min-width:220px}
      .rbac-matrix th.mc-p{background:#EEE8FF}
      .rbac-matrix th.mc-a{background:#E7EAF9}
      .rbac-matrix th.mc-g{background:#E6F8EE}
      .rbac-matrix th.mc-f{background:#FDF4E0}
      .rbac-matrix th.mc-e{background:#FFE8F1}
      .rbac-matrix td{padding:6px;border-bottom:1px solid #F0F1F8;text-align:center;vertical-align:middle}
      .rbac-matrix td.mres{text-align:left;padding:8px 14px;color:#2B2D6E;font-weight:500;background:#FBFBFD;min-width:220px}
      .rbac-matrix td.mres .mnote{font-size:10px;color:#8E90B8;font-weight:400;margin-top:2px;line-height:1.4}
      .rbac-matrix tr.mgroup td{background:#2B2D6E;color:#fff;text-align:left;padding:6px 14px;font-size:11px;text-transform:uppercase;letter-spacing:.08em;font-weight:600}
      .rbac-matrix td code{font-family:ui-monospace,monospace;font-size:11px;padding:2px 6px;border-radius:4px;display:inline-block;min-width:26px}
      .rbac-matrix td.m-full code{background:#22C55E;color:#fff}
      .rbac-matrix td.m-read code{background:#5B5DC7;color:#fff}
      .rbac-matrix td.m-readscoped code{background:#C7C9F0;color:#2B2D6E}
      .rbac-matrix td.m-create code{background:#F59E0B;color:#fff}
      .rbac-matrix td.m-update code{background:#8B5CF6;color:#fff}
      .rbac-matrix td.m-none code{background:#F0F1F8;color:#8E90B8}
      .rbac-matrix td.m-mixed code{background:#E5E5EC;color:#2B2D6E}
      .rbac-enfs{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .rbac-enf{background:#fff;border:1px solid #E5E5EC;border-radius:10px;padding:14px}
      .rbac-enf .re-file{font-size:11px;color:#8E90B8;display:flex;align-items:center;gap:6px;margin-bottom:4px}
      .rbac-enf .re-file code{background:none;color:#595B8F;font-family:ui-monospace,monospace}
      .rbac-enf .re-fn code{background:#F0F1F8;color:#2B2D6E;font-family:ui-monospace,monospace;padding:3px 8px;border-radius:6px;font-size:12px}
      .rbac-enf p{font-size:12.5px;color:#595B8F;line-height:1.55;margin:8px 0 0}
      .rbac-pits{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .rbac-pit{background:#FFF8F2;border:1px solid #F5D7C0;border-radius:10px;padding:14px}
      .rbac-pit h5{margin:0 0 4px;color:#8B4A1F;font-size:14px;display:flex;align-items:center;gap:6px}
      .rbac-pit p{margin:0;font-size:12.5px;color:#6B5236;line-height:1.55}
      @media (max-width:900px){.rbac-stats{grid-template-columns:1fr 1fr}.rbac-roles,.rbac-enfs,.rbac-pits{grid-template-columns:1fr}}
    </style>

    <nav class="rbac-tabs">
      <a href="#rbac-stats" class="active" data-t="stats">At a glance</a>
      <a href="#rbac-roles" data-t="roles">Roles</a>
      <a href="#rbac-matrix" data-t="matrix">Matrix</a>
      <a href="#rbac-enforcement" data-t="enforcement">Enforcement</a>
      <a href="#rbac-pitfalls" data-t="pitfalls">Pitfalls</a>
    </nav>

    <section id="rbac-stats" class="rbac-sec">
      <h3>At a glance</h3>
      <p class="sec-sub">Role-based access control for Klikk. Ten roles, sixteen permission classes, one central property-access resolver.</p>
      <div class="rbac-stats">${statCards}</div>
    </section>

    <section id="rbac-roles" class="rbac-sec">
      <h3>Roles</h3>
      <p class="sec-sub">User.role choices on the User model. Each role carries a default scope; object-level permissions narrow it further.</p>
      <div class="rbac-roles">${roleCards}</div>
    </section>

    <section id="rbac-matrix" class="rbac-sec">
      <h3>Matrix</h3>
      <p class="sec-sub">Roles across the top, resources down the left. Read horizontally to see who can do what to what. Hover a cell for the scoping rule.</p>
      ${legend}
      <div class="rbac-matrix-wrap">
        <table class="rbac-matrix">
          <thead><tr><th>Resource</th>${colHeads}</tr></thead>
          <tbody>${matrixBody}</tbody>
        </table>
      </div>
    </section>

    <section id="rbac-enforcement" class="rbac-sec">
      <h3>Enforcement</h3>
      <p class="sec-sub">How the matrix gets enforced in code. One access resolver + three object guards + per-ViewSet queryset filtering.</p>
      <div class="rbac-enfs">${enforcement}</div>
    </section>

    <section id="rbac-pitfalls" class="rbac-sec">
      <h3>Pitfalls</h3>
      <p class="sec-sub">Common mistakes and what to review when adding a new role, endpoint, or resource.</p>
      <div class="rbac-pits">${pitfalls}</div>
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.rbac-tabs a');
        const secs = [...tabs].map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
        tabs.forEach(t => t.addEventListener('click', e => {
          tabs.forEach(x => x.classList.remove('active'));
          t.classList.add('active');
        }));
        function onScroll(){
          const y = window.scrollY + 120;
          let active = secs[0];
          for (const s of secs) { if (s.offsetTop <= y) active = s; }
          tabs.forEach(t => {
            t.classList.toggle('active', t.getAttribute('href') === '#' + active.id);
          });
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- Business rules (state machines, invariants, gates) ---------- */
function pageRules() {
  const rules = {
    stats: [
      ['State machines', '8',   'Lease, LeaseBuilderSession, Unit, RentalMandate, ESigningSubmission, MaintenanceRequest, JobDispatch, JobQuoteRequest'],
      ['Signal handlers','11',  'post_save / post_delete wiring across leases, properties, maintenance, esigning'],
      ['Invariants',     '6',   'Occupancy, notice, e-sign link expiry, lease auto-activation, unit sync, mandate sync'],
      ['RHA gaps',       '3',   'Deposit refund windows, interest accrual, PIE Act — not yet enforced in code'],
      ['Config keys',    '~12', 'Defaults on Lease (water, prepaid) and RentalMandate (notice, threshold)'],
      ['Cron / Celery',  '0',   'Background work uses threading + transaction.on_commit — no scheduled jobs yet'],
    ],
    // State machines — each with states, transitions, and the code path that enforces them
    machines: [
      {
        name: 'Lease',
        path: 'apps/leases/models.py · Status',
        states: [
          { code: 'pending',    label: 'Pending',    desc: 'Created but not yet countersigned. Does NOT occupy a unit.', colour: 'amber' },
          { code: 'active',     label: 'Active',     desc: 'All parties signed. Unit is occupied. Rent invoices fire.',  colour: 'green' },
          { code: 'expired',    label: 'Expired',    desc: 'end_date passed without renewal.',                            colour: 'slate' },
          { code: 'terminated', label: 'Terminated', desc: 'Manually cancelled. Does NOT occupy a unit.',                 colour: 'red'   },
        ],
        transitions: [
          { from: 'pending',    to: 'active',     trigger: 'esigning webhook — all signers complete',  code: 'apps/esigning/webhooks.py:_activate_lease', auto: true },
          { from: 'active',     to: 'expired',    trigger: 'end_date reached OR manual',               code: 'manual / batch (TBD)', auto: false },
          { from: 'pending',    to: 'terminated', trigger: 'staff cancel before signing',              code: 'manual', auto: false },
          { from: 'active',     to: 'terminated', trigger: 'staff early termination',                  code: 'manual', auto: false },
        ],
      },
      {
        name: 'LeaseBuilderSession',
        path: 'apps/leases/models.py · Status',
        states: [
          { code: 'drafting',  label: 'Drafting',  desc: 'AI chat session in progress.',       colour: 'amber' },
          { code: 'review',    label: 'Review',    desc: 'Agent reviewing proposed document.', colour: 'blue'  },
          { code: 'finalized', label: 'Finalized', desc: 'Lease created from session.',        colour: 'green' },
        ],
        transitions: [
          { from: 'drafting', to: 'review',    trigger: 'agent clicks "review draft"',      code: 'manual', auto: false },
          { from: 'review',   to: 'finalized', trigger: 'agent clicks "create lease"',      code: 'apps/leases/builder.py', auto: false },
        ],
      },
      {
        name: 'Unit',
        path: 'apps/properties/models.py · Status',
        states: [
          { code: 'available',   label: 'Available',   desc: 'Ready to lease. Visible on listings.',      colour: 'green' },
          { code: 'occupied',    label: 'Occupied',    desc: 'At least one ACTIVE lease exists.',         colour: 'blue'  },
          { code: 'maintenance', label: 'Maintenance', desc: 'Taken offline. Not listable.',              colour: 'amber' },
        ],
        transitions: [
          { from: 'available',   to: 'occupied',    trigger: 'Lease becomes active → signal recomputes', code: 'apps/leases/signals.py:_resync_unit_status', auto: true },
          { from: 'occupied',    to: 'available',   trigger: 'last active lease ends → recompute',        code: 'apps/leases/signals.py:_resync_unit_status', auto: true },
          { from: 'any',         to: 'maintenance', trigger: 'staff toggle during turnaround',            code: 'manual', auto: false },
          { from: 'maintenance', to: 'available',   trigger: 'staff clears maintenance flag',             code: 'manual', auto: false },
        ],
      },
      {
        name: 'RentalMandate',
        path: 'apps/properties/models.py · Status',
        states: [
          { code: 'draft',             label: 'Draft',             desc: 'Being composed.',                       colour: 'slate' },
          { code: 'sent',              label: 'Sent',              desc: 'Link emailed, awaiting first signer.',  colour: 'amber' },
          { code: 'partially_signed',  label: 'Partially signed',  desc: 'At least one party signed.',            colour: 'blue'  },
          { code: 'active',            label: 'Active',            desc: 'All parties signed. Mandate in effect.',colour: 'green' },
          { code: 'expired',           label: 'Expired',           desc: 'end_date reached.',                     colour: 'slate' },
          { code: 'cancelled',         label: 'Cancelled',         desc: 'Withdrawn or declined.',                colour: 'red'   },
        ],
        transitions: [
          { from: 'draft',            to: 'sent',             trigger: 'staff sends for signing',          code: 'manual', auto: false },
          { from: 'sent',             to: 'partially_signed', trigger: 'first signer completes',           code: 'apps/esigning/models.py:sync_mandate_status', auto: true },
          { from: 'partially_signed', to: 'active',           trigger: 'all signers complete',             code: 'apps/esigning/models.py:sync_mandate_status', auto: true },
          { from: 'any',              to: 'cancelled',        trigger: 'any signer declines',              code: 'apps/esigning/models.py:sync_mandate_status', auto: true },
          { from: 'active',           to: 'expired',          trigger: 'end_date reached',                 code: 'manual / batch (TBD)', auto: false },
        ],
      },
      {
        name: 'ESigningSubmission',
        path: 'apps/esigning/models.py · Status',
        states: [
          { code: 'pending',     label: 'Pending',     desc: 'Link sent, no signer has opened it.', colour: 'slate' },
          { code: 'in_progress', label: 'In progress', desc: 'At least one signer has opened.',     colour: 'amber' },
          { code: 'completed',   label: 'Completed',   desc: 'All signers done.',                   colour: 'green' },
          { code: 'declined',    label: 'Declined',    desc: 'A signer declined.',                  colour: 'red'   },
          { code: 'expired',     label: 'Expired',     desc: 'Public link passed ESIGNING_PUBLIC_LINK_EXPIRY_DAYS (default 14).', colour: 'slate' },
        ],
        transitions: [
          { from: 'pending',     to: 'in_progress', trigger: 'first signer accesses link', code: 'apps/esigning/views.py (public)', auto: true },
          { from: 'in_progress', to: 'completed',   trigger: 'final signer signs (sequential) OR all signers done (parallel)', code: 'apps/esigning/webhooks.py', auto: true },
          { from: 'any',         to: 'declined',    trigger: 'any signer clicks decline',   code: 'apps/esigning/webhooks.py', auto: true },
          { from: 'pending',     to: 'expired',     trigger: 'link TTL reached unsigned',   code: 'apps/esigning/tasks.py (TBD)', auto: true },
        ],
      },
      {
        name: 'MaintenanceRequest',
        path: 'apps/maintenance/models.py · Status',
        states: [
          { code: 'open',        label: 'Open',        desc: 'Tenant or agent has filed it.',       colour: 'amber' },
          { code: 'in_progress', label: 'In progress', desc: 'Supplier dispatched, work underway.', colour: 'blue'  },
          { code: 'resolved',    label: 'Resolved',    desc: 'Work completed, awaiting close-out.', colour: 'green' },
          { code: 'closed',      label: 'Closed',      desc: 'Tenant confirmed or auto-closed.',    colour: 'slate' },
        ],
        transitions: [
          { from: 'open',        to: 'in_progress', trigger: 'supplier awarded + dispatch accepted', code: 'manual (agent)', auto: false },
          { from: 'in_progress', to: 'resolved',    trigger: 'supplier marks complete',              code: 'manual (supplier)', auto: false },
          { from: 'resolved',    to: 'closed',      trigger: 'tenant confirms OR auto-close timer',  code: 'manual / TBD', auto: false },
        ],
      },
      {
        name: 'JobDispatch',
        path: 'apps/maintenance/models.py · Status',
        states: [
          { code: 'draft',     label: 'Draft',     desc: 'Being composed.',              colour: 'slate' },
          { code: 'sent',      label: 'Sent',      desc: 'Emailed/WhatsApp\'d to suppliers.', colour: 'amber' },
          { code: 'quoting',   label: 'Quoting',   desc: 'At least one quote received.',  colour: 'blue'  },
          { code: 'awarded',   label: 'Awarded',   desc: 'Agent picked a supplier.',     colour: 'green' },
          { code: 'cancelled', label: 'Cancelled', desc: 'Dispatch withdrawn.',          colour: 'red'   },
        ],
        transitions: [
          { from: 'draft',   to: 'sent',      trigger: 'staff sends dispatch',     code: 'manual', auto: false },
          { from: 'sent',    to: 'quoting',   trigger: 'first quote received',     code: 'apps/maintenance/services.py', auto: true },
          { from: 'quoting', to: 'awarded',   trigger: 'staff awards a quote',     code: 'manual', auto: false },
          { from: 'any',     to: 'cancelled', trigger: 'staff cancels',            code: 'manual', auto: false },
        ],
      },
      {
        name: 'JobQuoteRequest',
        path: 'apps/maintenance/models.py · Status',
        states: [
          { code: 'pending',  label: 'Pending',  desc: 'Sent, not viewed.',         colour: 'slate' },
          { code: 'viewed',   label: 'Viewed',   desc: 'Supplier opened the link.', colour: 'amber' },
          { code: 'quoted',   label: 'Quoted',   desc: 'Supplier posted a quote.',  colour: 'blue'  },
          { code: 'awarded',  label: 'Awarded',  desc: 'Staff picked this quote.',  colour: 'green' },
          { code: 'declined', label: 'Declined', desc: 'Supplier declined.',        colour: 'red'   },
          { code: 'expired',  label: 'Expired',  desc: 'Deadline passed.',          colour: 'slate' },
        ],
        transitions: [
          { from: 'pending', to: 'viewed',   trigger: 'supplier opens link',     code: 'apps/maintenance/views.py (public)', auto: true },
          { from: 'viewed',  to: 'quoted',   trigger: 'supplier posts quote',    code: 'apps/maintenance/views.py', auto: false },
          { from: 'quoted',  to: 'awarded',  trigger: 'staff awards',            code: 'apps/maintenance/services.py', auto: false },
          { from: 'any',     to: 'declined', trigger: 'supplier declines',       code: 'manual', auto: false },
          { from: 'pending', to: 'expired',  trigger: 'deadline passed',         code: 'TBD (cron)', auto: true },
        ],
      },
    ],
    // Signal-driven business rules — the mechanism that enforces invariants
    signals: [
      { file: 'apps/leases/signals.py',       handler: '_resync_unit_status',        signal: 'post_save(Lease), post_delete(Lease)', effect: 'Recomputes Unit.status. Only status=active counts. Keeps unit availability in lockstep with lease lifecycle.' },
      { file: 'apps/leases/signals.py',       handler: 'broadcast_lease_update',     signal: 'post_save(Lease)',                      effect: 'WebSocket push to lease_updates channel — admin UI refreshes live.' },
      { file: 'apps/esigning/models.py',      handler: 'sync_mandate_status',        signal: 'post_save(ESigningSubmission)',         effect: 'Mirrors submission status into the parent RentalMandate. Keeps the legal doc status in sync with the signing artifact.' },
      { file: 'apps/esigning/webhooks.py',    handler: '_activate_lease',            signal: 'esigning completion webhook',           effect: 'Flips Lease.status PENDING → ACTIVE when all signers done. One-way, idempotent, skips leases not in PENDING.' },
      { file: 'apps/properties/signals.py',   handler: 'enqueue_owner_rag_ingestion',signal: 'post_save(Landlord), post_save(LandlordDocument)', effect: 'Background thread re-embeds owner docs into RAG. Idempotent: deletes old chunks before re-ingesting.' },
      { file: 'apps/properties/signals.py',   handler: 'enqueue_property_information_ingestion', signal: 'post_save(Property)',        effect: 'Re-ingests property.information_items into landlord notes RAG. Prunes removed items.' },
      { file: 'apps/maintenance/signals.py',  handler: 'ingest_answered_question',   signal: 'post_save(AgentQuestion) where status=ANSWERED', effect: 'Answered Q&A → agent_qa RAG. Auto-sets added_to_context=True.' },
      { file: 'apps/maintenance/signals.py',  handler: 'vectorize_maintenance_issue',signal: 'post_save(MaintenanceRequest)',         effect: 'Auto-indexes issue into similarity RAG for AI triage.' },
      { file: 'apps/maintenance/signals.py',  handler: 'write_activity_log',         signal: 'post_save(MaintenanceActivity)',        effect: 'Append-only JSONL log + WebSocket broadcast to maintenance_updates.' },
    ],
    // Invariants — hard rules that hold at all times
    invariants: [
      { title: 'Only active leases occupy a unit',                    rule: 'Unit.status = OCCUPIED iff ∃ Lease where unit=self AND status=active. PENDING, EXPIRED, TERMINATED never count.', code: 'apps/leases/signals.py:_resync_unit_status', why: 'Double-booking a unit with an unsigned future lease would show it as "occupied" in search — the pre-tenancy lifecycle phase (stages 1–7) happens while the unit IS still occupied by the current tenant, so PENDING leases must not displace them.' },
      { title: 'Lease auto-activates on full e-signing',              rule: 'Lease.status PENDING → ACTIVE happens exactly once, when the final signer completes. Idempotent: subsequent webhooks are no-ops.',                                    code: 'apps/esigning/webhooks.py:_activate_lease', why: 'Agents should never manually flip to active — the audit trail must show the transition was triggered by the signed artifact, not a human click.' },
      { title: 'Mandate status mirrors its e-signing submission',     rule: 'When ESigningSubmission transitions, the parent RentalMandate mirrors it: completed→active, declined→cancelled, in_progress→partially_signed.',                     code: 'apps/esigning/models.py:sync_mandate_status',  why: 'The mandate is the legal document; the submission is the vehicle. Desynchronised statuses have caused disputes in the past.' },
      { title: 'E-signing links expire',                              rule: 'Public signing links expire after ESIGNING_PUBLIC_LINK_EXPIRY_DAYS (default 14). Expired links cannot be signed even if the recipient kept the email.',            code: 'settings + apps/esigning/tasks.py (TBD)',      why: 'POPIA s14 retention minimisation. Links carry tenant PII in the rendered form — must not live forever.' },
      { title: 'Lease chains via previous_lease',                     rule: 'Renewals point their previous_lease FK at the prior lease. renewal_start_date marks the addendum boundary.',                                                        code: 'apps/leases/models.py:Lease',                  why: 'Enables continuous tenancy view, tenure calculations, and "show me the original lease for this tenant" queries.' },
      { title: 'Owner RAG is content-addressed',                      rule: 'Re-ingestion deletes old chunks keyed by (landlord_id, document_id) before inserting new ones — prevents stale embeddings bleeding into AI responses.',               code: 'apps/properties/tasks.py:ingest_owner_documents', why: 'Without this, an owner who re-uploads a corrected ID document would still surface the old version in agent-assist.' },
    ],
    // Config / defaults — the knobs that tune the machines
    config: [
      { area: 'Lease',          key: 'monthly_rent',                   default: '(required)', type: 'Decimal(10,2)', notes: 'Per-lease ZAR. No platform-level min/max.' },
      { area: 'Lease',          key: 'deposit',                        default: '(required)', type: 'Decimal(10,2)', notes: 'No enforced multiple of rent (RHA does not cap).' },
      { area: 'Lease',          key: 'rent_due_day',                   default: '1',           type: 'int 1–28',      notes: 'Day of month for invoice generation.' },
      { area: 'Lease',          key: 'notice_period_days',             default: '20',          type: 'int',           notes: 'Per-lease override. RHA floor is 20 business days / ~1 calendar month.' },
      { area: 'Lease',          key: 'water_included',                 default: 'True',        type: 'bool',          notes: 'Flip to False for sub-metered units.' },
      { area: 'Lease',          key: 'electricity_prepaid',            default: 'True',        type: 'bool',          notes: 'Default assumes unit has a prepaid meter.' },
      { area: 'Lease',          key: 'water_limit_litres',             default: '4000',        type: 'int',           notes: 'Soft cap; over-use billed back.' },
      { area: 'Mandate',        key: 'notice_period_days',             default: '60',          type: 'int',           notes: 'Term for owner to terminate the mandate itself.' },
      { area: 'Mandate',        key: 'maintenance_threshold',          default: '2000',        type: 'Decimal',       notes: 'ZAR cap an agent may approve without owner sign-off (Full Management only).' },
      { area: 'E-signing',      key: 'ESIGNING_PUBLIC_LINK_EXPIRY_DAYS',default:'14',          type: 'int (setting)', notes: 'Public signing link TTL.' },
      { area: 'FICA (owner)',   key: 'PROOF_OF_ADDRESS_WARN_DAYS',     default: '90',          type: 'int',           notes: 'Warning banner threshold for stale proof of address.' },
      { area: 'FICA (owner)',   key: 'PROOF_OF_ADDRESS_BLOCK_DAYS',    default: '180',         type: 'int',           notes: 'Blocks new mandates after this.' },
    ],
    // RHA + POPIA compliance gates not yet in code — the TODO list
    gaps: [
      { title: 'Deposit refund windows (RHA s5(3)(i)–(l))',            risk: 'high',   summary: 'Tribunal-level exposure. 7 days (no dispute), 14 days (with deductions), 21 days (if tenant disputes). Must auto-calendar at lease end.', action: 'Add DepositRefund model with lease FK, status machine (pending→paid / disputed), deadline field computed from lease_end_date + window. Cron job to fire warnings at day −3.' },
      { title: 'Deposit interest accrual',                             risk: 'medium', summary: 'RHA s5(3)(c) requires interest earned on the deposit to be paid to the tenant. Currently no ledger.',                                       action: 'Nightly job to pull interest rates per bank, accrue daily, surface on tenant statement. Keep interest ledger separate from rent ledger.' },
      { title: 'PIE Act eviction gate',                                risk: 'high',   summary: 'Prevention of Illegal Eviction from Unlawful Occupation of Land Act. Platform must block any "lock out / change locks" style action without a court order.', action: 'Add evictions module with explicit court-order upload step before any key-return / lockout workflow can proceed. Log refusals as compliance events.' },
      { title: 'Scheduled jobs',                                       risk: 'medium', summary: 'No Celery or cron. Everything uses threading + transaction.on_commit — fine for inline work, inadequate for deposit deadlines, rent invoice generation, and lease expiry sweeps.', action: 'Stand up django-q or Celery beat. First three jobs: daily rent invoicing, lease-expiry 90/60/30/7 day notifications, deposit-refund deadline warnings.' },
      { title: 'Lease expiry sweep',                                   risk: 'low',    summary: 'Lease.status → expired not automated; stays "active" past end_date until someone edits it.',                                                 action: 'Add nightly job that flips status to expired for leases past end_date. Fires Unit.status recompute via existing signal.' },
      { title: 'E-signing link expiry sweep',                          risk: 'medium', summary: 'Expired flag is designed for but no worker flips it. Status lingers as pending forever.',                                                    action: 'Nightly job scanning ESigningSubmission.created_at + TTL. Flip to expired and revoke token.' },
      { title: 'Audit log / immutable ledger',                         risk: 'medium', summary: 'Maintenance has MaintenanceActivity. Lease lifecycle, mandate, and deposit events have no append-only log — disputes can\'t be reconstructed.', action: 'Add LifecycleEvent model (generic FK + actor + before/after JSON). Write from signals alongside existing handlers.' },
    ],
  };

  const statCards = rules.stats.map(([k,v,h]) => `
    <div class="br-stat"><div class="sk">${k}</div><div class="sv">${v}</div><div class="sh">${h}</div></div>
  `).join('');

  const machineCards = rules.machines.map(m => {
    const states = m.states.map(s => `
      <div class="st st-${s.colour}">
        <div class="st-code">${s.code}</div>
        <div class="st-label">${s.label}</div>
        <div class="st-desc">${s.desc}</div>
      </div>
    `).join('');
    const transitions = m.transitions.map(t => `
      <tr>
        <td><code>${t.from}</code></td>
        <td class="tr-arrow">→</td>
        <td><code>${t.to}</code></td>
        <td>${t.trigger}</td>
        <td><span class="tr-auto ${t.auto ? 'auto' : 'man'}">${t.auto ? 'auto' : 'manual'}</span></td>
        <td><code class="tr-code">${t.code}</code></td>
      </tr>
    `).join('');
    return `
      <details class="br-machine" open>
        <summary>
          <span class="m-name">${m.name}</span>
          <span class="m-path">${m.path}</span>
          <span class="m-count">${m.states.length} states · ${m.transitions.length} transitions</span>
        </summary>
        <div class="m-states">${states}</div>
        <table class="m-trans">
          <thead><tr><th>From</th><th></th><th>To</th><th>Trigger</th><th>Mode</th><th>Code</th></tr></thead>
          <tbody>${transitions}</tbody>
        </table>
      </details>
    `;
  }).join('');

  const signalRows = rules.signals.map(s => `
    <tr>
      <td><code>${s.file}</code></td>
      <td><code class="sig-h">${s.handler}</code></td>
      <td>${s.signal}</td>
      <td>${s.effect}</td>
    </tr>
  `).join('');

  const invariants = rules.invariants.map(i => `
    <div class="br-inv">
      <h5><i class="ph ph-shield-check"></i> ${i.title}</h5>
      <div class="inv-rule"><strong>Rule.</strong> ${i.rule}</div>
      <div class="inv-code"><strong>Code.</strong> <code>${i.code}</code></div>
      <div class="inv-why"><strong>Why.</strong> ${i.why}</div>
    </div>
  `).join('');

  const configRows = rules.config.map(c => `
    <tr>
      <td><span class="cfg-area">${c.area}</span></td>
      <td><code>${c.key}</code></td>
      <td><code class="cfg-default">${c.default}</code></td>
      <td><code>${c.type}</code></td>
      <td>${c.notes}</td>
    </tr>
  `).join('');

  const gaps = rules.gaps.map(g => `
    <div class="br-gap risk-${g.risk}">
      <div class="g-head">
        <h5>${g.title}</h5>
        <span class="g-risk">${g.risk} risk</span>
      </div>
      <p class="g-sum">${g.summary}</p>
      <p class="g-act"><strong>Action.</strong> ${g.action}</p>
    </div>
  `).join('');

  return `
    <style>
      .br-tabs{position:sticky;top:0;z-index:10;background:#F5F5F8;padding:12px 0;display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #E5E5EC;margin-bottom:24px}
      .br-tabs a{padding:8px 14px;border-radius:20px;background:#fff;font-size:13px;font-weight:500;color:#595B8F;text-decoration:none;border:1px solid #E5E5EC}
      .br-tabs a.active{background:#2B2D6E;color:#fff;border-color:#2B2D6E}
      .br-sec{margin-bottom:48px;scroll-margin-top:72px}
      .br-sec h3{font-family:Fraunces,serif;font-weight:700;font-size:28px;margin:0 0 6px;color:#2B2D6E}
      .br-sec .sec-sub{color:#595B8F;font-size:14px;margin:0 0 20px}
      .br-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .br-stat{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px}
      .br-stat .sk{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8E90B8}
      .br-stat .sv{font-family:Fraunces,serif;font-weight:700;font-size:26px;color:#2B2D6E;line-height:1.1;margin:4px 0}
      .br-stat .sh{font-size:12px;color:#595B8F}
      .br-machine{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px 18px;margin-bottom:14px}
      .br-machine summary{cursor:pointer;display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;list-style:none}
      .br-machine summary::-webkit-details-marker{display:none}
      .br-machine .m-name{font-family:Fraunces,serif;font-weight:700;font-size:20px;color:#2B2D6E}
      .br-machine .m-path{font-family:ui-monospace,monospace;font-size:11px;color:#8E90B8}
      .br-machine .m-count{font-size:11px;color:#595B8F;margin-left:auto}
      .m-states{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin:14px 0}
      .st{padding:10px;border-radius:8px;border:1px solid #E5E5EC;background:#FBFBFD;border-left:4px solid #8E90B8}
      .st.st-green{border-left-color:#22C55E}
      .st.st-amber{border-left-color:#F59E0B}
      .st.st-blue{border-left-color:#5B5DC7}
      .st.st-red{border-left-color:#EF4444}
      .st.st-slate{border-left-color:#8E90B8}
      .st .st-code{font-family:ui-monospace,monospace;font-size:11px;color:#595B8F}
      .st .st-label{font-weight:600;color:#2B2D6E;font-size:13px;margin:2px 0}
      .st .st-desc{font-size:11.5px;color:#595B8F;line-height:1.5}
      .m-trans{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
      .m-trans th{background:#F5F5F8;padding:6px 10px;text-align:left;color:#595B8F;font-weight:500;border-bottom:1px solid #E5E5EC;font-size:11px;text-transform:uppercase;letter-spacing:.06em}
      .m-trans td{padding:8px 10px;border-bottom:1px solid #F0F1F8;vertical-align:top}
      .m-trans code{font-family:ui-monospace,monospace;font-size:11.5px;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px}
      .m-trans .tr-arrow{color:#8E90B8;text-align:center}
      .m-trans .tr-code{background:none;color:#8E90B8;padding:0;font-size:11px}
      .tr-auto{font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:2px 8px;border-radius:6px;font-weight:600}
      .tr-auto.auto{background:#E6F8EE;color:#166534}
      .tr-auto.man{background:#FDF4E0;color:#8B4A1F}
      .br-sigs{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .br-sigs th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .br-sigs td{padding:10px 12px;border-top:1px solid #F0F1F8;vertical-align:top;color:#2B2D6E}
      .br-sigs code{font-family:ui-monospace,monospace;font-size:11.5px;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px}
      .br-sigs .sig-h{background:#EEE8FF;color:#2B2D6E}
      .br-invs{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .br-inv{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px;border-left:4px solid #2B2D6E}
      .br-inv h5{margin:0 0 8px;font-size:14px;color:#2B2D6E;display:flex;align-items:center;gap:6px}
      .br-inv .inv-rule,.br-inv .inv-code,.br-inv .inv-why{font-size:12.5px;color:#595B8F;line-height:1.6;margin:4px 0}
      .br-inv code{font-family:ui-monospace,monospace;font-size:11.5px;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px}
      .br-cfg{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .br-cfg th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .br-cfg td{padding:8px 12px;border-top:1px solid #F0F1F8;color:#2B2D6E}
      .br-cfg code{font-family:ui-monospace,monospace;font-size:11.5px;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px}
      .br-cfg .cfg-area{font-size:10px;text-transform:uppercase;letter-spacing:.06em;background:#EEE8FF;color:#2B2D6E;padding:2px 8px;border-radius:6px}
      .br-cfg .cfg-default{background:#E6F8EE;color:#166534}
      .br-gaps{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .br-gap{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px}
      .br-gap.risk-high{background:#FFF1F1;border-color:#F5C8C8}
      .br-gap.risk-medium{background:#FFF8F2;border-color:#F5D7C0}
      .br-gap.risk-low{background:#F5F5F8;border-color:#E5E5EC}
      .br-gap .g-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
      .br-gap h5{margin:0;font-size:14px;color:#2B2D6E}
      .br-gap .g-risk{font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:2px 8px;border-radius:6px;font-weight:600}
      .br-gap.risk-high .g-risk{background:#EF4444;color:#fff}
      .br-gap.risk-medium .g-risk{background:#F59E0B;color:#fff}
      .br-gap.risk-low .g-risk{background:#8E90B8;color:#fff}
      .br-gap p{font-size:12.5px;color:#595B8F;line-height:1.6;margin:4px 0}
      .br-gap .g-act{color:#2B2D6E}
      @media (max-width:900px){.br-stats{grid-template-columns:1fr 1fr}.br-invs,.br-gaps{grid-template-columns:1fr}}
    </style>

    <nav class="br-tabs">
      <a href="#br-stats" class="active">At a glance</a>
      <a href="#br-machines">State machines</a>
      <a href="#br-signals">Signals</a>
      <a href="#br-invariants">Invariants</a>
      <a href="#br-config">Config</a>
      <a href="#br-gaps">Gaps</a>
    </nav>

    <section id="br-stats" class="br-sec">
      <h3>At a glance</h3>
      <p class="sec-sub">The business logic that stitches the platform together. Eight state machines, eleven signal handlers, six invariants, and seven known gaps that will land before RHA audit readiness.</p>
      <div class="br-stats">${statCards}</div>
    </section>

    <section id="br-machines" class="br-sec">
      <h3>State machines</h3>
      <p class="sec-sub">Every model that has a Status enum, its permitted states, and the code path that performs each transition. "auto" transitions must never be triggered manually — the audit trail depends on them firing from the signal or webhook.</p>
      ${machineCards}
    </section>

    <section id="br-signals" class="br-sec">
      <h3>Signals</h3>
      <p class="sec-sub">Where the invariants actually get enforced. Every handler here has a precondition and an effect — review all of them before touching the underlying models.</p>
      <table class="br-sigs">
        <thead><tr><th>File</th><th>Handler</th><th>Signal</th><th>Effect</th></tr></thead>
        <tbody>${signalRows}</tbody>
      </table>
    </section>

    <section id="br-invariants" class="br-sec">
      <h3>Invariants</h3>
      <p class="sec-sub">Hard rules that must hold after every transaction. Phrase them as assertions; they are the tests a future refactor must preserve.</p>
      <div class="br-invs">${invariants}</div>
    </section>

    <section id="br-config" class="br-sec">
      <h3>Config</h3>
      <p class="sec-sub">Per-model defaults and platform settings. Any number that matters to the business belongs here — not in view code.</p>
      <table class="br-cfg">
        <thead><tr><th>Area</th><th>Key</th><th>Default</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>${configRows}</tbody>
      </table>
    </section>

    <section id="br-gaps" class="br-sec">
      <h3>Gaps</h3>
      <p class="sec-sub">Rules the platform <em>should</em> enforce but doesn't yet. Seven items. Three are RHA Tribunal risk; four are engineering debt.</p>
      <div class="br-gaps">${gaps}</div>
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.br-tabs a');
        const secs = [...tabs].map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
        tabs.forEach(t => t.addEventListener('click', () => {
          tabs.forEach(x => x.classList.remove('active'));
          t.classList.add('active');
        }));
        function onScroll(){
          const y = window.scrollY + 120;
          let active = secs[0];
          for (const s of secs) { if (s.offsetTop <= y) active = s; }
          tabs.forEach(t => {
            t.classList.toggle('active', t.getAttribute('href') === '#' + active.id);
          });
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- Integrations (third-party services + POPIA flags) ---------- */
function pageIntegrations() {
  const integ = {
    stats: [
      ['Services',        '22',   'Live, configurable, and planned'],
      ['Cross-border',    '5',    'Anthropic, Twilio, Google Maps, Weaviate Cloud (optional), Firebase (planned) — POPIA s72 applies'],
      ['RSA-local',       '3',    'Property24 scraper, PrivateProperty scraper, Gotenberg (self-hosted)'],
      ['Not yet wired',   '6',    'TransUnion, Deeds Office, Lightstone, payment gateway, Redis, Firebase push'],
      ['Primary AI',      'Claude Sonnet 4.6', 'Anthropic. No fallback provider; graceful-degrade if key missing.'],
      ['eSigning',        'Native', 'DocuSeal removed April 2026. Gotenberg + Fernet-signed PDFs only.'],
    ],
    // Grouped by category — each with a colour bucket
    categories: [
      { key: 'ai',        label: 'AI & embeddings',       colour: 'violet' },
      { key: 'pdf',       label: 'PDF & documents',       colour: 'blue'   },
      { key: 'storage',   label: 'Storage & database',    colour: 'teal'   },
      { key: 'rag',       label: 'Vector / RAG',          colour: 'indigo' },
      { key: 'comms',     label: 'Email / SMS / push',    colour: 'orange' },
      { key: 'market',    label: 'Market data',           colour: 'green'  },
      { key: 'maps',      label: 'Maps & geospatial',     colour: 'cyan'   },
      { key: 'realtime',  label: 'Realtime infra',        colour: 'slate'  },
      { key: 'planned',   label: 'Planned / not wired',   colour: 'grey'   },
      { key: 'removed',   label: 'Removed',               colour: 'red'    },
    ],
    services: [
      // AI
      { name: 'Anthropic — Claude Sonnet 4.6', cat: 'ai', residency: 'US', status: 'live',
        used: 'Lease drafting, clause generation, maintenance triage, agent-assist RAG, property photo classification',
        wiring: 'ANTHROPIC_API_KEY env · anthropic>=0.40.0 · client: anthropic.Anthropic(api_key=key)',
        popia: 'Cross-border. Lease & tenant PI transmitted. Requires explicit consent + DPA on file (POPIA s72).',
        flag: 'cross-border' },
      { name: 'Anthropic — web_fetch (optional)', cat: 'ai', residency: 'US', status: 'live',
        used: 'Agent-assist can fetch public web pages for context (disabled by default)',
        wiring: 'ANTHROPIC_WEB_FETCH_ENABLED env (bool). Max 5 fetches per session.',
        popia: 'URLs transmitted to Anthropic. Must stay opt-in; never enable for tenant-facing flows.',
        flag: 'cross-border' },
      { name: 'Sentence Transformers (Nomic Embed v1.5)', cat: 'ai', residency: 'Local', status: 'live',
        used: 'Embeddings for RAG — lease clauses, Q&A, maintenance issues, market listings',
        wiring: 'sentence-transformers>=3.0 · model downloaded from HuggingFace on first use',
        popia: 'Local inference. No egress once model is cached.',
        flag: 'local' },
      // PDF
      { name: 'Gotenberg', cat: 'pdf', residency: 'Self-hosted', status: 'live',
        used: 'HTML → PDF rendering for leases, signed addenda, statements, templates',
        wiring: 'GOTENBERG_URL env (default http://localhost:3000) · docker compose service · REST POST /forms/chromium/convert/html',
        popia: 'Self-hosted. No PI leaves the VPC. Zero third-party exposure.',
        flag: 'local' },
      { name: 'xhtml2pdf (fallback)', cat: 'pdf', residency: 'Local', status: 'live',
        used: 'Fallback PDF generator when Gotenberg unavailable',
        wiring: 'xhtml2pdf>=0.2.11 in-process',
        popia: 'Local. No egress.',
        flag: 'local' },
      { name: 'python-docx / docxtpl', cat: 'pdf', residency: 'Local', status: 'live',
        used: 'Legacy DOCX template rendering with merge fields (being phased out)',
        wiring: 'docxtpl>=0.16.0 · python-docx>=1.1.0',
        popia: 'Local. Merge field injection risk if templates not sandboxed.',
        flag: 'local' },
      // Storage
      { name: 'PostgreSQL', cat: 'storage', residency: 'Self-hosted', status: 'live',
        used: 'Primary datastore — all leases, users, properties, signings, notifications',
        wiring: 'psycopg2-binary>=2.9 · DB_HOST env · Django ORM',
        popia: 'Production must run inside RSA boundary (e.g. AWS af-south-1 RDS). Encryption-at-rest mandatory per POPIA s19.',
        flag: 'rsa-required' },
      { name: 'AWS S3 (af-south-1)', cat: 'storage', residency: 'RSA (Cape Town)', status: 'planned',
        used: 'Planned document storage — lease PDFs, screening artefacts, Vault33 blobs',
        wiring: 'boto3 · django-storages · AWS_S3_REGION_NAME=af-south-1 (not yet in settings)',
        popia: 'RSA region explicitly chosen for data residency. No cross-border concern.',
        flag: 'rsa' },
      // RAG
      { name: 'ChromaDB (on-disk)', cat: 'rag', residency: 'Local', status: 'live',
        used: 'Default vector store — RAG for contracts, Q&A, maintenance, market listings, Vault documents',
        wiring: 'chromadb>=0.5 · persistent client at RAG_CHROMA_PATH (default rag_chroma/)',
        popia: 'Local. Embeddings contain derived PI; retention schedule same as source documents.',
        flag: 'local' },
      { name: 'Weaviate Cloud (optional)', cat: 'rag', residency: 'Global (cloud)', status: 'optional',
        used: 'Optional multi-tenant backend for Vault33 when ChromaDB isolation insufficient',
        wiring: 'WEAVIATE_URL + WEAVIATE_API_KEY env · falls back to Chroma if unset',
        popia: 'Cross-border. Only enable after DPA signed; Vault33 consent model must cover cloud storage.',
        flag: 'cross-border' },
      // Comms
      { name: 'Twilio — SMS & WhatsApp', cat: 'comms', residency: 'US / Ireland', status: 'live',
        used: 'OTPs, lease signing links, maintenance dispatch, Vault33 approval codes',
        wiring: 'TWILIO_ACCOUNT_SID · TWILIO_AUTH_TOKEN · TWILIO_SMS_FROM · TWILIO_WHATSAPP_FROM · twilio>=9.0 · stub-mode if unset',
        popia: 'Cross-border. Phone numbers transmitted. Direct marketing sends need POPIA s69 opt-in (Form 4).',
        flag: 'cross-border' },
      { name: 'Django email (SMTP)', cat: 'comms', residency: 'Configured', status: 'live',
        used: 'Transactional email — signing links, OTPs, notifications',
        wiring: 'EMAIL_BACKEND · EMAIL_HOST · EMAIL_HOST_USER · EMAIL_HOST_PASSWORD · DEFAULT_FROM_EMAIL',
        popia: 'Residency depends on provider — Gmail/SES = cross-border. RSA SMTP (AfriHost, RSAweb) keeps PII local.',
        flag: 'configurable' },
      { name: 'Firebase Cloud Messaging (planned)', cat: 'comms', residency: 'Global (GCP)', status: 'planned',
        used: 'Mobile push for tenant app (iOS + Android)',
        wiring: 'firebase-admin>=6.5 in requirements · not yet initialised in settings',
        popia: 'Cross-border when enabled. Device tokens are PI. Need explicit push consent.',
        flag: 'cross-border' },
      // Market data
      { name: 'Property24 scraper', cat: 'market', residency: 'RSA', status: 'live',
        used: 'Rental listing comps, market data enrichment',
        wiring: 'BeautifulSoup + lxml · apps/market_data/scrapers/property24.py · management cmd scrape_market_data --source property24',
        popia: 'No PI scraped. Respect Property24 ToS + robots.txt.',
        flag: 'local' },
      { name: 'PrivateProperty scraper', cat: 'market', residency: 'RSA', status: 'stub',
        used: 'Future listing syndication + comps',
        wiring: 'Scraper class placeholder in apps/market_data/scrapers/',
        popia: 'Will follow same rules as Property24 scraper.',
        flag: 'local' },
      { name: 'News feed parser', cat: 'market', residency: 'Global', status: 'live',
        used: 'Area news enrichment via RSS/Atom feeds (suburb-level)',
        wiring: 'feedparser>=6.0',
        popia: 'No PI. Public feeds only.',
        flag: 'local' },
      // Maps
      { name: 'Google Maps API', cat: 'maps', residency: 'US', status: 'live',
        used: 'Street View imagery, nearby places, distance matrix for area enrichment',
        wiring: 'GOOGLE_MAPS_API_KEY env · REST calls via requests · images cached locally',
        popia: 'Cross-border. Coordinates transmitted. Billing-aware check before Street View fetch.',
        flag: 'cross-border' },
      // Realtime
      { name: 'Django Channels + Daphne', cat: 'realtime', residency: 'Self-hosted', status: 'live',
        used: 'WebSockets — lease updates, maintenance activity, esigning status, admin live refresh',
        wiring: 'channels>=4.0 · daphne>=4.0 · in-memory channel layer (dev) · Redis layer required for prod',
        popia: 'Local. Not a third party; dev mode only without Redis.',
        flag: 'local' },
      { name: 'Redis (planned)', cat: 'realtime', residency: 'Self-hosted', status: 'planned',
        used: 'Channel layer for multi-worker Daphne + cache + future Celery broker',
        wiring: 'Not in settings. docker-compose ready.',
        popia: 'Must be self-hosted / same VPC as Django.',
        flag: 'local' },
      // Planned
      { name: 'TransUnion SA (ITC) — tenant screening', cat: 'planned', residency: 'RSA', status: 'planned',
        used: 'Credit bureau check, rental history, ID verification, employment',
        wiring: 'Not wired. REST client stub in apps/screening/ when implemented.',
        popia: 'Consent required (POPIA s11 + NCR rules). Results are special PI. Store in Vault33 with short retention.',
        flag: 'rsa-consent' },
      { name: 'Deeds Office / Lightstone', cat: 'planned', residency: 'RSA', status: 'planned',
        used: 'Property ownership verification, mandate provenance, sale history',
        wiring: 'Not wired. Seed data only.',
        popia: 'Public registry data. Combining with user data may create PI → PAIA considerations.',
        flag: 'rsa' },
      { name: 'Payment gateway (Yoco / Ozow / PayFast / DebiCheck)', cat: 'planned', residency: 'RSA', status: 'planned',
        used: 'Rent payments, deposit collection, agent commission payouts',
        wiring: 'No gateway imported. Payment model fields are structural only.',
        popia: 'Payment data is NOT POPIA-covered (PCI-DSS + SARB territory) — but link to identity in ledger must be protected.',
        flag: 'rsa' },
      // Removed
      { name: 'DocuSeal', cat: 'removed', residency: '(EU, was)', status: 'removed',
        used: '(formerly: e-signature capture, signer ordering, webhook callbacks)',
        wiring: 'Fully removed April 2026. No live imports. Migration 0010_remove_docuseal_fields applied.',
        popia: 'N/A — replaced by native signing (Gotenberg + Fernet-signed PDFs + signer_role public links).',
        flag: 'removed' },
    ],
    // POPIA-specific cheat sheet per integration
    popia: [
      { svc: 'Anthropic Claude',   section: 's72',     risk: 'high',    note: 'Cross-border transfer of tenant & owner PI. Requires: (a) data subject consent, OR (b) adequate law in destination country, OR (c) binding corporate rules. Anthropic signs DPA — obtain and file.' },
      { svc: 'Twilio SMS',         section: 's72 + s69',risk: 'medium', note: 'Phone numbers to US/Ireland. s69 marketing rules apply to rent reminders if deemed promotional — keep strictly transactional. Capture opt-in for non-essential SMS.' },
      { svc: 'Google Maps',        section: 's72',     risk: 'low',     note: 'Coordinates ≠ identifiable PI alone, but combined with address + person becomes PI. Cache server-side so client doesn\'t re-transmit per page view.' },
      { svc: 'Weaviate Cloud',     section: 's72',     risk: 'high',    note: 'Vault33 data is the most sensitive we hold. Default stays on ChromaDB (local). Weaviate Cloud requires separate consent event per data subject.' },
      { svc: 'AWS S3 af-south-1',  section: 's19',     risk: 'low',     note: 'RSA region. Use SSE-KMS with customer-managed keys. Object lifecycle policy aligned with retention schedule (leases 5y, FICA 5y per FIC Act).' },
      { svc: 'TransUnion',         section: 's11 + s26',risk: 'high',    note: 'Credit record = special PI under s26. Written consent (not ticked-box) required. Retention: delete screening artefact after lease signed + 12mo.' },
      { svc: 'PostgreSQL',         section: 's19',     risk: 'critical',note: 'Single source of truth. Encrypt at rest. Row-level security via ORM, not DB. Backups encrypted + access-logged.' },
    ],
    // Gaps ordered by priority
    gaps: [
      { title: 'Credit bureau not wired',              blocker: 'Cannot ship screening feature',          fix: 'Integrate TransUnion SA (ITC) REST API. Build consent UI, result caching, retention job.',    effort: 'L' },
      { title: 'No payment gateway',                   blocker: 'Cannot collect rent / deposits',         fix: 'Pick Yoco + Ozow (cards + EFT) or PayFast (all-in-one). Build invoice → payment → ledger.', effort: 'L' },
      { title: 'Redis not configured',                 blocker: 'Channels won\'t scale past 1 worker',    fix: 'Add redis service to docker-compose; set CHANNEL_LAYERS to channels_redis.core.RedisChannelLayer.', effort: 'S' },
      { title: 'No Celery / task queue',               blocker: 'Scheduled jobs (deposit refund, lease expiry) have nowhere to live', fix: 'Celery beat + Redis broker OR django-q. See Business rules gaps.',   effort: 'M' },
      { title: 'Firebase push not initialised',        blocker: 'Mobile app cannot receive push',         fix: 'Initialise firebase-admin, add service-account key (sealed), add device-token model + endpoint.', effort: 'M' },
      { title: 'No observability (Sentry / Datadog)',  blocker: 'Production errors invisible',            fix: 'Sentry Django SDK + DSN env. Breadcrumbs for esigning webhook + AI calls.',               effort: 'S' },
      { title: 'Deeds Office not wired',               blocker: 'Cannot verify owner claims at onboarding', fix: 'Lightstone API or scrape SA Deeds Office (has public lookup). Flag mismatches.',        effort: 'M' },
    ],
  };

  const catLookup = Object.fromEntries(integ.categories.map(c => [c.key, c]));

  const statCards = integ.stats.map(([k,v,h]) => `
    <div class="in-stat"><div class="sk">${k}</div><div class="sv">${v}</div><div class="sh">${h}</div></div>
  `).join('');

  const catPills = integ.categories.map(c => {
    const count = integ.services.filter(s => s.cat === c.key).length;
    return `<a href="#cat-${c.key}" class="cat-pill pill-${c.colour}"><span>${c.label}</span><span class="cat-count">${count}</span></a>`;
  }).join('');

  const serviceCards = integ.categories.map(c => {
    const items = integ.services.filter(s => s.cat === c.key);
    if (!items.length) return '';
    const rows = items.map(s => `
      <div class="in-svc">
        <div class="svc-head">
          <div class="svc-name">${s.name}</div>
          <div class="svc-badges">
            <span class="svc-status st-${s.status}">${s.status}</span>
            <span class="svc-flag fl-${s.flag}">${s.flag.replace('-', ' ')}</span>
            <span class="svc-res">${s.residency}</span>
          </div>
        </div>
        <div class="svc-row"><span class="svc-k">Used for</span><span class="svc-v">${s.used}</span></div>
        <div class="svc-row"><span class="svc-k">Wiring</span><span class="svc-v"><code>${s.wiring}</code></span></div>
        <div class="svc-row svc-popia"><span class="svc-k">POPIA</span><span class="svc-v">${s.popia}</span></div>
      </div>
    `).join('');
    return `
      <div id="cat-${c.key}" class="in-cat cat-${c.colour}">
        <h4><span class="cat-dot"></span> ${c.label} <span class="cat-num">${items.length}</span></h4>
        <div class="in-svcs">${rows}</div>
      </div>
    `;
  }).join('');

  const popiaRows = integ.popia.map(p => `
    <tr class="risk-${p.risk}">
      <td>${p.svc}</td>
      <td><code>${p.section}</code></td>
      <td><span class="risk-pill rp-${p.risk}">${p.risk}</span></td>
      <td>${p.note}</td>
    </tr>
  `).join('');

  const gapCards = integ.gaps.map(g => `
    <div class="in-gap eff-${g.effort}">
      <div class="g-head">
        <h5>${g.title}</h5>
        <span class="g-eff">${g.effort}</span>
      </div>
      <p class="g-blk"><strong>Blocker.</strong> ${g.blocker}</p>
      <p class="g-fix"><strong>Fix.</strong> ${g.fix}</p>
    </div>
  `).join('');

  return `
    <style>
      .in-tabs{position:sticky;top:0;z-index:10;background:#F5F5F8;padding:12px 0;display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #E5E5EC;margin-bottom:24px}
      .in-tabs a{padding:8px 14px;border-radius:20px;background:#fff;font-size:13px;font-weight:500;color:#595B8F;text-decoration:none;border:1px solid #E5E5EC}
      .in-tabs a.active{background:#2B2D6E;color:#fff;border-color:#2B2D6E}
      .in-sec{margin-bottom:48px;scroll-margin-top:72px}
      .in-sec h3{font-family:Fraunces,serif;font-weight:700;font-size:28px;margin:0 0 6px;color:#2B2D6E}
      .in-sec .sec-sub{color:#595B8F;font-size:14px;margin:0 0 20px}
      .in-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .in-stat{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px}
      .in-stat .sk{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8E90B8}
      .in-stat .sv{font-family:Fraunces,serif;font-weight:700;font-size:22px;color:#2B2D6E;line-height:1.15;margin:4px 0}
      .in-stat .sh{font-size:12px;color:#595B8F}
      .in-cats{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}
      .cat-pill{padding:6px 12px;border-radius:20px;font-size:12px;font-weight:500;text-decoration:none;display:inline-flex;align-items:center;gap:6px;border:1px solid transparent}
      .cat-pill .cat-count{background:rgba(255,255,255,.55);padding:0 6px;border-radius:10px;font-size:10px}
      .cat-pill.pill-violet{background:#EEE8FF;color:#2B2D6E;border-color:#CFC4F7}
      .cat-pill.pill-blue{background:#E7EAF9;color:#2B2D6E;border-color:#BFC7EE}
      .cat-pill.pill-teal{background:#DCF4EE;color:#166534;border-color:#A8E3D1}
      .cat-pill.pill-indigo{background:#E2E3F7;color:#2B2D6E;border-color:#B5B7E8}
      .cat-pill.pill-orange{background:#FDE9D0;color:#8B4A1F;border-color:#F5C98A}
      .cat-pill.pill-green{background:#DFF5E3;color:#166534;border-color:#A8E0B3}
      .cat-pill.pill-cyan{background:#D8F1F6;color:#0E5E6E;border-color:#8FD3DF}
      .cat-pill.pill-slate{background:#E5E5EC;color:#595B8F;border-color:#C8C9D7}
      .cat-pill.pill-grey{background:#F0F1F8;color:#8E90B8;border-color:#D5D6E2}
      .cat-pill.pill-red{background:#FFE2E2;color:#A4231F;border-color:#F3B7B5}
      .in-cat{margin-bottom:24px;scroll-margin-top:120px}
      .in-cat h4{font-family:Fraunces,serif;font-weight:700;font-size:18px;margin:0 0 10px;color:#2B2D6E;display:flex;align-items:center;gap:10px}
      .in-cat .cat-dot{width:10px;height:10px;border-radius:50%;background:#8E90B8;display:inline-block}
      .in-cat.cat-violet .cat-dot{background:#8B5CF6}
      .in-cat.cat-blue .cat-dot{background:#5B5DC7}
      .in-cat.cat-teal .cat-dot{background:#14B8A6}
      .in-cat.cat-indigo .cat-dot{background:#6366F1}
      .in-cat.cat-orange .cat-dot{background:#F59E0B}
      .in-cat.cat-green .cat-dot{background:#22C55E}
      .in-cat.cat-cyan .cat-dot{background:#06B6D4}
      .in-cat.cat-slate .cat-dot{background:#64748B}
      .in-cat.cat-grey .cat-dot{background:#A1A1AA}
      .in-cat.cat-red .cat-dot{background:#EF4444}
      .cat-num{background:#F0F1F8;color:#595B8F;padding:2px 8px;border-radius:10px;font-size:11px;font-family:'DM Sans',sans-serif;font-weight:500}
      .in-svcs{display:grid;grid-template-columns:1fr 1fr;gap:12px}
      .in-svc{background:#fff;border:1px solid #E5E5EC;border-radius:10px;padding:12px 14px}
      .svc-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px;flex-wrap:wrap}
      .svc-name{font-weight:600;color:#2B2D6E;font-size:14px}
      .svc-badges{display:flex;gap:4px;flex-wrap:wrap}
      .svc-status{font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:2px 6px;border-radius:4px;font-weight:600}
      .svc-status.st-live{background:#22C55E;color:#fff}
      .svc-status.st-planned{background:#F59E0B;color:#fff}
      .svc-status.st-optional{background:#5B5DC7;color:#fff}
      .svc-status.st-stub{background:#A1A1AA;color:#fff}
      .svc-status.st-removed{background:#EF4444;color:#fff}
      .svc-flag{font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:2px 6px;border-radius:4px;font-weight:500}
      .svc-flag.fl-cross-border{background:#FFE2E2;color:#A4231F}
      .svc-flag.fl-local{background:#DFF5E3;color:#166534}
      .svc-flag.fl-rsa{background:#E2E3F7;color:#2B2D6E}
      .svc-flag.fl-rsa-required{background:#E2E3F7;color:#2B2D6E}
      .svc-flag.fl-rsa-consent{background:#FDE9D0;color:#8B4A1F}
      .svc-flag.fl-configurable{background:#E5E5EC;color:#595B8F}
      .svc-flag.fl-removed{background:#F0F1F8;color:#8E90B8;text-decoration:line-through}
      .svc-res{font-size:10px;color:#8E90B8;background:#F5F5F8;padding:2px 6px;border-radius:4px}
      .svc-row{display:grid;grid-template-columns:80px 1fr;gap:10px;font-size:12px;padding:4px 0;border-top:1px solid #F0F1F8}
      .svc-row .svc-k{color:#8E90B8;font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding-top:2px}
      .svc-row .svc-v{color:#595B8F;line-height:1.55}
      .svc-row .svc-v code{font-family:ui-monospace,monospace;font-size:10.5px;background:#F0F1F8;color:#2B2D6E;padding:1px 5px;border-radius:3px;word-break:break-word}
      .svc-row.svc-popia .svc-v{color:#2B2D6E}
      .in-popia{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .in-popia th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .in-popia td{padding:10px 12px;border-top:1px solid #F0F1F8;vertical-align:top;color:#2B2D6E}
      .in-popia code{font-family:ui-monospace,monospace;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px;font-size:11px}
      .risk-pill{font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:2px 8px;border-radius:6px;font-weight:600}
      .risk-pill.rp-critical{background:#7F1D1D;color:#fff}
      .risk-pill.rp-high{background:#EF4444;color:#fff}
      .risk-pill.rp-medium{background:#F59E0B;color:#fff}
      .risk-pill.rp-low{background:#22C55E;color:#fff}
      .in-gaps{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .in-gap{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px;border-left:4px solid #F59E0B}
      .in-gap.eff-S{border-left-color:#22C55E}
      .in-gap.eff-M{border-left-color:#F59E0B}
      .in-gap.eff-L{border-left-color:#EF4444}
      .in-gap .g-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
      .in-gap h5{margin:0;font-size:14px;color:#2B2D6E}
      .in-gap .g-eff{font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding:2px 8px;border-radius:6px;font-weight:600;background:#F0F1F8;color:#595B8F}
      .in-gap.eff-S .g-eff{background:#DFF5E3;color:#166534}
      .in-gap.eff-M .g-eff{background:#FDE9D0;color:#8B4A1F}
      .in-gap.eff-L .g-eff{background:#FFE2E2;color:#A4231F}
      .in-gap p{font-size:12.5px;color:#595B8F;line-height:1.6;margin:4px 0}
      .in-gap .g-fix{color:#2B2D6E}
      @media (max-width:900px){.in-stats,.in-svcs,.in-gaps{grid-template-columns:1fr}}
    </style>

    <nav class="in-tabs">
      <a href="#in-stats" class="active">At a glance</a>
      <a href="#in-services">Services</a>
      <a href="#in-popia">POPIA flags</a>
      <a href="#in-gaps">Gaps</a>
    </nav>

    <section id="in-stats" class="in-sec">
      <h3>At a glance</h3>
      <p class="sec-sub">Twenty-two third-party services. Five cross the border and need POPIA s72 coverage; six are not yet wired and block flagship features. DocuSeal is out; native signing is the sole e-sign backend.</p>
      <div class="in-stats">${statCards}</div>
    </section>

    <section id="in-services" class="in-sec">
      <h3>Services</h3>
      <p class="sec-sub">Grouped by category. Each card shows the service, its data-residency, wiring (env vars + packages), and the POPIA implication.</p>
      <div class="in-cats">${catPills}</div>
      ${serviceCards}
    </section>

    <section id="in-popia" class="in-sec">
      <h3>POPIA flags</h3>
      <p class="sec-sub">Per-service compliance cheat sheet. Cross-border services (s72) and special-PI processors (s26) need explicit sign-off from the data subject.</p>
      <table class="in-popia">
        <thead><tr><th>Service</th><th>Section</th><th>Risk</th><th>Note</th></tr></thead>
        <tbody>${popiaRows}</tbody>
      </table>
    </section>

    <section id="in-gaps" class="in-sec">
      <h3>Gaps</h3>
      <p class="sec-sub">Integrations still to build. Sized S/M/L: small = a day, medium = a week, large = a month.</p>
      <div class="in-gaps">${gapCards}</div>
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.in-tabs a');
        const secs = [...tabs].map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
        tabs.forEach(t => t.addEventListener('click', () => {
          tabs.forEach(x => x.classList.remove('active'));
          t.classList.add('active');
        }));
        function onScroll(){
          const y = window.scrollY + 120;
          let active = secs[0];
          for (const s of secs) { if (s.offsetTop <= y) active = s; }
          tabs.forEach(t => {
            t.classList.toggle('active', t.getAttribute('href') === '#' + active.id);
          });
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- Test battery (E2E per lifecycle stage + security + machines) ---------- */
function pageTests() {
  const tests = {
    stats: [
      ['Lifecycle stages', '15',  'Golden-path E2E test per stage (rental_lifecycle.yaml)'],
      ['State machines',   '8',   'Transition tests for Lease, Unit, Mandate, ESigning, Maintenance, etc.'],
      ['Security tests',   '~40', 'RBAC denies, cross-tenant isolation, auth, rate limiting'],
      ['Critical endpoints','10', 'One black-box test each (from /api → Critical tab)'],
      ['Runner',           'pytest + DRF APIClient', 'backend/tests/ + apps/*/tests/. MCP E2E via tremly-mcp stdio server.'],
      ['CI budget',        '<6 min', 'Unit + integration targets on PR. Full battery nightly.'],
    ],
    // Per-lifecycle-stage golden-path tests
    lifecycle: [
      { step: 1,  phase: 'pre', title: 'Notice',      test: 'test_notice_triggers_listing',
        setup: 'Active lease 10 months in; tenant role = tenant.',
        acts:  ['POST /api/v1/leases/{id}/notice/ with notice_date=today', 'Expected 2-month window'],
        asserts: ['Lease.notice_given_at set', 'Notification row created for landlord + agent', 'Property marketing status flips to "available_from"', 'Signal fires; WebSocket broadcasts'] },
      { step: 2,  phase: 'pre', title: 'Market',      test: 'test_listing_syndicates_to_portals',
        setup: 'Property with 2-month notice. Feature flag for Property24 on.',
        acts:  ['POST /api/v1/properties/{id}/list/', 'Syndication task runs (mocked network)'],
        asserts: ['PropertyListing created', 'External IDs stored', 'Scraper comps cached in market_data'] },
      { step: 3,  phase: 'pre', title: 'Viewings',    test: 'test_viewing_scheduled_and_collected',
        setup: 'Listed property + prospect user.',
        acts:  ['POST /api/v1/viewings/ with slot', 'Prospect POSTs attendance form'],
        asserts: ['Viewing.status=scheduled→attended', 'Calendar event emitted', 'No PII leak on public RSVP endpoint'] },
      { step: 4,  phase: 'pre', title: 'Screen',      test: 'test_ai_screening_produces_score',
        setup: 'Applicant submits ID + payslips + consent.',
        acts:  ['POST /api/v1/screening/ with docs', 'AI scoring task runs (Anthropic stubbed)'],
        asserts: ['ScreeningRequest.status=complete', 'Score stored as special PI', 'Retention job scheduled', 'Consent artefact present (POPIA s11)'] },
      { step: 5,  phase: 'pre', title: 'Lease',       test: 'test_lease_generated_and_sent',
        setup: 'Accepted applicant + property + template.',
        acts:  ['POST /api/v1/leases/ from template', 'POST /api/v1/esigning/submissions/ (sequential)'],
        asserts: ['Lease.status=pending', 'ESigningSubmission.status=pending', 'Signer links emailed (Twilio/SMTP stubbed)', 'Merge fields resolved — no {{…}} in output'] },
      { step: 6,  phase: 'pre', title: 'Invoicing',   test: 'test_rent_schedule_configured',
        setup: 'Pending lease with monthly_rent + rent_due_day.',
        acts:  ['POST /api/v1/leases/{id}/invoice-schedule/'],
        asserts: ['12 invoice rows queued', 'Escalation applied on anniversary', 'Due dates honour rent_due_day'] },
      { step: 7,  phase: 'pre', title: 'Deposit',     test: 'test_deposit_lodged_interest_tracked',
        setup: 'Lease pending; deposit amount set.',
        acts:  ['POST /api/v1/payments/ kind=deposit', 'Ledger updated'],
        asserts: ['Deposit in interest-bearing account flag true', 'Interest accrual job scheduled (GAP — test marks xfail)', 'Receipt issued to tenant'] },
      { step: 8,  phase: 'turn', title: 'Move-Out',   test: 'test_outgoing_inspection_signed',
        setup: 'Previous lease in final week.',
        acts:  ['POST /api/v1/inspections/ kind=outgoing with photos + signatures'],
        asserts: ['Inspection.status=signed_by_both', 'PDF generated via Gotenberg', 'Snag list extracted → maintenance requests queued'] },
      { step: 9,  phase: 'turn', title: 'Repairs',    test: 'test_overnight_dispatch_awards_supplier',
        setup: 'Snag list from inspection.',
        acts:  ['POST /api/v1/maintenance/dispatches/', 'Supplier posts quote', 'Agent awards'],
        asserts: ['JobDispatch.status draft→sent→quoting→awarded', 'JobQuoteRequest.status flows', 'Supplier notified (stub)'] },
      { step: 10, phase: 'turn', title: 'Move-In',    test: 'test_incoming_inspection_and_lease_activates',
        setup: 'All signers completed e-signing.',
        acts:  ['esigning webhook: completed', 'POST /api/v1/inspections/ kind=incoming'],
        asserts: ['Lease.status PENDING → ACTIVE (auto)', 'Unit.status → OCCUPIED via signal', 'First rent invoice issued'] },
      { step: 11, phase: 'turn', title: 'Onboard',    test: 'test_tenant_portal_access_and_welcome_pack',
        setup: 'Active lease.',
        acts:  ['Tenant logs in', 'GET /api/v1/tenant/dashboard/'],
        asserts: ['Tenant sees only their lease', 'Welcome pack docs attached', 'Utility transfer checklist created'] },
      { step: 12, phase: 'active', title: 'Rent',     test: 'test_monthly_invoice_and_payment_reconcile',
        setup: 'Active lease mid-term.',
        acts:  ['Cron: invoice generation (call task)', 'Tenant pays (stub gateway)'],
        asserts: ['Invoice.status paid; receipt issued', 'Ledger balanced', 'Payment reminder muted for this period'] },
      { step: 13, phase: 'active', title: 'Maintain', test: 'test_tenant_ticket_triaged_and_dispatched',
        setup: 'Active tenant + working supplier directory.',
        acts:  ['POST /api/v1/maintenance/requests/ (tenant)', 'AI triage + supplier match'],
        asserts: ['MaintenanceRequest.status open→in_progress after dispatch', 'RAG embedded; similar past issue returned', 'Tenant update pushed via WebSocket'] },
      { step: 14, phase: 'active', title: 'Renew',    test: 'test_renewal_notification_and_branch',
        setup: 'Lease 80 business days before end_date.',
        acts:  ['Cron: renewal notification fires', 'Either renew, go month-to-month, or vacate'],
        asserts: ['Renewal addendum created with previous_lease FK set', 'Month-to-month extends Lease without new signing', 'Vacate branch loops back to stage 1 — regression test for circularity'] },
      { step: 15, phase: 'closeout', title: 'Refund', test: 'test_deposit_refund_within_rha_window',
        setup: 'Lease expired, inspection closed, no dispute.',
        acts:  ['POST /api/v1/deposits/{id}/refund/'],
        asserts: ['Refund paid within 7 days (no deductions) / 14 days (with deductions) / 21 days (disputed)', 'Interest ledger included in itemised statement', 'PIE Act never invoked (not an eviction)'] },
    ],
    // State machine tests (one per machine)
    machines: [
      { machine: 'Lease',             test: 'test_lease_activates_on_final_signature_only',           asserts: 'Webhook fires; Lease PENDING→ACTIVE exactly once; re-firing is no-op.' },
      { machine: 'Lease',             test: 'test_lease_terminated_does_not_occupy',                   asserts: 'Unit.status reverts from OCCUPIED to AVAILABLE after termination.' },
      { machine: 'Unit',              test: 'test_unit_occupancy_requires_active_lease',               asserts: 'Pending, expired, terminated leases leave unit AVAILABLE.' },
      { machine: 'Unit',              test: 'test_unit_maintenance_manual_toggle',                     asserts: 'Staff can flip to MAINTENANCE; signal respects override.' },
      { machine: 'RentalMandate',     test: 'test_mandate_mirrors_submission_status',                  asserts: 'completed→active, declined→cancelled, in_progress→partially_signed.' },
      { machine: 'ESigningSubmission',test: 'test_esigning_link_expires_after_14_days',                asserts: 'After TTL, link returns 410 Gone and Submission.status=expired.' },
      { machine: 'MaintenanceRequest',test: 'test_maintenance_status_rolls_forward_not_back',          asserts: 'open→in_progress→resolved→closed. Reverse transitions rejected.' },
      { machine: 'JobDispatch',       test: 'test_dispatch_auto_flips_to_quoting_on_first_quote',      asserts: 'sent → quoting on first JobQuoteRequest.status=quoted.' },
      { machine: 'JobQuoteRequest',   test: 'test_quote_expires_after_deadline',                       asserts: 'Pending quote → expired once deadline passes.' },
    ],
    // Security battery
    security: [
      { group: 'Auth',     test: 'test_jwt_login_returns_access_and_refresh',             asserts: 'POST /api/v1/auth/login → 200 with both tokens. Wrong password → 401.' },
      { group: 'Auth',     test: 'test_jwt_refresh_rotates_token',                        asserts: 'Old refresh token becomes invalid after rotate (if configured).' },
      { group: 'Auth',     test: 'test_otp_throttle_after_five_attempts',                 asserts: 'Sixth OTP request within 10 min → 429.' },
      { group: 'Auth',     test: 'test_password_reset_link_expires',                      asserts: 'Reset link single-use; expires after 1 hour.' },
      { group: 'RBAC',     test: 'test_tenant_cannot_list_properties',                    asserts: 'TENANT GET /api/v1/properties/ → 403.' },
      { group: 'RBAC',     test: 'test_supplier_cannot_read_other_supplier_jobs',         asserts: 'Supplier A queries Supplier B\'s JobQuoteRequest → 404 (not 403, to avoid leaking existence).' },
      { group: 'RBAC',     test: 'test_owner_cannot_see_tenant_fica',                     asserts: 'OWNER GET tenant FICA document endpoint → 403; minimisation invariant.' },
      { group: 'RBAC',     test: 'test_viewer_module_access_enforced',                    asserts: 'VIEWER with module_access=["maintenance"] → 403 on /properties/.' },
      { group: 'RBAC',     test: 'test_agency_admin_scoped_to_own_agency',                asserts: 'Agency A admin cannot read Agency B\'s properties, agents, or tenants.' },
      { group: 'RBAC',     test: 'test_agent_without_assignment_sees_nothing',            asserts: 'AGENT role with zero PropertyAgentAssignment.active returns empty list on /properties/.' },
      { group: 'Tenant',   test: 'test_tenant_scoped_to_own_lease',                       asserts: 'Tenant A cannot read Tenant B\'s lease even with valid JWT.' },
      { group: 'Tenant',   test: 'test_tenant_cannot_modify_invoice',                     asserts: 'PATCH /api/v1/invoices/ by tenant → 403.' },
      { group: 'E-signing',test: 'test_public_sign_link_requires_otp',                    asserts: 'GET /api/v1/esigning/public/{token}/ → 200 preview, but POST submit without OTP → 401.' },
      { group: 'E-signing',test: 'test_public_sign_link_idempotent',                      asserts: 'Submitting same signature twice → 200 both times, single audit entry.' },
      { group: 'Vault33',  test: 'test_vault_gateway_refuses_expired_loan',               asserts: 'Subscriber API key with expired scope returns 401 and logs refusal.' },
      { group: 'Vault33',  test: 'test_vault_owner_revoke_kills_active_loan',             asserts: 'After revoke, subscriber loses access within 60s; audit row closes loan.' },
      { group: 'Rate',     test: 'test_rate_limit_on_login',                              asserts: '10 login attempts/min per IP → 429 thereafter.' },
      { group: 'Rate',     test: 'test_rate_limit_on_public_lookup',                      asserts: 'OTP-protected public endpoints throttled per phone + IP.' },
      { group: 'Webhooks', test: 'test_esigning_webhook_signature_verified',              asserts: 'Bad signature → 400; replay (same event_id) → 200 no-op.' },
      { group: 'Data',     test: 'test_delete_user_anonymises_audit_rows',                asserts: 'User delete → audit retained with subject_id hashed; no raw PI left.' },
    ],
    // Integration smoke tests
    smoke: [
      { svc: 'Gotenberg',        test: 'test_gotenberg_renders_lease_pdf',     how: 'POST html → inspect PDF bytes + page count + text extract contains "Gauteng Residential Tenancy".' },
      { svc: 'Anthropic',        test: 'test_anthropic_client_stubbed',        how: 'VCR cassette or monkeypatched client. Assert prompt shape + parsed response.' },
      { svc: 'Twilio',           test: 'test_twilio_stub_logs_send',           how: 'No creds → stub mode; assert send() logs and returns fake SID; does not raise.' },
      { svc: 'ChromaDB',         test: 'test_rag_upsert_and_query_round_trip', how: 'Upsert 3 docs; query; top-1 must match source. Idempotent on second upsert.' },
      { svc: 'Weaviate Cloud',   test: 'test_weaviate_fallback_to_chroma',     how: 'Unset WEAVIATE_URL → code must silently fall back to Chroma; no exception.' },
      { svc: 'Property24',       test: 'test_p24_scraper_fixture_parses',      how: 'Load saved HTML fixture; assert listing count, price, address parsed.' },
      { svc: 'Channels',         test: 'test_websocket_broadcasts_lease_update',how: 'WebsocketCommunicator subscribes; save Lease; assert payload received with lease_id.' },
    ],
    // Test infrastructure + how to run
    infra: [
      { title: 'Unit + integration (pytest)', cmd: 'pytest backend/apps -x --reuse-db',                            notes: 'Fast loop. Uses factory_boy + Faker (SA locale).' },
      { title: 'Full battery',                cmd: 'pytest backend --maxfail=5',                                    notes: 'CI nightly. Includes slow + external-stub tests.' },
      { title: 'MCP E2E (tremly-mcp)',        cmd: 'node services/tremly-mcp/index.mjs',                           notes: 'stdio MCP server. Claude Desktop / Cursor drives the entire happy path against local Django.' },
      { title: 'Lease + e-signing battery',   cmd: 'Skill: klikk-leases-test-battery',                              notes: 'Runs template ↔ tiptap round-trip, merge-field audit, form submit, signer resend, public sign flow.' },
      { title: 'Coverage report',             cmd: 'pytest --cov=apps --cov-report=term-missing',                   notes: 'Target: 80% for apps/leases, apps/esigning, apps/accounts. 60% elsewhere.' },
      { title: 'Golden fixture dataset',      cmd: 'python manage.py loaddata seed_stellenbosch.json',              notes: '1 agency, 2 agents, 10 properties (Stellenbosch), 7 tenants, 4 suppliers. Used for /flows demos.' },
      { title: 'Seed demo data',              cmd: 'python manage.py seed_demo --scenario=klikk-rentals-v1',        notes: 'Generates a fully signed, mid-tenancy lease so Overview + Maintenance have data out of the box.' },
    ],
  };

  const statCards = tests.stats.map(([k,v,h]) => `
    <div class="tt-stat"><div class="sk">${k}</div><div class="sv">${v}</div><div class="sh">${h}</div></div>
  `).join('');

  const phaseClass = p => ({ pre:'teal', turn:'amber', active:'blue', closeout:'violet' }[p] || 'slate');
  const lifecycleCards = tests.lifecycle.map(l => `
    <div class="tt-life phase-${phaseClass(l.phase)}">
      <div class="tl-head">
        <span class="tl-step">${l.step}</span>
        <span class="tl-phase">${l.phase}</span>
        <h5>${l.title}</h5>
      </div>
      <div class="tl-test"><code>${l.test}</code></div>
      <div class="tl-row"><span class="tl-k">Setup</span><span class="tl-v">${l.setup}</span></div>
      <div class="tl-row"><span class="tl-k">Acts</span><span class="tl-v">${l.acts.map(a => `<div>→ ${a}</div>`).join('')}</span></div>
      <div class="tl-row"><span class="tl-k">Asserts</span><span class="tl-v">${l.asserts.map(a => `<div>✓ ${a}</div>`).join('')}</span></div>
    </div>
  `).join('');

  const machineRows = tests.machines.map(m => `
    <tr>
      <td><span class="m-pill">${m.machine}</span></td>
      <td><code>${m.test}</code></td>
      <td>${m.asserts}</td>
    </tr>
  `).join('');

  // Security grouped
  const secGroups = [...new Set(tests.security.map(s => s.group))];
  const secSections = secGroups.map(g => {
    const items = tests.security.filter(s => s.group === g);
    return `
      <div class="tt-secgrp">
        <h5>${g}</h5>
        <ul>${items.map(s => `<li><code>${s.test}</code><div>${s.asserts}</div></li>`).join('')}</ul>
      </div>
    `;
  }).join('');

  const smokeRows = tests.smoke.map(s => `
    <tr>
      <td>${s.svc}</td>
      <td><code>${s.test}</code></td>
      <td>${s.how}</td>
    </tr>
  `).join('');

  const infraRows = tests.infra.map(i => `
    <div class="tt-infra">
      <h5>${i.title}</h5>
      <pre><code>${i.cmd}</code></pre>
      <p>${i.notes}</p>
    </div>
  `).join('');

  return `
    <style>
      .tt-tabs{position:sticky;top:0;z-index:10;background:#F5F5F8;padding:12px 0;display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #E5E5EC;margin-bottom:24px}
      .tt-tabs a{padding:8px 14px;border-radius:20px;background:#fff;font-size:13px;font-weight:500;color:#595B8F;text-decoration:none;border:1px solid #E5E5EC}
      .tt-tabs a.active{background:#2B2D6E;color:#fff;border-color:#2B2D6E}
      .tt-sec{margin-bottom:48px;scroll-margin-top:72px}
      .tt-sec h3{font-family:Fraunces,serif;font-weight:700;font-size:28px;margin:0 0 6px;color:#2B2D6E}
      .tt-sec .sec-sub{color:#595B8F;font-size:14px;margin:0 0 20px}
      .tt-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .tt-stat{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px}
      .tt-stat .sk{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8E90B8}
      .tt-stat .sv{font-family:Fraunces,serif;font-weight:700;font-size:22px;color:#2B2D6E;line-height:1.15;margin:4px 0}
      .tt-stat .sh{font-size:12px;color:#595B8F}
      .tt-lifes{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .tt-life{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px;border-left:4px solid #8E90B8}
      .tt-life.phase-teal{border-left-color:#14B8A6}
      .tt-life.phase-amber{border-left-color:#F59E0B}
      .tt-life.phase-blue{border-left-color:#5B5DC7}
      .tt-life.phase-violet{border-left-color:#8B5CF6}
      .tl-head{display:flex;align-items:baseline;gap:10px;margin-bottom:6px}
      .tl-step{font-family:Fraunces,serif;font-weight:700;font-size:22px;color:#2B2D6E}
      .tl-phase{font-size:10px;text-transform:uppercase;letter-spacing:.08em;background:#F0F1F8;color:#595B8F;padding:2px 8px;border-radius:6px}
      .tl-head h5{margin:0;font-size:15px;color:#2B2D6E}
      .tl-test{margin-bottom:8px}
      .tl-test code{font-family:ui-monospace,monospace;font-size:11.5px;background:#EEE8FF;color:#2B2D6E;padding:3px 8px;border-radius:6px;display:inline-block}
      .tl-row{display:grid;grid-template-columns:68px 1fr;gap:10px;font-size:12px;padding:4px 0;border-top:1px solid #F0F1F8}
      .tl-row .tl-k{color:#8E90B8;font-size:10px;text-transform:uppercase;letter-spacing:.06em;padding-top:2px}
      .tl-row .tl-v{color:#595B8F;line-height:1.55}
      .tl-row .tl-v div{padding:1px 0}
      .tt-mach{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .tt-mach th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .tt-mach td{padding:10px 12px;border-top:1px solid #F0F1F8;vertical-align:top;color:#2B2D6E}
      .tt-mach code{font-family:ui-monospace,monospace;font-size:11.5px;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px}
      .m-pill{font-size:11px;background:#EEE8FF;color:#2B2D6E;padding:2px 8px;border-radius:6px}
      .tt-secs{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .tt-secgrp{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:12px 14px}
      .tt-secgrp h5{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#8E90B8}
      .tt-secgrp ul{list-style:none;padding:0;margin:0}
      .tt-secgrp li{padding:6px 0;border-top:1px solid #F0F1F8;font-size:12px;color:#595B8F;line-height:1.55}
      .tt-secgrp li:first-child{border-top:none}
      .tt-secgrp li code{display:block;font-family:ui-monospace,monospace;font-size:11.5px;color:#2B2D6E;margin-bottom:2px;word-break:break-all}
      .tt-smoke{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .tt-smoke th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .tt-smoke td{padding:10px 12px;border-top:1px solid #F0F1F8;vertical-align:top;color:#2B2D6E}
      .tt-smoke code{font-family:ui-monospace,monospace;font-size:11.5px;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px}
      .tt-infras{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .tt-infra{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px}
      .tt-infra h5{margin:0 0 6px;font-size:14px;color:#2B2D6E}
      .tt-infra pre{background:#0F172A;color:#E2E8F0;padding:8px 12px;border-radius:8px;margin:0 0 6px;font-size:12px;overflow-x:auto}
      .tt-infra pre code{font-family:ui-monospace,monospace;background:none;color:inherit;padding:0}
      .tt-infra p{margin:0;font-size:12px;color:#595B8F;line-height:1.55}
      @media (max-width:900px){.tt-stats{grid-template-columns:1fr 1fr}.tt-lifes,.tt-secs,.tt-infras{grid-template-columns:1fr}}
    </style>

    <nav class="tt-tabs">
      <a href="#tt-stats" class="active">At a glance</a>
      <a href="#tt-lifecycle">Lifecycle E2E</a>
      <a href="#tt-machines">State machines</a>
      <a href="#tt-security">Security</a>
      <a href="#tt-smoke">Integration smoke</a>
      <a href="#tt-infra">How to run</a>
    </nav>

    <section id="tt-stats" class="tt-sec">
      <h3>At a glance</h3>
      <p class="sec-sub">The test battery an agent must pass to claim it has rebuilt the platform. One golden-path E2E per lifecycle stage, plus state-machine, security, and integration smoke.</p>
      <div class="tt-stats">${statCards}</div>
    </section>

    <section id="tt-lifecycle" class="tt-sec">
      <h3>Lifecycle E2E</h3>
      <p class="sec-sub">Fifteen tests, one per rental-lifecycle stage. Each has setup, acts (what to call), and asserts (what must be true). Pass all fifteen and the happy path is wired.</p>
      <div class="tt-lifes">${lifecycleCards}</div>
    </section>

    <section id="tt-machines" class="tt-sec">
      <h3>State machines</h3>
      <p class="sec-sub">Transition tests — one per meaningful state flip. Use <code>pytest-django</code> with <code>transactional_db</code> and signals enabled.</p>
      <table class="tt-mach">
        <thead><tr><th>Machine</th><th>Test</th><th>Asserts</th></tr></thead>
        <tbody>${machineRows}</tbody>
      </table>
    </section>

    <section id="tt-security" class="tt-sec">
      <h3>Security</h3>
      <p class="sec-sub">Auth, RBAC, tenant isolation, rate limiting, webhooks. Every denial is a test; every shortcut a regression waiting to happen.</p>
      <div class="tt-secs">${secSections}</div>
    </section>

    <section id="tt-smoke" class="tt-sec">
      <h3>Integration smoke</h3>
      <p class="sec-sub">External dependencies — stubbed by default, toggle on for nightly.</p>
      <table class="tt-smoke">
        <thead><tr><th>Service</th><th>Test</th><th>How</th></tr></thead>
        <tbody>${smokeRows}</tbody>
      </table>
    </section>

    <section id="tt-infra" class="tt-sec">
      <h3>How to run</h3>
      <p class="sec-sub">Commands, fixtures, coverage targets. Skill <code>klikk-platform-testing</code> owns the full protocol — this is the short version.</p>
      <div class="tt-infras">${infraRows}</div>
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.tt-tabs a');
        const secs = [...tabs].map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
        tabs.forEach(t => t.addEventListener('click', () => {
          tabs.forEach(x => x.classList.remove('active'));
          t.classList.add('active');
        }));
        function onScroll(){
          const y = window.scrollY + 120;
          let active = secs[0];
          for (const s of secs) { if (s.offsetTop <= y) active = s; }
          tabs.forEach(t => {
            t.classList.toggle('active', t.getAttribute('href') === '#' + active.id);
          });
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- Environment (dev setup, env vars, docker, ports) ---------- */
function pageEnv() {
  const env = {
    stats: [
      ['Docker services', '4',    'db, backend, admin, gotenberg (docuseal removed April 2026)'],
      ['Launch configs',  '17',   'VS Code / .claude/launch.json — dev servers for every surface'],
      ['Ports in use',    '14',   '5173, 5174, 5175, 5176, 5177, 5178, 8000, 8005, 8006, 3000, 3005, 3006, 4321, 5432'],
      ['Env vars',        '~28',  'Across backend, admin, mobile, website'],
      ['Prereqs',         '6 tools', 'Python 3.11+, Node 20+/22+, Docker, Flutter, Postgres 16, Gotenberg'],
      ['Data residency',  'af-south-1', 'RSA region for prod S3 + RDS'],
    ],
    prereqs: [
      { tool: 'Python 3.11+',   install: 'pyenv install 3.11.9 && pyenv local 3.11.9', notes: 'venv lives at backend/.venv.' },
      { tool: 'Node 20+ / 22+', install: 'nvm install 20 && nvm install 22',          notes: 'Admin uses 20.19.4; website + tenant use 22.17.1.' },
      { tool: 'Docker 24+',     install: 'brew install --cask docker',                  notes: 'Compose v2.' },
      { tool: 'Postgres 16',    install: 'docker compose up -d db',                     notes: 'Or native: brew install postgresql@16.' },
      { tool: 'Flutter 3.22+',  install: 'follow flutter.dev install',                  notes: 'tenant_app (legacy) + agent mobile.' },
      { tool: 'Gotenberg 8',    install: 'docker compose up -d gotenberg',              notes: 'HTML→PDF. Port 3000.' },
    ],
    // Docker compose services
    docker: [
      { name: 'db',        image: 'postgres:16',             port: '5432', purpose: 'Primary datastore. klikk_db / klikk_user / klikk_pass (dev).' },
      { name: 'backend',   image: 'build: ./backend',        port: '8000', purpose: 'Django + DRF + Channels. runserver in dev; Daphne in prod.' },
      { name: 'admin',     image: 'build: ./admin',          port: '5173', purpose: 'Vue 3 SPA. Vite dev.' },
      { name: 'gotenberg', image: 'gotenberg/gotenberg:8',   port: '3000', purpose: 'HTML→PDF Chromium headless.' },
    ],
    // Ports map — all the ports the stack uses
    ports: [
      { port: 5432, svc: 'Postgres',        url: '-',                             src: 'docker-compose.yml' },
      { port: 8000, svc: 'Django API',      url: 'http://127.0.0.1:8000/api/v1/', src: 'launch.json · Django API' },
      { port: 5173, svc: 'Admin SPA',       url: 'http://localhost:5173/',        src: 'launch.json · Admin SPA (Vite)' },
      { port: 5174, svc: 'Tenant web app',  url: 'http://localhost:5174/',        src: 'launch.json · Tenant web app' },
      { port: 5175, svc: 'Klikk Tenant',    url: 'http://localhost:5175/',        src: 'launch.json · Klikk Tenant App' },
      { port: 5176, svc: 'Klikk Agent',     url: 'http://localhost:5176/',        src: 'launch.json · Klikk Agent App (Quasar)' },
      { port: 5177, svc: 'Klikk Tenant NEW',url: 'http://localhost:5177/',        src: 'launch.json · Klikk Tenant App NEW (Quasar)' },
      { port: 5178, svc: 'Admin worktree',  url: 'http://localhost:5178/',        src: 'launch.json · Admin SPA worktree' },
      { port: 4321, svc: 'Astro website',   url: 'http://localhost:4321/',        src: 'launch.json · Klikk Website' },
      { port: 3000, svc: 'Gotenberg',       url: 'http://localhost:3000/',        src: 'docker-compose.yml' },
      { port: 3005, svc: 'Website preview', url: 'http://localhost:3005/',        src: 'launch.json · Website Preview' },
      { port: 3006, svc: 'Admin mockups',   url: 'http://localhost:3006/',        src: 'launch.json · Admin Mockups' },
      { port: 8005, svc: 'Dashboard proto', url: 'http://localhost:8005/',        src: 'launch.json · Dashboard Prototype' },
      { port: 8006, svc: 'Prototypes index',url: 'http://localhost:8006/',        src: 'launch.json · Prototypes Index (this page)' },
    ],
    // Env vars grouped by concern
    envGroups: [
      {
        label: 'Django core',
        vars: [
          { key: 'SECRET_KEY',          default: '(required)', example: 'dev-secret-key-change-in-production', purpose: 'Django cryptographic signing. Rotate for prod.' },
          { key: 'DEBUG',               default: 'True',       example: 'False (prod)',                          purpose: 'Must be False in production.' },
          { key: 'ALLOWED_HOSTS',       default: 'localhost,127.0.0.1', example: 'api.klikk.co.za,app.klikk.co.za', purpose: 'Comma-sep list. Add LAN IP for Flutter on device.' },
        ],
      },
      {
        label: 'Database',
        vars: [
          { key: 'DB_NAME',             default: 'klikk_db',     example: 'klikk_prod',    purpose: 'Postgres database name.' },
          { key: 'DB_USER',             default: 'klikk_user',   example: 'klikk_app',     purpose: 'Application DB user.' },
          { key: 'DB_PASSWORD',         default: 'klikk_pass',   example: '(from vault)',  purpose: 'Never commit. Use AWS Secrets Manager in prod.' },
          { key: 'DB_HOST',             default: 'localhost',    example: 'db.internal',   purpose: 'Internal hostname for prod RDS.' },
          { key: 'DB_PORT',             default: '5432',         example: '5432',          purpose: 'Postgres port.' },
        ],
      },
      {
        label: 'AI (Anthropic)',
        vars: [
          { key: 'ANTHROPIC_API_KEY',                default: '(required for AI)', example: 'sk-ant-...',     purpose: 'Enables lease drafting, screening AI, maintenance triage. Optional — features degrade gracefully if missing.' },
          { key: 'ANTHROPIC_WEB_FETCH_ENABLED',      default: 'false',             example: 'true',           purpose: 'Lets agent-assist fetch public URLs. Keep false for tenant flows.' },
          { key: 'RAG_CHROMA_PATH',                  default: 'rag_chroma/',       example: '/data/rag',      purpose: 'On-disk vector store root.' },
          { key: 'RAG_QUERY_CHUNKS',                 default: '8',                  example: '8',              purpose: 'Chunks to retrieve per query.' },
          { key: 'RAG_PDF_MAX_PAGES',                default: '120',                example: '120',            purpose: 'PDF ingest cap.' },
          { key: 'CONTRACT_DOCUMENTS_ROOT',          default: 'backend/documents/', example: '/data/contracts',purpose: 'Root for contract RAG ingestion.' },
          { key: 'WEAVIATE_URL',                     default: '(unset)',            example: 'https://...weaviate.network', purpose: 'If set, Vault33 uses Weaviate Cloud instead of Chroma.' },
          { key: 'WEAVIATE_API_KEY',                 default: '(unset)',            example: 'wcs-...',        purpose: 'Required with WEAVIATE_URL.' },
        ],
      },
      {
        label: 'PDF & documents',
        vars: [
          { key: 'GOTENBERG_URL',       default: 'http://localhost:3000', example: 'http://gotenberg:3000', purpose: 'Chromium PDF renderer base URL.' },
        ],
      },
      {
        label: 'E-signing',
        vars: [
          { key: 'ESIGNING_PUBLIC_LINK_EXPIRY_DAYS', default: '14',         example: '14',                          purpose: 'TTL for public signing links.' },
          { key: 'ESIGNING_FROM_EMAIL',              default: 'DEFAULT_FROM_EMAIL', example: 'sign@klikk.co.za',      purpose: 'From: address on signing-link emails.' },
        ],
      },
      {
        label: 'Email',
        vars: [
          { key: 'EMAIL_BACKEND',       default: 'console',          example: 'django.core.mail.backends.smtp.EmailBackend', purpose: 'Dev uses console; prod uses SMTP.' },
          { key: 'EMAIL_HOST',          default: '-',                example: 'smtp.gmail.com',                              purpose: 'Gmail needs app password (2FA).' },
          { key: 'EMAIL_PORT',          default: '587',              example: '587',                                          purpose: 'TLS submission port.' },
          { key: 'EMAIL_USE_TLS',       default: 'True',             example: 'True',                                         purpose: 'Always True for submission.' },
          { key: 'EMAIL_HOST_USER',     default: '-',                example: 'you@gmail.com',                                purpose: 'SMTP user.' },
          { key: 'EMAIL_HOST_PASSWORD', default: '-',                example: '(app password)',                               purpose: '16-char Gmail app password, not your Google password.' },
          { key: 'DEFAULT_FROM_EMAIL',  default: '-',                example: 'Klikk <noreply@klikk.co.za>',                   purpose: 'From: address on transactional email.' },
        ],
      },
      {
        label: 'SMS / WhatsApp',
        vars: [
          { key: 'TWILIO_ACCOUNT_SID',  default: '(stub)', example: 'ACxxxx...',        purpose: 'If unset, notifications log to console only.' },
          { key: 'TWILIO_AUTH_TOKEN',   default: '(stub)', example: '(from Twilio)',    purpose: 'Twilio auth token.' },
          { key: 'TWILIO_SMS_FROM',     default: '(stub)', example: '+27600000000',     purpose: 'Sender number for SMS (E.164).' },
          { key: 'TWILIO_WHATSAPP_FROM',default: '(stub)', example: 'whatsapp:+27600000000', purpose: 'WhatsApp sandbox / approved sender.' },
        ],
      },
      {
        label: 'OAuth & maps',
        vars: [
          { key: 'GOOGLE_OAUTH_CLIENT_ID',  default: '(unset)', example: '...apps.googleusercontent.com',           purpose: 'Social login.' },
          { key: 'GOOGLE_MAPS_API_KEY',     default: '(unset)', example: 'AIza...',                                  purpose: 'Street View + Places + Distance Matrix.' },
        ],
      },
      {
        label: 'Admin SPA (Vite)',
        vars: [
          { key: 'VITE_API_URL',        default: 'http://localhost:8000/api/v1', example: 'https://api.klikk.co.za/api/v1', purpose: 'Set in admin/.env or docker-compose.' },
          { key: 'VITE_WS_URL',         default: 'ws://localhost:8000/ws',       example: 'wss://api.klikk.co.za/ws',       purpose: 'Channels WebSocket base.' },
        ],
      },
    ],
    // Local dev workflow — step-by-step from a clean clone
    workflow: [
      { step: 1, title: 'Clone + env',       cmd: 'git clone <repo> && cd tremly_property_manager && cp backend/.env.example backend/.env',    notes: 'Edit backend/.env with your Anthropic key, Gmail SMTP creds (optional).' },
      { step: 2, title: 'Spin up Postgres',  cmd: 'docker compose up -d db',                                                                      notes: 'Or run native Postgres. Django migrates automatically in step 4.' },
      { step: 3, title: 'Backend venv',      cmd: 'cd backend && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt',                                                     notes: 'Use backend/.venv — the launch.json depends on it.' },
      { step: 4, title: 'Migrate + seed',    cmd: 'python manage.py migrate && python manage.py seed_demo --scenario=klikk-rentals-v1',          notes: 'Creates fully-signed demo lease so Overview/Maintenance have data.' },
      { step: 5, title: 'Gotenberg',         cmd: 'docker compose up -d gotenberg',                                                                notes: 'Required for PDF generation tests.' },
      { step: 6, title: 'Admin SPA',         cmd: 'cd admin && nvm use 20 && npm install && npm run dev -- --host 127.0.0.1',                     notes: 'If 5173 is blank — Cursor may be port-forwarding. See CLAUDE.md fix.' },
      { step: 7, title: 'Backend',           cmd: 'cd backend && .venv/bin/daphne -b 127.0.0.1 -p 8000 config.asgi:application',                  notes: 'Daphne supports Channels WebSockets; runserver does not.' },
      { step: 8, title: 'Tests',             cmd: 'pytest backend --reuse-db -x',                                                                  notes: 'Expect <2 min for unit + integration targets.' },
    ],
    // Prod deployment sketch
    prod: [
      { area: 'Compute',   current: 'TBD — likely AWS ECS Fargate or Hetzner VPS', notes: 'Django via Daphne; Nginx fronting; Cloudflare proxy.' },
      { area: 'Database',  current: 'AWS RDS Postgres 16 (af-south-1)',            notes: 'Multi-AZ, encryption at rest with customer-managed KMS key.' },
      { area: 'Storage',   current: 'AWS S3 (af-south-1)',                          notes: 'SSE-KMS, lifecycle rules, object lock for audit trail.' },
      { area: 'Secrets',   current: 'AWS Secrets Manager',                          notes: 'Rotated monthly; IAM-gated. No .env in prod.' },
      { area: 'CDN',       current: 'Cloudflare',                                    notes: 'WAF + DDoS; caching for static admin + website.' },
      { area: 'Email',     current: 'AWS SES (af-south-1 when available, else eu-west-1)', notes: 'DKIM + SPF + DMARC on klikk.co.za.' },
      { area: 'Observability', current: 'Sentry + CloudWatch (planned)',            notes: 'Sentry DSN env; structured JSON logs to CloudWatch.' },
      { area: 'CI/CD',     current: 'GitHub Actions (planned)',                     notes: 'PR: lint + unit; main: full battery + staging deploy; tag: prod deploy.' },
      { area: 'Backups',   current: 'RDS automated snapshots (7 days)',             notes: 'Weekly logical dump to S3 with 90-day retention.' },
    ],
  };

  const statCards = env.stats.map(([k,v,h]) => `
    <div class="en-stat"><div class="sk">${k}</div><div class="sv">${v}</div><div class="sh">${h}</div></div>
  `).join('');

  const prereqRows = env.prereqs.map(p => `
    <tr>
      <td>${p.tool}</td>
      <td><code>${p.install}</code></td>
      <td>${p.notes}</td>
    </tr>
  `).join('');

  const dockerRows = env.docker.map(d => `
    <tr>
      <td><span class="dk-name">${d.name}</span></td>
      <td><code>${d.image}</code></td>
      <td><code>${d.port}</code></td>
      <td>${d.purpose}</td>
    </tr>
  `).join('');

  const portRows = env.ports.map(p => `
    <tr>
      <td><code class="pt-num">${p.port}</code></td>
      <td>${p.svc}</td>
      <td><code>${p.url}</code></td>
      <td><span class="pt-src">${p.src}</span></td>
    </tr>
  `).join('');

  const envGroups = env.envGroups.map(g => `
    <div class="en-group">
      <h5>${g.label}</h5>
      <table class="en-vars">
        <thead><tr><th>Key</th><th>Default</th><th>Example</th><th>Purpose</th></tr></thead>
        <tbody>${g.vars.map(v => `
          <tr>
            <td><code class="v-key">${v.key}</code></td>
            <td><code class="v-def">${v.default}</code></td>
            <td><code>${v.example}</code></td>
            <td>${v.purpose}</td>
          </tr>`).join('')}</tbody>
      </table>
    </div>
  `).join('');

  const workflowSteps = env.workflow.map(w => `
    <div class="en-wf">
      <div class="wf-step">${w.step}</div>
      <div class="wf-body">
        <h5>${w.title}</h5>
        <pre><code>${w.cmd}</code></pre>
        <p>${w.notes}</p>
      </div>
    </div>
  `).join('');

  const prodRows = env.prod.map(p => `
    <tr>
      <td><strong>${p.area}</strong></td>
      <td>${p.current}</td>
      <td>${p.notes}</td>
    </tr>
  `).join('');

  return `
    <style>
      .en-tabs{position:sticky;top:0;z-index:10;background:#F5F5F8;padding:12px 0;display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #E5E5EC;margin-bottom:24px}
      .en-tabs a{padding:8px 14px;border-radius:20px;background:#fff;font-size:13px;font-weight:500;color:#595B8F;text-decoration:none;border:1px solid #E5E5EC}
      .en-tabs a.active{background:#2B2D6E;color:#fff;border-color:#2B2D6E}
      .en-sec{margin-bottom:48px;scroll-margin-top:72px}
      .en-sec h3{font-family:Fraunces,serif;font-weight:700;font-size:28px;margin:0 0 6px;color:#2B2D6E}
      .en-sec .sec-sub{color:#595B8F;font-size:14px;margin:0 0 20px}
      .en-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .en-stat{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px}
      .en-stat .sk{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8E90B8}
      .en-stat .sv{font-family:Fraunces,serif;font-weight:700;font-size:22px;color:#2B2D6E;line-height:1.15;margin:4px 0}
      .en-stat .sh{font-size:12px;color:#595B8F}
      .en-tbl{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .en-tbl th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .en-tbl td{padding:8px 12px;border-top:1px solid #F0F1F8;vertical-align:top;color:#2B2D6E}
      .en-tbl code{font-family:ui-monospace,monospace;font-size:11.5px;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px;word-break:break-word}
      .dk-name{background:#EEE8FF;color:#2B2D6E;padding:2px 8px;border-radius:6px;font-family:ui-monospace,monospace;font-size:11.5px}
      .pt-num{background:#E2E3F7;color:#2B2D6E}
      .pt-src{font-size:11px;color:#8E90B8}
      .en-group{margin-bottom:24px}
      .en-group h5{font-family:Fraunces,serif;font-weight:700;font-size:16px;margin:0 0 8px;color:#2B2D6E}
      .en-vars{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .en-vars th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .en-vars td{padding:8px 12px;border-top:1px solid #F0F1F8;vertical-align:top;color:#2B2D6E}
      .en-vars code{font-family:ui-monospace,monospace;font-size:11.5px;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px;word-break:break-word}
      .en-vars .v-key{background:#EEE8FF;color:#2B2D6E}
      .en-vars .v-def{background:#FBF3E0;color:#8B4A1F}
      .en-wfs{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .en-wf{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px;display:flex;gap:12px}
      .wf-step{flex:0 0 36px;height:36px;border-radius:50%;background:#2B2D6E;color:#fff;display:flex;align-items:center;justify-content:center;font-family:Fraunces,serif;font-weight:700;font-size:16px}
      .wf-body{flex:1;min-width:0}
      .wf-body h5{margin:0 0 6px;font-size:14px;color:#2B2D6E}
      .wf-body pre{background:#0F172A;color:#E2E8F0;padding:8px 12px;border-radius:8px;margin:0 0 6px;font-size:11.5px;overflow-x:auto;white-space:pre-wrap;word-break:break-word}
      .wf-body pre code{font-family:ui-monospace,monospace;background:none;color:inherit;padding:0}
      .wf-body p{margin:0;font-size:12px;color:#595B8F;line-height:1.55}
      @media (max-width:900px){.en-stats{grid-template-columns:1fr 1fr}.en-wfs{grid-template-columns:1fr}}
    </style>

    <nav class="en-tabs">
      <a href="#en-stats" class="active">At a glance</a>
      <a href="#en-prereq">Prereqs</a>
      <a href="#en-docker">Docker</a>
      <a href="#en-ports">Ports</a>
      <a href="#en-vars">Env vars</a>
      <a href="#en-wf">Workflow</a>
      <a href="#en-prod">Production</a>
    </nav>

    <section id="en-stats" class="en-sec">
      <h3>At a glance</h3>
      <p class="sec-sub">The shape of the environment an agent must stand up to run Klikk locally, run the tests, and ship it to production.</p>
      <div class="en-stats">${statCards}</div>
    </section>

    <section id="en-prereq" class="en-sec">
      <h3>Prereqs</h3>
      <p class="sec-sub">Six tools need to be on the machine before anything runs.</p>
      <table class="en-tbl">
        <thead><tr><th>Tool</th><th>Install</th><th>Notes</th></tr></thead>
        <tbody>${prereqRows}</tbody>
      </table>
    </section>

    <section id="en-docker" class="en-sec">
      <h3>Docker compose</h3>
      <p class="sec-sub">The containerised pieces. Pick individual services for dev (<code>db</code>, <code>gotenberg</code>) or run the full stack for integration work.</p>
      <table class="en-tbl">
        <thead><tr><th>Service</th><th>Image</th><th>Port</th><th>Purpose</th></tr></thead>
        <tbody>${dockerRows}</tbody>
      </table>
    </section>

    <section id="en-ports" class="en-sec">
      <h3>Ports</h3>
      <p class="sec-sub">Fourteen ports across backend, admin, website, mobile shells, and prototype servers. Conflicts with 5173 are almost always Cursor port-forwarding — check the Ports view.</p>
      <table class="en-tbl">
        <thead><tr><th>Port</th><th>Service</th><th>URL</th><th>Source</th></tr></thead>
        <tbody>${portRows}</tbody>
      </table>
    </section>

    <section id="en-vars" class="en-sec">
      <h3>Environment variables</h3>
      <p class="sec-sub">Grouped by concern. Anything marked <code>(required)</code> blocks boot. Anything marked <code>(stub)</code> falls back to log-only mode if missing.</p>
      ${envGroups}
    </section>

    <section id="en-wf" class="en-sec">
      <h3>Local dev workflow</h3>
      <p class="sec-sub">From clean clone to first request in eight steps.</p>
      <div class="en-wfs">${workflowSteps}</div>
    </section>

    <section id="en-prod" class="en-sec">
      <h3>Production</h3>
      <p class="sec-sub">Sketch of the target prod stack. CI/CD, observability, and secrets management are the biggest open items.</p>
      <table class="en-tbl">
        <thead><tr><th>Area</th><th>Target</th><th>Notes</th></tr></thead>
        <tbody>${prodRows}</tbody>
      </table>
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.en-tabs a');
        const secs = [...tabs].map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
        tabs.forEach(t => t.addEventListener('click', () => {
          tabs.forEach(x => x.classList.remove('active'));
          t.classList.add('active');
        }));
        function onScroll(){
          const y = window.scrollY + 120;
          let active = secs[0];
          for (const s of secs) { if (s.offsetTop <= y) active = s; }
          tabs.forEach(t => {
            t.classList.toggle('active', t.getAttribute('href') === '#' + active.id);
          });
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- Copy library (SA English, voice, buttons, emptystates, errors) ---------- */
function pageCopy() {
  const copy = {
    stats: [
      ['Language',      'SA English', 'British spelling, local idiom, no Americanisms'],
      ['Voice',         'Direct · warm · plain', 'Fewer words. No jargon. No filler. No emoji in tenant-facing flows.'],
      ['Reading level', 'Grade 7–8',  'Test with Hemingway or Flesch. Tenants are not SaaS buyers.'],
      ['Button rule',   'Verb + noun', '"Sign lease", "Pay rent", "Upload ID" — not "Submit" or "Continue".'],
      ['Error rule',    'Specific + actionable', 'Tell them what went wrong AND what to do next.'],
      ['Tone markers',  '3',          'Confident (not chirpy), helpful (not pushy), honest (not defensive).'],
    ],
    principles: [
      { title: 'SA English, always',          body: 'Realise not realize. Colour not color. Cheque not check. Use Rand (R) and 100 000 with a space, not 100,000. When in doubt, Oxford dictionary wins.' },
      { title: 'Verb + noun for actions',     body: '"Sign lease" beats "Click here to sign". "Pay rent" beats "Continue". The button is a verb on the thing being verbed.' },
      { title: 'Short sentences',             body: 'If a sentence runs past 18 words, break it. The tenant is reading on a 5-inch screen in a taxi.' },
      { title: 'No jargon unless required',   body: 'Say "monthly rent", not "recurring payable". Say "deposit", not "security instrument". Exception: legal terms that must be precise (lease, mandate, OTP).' },
      { title: 'Plain truths over cleverness',body: '"Your rent is 4 days late" > "Oops! Looks like your rent took a detour." Wit is for marketing; product copy is for humans under stress.' },
      { title: 'Name the next action',        body: 'Every error and empty state ends with a verb the user can do. "Add a unit to start" beats "No units yet".' },
      { title: 'Numbers own their currency',  body: 'Always "R1 250,00" — R, thin-space group, comma decimal. Never USD-style "1,250.00" unless rendering an imported statement verbatim.' },
      { title: 'Dates are SA format',         body: '"17 Apr 2026" or "2026-04-17". Never "4/17/2026". Relative dates ("in 3 days") are fine in prose, exact in legal copy.' },
      { title: 'No emoji in tenant flows',    body: 'Allowed in agent UI (celebration on move-in, warning triangles). Never in signing, payment, eviction, or tribunal-adjacent screens.' },
      { title: 'POPIA-safe consent copy',     body: 'Checkboxes phrased as specific consents, not "I agree to terms". Each cross-border transfer gets its own line, per POPIA s11.' },
    ],
    // Button labels — grouped by workflow
    buttons: [
      { group: 'Leasing',     use: 'Start a lease',             label: 'Draft lease',          notes: '"Start lease" feels incomplete. "Draft" signals it\'s editable.' },
      { group: 'Leasing',     use: 'Send lease for signing',    label: 'Send for signing',     notes: 'Not "Send lease" — ambiguous with "send a copy".' },
      { group: 'Leasing',     use: 'Sign lease (tenant)',        label: 'Sign lease',           notes: 'Never "I agree" — signing is an event, not an opinion.' },
      { group: 'Leasing',     use: 'Renew an existing lease',   label: 'Renew lease',          notes: 'On the lease, not a dropdown — single purpose.' },
      { group: 'Leasing',     use: 'End lease (tenant notice)', label: 'Give 2-month notice',  notes: 'Makes the commitment explicit — not "Move out" or "Cancel".' },
      { group: 'Leasing',     use: 'Terminate lease (agent)',   label: 'Terminate lease',      notes: 'Destructive; requires confirm. Not "Cancel" (ambiguous with undo).' },
      { group: 'Payment',     use: 'Primary pay action',        label: 'Pay rent',             notes: 'Always name the thing being paid. "Pay now" is too vague.' },
      { group: 'Payment',     use: 'Pay deposit',               label: 'Pay deposit',          notes: 'Distinct button even if same gateway.' },
      { group: 'Payment',     use: 'Download statement',        label: 'Download statement',   notes: 'Not "Export" — tenants aren\'t analysts.' },
      { group: 'Payment',     use: 'Request refund',            label: 'Request refund',       notes: 'Deposit refund; triggers RHA workflow.' },
      { group: 'Maintenance', use: 'Report an issue',           label: 'Report issue',         notes: 'Tenant-facing. Not "Create ticket" or "Log request".' },
      { group: 'Maintenance', use: 'Dispatch supplier',         label: 'Send to supplier',     notes: 'Agent-facing. Plain and obvious.' },
      { group: 'Maintenance', use: 'Approve quote',             label: 'Approve quote',        notes: 'Pairs with "Request changes" or "Decline".' },
      { group: 'Maintenance', use: 'Mark as fixed',             label: 'Mark as resolved',     notes: 'Uses state name the system actually stores.' },
      { group: 'Inspection',  use: 'Start inspection',          label: 'Start inspection',     notes: 'Present tense — it happens in one sitting.' },
      { group: 'Inspection',  use: 'Sign inspection report',    label: 'Sign report',          notes: 'Tenant + agent both tap this.' },
      { group: 'Profile',     use: 'Update phone/address',      label: 'Save changes',         notes: 'Acceptable fallback when the noun is the whole form.' },
      { group: 'Profile',     use: 'Upload FICA docs',          label: 'Upload documents',     notes: 'Tenant/owner context. Agent copy can say "Upload FICA".' },
      { group: 'Profile',     use: 'Delete account',            label: 'Delete my account',    notes: 'Explicit ownership. Not "Delete account" — make it personal.' },
      { group: 'Vault33',     use: 'Approve data checkout',     label: 'Approve this request', notes: 'Short, specific. Never "Allow".' },
      { group: 'Vault33',     use: 'Revoke active checkout',    label: 'Revoke access',        notes: 'Destructive; pair with confirm modal.' },
      { group: 'Negative',    use: 'Close modal without saving',label: 'Cancel',               notes: 'The one place "Cancel" is right — reversing an intent.' },
      { group: 'Negative',    use: 'Delete anything',           label: 'Delete [noun]',        notes: 'Always name the noun: "Delete lease", "Delete property".' },
    ],
    // Empty states — one per core list
    empties: [
      { surface: 'Properties list',      title: 'Your portfolio is empty',         body: 'Add a property to begin tracking leases, deposits, and compliance.',             cta: 'Add property' },
      { surface: 'Tenants list',         title: 'No tenants yet',                  body: 'Tenants appear here once they\'re on an active lease.',                          cta: 'Create lease' },
      { surface: 'Leases list',          title: 'No leases yet',                   body: 'Draft a lease to capture the term, rent, and deposit for a new tenancy.',       cta: 'Draft lease' },
      { surface: 'Maintenance (agent)',  title: 'All quiet on the maintenance front', body: 'When a tenant reports an issue, or you raise one, it will land here.',       cta: 'Report issue' },
      { surface: 'Maintenance (tenant)', title: 'No open issues',                  body: 'Anything broken? Report it — photos help the supplier quote fast.',             cta: 'Report issue' },
      { surface: 'Suppliers',            title: 'Build your supplier directory',   body: 'Add plumbers, electricians, painters. You\'ll dispatch jobs to them in one tap.',cta: 'Add supplier' },
      { surface: 'Invoices (tenant)',    title: 'Nothing due',                     body: 'Your next invoice will appear around the 25th of this month.',                    cta: null },
      { surface: 'Invoices (agent)',     title: 'No invoices in this period',      body: 'Invoices get generated around rent due day for every active lease.',              cta: 'Generate now' },
      { surface: 'Inspections',          title: 'No inspections on file',          body: 'Inspections must be signed by tenant and agent within 7 days of move-in or move-out.', cta: 'Start inspection' },
      { surface: 'Documents (owner)',    title: 'Upload your FICA documents',      body: 'ID, proof of address (under 3 months), CIPC certificate for companies.',         cta: 'Upload documents' },
      { surface: 'Notifications',        title: "You're all caught up",            body: 'New messages, reminders, and signatures will appear here.',                      cta: null },
      { surface: 'Screening results',    title: 'No applicants yet',               body: 'When someone applies, their screening report and score land here.',              cta: null },
      { surface: 'Audit log',            title: 'Nothing to audit',                body: 'Actions taken on this property will be logged here — immutable, timestamped.',   cta: null },
      { surface: 'Vault33 inbox',        title: 'No pending requests',             body: 'When a bank, conveyancer, or agent asks to see your data, the request lands here for you to approve or decline.', cta: null },
    ],
    // Error messages — one per common failure
    errors: [
      { code: 'AUTH_INVALID',         ui: 'Login',                wrong: 'Invalid credentials.',                            right: "That email and password don't match. Check the email, then try again.",                                                 note: 'Specific but not informative enough to help account enumeration.' },
      { code: 'OTP_EXPIRED',          ui: 'OTP entry',            wrong: 'Token expired.',                                  right: 'This code has expired. Request a new one — they last 10 minutes.',                                                    note: 'Name the thing + what to do.' },
      { code: 'OTP_WRONG',            ui: 'OTP entry',            wrong: 'Wrong code.',                                     right: "That code didn't match. You have 4 tries left, then you'll need a new one.",                                            note: 'Show remaining attempts to reduce support load.' },
      { code: 'LEASE_DRAFT_INCOMPLETE',ui: 'Draft lease',          wrong: 'Validation error.',                                right: "We can't send this yet — the rent amount, start date, and tenant email are still missing.",                             note: 'List all missing fields at once, not one at a time.' },
      { code: 'SIGN_LINK_EXPIRED',    ui: 'Public sign page',     wrong: 'Link expired.',                                   right: 'This signing link expired on 17 Apr. Please ask your agent for a fresh link.',                                         note: 'Include the date — tenants forget.' },
      { code: 'PAYMENT_DECLINED',     ui: 'Pay rent',             wrong: 'Payment failed.',                                 right: "Your bank declined this payment. Try another card, or switch to EFT from the Pay menu.",                                note: 'Give at least one fallback route.' },
      { code: 'UPLOAD_TOO_LARGE',     ui: 'Upload documents',     wrong: 'File too large.',                                 right: 'This file is 14 MB — we can only accept files up to 10 MB. Try compressing it or splitting into two.',                  note: 'Show actual size vs limit.' },
      { code: 'UPLOAD_WRONG_TYPE',    ui: 'Upload documents',     wrong: 'Invalid file type.',                              right: "We accept PDF, JPG, and PNG. That looks like a HEIC — convert it first (on iPhone: Settings → Camera → Formats).",  note: 'Teach, don\'t just reject.' },
      { code: 'ROLE_FORBIDDEN',       ui: 'Deep link',            wrong: 'Forbidden.',                                      right: "You don't have access to this page. If you think that's a mistake, your agency admin can adjust your permissions.",     note: 'Never just "403" — it feels broken.' },
      { code: 'RATE_LIMIT',           ui: 'API',                  wrong: 'Too many requests.',                              right: "You've tried this too many times. Wait 5 minutes, then try again.",                                                    note: 'Give a concrete wait time.' },
      { code: 'CROSS_TENANT',         ui: 'Silent API',           wrong: '(nothing shown)',                                  right: 'Return 404, not 403 — never leak whether the resource exists.',                                                        note: 'Copy rule: do not echo the resource ID.' },
      { code: 'VAULT_LOAN_EXPIRED',   ui: 'Data subject view',    wrong: 'Access denied.',                                  right: "This request is no longer valid — the access window closed on 12 Apr. Ask the requester to send a new request.",       note: 'Empathetic but firm.' },
      { code: 'ESIGN_ALREADY_SIGNED', ui: 'Public sign page',     wrong: 'Already signed.',                                 right: "You've already signed this document. Check your email for the signed copy, or ask the agent to resend.",                 note: 'Idempotent UX.' },
      { code: 'NETWORK_OFFLINE',      ui: 'Anywhere',             wrong: 'Network error.',                                  right: "You're offline. Your changes are saved locally — we'll sync as soon as you're back online.",                             note: 'Mobile-first reality.' },
      { code: 'SERVER_5XX',           ui: 'Anywhere',             wrong: 'Something went wrong.',                           right: "Something broke on our end. We've logged it. If this keeps happening, email help@klikk.co.za with this code: 5XX-[id].", note: 'Give them a handle to quote.' },
    ],
    // Notification/message templates — email + SMS + push
    templates: [
      { kind: 'email', id: 'lease.sign.invite',      subject: 'Your new lease is ready to sign',                body: 'Hi {first_name},\n\nYour lease for {unit_address} is ready. Tap below to sign — it takes about 3 minutes.\n\n[Sign lease →]\n\nThis link expires on {expires_date}. If you have any questions, reply to this email.\n\n— The Klikk team', notes: 'Single clear CTA. Expiry visible. Plain text fallback.' },
      { kind: 'email', id: 'payment.late.reminder',  subject: 'Friendly reminder — rent is due',               body: 'Hi {first_name},\n\nRent for {month} ({amount}) is due. If you\'ve already paid, ignore this.\n\n[Pay rent →]\n\nNeed a payment plan? Reply here — we\'d rather talk than chase.\n\n— The Klikk team', notes: 'First reminder, friendly. Subsequent reminders escalate tone, not volume.' },
      { kind: 'sms',   id: 'otp.generic',            subject: null,                                             body: 'Klikk: your code is {code}. Valid 10 minutes. Never share this code — we\'ll never ask for it.',                                                                                                                                                   notes: '160 chars max. Includes anti-phishing line.' },
      { kind: 'sms',   id: 'maintenance.dispatched', subject: null,                                             body: 'Klikk: {supplier_name} ({supplier_phone}) will attend to your maintenance issue on {date}. Reply STOP to opt out.',                                                                                                                                         notes: 'Contact + date + opt-out per POPIA s69.' },
      { kind: 'sms',   id: 'inspection.reminder',    subject: null,                                             body: 'Klikk: your {kind} inspection is tomorrow at {time} at {unit_address}. Reply RESCHEDULE if you need a new slot.',                                                                                                                                             notes: 'Actionable reply keyword.' },
      { kind: 'push',  id: 'maintenance.update',     subject: 'Update on your maintenance request',            body: '{supplier_name} has {status} your request for {summary}.',                                                                                                                                                                                                   notes: 'iOS 180-char limit. Personal + informative.' },
      { kind: 'push',  id: 'vault.request.pending',  subject: 'Someone wants to see your data',                body: '{requester} is requesting access to your {scope} — tap to review before {expires_date}.',                                                                                                                                                                   notes: 'Vault33 loan slip — empowers the data subject.' },
      { kind: 'email', id: 'deposit.refund.pending', subject: 'Your deposit refund is processing',             body: 'Hi {first_name},\n\nWe\'ve received your deposit refund request. Here\'s what happens next:\n\n• Within 7 days — if there are no deductions\n• Within 14 days — if we need to pay contractors\n• Within 21 days — if you\'ve disputed the statement\n\nItemised statement attached.\n\n— The Klikk team', notes: 'RHA deadlines baked in — sets expectations correctly.' },
    ],
    // Taboos — don't-say list
    taboos: [
      { avoid: 'Oops!',                  use: 'Name the problem directly',           why: 'Pretending everything is cheerful when something broke feels dishonest.' },
      { avoid: 'Click here',             use: '[Verb + noun]',                       why: 'Screen readers read "click here" as a command with no context. And half the users are on touch.' },
      { avoid: 'Please',                 use: '(drop it)',                            why: 'Unless genuinely asking a favour, "please" is filler that slows the sentence.' },
      { avoid: 'Submit',                 use: 'Save changes / Sign lease / Pay rent', why: '"Submit" is web-1.0 form-speak. Name the outcome.' },
      { avoid: 'We value your privacy',  use: '(say what you\'ll do)',                why: 'Empty reassurance. POPIA notices must be specific.' },
      { avoid: 'Quickly / just / simply',use: '(cut)',                                 why: 'If something is quick, they\'ll feel it. Telling them it\'s simple patronises when it isn\'t.' },
      { avoid: 'Smart / AI-powered',     use: 'Name the thing it does',               why: 'In product UI. Fine in marketing. Tenants don\'t care what it is, they care what it does.' },
      { avoid: 'An error has occurred',  use: '[What broke + what to do]',            why: 'Generic errors triple support load.' },
      { avoid: 'Users',                  use: 'Tenant / agent / owner / supplier',    why: 'Name the role. "User" is engineer-speak.' },
      { avoid: 'Invalid',                use: '[Why, specifically]',                   why: 'Every "invalid email" should become "Email must include an @ and a domain, e.g. sipho@example.co.za".' },
    ],
  };

  const statCards = copy.stats.map(([k,v,h]) => `
    <div class="cp-stat"><div class="sk">${k}</div><div class="sv">${v}</div><div class="sh">${h}</div></div>
  `).join('');

  const principleCards = copy.principles.map(p => `
    <div class="cp-pri">
      <h5>${p.title}</h5>
      <p>${p.body}</p>
    </div>
  `).join('');

  // Buttons grouped
  const btnGroups = [...new Set(copy.buttons.map(b => b.group))];
  const btnSections = btnGroups.map(g => {
    const items = copy.buttons.filter(b => b.group === g);
    return `
      <div class="cp-btngrp">
        <h5>${g}</h5>
        <table class="cp-tbl">
          <thead><tr><th>When</th><th>Label</th><th>Notes</th></tr></thead>
          <tbody>${items.map(b => `
            <tr>
              <td>${b.use}</td>
              <td><button class="cp-btn">${b.label}</button></td>
              <td>${b.notes}</td>
            </tr>
          `).join('')}</tbody>
        </table>
      </div>
    `;
  }).join('');

  const emptyCards = copy.empties.map(e => `
    <div class="cp-empty">
      <div class="cp-e-surface">${e.surface}</div>
      <h5>${e.title}</h5>
      <p>${e.body}</p>
      ${e.cta ? `<button class="cp-btn">${e.cta}</button>` : '<div class="cp-nocta">no CTA — passive state</div>'}
    </div>
  `).join('');

  const errorRows = copy.errors.map(e => `
    <tr>
      <td><code>${e.code}</code><div class="err-ui">${e.ui}</div></td>
      <td class="err-wrong">✗ ${e.wrong}</td>
      <td class="err-right">✓ ${e.right}</td>
      <td class="err-note">${e.note}</td>
    </tr>
  `).join('');

  const tmplCards = copy.templates.map(t => `
    <div class="cp-tmpl tmpl-${t.kind}">
      <div class="tm-head">
        <span class="tm-kind">${t.kind}</span>
        <code class="tm-id">${t.id}</code>
      </div>
      ${t.subject ? `<div class="tm-subj"><strong>Subject:</strong> ${t.subject}</div>` : ''}
      <pre class="tm-body">${t.body}</pre>
      <p class="tm-note">${t.notes}</p>
    </div>
  `).join('');

  const tabooRows = copy.taboos.map(t => `
    <tr>
      <td class="tb-avoid">✗ ${t.avoid}</td>
      <td class="tb-use">✓ ${t.use}</td>
      <td>${t.why}</td>
    </tr>
  `).join('');

  return `
    <style>
      .cp-tabs{position:sticky;top:0;z-index:10;background:#F5F5F8;padding:12px 0;display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #E5E5EC;margin-bottom:24px}
      .cp-tabs a{padding:8px 14px;border-radius:20px;background:#fff;font-size:13px;font-weight:500;color:#595B8F;text-decoration:none;border:1px solid #E5E5EC}
      .cp-tabs a.active{background:#2B2D6E;color:#fff;border-color:#2B2D6E}
      .cp-sec{margin-bottom:48px;scroll-margin-top:72px}
      .cp-sec h3{font-family:Fraunces,serif;font-weight:700;font-size:28px;margin:0 0 6px;color:#2B2D6E}
      .cp-sec .sec-sub{color:#595B8F;font-size:14px;margin:0 0 20px}
      .cp-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .cp-stat{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px}
      .cp-stat .sk{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8E90B8}
      .cp-stat .sv{font-family:Fraunces,serif;font-weight:700;font-size:22px;color:#2B2D6E;line-height:1.15;margin:4px 0}
      .cp-stat .sh{font-size:12px;color:#595B8F}
      .cp-pris{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
      .cp-pri{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px;border-left:4px solid #FF3D7F}
      .cp-pri h5{margin:0 0 4px;font-size:14px;color:#2B2D6E}
      .cp-pri p{margin:0;font-size:12.5px;color:#595B8F;line-height:1.6}
      .cp-btngrp{margin-bottom:24px}
      .cp-btngrp h5{font-family:Fraunces,serif;font-weight:700;font-size:16px;margin:0 0 8px;color:#2B2D6E}
      .cp-tbl{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .cp-tbl th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .cp-tbl td{padding:10px 12px;border-top:1px solid #F0F1F8;vertical-align:middle;color:#2B2D6E}
      .cp-btn{background:#2B2D6E;color:#fff;border:none;padding:8px 14px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;font-family:'DM Sans',sans-serif}
      .cp-empties{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
      .cp-empty{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:18px;text-align:center}
      .cp-empty .cp-e-surface{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#8E90B8;margin-bottom:10px}
      .cp-empty h5{margin:0 0 6px;font-size:16px;color:#2B2D6E;font-family:Fraunces,serif;font-weight:700}
      .cp-empty p{margin:0 0 14px;font-size:13px;color:#595B8F;line-height:1.55}
      .cp-empty .cp-nocta{font-size:11px;color:#8E90B8;font-style:italic}
      .cp-errs{width:100%;border-collapse:collapse;font-size:12.5px;background:#fff;border:1px solid #E5E5EC;border-radius:12px;overflow:hidden}
      .cp-errs th{background:#F5F5F8;padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#595B8F}
      .cp-errs td{padding:10px 12px;border-top:1px solid #F0F1F8;vertical-align:top;color:#2B2D6E;line-height:1.55}
      .cp-errs code{font-family:ui-monospace,monospace;background:#F0F1F8;color:#2B2D6E;padding:2px 6px;border-radius:4px;font-size:11px}
      .cp-errs .err-ui{font-size:11px;color:#8E90B8;margin-top:3px}
      .cp-errs .err-wrong{color:#A4231F;background:#FFF1F1}
      .cp-errs .err-right{color:#166534;background:#F0FFF4}
      .cp-errs .err-note{font-size:11.5px;color:#595B8F;font-style:italic}
      .cp-tmpls{display:grid;grid-template-columns:1fr 1fr;gap:14px}
      .cp-tmpl{background:#fff;border:1px solid #E5E5EC;border-radius:12px;padding:14px;border-top:4px solid #8E90B8}
      .cp-tmpl.tmpl-email{border-top-color:#5B5DC7}
      .cp-tmpl.tmpl-sms{border-top-color:#22C55E}
      .cp-tmpl.tmpl-push{border-top-color:#F59E0B}
      .cp-tmpl .tm-head{display:flex;gap:8px;align-items:center;margin-bottom:8px}
      .cp-tmpl .tm-kind{font-size:10px;text-transform:uppercase;letter-spacing:.08em;padding:2px 8px;border-radius:6px;font-weight:600}
      .cp-tmpl.tmpl-email .tm-kind{background:#E7EAF9;color:#2B2D6E}
      .cp-tmpl.tmpl-sms .tm-kind{background:#DFF5E3;color:#166534}
      .cp-tmpl.tmpl-push .tm-kind{background:#FDE9D0;color:#8B4A1F}
      .cp-tmpl .tm-id{font-family:ui-monospace,monospace;font-size:11px;background:#F0F1F8;color:#595B8F;padding:2px 6px;border-radius:4px}
      .cp-tmpl .tm-subj{font-size:12.5px;color:#2B2D6E;margin-bottom:6px}
      .cp-tmpl .tm-body{background:#FBFBFD;border:1px solid #F0F1F8;padding:10px;border-radius:8px;font-family:'DM Sans',sans-serif;font-size:12px;color:#2B2D6E;white-space:pre-wrap;line-height:1.6;margin:0 0 8px}
      .cp-tmpl .tm-note{font-size:11px;color:#595B8F;font-style:italic;margin:0}
      .cp-tabs{}
      .tb-avoid{color:#A4231F;background:#FFF1F1;font-weight:500}
      .tb-use{color:#166534;background:#F0FFF4;font-weight:500}
      @media (max-width:900px){.cp-stats,.cp-pris,.cp-empties,.cp-tmpls{grid-template-columns:1fr}}
    </style>

    <nav class="cp-tabs">
      <a href="#cp-stats" class="active">At a glance</a>
      <a href="#cp-principles">Principles</a>
      <a href="#cp-buttons">Buttons</a>
      <a href="#cp-empties">Empty states</a>
      <a href="#cp-errors">Errors</a>
      <a href="#cp-templates">Templates</a>
      <a href="#cp-taboos">Don't say</a>
    </nav>

    <section id="cp-stats" class="cp-sec">
      <h3>At a glance</h3>
      <p class="sec-sub">The voice and vocabulary of Klikk — SA English, plain, direct, verb-led. This page is the copy reference for every screen.</p>
      <div class="cp-stats">${statCards}</div>
    </section>

    <section id="cp-principles" class="cp-sec">
      <h3>Principles</h3>
      <p class="sec-sub">Ten rules that govern every label, error, and email. When in doubt, fewer words and a clearer verb.</p>
      <div class="cp-pris">${principleCards}</div>
    </section>

    <section id="cp-buttons" class="cp-sec">
      <h3>Buttons</h3>
      <p class="sec-sub">The canonical label for every primary action, grouped by workflow. Match these exactly — don't paraphrase.</p>
      ${btnSections}
    </section>

    <section id="cp-empties" class="cp-sec">
      <h3>Empty states</h3>
      <p class="sec-sub">Every list needs one. Format: what-it-is, why-it's-empty, what-to-do. If no useful action exists, no CTA.</p>
      <div class="cp-empties">${emptyCards}</div>
    </section>

    <section id="cp-errors" class="cp-sec">
      <h3>Errors</h3>
      <p class="sec-sub">Every error names the problem and the next step. Never just a code, never just "something went wrong".</p>
      <table class="cp-errs">
        <thead><tr><th>Code · UI</th><th>Don't</th><th>Do</th><th>Why</th></tr></thead>
        <tbody>${errorRows}</tbody>
      </table>
    </section>

    <section id="cp-templates" class="cp-sec">
      <h3>Templates</h3>
      <p class="sec-sub">Transactional email, SMS, and push. Short, useful, with one CTA. SMS is 160 characters max. Push body under 180.</p>
      <div class="cp-tmpls">${tmplCards}</div>
    </section>

    <section id="cp-taboos" class="cp-sec">
      <h3>Don't say</h3>
      <p class="sec-sub">A short list of phrases to replace. Copy these to the style-check linter when we ship one.</p>
      <table class="cp-tbl">
        <thead><tr><th>Avoid</th><th>Use instead</th><th>Why</th></tr></thead>
        <tbody>${tabooRows}</tbody>
      </table>
    </section>

    <script>
      (function(){
        const tabs = document.querySelectorAll('.cp-tabs a');
        const secs = [...tabs].map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
        tabs.forEach(t => t.addEventListener('click', () => {
          tabs.forEach(x => x.classList.remove('active'));
          t.classList.add('active');
        }));
        function onScroll(){
          const y = window.scrollY + 120;
          let active = secs[0];
          for (const s of secs) { if (s.offsetTop <= y) active = s; }
          tabs.forEach(t => {
            t.classList.toggle('active', t.getAttribute('href') === '#' + active.id);
          });
        }
        window.addEventListener('scroll', onScroll, { passive: true });
      })();
    </script>
  `;
}

/* ---------- Overview (Product one-pager) ---------- */
function pageOverview() {
  const overviewFacts = [
    ['Product',         'Klikk'],
    ['Parent',          'Tremly Property Manager'],
    ['Tagline',         'One click, every rental'],
    ['Domain',          'klikk.co.za · app.klikk.co.za'],
    ['Category',        'Property-management SaaS (vertical)'],
    ['Market',          'South Africa — residential rentals'],
    ['Launch status',   'v1 shipping · full 15-stage rental lifecycle live'],
    ['Primary user',    'Founder-landlord — owns the properties, operates the platform'],
    ['All roles',       'landlord · agent · tenant · owner · supplier · admin'],
    ['Product lines',   'Klikk Rentals (live) · Klikk Real Estate (roadmap) · Klikk BI (roadmap)'],
    ['Platforms',       '6 surfaces — see Platforms section'],
    ['Stack · backend', 'Django 5 · DRF · PostgreSQL · Daphne (ASGI) · Gotenberg (PDF)'],
    ['Stack · web',     'Vue 3 · Vite · Tailwind 3 · Pinia · Vue Router'],
    ['Stack · mobile',  'Quasar · Capacitor · Vue 3 (replaces earlier Flutter build)'],
    ['Stack · AI',      'Anthropic Claude (cross-border · s72 safeguards)'],
    ['Icon library',    'Phosphor Icons (MIT · 9,000+ glyphs · 6 weights)'],
    ['Typography',      'Inter 15 px base (product) · Bricolage Grotesque 800 (marketing)'],
    ['Brand colours',   'Navy #2B2D6E · Accent Pink #FF3D7F'],
    ['Region',          'af-south-1 (AWS Cape Town) · POPIA data residency'],
    ['Compliance',      'POPIA · PAIA · RHA · FICA · NCA · ECTA · CPA · Prescription Act'],
    ['Languages',       'English (primary) · Afrikaans (planned)'],
    ['Currency',        'ZAR · R-formatted everywhere · thousands separator · 2 decimals'],
    ['Timezone',        'Africa/Johannesburg (SAST, UTC+2, no DST)'],
    ['API',             'REST · /api/v1/ · JWT auth (simplejwt)'],
    ['Auth flow',       'Email + password · JWT access + refresh · role-based route guards'],
    ['Sub-processors',  '9 (see Data flow) — TransUnion · Anthropic · AWS · Gotenberg · P24 · SMS · Email · Payments · Suppliers'],
  ];

  const functionality = [
    { icon: 'ph-megaphone',        title: 'Tenant acquisition',   body: 'Advertise vacancies on Property24 & Private Property, run viewings, collect applications, and screen applicants with AI-scored credit / criminal / ID / employment checks.', stages: '1–4' },
    { icon: 'ph-file-text',        title: 'Lease execution',       body: 'AI generates RHA-compliant lease from a merge-field template, sent for e-signing (native Gotenberg-signed PDF), deposit + first rent collected and lodged in interest-bearing account.', stages: '5–7' },
    { icon: 'ph-arrows-clockwise', title: 'Turnaround',            body: 'Overnight handover between outgoing and incoming tenant — joint inspections with photo evidence, supplier dispatch for snag list, onboarding + tenant portal setup.', stages: '8–11' },
    { icon: 'ph-house-line',       title: 'Active tenancy',        body: 'Monthly rent tracking with payment reconciliation, in-app tenant chat with AI triage, maintenance tickets dispatched to matched suppliers, receipts on demand.', stages: '12–13' },
    { icon: 'ph-signature',        title: 'Renewal & closeout',    body: 'Renewal notification 80 business days before expiry; tenant chooses renew, month-to-month, or vacate. On exit: itemised deposit refund with full accrued interest within 7/14/21 days.', stages: '14–15' },
    { icon: 'ph-buildings',        title: 'Owner back-office',     body: 'Landlord portal: every property, every lease, every payment, every document — owner-scoped views, monthly statements, year-end schedules, FICA/compliance document vault.', stages: 'cross-cutting' },
    { icon: 'ph-sparkle',          title: 'AI agent workbench',    body: 'Natural-language control of the entire platform. Draft leases, answer tenant questions, chase late rent, triage maintenance, summarise the week — all from one chat box.', stages: 'cross-cutting' },
    { icon: 'ph-chart-line-up',    title: 'Business intelligence', body: 'Portfolio dashboard: occupancy, arrears ageing, yield per property, maintenance spend, deposit pool, renewal pipeline — with export to CSV / PDF.', stages: 'cross-cutting · roadmap' },
  ];

  const platforms = [
    { name: 'Admin SPA',         stack: 'Vue 3 + Vite + Tailwind',        port: 5173, url: 'app.klikk.co.za',       who: 'agents · owners · suppliers',      status: 'live' },
    { name: 'Tenant mobile',     stack: 'Quasar + Capacitor (iOS/Android)', port: 5177, url: 'native app stores',     who: 'tenants',                           status: 'beta' },
    { name: 'Tenant web',        stack: 'Vue 3 + Vite',                    port: 5174, url: 'my.klikk.co.za (planned)', who: 'tenants (browser fallback)',    status: 'legacy' },
    { name: 'Agent app',         stack: 'Quasar',                          port: 5176, url: 'agent.klikk.co.za (planned)', who: 'field agents (mobile)',   status: 'planned' },
    { name: 'Marketing website', stack: 'Astro',                           port: 4321, url: 'klikk.co.za',            who: 'prospects',                         status: 'build' },
    { name: 'Backend API',       stack: 'Django 5 · DRF · Daphne · Postgres', port: 8000, url: 'api.klikk.co.za',    who: 'serves every client',               status: 'live' },
    { name: 'Gotenberg (PDF)',   stack: 'Docker service',                  port: 3000, url: 'internal',               who: 'HTML→PDF for leases / reports',     status: 'live' },
    { name: 'Prototypes workbench', stack: 'Node HTTP (this server)',      port: 8006, url: 'localhost',              who: 'founder + build agents',            status: 'internal' },
  ];

  const css = `
  <style>
    .ov-wrap{padding:40px 56px 120px;max-width:1100px}
    .ov-head h1{font-family:'Fraunces',serif;font-size:44px;font-weight:700;line-height:1.05;margin:0 0 10px;letter-spacing:-.02em}
    .ov-head p.kicker{color:#6c6e92;font-size:15px;margin:0 0 36px;max-width:720px;line-height:1.55}
    .ov-head .doc-badge{display:inline-flex;align-items:center;gap:8px;padding:5px 12px;border-radius:999px;background:#fff;border:1px solid #EFEFF5;font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#8a8ca8;margin-bottom:18px}
    .ov-head .doc-badge .dot{width:6px;height:6px;border-radius:999px;background:#FF3D7F;animation:klikk-pulse 1.6s ease-in-out infinite}
    @keyframes klikk-pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.55;transform:scale(1.4)}}
    .ov-head h2{font-family:'Fraunces',serif;font-size:26px;font-weight:700;margin:56px 0 6px;letter-spacing:-.01em}
    .ov-head h2 + .kicker{margin-bottom:22px}
    .ov-table{background:#fff;border-radius:16px;box-shadow:0 1px 3px rgba(43,45,110,.06),0 4px 10px -4px rgba(43,45,110,.08);overflow:hidden;border:1px solid #EFEFF5}
    .ov-row{display:grid;grid-template-columns:220px 1fr;padding:13px 22px;border-bottom:1px solid #F3F3F8;font-size:14px;line-height:1.5}
    .ov-row:last-child{border-bottom:0}
    .ov-row:nth-child(even){background:#FAFAFC}
    .ov-row .k{font-weight:600;color:#8a8ca8;font-size:12px;text-transform:uppercase;letter-spacing:.06em;padding-top:2px}
    .ov-row .v{color:#2B2D6E;font-weight:500}
    .ov-summary{background:linear-gradient(160deg,#fff,#FAFAFC);border-radius:16px;border:1px solid #EFEFF5;padding:32px 36px;box-shadow:0 1px 3px rgba(43,45,110,.05)}
    .ov-summary p{font-size:15.5px;line-height:1.72;color:#3a3c5f;margin:0 0 18px}
    .ov-summary p:last-child{margin-bottom:0}
    .ov-summary strong{color:#2B2D6E;font-weight:600}
    .ov-summary em{color:#FF3D7F;font-style:normal;font-weight:600}
    .ov-func{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
    .ov-func-card{background:#fff;border:1px solid #EFEFF5;border-radius:14px;padding:22px 24px;display:grid;grid-template-columns:44px 1fr;gap:16px;align-items:start;transition:all .12s}
    .ov-func-card:hover{border-color:#FF3D7F;box-shadow:0 6px 18px -8px rgba(255,61,127,.25);transform:translateY(-1px)}
    .ov-func-card .ico{width:44px;height:44px;border-radius:12px;background:#F5F5F8;display:flex;align-items:center;justify-content:center;font-size:22px;color:#2B2D6E}
    .ov-func-card .t{font-size:15px;font-weight:600;margin:2px 0 6px;color:#2B2D6E;display:flex;justify-content:space-between;align-items:center;gap:10px}
    .ov-func-card .stage{font-size:10.5px;font-weight:600;background:#F5F5F8;color:#8a8ca8;padding:3px 8px;border-radius:999px;letter-spacing:.04em}
    .ov-func-card .b{font-size:13.5px;color:#6c6e92;line-height:1.55;margin:0}
    .ov-platforms{background:#fff;border-radius:16px;border:1px solid #EFEFF5;overflow:hidden;box-shadow:0 1px 3px rgba(43,45,110,.05)}
    .ov-plat-head{display:grid;grid-template-columns:1.3fr 1.6fr .6fr 1.4fr 1.3fr .7fr;gap:12px;padding:14px 22px;background:#FAFAFC;border-bottom:1px solid #EFEFF5;font-size:11px;font-weight:600;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em}
    .ov-plat-row{display:grid;grid-template-columns:1.3fr 1.6fr .6fr 1.4fr 1.3fr .7fr;gap:12px;padding:15px 22px;border-bottom:1px solid #F3F3F8;font-size:13.5px;align-items:center}
    .ov-plat-row:last-child{border-bottom:0}
    .ov-plat-row .nm{font-weight:600;color:#2B2D6E}
    .ov-plat-row .st,.ov-plat-row .pt,.ov-plat-row .who,.ov-plat-row .url{color:#6c6e92}
    .ov-plat-row .pt{font-family:'SF Mono',Menlo,Consolas,monospace;font-size:12.5px}
    .status-pill{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase}
    .status-pill[data-s="live"]{background:#E8F7EE;color:#1a7a3a}
    .status-pill[data-s="beta"]{background:#FFF3DC;color:#9a6a00}
    .status-pill[data-s="build"]{background:#E5EAFF;color:#3840a8}
    .status-pill[data-s="planned"]{background:#F0F0F4;color:#7a7a9c}
    .status-pill[data-s="legacy"]{background:#FFE8EA;color:#A12131}
    .status-pill[data-s="internal"]{background:#F5EAFF;color:#6633a8}
    .ov-nextgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}
    .ov-next{background:#fff;border:1px dashed #D7D8E8;border-radius:12px;padding:14px 16px;color:#8a8ca8;font-size:12px;line-height:1.5}
    .ov-next strong{display:block;font-size:13.5px;color:#2B2D6E;margin-bottom:4px}
    .ov-next[data-ready="yes"]{border-style:solid;border-color:#EFEFF5;background:#FAFAFC}
    .ov-next[data-ready="yes"] strong::after{content:'';display:inline-block;width:6px;height:6px;border-radius:999px;background:#1a7a3a;margin-left:6px;vertical-align:middle}
  </style>
  <link href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css" rel="stylesheet">
  `;

  const facts = overviewFacts.map(([k, v]) => `
    <div class="ov-row"><div class="k">${k}</div><div class="v">${v}</div></div>
  `).join('');

  const func = functionality.map(f => `
    <div class="ov-func-card">
      <div class="ico"><i class="ph ${f.icon}"></i></div>
      <div>
        <div class="t"><span>${f.title}</span><span class="stage">${f.stages}</span></div>
        <p class="b">${f.body}</p>
      </div>
    </div>
  `).join('');

  const plat = platforms.map(p => `
    <div class="ov-plat-row">
      <div class="nm">${p.name}</div>
      <div class="st">${p.stack}</div>
      <div class="pt">${p.port || '—'}</div>
      <div class="who">${p.who}</div>
      <div class="url">${p.url}</div>
      <div><span class="status-pill" data-s="${p.status}">${p.status}</span></div>
    </div>
  `).join('');

  return `
    ${css}
    <div class="ov-wrap">
      <div class="ov-head">
        <div class="doc-badge"><span class="dot"></span> One-pager for build agents</div>
        <h1>Klikk</h1>
        <p class="kicker">Everything an engineer, designer, or AI agent needs to know about the app — on one page. Start here, then drill into Flows, Components, or Data.</p>

        <h2>1 &nbsp;·&nbsp; Overview</h2>
        <p class="kicker">Facts at a glance — read top-to-bottom before writing a single line of code.</p>
        <div class="ov-table">${facts}</div>

        <h2>2 &nbsp;·&nbsp; What the app does</h2>
        <p class="kicker">In words.</p>
        <div class="ov-summary">
          <p><strong>Klikk is a turn-key residential rental-management platform built specifically for South African landlords and agents.</strong> It automates the entire rental lifecycle — from the moment a tenant gives notice to the final deposit refund 14 months later — in one place, on every device the landlord, tenant, owner, or supplier happens to be using.</p>
          <p>Unlike generic international property tools, Klikk is written on top of South African law. Every workflow is <strong>RHA-compliant</strong>, every data flow is <strong>POPIA-safe</strong>, every counterparty document is <strong>FICA-ready</strong>, and every deposit sits in an interest-bearing account with interest accruing from the day of lodging — as the law requires. The platform is multi-tenant (each landlord's data is isolated) and multi-role: the same property surfaces differently to the landlord, the tenant, the owner, and the contractor working on it.</p>
          <p>At the centre is an <em>AI agent workbench</em> that handles the tasks landlords usually outsource to expensive managing agents — screening applicants, drafting leases, answering tenant questions, dispatching maintenance, chasing payments, summarising the week. The founder of Klikk is also a landlord; the platform is built on live rental properties, and every feature is battle-tested on real tenants before it ships.</p>
        </div>

        <h2>3 &nbsp;·&nbsp; Functionality</h2>
        <p class="kicker">Eight capability groups — mapped to the 15-stage lifecycle. Numbers in each card refer to the stages covered (see Flows).</p>
        <div class="ov-func">${func}</div>

        <h2>4 &nbsp;·&nbsp; Platforms</h2>
        <p class="kicker">Eight surfaces. Each runs the same API and reads from the same Postgres — the difference is who the screen is for.</p>
        <div class="ov-platforms">
          <div class="ov-plat-head">
            <div>Surface</div><div>Stack</div><div>Port</div><div>Who uses it</div><div>URL</div><div>Status</div>
          </div>
          ${plat}
        </div>

        <h2>5 &nbsp;·&nbsp; What's coming to this workbench</h2>
        <p class="kicker">Pages still to build so an agent can hand-off to implementation without asking a human.</p>
        <div class="ov-nextgrid">
          <div class="ov-next" data-ready="yes"><strong>Overview</strong>this page</div>
          <div class="ov-next"><strong>Components</strong>every reusable UI atom with live demo, props, slots, a11y notes</div>
          <div class="ov-next"><strong>Data model</strong>entities, fields, FKs, indices — resolves against features.yaml</div>
          <div class="ov-next"><strong>API contracts</strong>every endpoint: method, path, auth, request, response, errors</div>
          <div class="ov-next"><strong>RBAC matrix</strong>role × resource × action grid</div>
          <div class="ov-next"><strong>Business rules</strong>state machines, formulas, escalation, deposit interest</div>
          <div class="ov-next"><strong>Integrations</strong>TransUnion · Anthropic · P24 · Gotenberg · payments — scope + Operator agreement</div>
          <div class="ov-next"><strong>Acceptance tests</strong>golden-path E2E per lifecycle stage</div>
          <div class="ov-next"><strong>Copy library</strong>buttons · empties · errors · email · SMS — SA English, legally vetted</div>
          <div class="ov-next"><strong>Environment</strong>env vars · docker-compose order · CI/CD · seed data</div>
        </div>
      </div>
    </div>
  `;
}

/* ---------- Components (live catalogue) ---------- */
function pageComponents() {
  const css = `
  <link href="https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    .cw{padding:40px 56px 120px;max-width:1120px;font-family:'Inter',sans-serif}
    .cw h1{font-family:'Fraunces',serif;font-size:40px;font-weight:700;margin:0 0 8px;letter-spacing:-.02em}
    .cw .lede{color:#6c6e92;font-size:15px;margin:0 0 32px;max-width:760px;line-height:1.55}
    .cw .doc-badge{display:inline-flex;align-items:center;gap:8px;padding:5px 12px;border-radius:999px;background:#fff;border:1px solid #EFEFF5;font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#8a8ca8;margin-bottom:18px}
    .cw .doc-badge .dot{width:6px;height:6px;border-radius:999px;background:#FF3D7F}
    .cw h2{font-family:'Fraunces',serif;font-size:24px;font-weight:700;margin:46px 0 4px;letter-spacing:-.01em;color:#2B2D6E}
    .cw h2 .n{color:#FF3D7F;font-weight:600;margin-right:8px}
    .cw h2 + p.kicker{color:#6c6e92;font-size:13.5px;margin:0 0 18px;max-width:700px;line-height:1.55}

    /* token primer tiles */
    .tok-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:32px}
    .tok{background:#fff;border:1px solid #EFEFF5;border-radius:12px;padding:14px 16px}
    .tok .l{font-size:10.5px;color:#8a8ca8;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
    .tok .v{font-size:13px;color:#2B2D6E;font-weight:500}
    .tok .sw{display:inline-block;width:14px;height:14px;border-radius:4px;vertical-align:-2px;margin-right:6px;border:1px solid rgba(0,0,0,.06)}

    /* component card */
    .comp{background:#fff;border:1px solid #EFEFF5;border-radius:14px;margin-bottom:16px;overflow:hidden}
    .comp-head{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid #F3F3F8;background:#FAFAFE}
    .comp-head h3{margin:0;font-family:'Fraunces',serif;font-size:16px;font-weight:600;color:#2B2D6E;letter-spacing:-.01em}
    .comp-head .src{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#8a8ca8}
    .comp-body{display:grid;grid-template-columns:1.2fr 1fr;gap:0}
    .comp-demo{padding:28px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:10px;background:#FCFCFE;min-height:120px;border-right:1px solid #F3F3F8}
    .comp-demo.vertical{flex-direction:column;align-items:stretch}
    .comp-demo.dark{background:#2B2D6E;color:#fff}
    .comp-spec{padding:16px 20px;font-size:12px;color:#6c6e92;line-height:1.55}
    .comp-spec .vue{background:#1E1F3A;color:#E6E7F5;border-radius:8px;padding:10px 12px;font-family:ui-monospace,Menlo,monospace;font-size:11.5px;line-height:1.5;overflow-x:auto;margin-bottom:10px;white-space:pre}
    .comp-spec .vue .k{color:#FF99BE}.comp-spec .vue .a{color:#80D4FF}.comp-spec .vue .s{color:#E8C788}.comp-spec .vue .c{color:#7A7F9F}
    .comp-spec h4{font-size:10.5px;color:#8a8ca8;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin:10px 0 4px}
    .comp-spec ul{margin:0;padding-left:16px}
    .comp-spec ul li{margin:2px 0;font-size:12px}
    .comp-spec code{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;background:#F5F5F8;padding:1px 5px;border-radius:3px;color:#2B2D6E}

    /* === The component styles (cloned from admin/src/index.css) === */
    .btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:500;border:1px solid transparent;cursor:pointer;transition:all .12s;font-family:inherit;text-decoration:none;line-height:1.4}
    .btn:hover{box-shadow:0 0 0 2px rgba(255,61,127,.35)}
    .btn:active{transform:scale(.97)}
    .btn:disabled{opacity:.5;cursor:not-allowed}
    .btn-primary{background:#2B2D6E;color:#fff}
    .btn-primary:hover{background:#1F2055}
    .btn-ghost{background:transparent;color:#2B2D6E;border-color:#E1E1EC}
    .btn-ghost:hover{background:#FAFAFE}
    .btn-danger{background:#DC2626;color:#fff}
    .btn-danger:hover{background:#B91C1C}
    .btn-accent{background:#FF3D7F;color:#fff}
    .btn-accent:hover{background:#E62E6B}
    .btn-sm{padding:5px 10px;font-size:12px;border-radius:6px}
    .btn-lg{padding:12px 20px;font-size:14.5px;border-radius:10px}
    .btn-icon{padding:8px;border-radius:8px;width:34px;height:34px;justify-content:center}
    .btn i.ph{font-size:15px}
    @keyframes klikk-spin-dot{0%,100%{transform:translateX(0)}50%{transform:translateX(4px)}}
    .klikk-load{display:inline-flex;align-items:center;gap:4px}
    .klikk-load .klikk-K{font-weight:700;font-size:13px;letter-spacing:-.02em}
    .klikk-load .klikk-D{width:5px;height:5px;border-radius:50%;background:#FF3D7F;animation:klikk-spin-dot .8s ease-in-out infinite}

    .input{width:100%;border:1px solid #E1E1EC;border-radius:8px;padding:8px 12px;font-size:13px;color:#2B2D6E;background:#fff;font-family:inherit;transition:all .12s;outline:none}
    .input:focus{border-color:#2B2D6E;box-shadow:0 0 0 3px rgba(43,45,110,.1)}
    .input.error{border-color:#DC2626}
    .input.success{border-color:#16A34A}
    .input:disabled{background:#F5F5F8;color:#8a8ca8;cursor:not-allowed}
    .label{display:block;font-size:12px;font-weight:500;color:#3a3c5f;margin-bottom:4px}
    .help{font-size:11px;color:#8a8ca8;margin-top:4px}
    .err{font-size:11px;color:#DC2626;margin-top:4px}
    .field{display:block;margin:0;width:100%}

    .search-wrap{position:relative;display:inline-flex;width:100%;max-width:320px}
    .search-wrap .input{padding-left:34px;padding-right:32px}
    .search-wrap i.ph-magnifying-glass{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:#8a8ca8}
    .search-wrap button.x{position:absolute;right:8px;top:50%;transform:translateY(-50%);border:0;background:transparent;cursor:pointer;color:#8a8ca8;padding:2px;border-radius:4px}

    .check-wrap{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:#3a3c5f;cursor:pointer}
    .check-wrap input{accent-color:#2B2D6E;width:16px;height:16px;cursor:pointer}
    .toggle{position:relative;display:inline-block;width:38px;height:22px;vertical-align:middle}
    .toggle input{opacity:0;width:0;height:0}
    .toggle .slider{position:absolute;cursor:pointer;inset:0;background:#D7D8E8;border-radius:999px;transition:.18s}
    .toggle .slider::before{content:'';position:absolute;left:3px;top:3px;width:16px;height:16px;background:#fff;border-radius:50%;transition:.18s;box-shadow:0 1px 2px rgba(0,0,0,.18)}
    .toggle input:checked + .slider{background:#2B2D6E}
    .toggle input:checked + .slider::before{transform:translateX(16px)}

    /* badges (10 variants from admin/src) */
    .badge{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:600;letter-spacing:.02em}
    .badge-green{background:#E6F4EB;color:#15803D}
    .badge-red{background:#FFE8EA;color:#A12131}
    .badge-amber{background:#FDF3E0;color:#9A5800}
    .badge-blue{background:#E5EAFF;color:#3840a8}
    .badge-purple{background:#F5EAFF;color:#6633a8}
    .badge-gray{background:#F0F0F4;color:#7a7a9c}
    .badge-emerald{background:#DCFCE7;color:#166534}
    .badge-rose{background:#FFE4EF;color:#9C1D4F}
    .badge-indigo{background:#E0E7FF;color:#3730a3}
    .badge-amber-deep{background:#FEF3C7;color:#78350F}

    /* pill (for FilterPills) */
    .pill{padding:5px 12px;border-radius:999px;font-size:12px;font-weight:500;background:#fff;border:1px solid #E1E1EC;color:#3a3c5f;cursor:pointer;transition:all .12s;display:inline-flex;align-items:center;gap:6px}
    .pill:hover{border-color:#2B2D6E}
    .pill-active{background:#2B2D6E;color:#fff;border-color:#2B2D6E}
    .pill .ct{background:rgba(255,255,255,.2);padding:1px 7px;border-radius:999px;font-size:10.5px;font-weight:600}
    .pill:not(.pill-active) .ct{background:#F0F0F4;color:#7a7a9c}

    /* card */
    .cd{background:#fff;border:1px solid #EFEFF5;border-radius:12px;padding:16px 20px;box-shadow:0 1px 3px rgba(43,45,110,.06)}
    .cd-lifted{box-shadow:0 4px 12px rgba(43,45,110,.1),0 16px 32px -10px rgba(43,45,110,.18)}
    .cd-interactive{cursor:pointer;transition:all .15s}
    .cd-interactive:hover{box-shadow:0 6px 18px -6px rgba(43,45,110,.18);transform:translateY(-1px)}

    /* modal demo */
    .mdl{background:#fff;border-radius:14px;box-shadow:0 20px 60px -10px rgba(43,45,110,.3),0 0 0 1px rgba(43,45,110,.06);width:100%;max-width:360px}
    .mdl-h{padding:14px 18px;border-bottom:1px solid #F3F3F8;display:flex;justify-content:space-between;align-items:center}
    .mdl-h h4{margin:0;font-size:14px;font-weight:600;color:#2B2D6E;font-family:inherit}
    .mdl-b{padding:16px 18px;font-size:13px;color:#6c6e92;line-height:1.5}
    .mdl-f{padding:12px 18px;border-top:1px solid #F3F3F8;display:flex;justify-content:flex-end;gap:8px}

    /* toast demo */
    .tst-grp{display:flex;flex-direction:column;gap:8px;width:100%}
    .tst{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;border-radius:10px;font-size:12.5px;border:1px solid;box-shadow:0 4px 12px rgba(43,45,110,.08)}
    .tst.t-success{background:#fff;border-color:#BBF7D0;color:#166534}
    .tst.t-error{background:#fff;border-color:#FECACA;color:#991B1B}
    .tst.t-warning{background:#fff;border-color:#FDE68A;color:#92400E}
    .tst.t-info{background:#fff;border-color:#BFDBFE;color:#1E40AF}
    .tst i.ph{font-size:16px;flex-shrink:0;margin-top:1px}

    /* empty state */
    .empty{padding:22px;text-align:center;width:100%}
    .empty i.ph{font-size:34px;color:#8a8ca8;margin-bottom:6px;display:block}
    .empty h4{font-size:14px;color:#2B2D6E;margin:0 0 3px;font-family:inherit;font-weight:600}
    .empty p{font-size:12px;color:#6c6e92;margin:0 0 10px}

    /* breadcrumb / page header */
    .crumb{display:flex;align-items:center;gap:6px;font-size:12px;color:#8a8ca8}
    .crumb .sep{color:#D7D8E8}
    .crumb .last{color:#2B2D6E;font-weight:500}
    .ph-card{background:#fff;border-radius:10px;padding:14px 18px;border:1px solid #EFEFF5;width:100%}
    .ph-card h4{margin:6px 0 2px;font-size:17px;font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E}
    .ph-card p{margin:0;font-size:12.5px;color:#8a8ca8}

    /* stepper */
    .stp{display:flex;align-items:center;gap:6px;width:100%;padding:4px}
    .stp .s{display:flex;flex-direction:column;align-items:center;gap:4px;flex:1;font-size:11px;color:#8a8ca8}
    .stp .s .dot{width:24px;height:24px;border-radius:50%;background:#F0F0F4;color:#8a8ca8;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600}
    .stp .s.done .dot{background:#16A34A;color:#fff}
    .stp .s.active .dot{background:#2B2D6E;color:#fff;box-shadow:0 0 0 3px rgba(43,45,110,.15)}
    .stp .s.active{color:#2B2D6E;font-weight:600}
    .stp .bar{height:2px;flex:1;background:#F0F0F4;margin-bottom:15px}
    .stp .bar.done{background:#16A34A}

    /* table sample */
    .tbl{width:100%;font-size:12px;border-collapse:collapse}
    .tbl th{text-align:left;padding:7px 10px;font-size:10px;color:#8a8ca8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;border-bottom:1px solid #EFEFF5}
    .tbl td{padding:9px 10px;border-bottom:1px solid #F3F3F8;color:#3a3c5f}
    .tbl tr:hover td{background:#FAFAFE}

    @media (max-width:820px){.comp-body{grid-template-columns:1fr}.comp-demo{border-right:0;border-bottom:1px solid #F3F3F8}.tok-grid{grid-template-columns:repeat(2,1fr)}}
  </style>`;

  /* ── helper to render a component card ── */
  const card = (c) => `
    <div class="comp">
      <div class="comp-head">
        <h3>${c.name}</h3>
        <div class="src">${c.src || ''}</div>
      </div>
      <div class="comp-body">
        <div class="comp-demo ${c.demoClass||''}">${c.demo}</div>
        <div class="comp-spec">
          ${c.vue ? `<div class="vue">${c.vue}</div>` : ''}
          ${c.purpose ? `<p style="margin:0 0 8px">${c.purpose}</p>` : ''}
          ${c.props && c.props.length ? `<h4>Props</h4><ul>${c.props.map(p=>`<li><code>${p[0]}</code> · ${p[1]}</li>`).join('')}</ul>` : ''}
          ${c.events && c.events.length ? `<h4>Events</h4><ul>${c.events.map(e=>`<li><code>${e[0]}</code> · ${e[1]}</li>`).join('')}</ul>` : ''}
          ${c.notes ? `<h4>Notes</h4><ul>${c.notes.map(n=>`<li>${n}</li>`).join('')}</ul>` : ''}
        </div>
      </div>
    </div>`;

  /* ───────── Buttons ───────── */
  const buttons = [
    {
      name: 'Button · primary',
      src: 'admin/src/index.css → .btn-primary',
      demo: `
        <button class="btn btn-primary">Save changes</button>
        <button class="btn btn-primary"><i class="ph ph-paper-plane-tilt"></i> Send</button>
        <button class="btn btn-primary"><span class="klikk-load"><span class="klikk-K">K</span><span class="klikk-D"></span></span>&nbsp;Submitting</button>
        <button class="btn btn-primary" disabled>Disabled</button>`,
      vue: `<span class="k">&lt;button</span> <span class="a">class</span>=<span class="s">"btn btn-primary"</span><span class="k">&gt;</span>Save changes<span class="k">&lt;/button&gt;</span>`,
      purpose: 'The single most-used component. Navy fill, white text, pink accent ring on hover, scale-down on active.',
      props: [['class', 'btn · btn-primary · btn-sm|btn-lg (optional) · disabled']],
      notes: ['Loading state shows the Klikk "K + bouncing dot" mark (see /icons).', 'Never chain two primaries in the same context — use ghost for the secondary.']
    },
    {
      name: 'Button · ghost (secondary)',
      src: 'admin/src/index.css → .btn-ghost',
      demo: `
        <button class="btn btn-ghost">Cancel</button>
        <button class="btn btn-ghost btn-sm"><i class="ph ph-arrow-left"></i> Back</button>
        <button class="btn btn-ghost" disabled>Disabled</button>`,
      vue: `<span class="k">&lt;button</span> <span class="a">class</span>=<span class="s">"btn btn-ghost"</span><span class="k">&gt;</span>Cancel<span class="k">&lt;/button&gt;</span>`,
      purpose: 'For the less-emphasised action next to a primary. Transparent, navy text, light border.',
    },
    {
      name: 'Button · danger',
      src: 'admin/src/index.css → .btn-danger',
      demo: `
        <button class="btn btn-danger">Delete property</button>
        <button class="btn btn-danger btn-sm"><i class="ph ph-trash"></i> Remove</button>`,
      vue: `<span class="k">&lt;button</span> <span class="a">class</span>=<span class="s">"btn btn-danger"</span><span class="k">&gt;</span>Delete<span class="k">&lt;/button&gt;</span>`,
      purpose: 'Destructive actions only. Always pair with ConfirmDialog for multi-second commitment.',
      notes: ['Never use for "Cancel" — cancel is never destructive in Klikk.']
    },
    {
      name: 'Button · accent (rare)',
      src: 'admin/src/index.css → .btn-accent (proposed)',
      demo: `
        <button class="btn btn-accent">Start free trial</button>
        <button class="btn btn-accent btn-lg">Upgrade now</button>`,
      vue: `<span class="k">&lt;button</span> <span class="a">class</span>=<span class="s">"btn btn-accent"</span><span class="k">&gt;</span>Start free trial<span class="k">&lt;/button&gt;</span>`,
      purpose: 'Pink fill — reserved for marketing / conversion-only CTAs. Never used inside the product chrome.',
    },
    {
      name: 'Button · icon-only',
      src: 'admin/src/index.css → .btn-icon',
      demo: `
        <button class="btn btn-icon btn-ghost" aria-label="Edit"><i class="ph ph-pencil-simple"></i></button>
        <button class="btn btn-icon btn-ghost" aria-label="More"><i class="ph ph-dots-three-vertical"></i></button>
        <button class="btn btn-icon btn-primary" aria-label="Add"><i class="ph ph-plus"></i></button>
        <button class="btn btn-icon btn-danger" aria-label="Remove"><i class="ph ph-x"></i></button>`,
      vue: `<span class="k">&lt;button</span> <span class="a">class</span>=<span class="s">"btn btn-icon btn-ghost"</span> <span class="a">aria-label</span>=<span class="s">"Edit"</span><span class="k">&gt;</span>...<span class="k">&lt;/button&gt;</span>`,
      purpose: 'Square, 34×34. MUST have aria-label — the icon is not self-describing.',
    },
  ];

  /* ───────── Inputs ───────── */
  const inputs = [
    {
      name: 'Text input + label',
      src: 'admin/src/index.css → .input · .label',
      demoClass: 'vertical',
      demo: `
        <label class="field">
          <span class="label">Full name</span>
          <input class="input" value="Marco Dippenaar" />
          <span class="help">Full legal name exactly as it appears on your SA ID.</span>
        </label>
        <label class="field">
          <span class="label">Email</span>
          <input class="input error" value="marco.com" />
          <span class="err">Enter a valid email address.</span>
        </label>`,
      vue: `<span class="k">&lt;label</span> <span class="a">class</span>=<span class="s">"field"</span><span class="k">&gt;</span>
  <span class="k">&lt;span</span> <span class="a">class</span>=<span class="s">"label"</span><span class="k">&gt;</span>Email<span class="k">&lt;/span&gt;</span>
  <span class="k">&lt;input</span> <span class="a">class</span>=<span class="s">"input"</span> <span class="a">v-model</span>=<span class="s">"email"</span> <span class="k">/&gt;</span>
<span class="k">&lt;/label&gt;</span>`,
      props: [['v-model', 'string'],['class', 'input · input.error · input.success']],
    },
    {
      name: 'SearchInput',
      src: 'admin/src/components/SearchInput.vue',
      demo: `
        <div class="search-wrap">
          <i class="ph ph-magnifying-glass"></i>
          <input class="input" placeholder="Search properties, tenants, leases…" value="stellenbosch" />
          <button class="x" aria-label="Clear"><i class="ph ph-x"></i></button>
        </div>`,
      vue: `<span class="k">&lt;SearchInput</span> <span class="a">v-model</span>=<span class="s">"query"</span> <span class="a">placeholder</span>=<span class="s">"Search…"</span> <span class="k">/&gt;</span>`,
      props: [['modelValue', 'string'], ['placeholder', 'string']],
      events: [['update:modelValue', 'fires on every keystroke']],
    },
    {
      name: 'Currency (ZAR) input',
      src: 'admin/src/components/MoneyInput.vue (proposed)',
      demo: `
        <label class="field" style="max-width:240px">
          <span class="label">Monthly rent</span>
          <div style="position:relative">
            <span style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:#8a8ca8;font-size:13px">R</span>
            <input class="input" style="padding-left:22px" value="14 500.00" />
          </div>
          <span class="help">Rands — thousands separator is a space · 2 decimals always.</span>
        </label>`,
      vue: `<span class="k">&lt;MoneyInput</span> <span class="a">v-model</span>=<span class="s">"rent"</span> <span class="a">currency</span>=<span class="s">"ZAR"</span> <span class="k">/&gt;</span>`,
      purpose: 'SA-specific — R prefix, space thousands, 2 decimals. Reject negative, reject non-numeric.',
    },
    {
      name: 'SA ID Number input',
      src: 'admin/src/components/IdNumberInput.vue (proposed)',
      demo: `
        <label class="field" style="max-width:260px">
          <span class="label">South African ID number</span>
          <input class="input success" value="9006125555088" maxlength="13" />
          <span class="help" style="color:#16A34A">Valid · Luhn check passed · DOB 1990-06-12 · Male · SA citizen</span>
        </label>`,
      vue: `<span class="k">&lt;IdNumberInput</span> <span class="a">v-model</span>=<span class="s">"idNumber"</span> <span class="a">@valid</span>=<span class="s">"onValid"</span> <span class="k">/&gt;</span>`,
      purpose: '13-digit validator + Luhn check + parse DOB / gender / citizenship. Surface in screening + FICA.',
      notes: ['Stored encrypted in Vault33 (POPIA special PI under s27).']
    },
    {
      name: 'Province select (SA)',
      src: 'admin/src/components/ProvinceSelect.vue (proposed)',
      demo: `
        <label class="field" style="max-width:260px">
          <span class="label">Province</span>
          <select class="input">
            <option>Western Cape</option><option>Gauteng</option><option>KwaZulu-Natal</option>
            <option>Eastern Cape</option><option>Free State</option><option>Limpopo</option>
            <option>Mpumalanga</option><option>North West</option><option>Northern Cape</option>
          </select>
        </label>`,
      purpose: '9 SA provinces. Use in property forms, tenant addresses, owner addresses.',
    },
    {
      name: 'Checkbox · Radio · Toggle',
      src: 'admin/src/index.css',
      demo: `
        <label class="check-wrap"><input type="checkbox" checked /> Tenant consents to credit check (POPIA s11)</label><br/>
        <label class="check-wrap"><input type="radio" name="r" checked /> Monthly</label>
        <label class="check-wrap" style="margin-left:16px"><input type="radio" name="r" /> Weekly</label><br/>
        <label class="check-wrap"><span class="toggle"><input type="checkbox" checked /><span class="slider"></span></span> Notify tenant on rent received</label>`,
      notes: ['Accent colour on the native checkbox = navy. Toggle uses the same navy when checked.'],
    },
  ];

  /* ───────── Status badges / pills ───────── */
  const status = [
    {
      name: 'Badge · all 10 variants',
      src: 'admin/src/index.css → .badge-*',
      demo: `
        <span class="badge badge-green">Active</span>
        <span class="badge badge-red">Overdue</span>
        <span class="badge badge-amber">Pending</span>
        <span class="badge badge-blue">Info</span>
        <span class="badge badge-purple">Special PI</span>
        <span class="badge badge-gray">Archived</span>
        <span class="badge badge-emerald">Paid</span>
        <span class="badge badge-rose">Terminated</span>
        <span class="badge badge-indigo">Draft</span>
        <span class="badge badge-amber-deep">Escalated</span>`,
      purpose: 'Ten colour variants — paint a meaning, not a decoration. Map table at the bottom of this page.',
    },
    {
      name: 'Lease status pills',
      src: 'Lease.status → badge mapping',
      demo: `
        <span class="badge badge-gray">draft</span>
        <span class="badge badge-amber">pending</span>
        <span class="badge badge-green">active</span>
        <span class="badge badge-indigo">renewed</span>
        <span class="badge badge-gray">expired</span>
        <span class="badge badge-rose">terminated</span>`,
      purpose: 'Resolves Lease.status (apps/leases/models.py) into a visual. Canonical mapping.',
    },
    {
      name: 'FilterPills (toggle)',
      src: 'admin/src/components/FilterPills.vue',
      demo: `
        <button class="pill pill-active">All <span class="ct">124</span></button>
        <button class="pill">Active <span class="ct">88</span></button>
        <button class="pill">Pending <span class="ct">9</span></button>
        <button class="pill">Expiring &lt; 90d <span class="ct">17</span></button>
        <button class="pill">Terminated <span class="ct">10</span></button>`,
      vue: `<span class="k">&lt;FilterPills</span> <span class="a">v-model</span>=<span class="s">"filter"</span> <span class="a">:options</span>=<span class="s">"leaseFilters"</span> <span class="k">/&gt;</span>`,
      props: [['modelValue', 'string'], ['options', 'PillOption[] — {label, value, count?, icon?}']],
      events: [['update:modelValue', 'fires on click']],
    },
  ];

  /* ───────── Cards & surfaces ───────── */
  const cards = [
    {
      name: 'Card · default + lifted',
      src: 'admin/src/index.css → .card · .shadow-lifted',
      demo: `
        <div class="cd" style="width:200px">
          <div style="font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;margin-bottom:4px">34 Oak Lane</div>
          <div style="font-size:12px;color:#6c6e92">3 bed · R15 500 · Occupied</div>
        </div>
        <div class="cd cd-lifted" style="width:200px">
          <div style="font-family:'Fraunces',serif;font-weight:600;color:#2B2D6E;margin-bottom:4px">Hover-lifted card</div>
          <div style="font-size:12px;color:#6c6e92">Elevation 2</div>
        </div>`,
      purpose: 'Three shadow tiers: soft (rest), lifted (hover/selected), phone (mockups). No other elevations.',
    },
    {
      name: 'PageHeader + Breadcrumb',
      src: 'admin/src/components/PageHeader.vue · Breadcrumb.vue',
      demoClass: 'vertical',
      demo: `
        <div class="ph-card">
          <div class="crumb"><span>Properties</span><span class="sep">/</span><span>34 Oak Lane</span><span class="sep">/</span><span class="last">Lease #L-2026-0041</span></div>
          <h4>Lease #L-2026-0041</h4>
          <p>Created 12 April 2026 · 3 signers · Pending signatures</p>
        </div>`,
      vue: `<span class="k">&lt;PageHeader</span> <span class="a">title</span>=<span class="s">"Lease #L-2026-0041"</span> <span class="a">:crumbs</span>=<span class="s">"crumbs"</span> <span class="a">back</span><span class="k">&gt;</span>
  <span class="k">&lt;template</span> <span class="a">#actions</span><span class="k">&gt;</span>...<span class="k">&lt;/template&gt;</span>
<span class="k">&lt;/PageHeader&gt;</span>`,
      props: [['title', 'string'], ['subtitle', 'string'], ['crumbs', 'BreadcrumbItem[]'], ['back', 'boolean']],
    },
  ];

  /* ───────── Overlays ───────── */
  const overlays = [
    {
      name: 'ConfirmDialog · danger',
      src: 'admin/src/components/ConfirmDialog.vue',
      demo: `
        <div class="mdl">
          <div class="mdl-h"><h4>Terminate lease?</h4><button class="btn btn-icon btn-ghost"><i class="ph ph-x"></i></button></div>
          <div class="mdl-b">This will end the lease on <strong>30 Apr 2026</strong>, freeze invoicing, and trigger the outgoing inspection step. The tenant's deposit remains held until refund.</div>
          <div class="mdl-f"><button class="btn btn-ghost">Cancel</button><button class="btn btn-danger">Terminate</button></div>
        </div>`,
      vue: `<span class="k">&lt;ConfirmDialog</span>
  <span class="a">v-model:open</span>=<span class="s">"confirmOpen"</span>
  <span class="a">title</span>=<span class="s">"Terminate lease?"</span>
  <span class="a">description</span>=<span class="s">"This will end..."</span>
  <span class="a">variant</span>=<span class="s">"danger"</span>
  <span class="a">@confirm</span>=<span class="s">"onTerminate"</span>
<span class="k">/&gt;</span>`,
      props: [['open', 'boolean'], ['title', 'string'], ['description', 'string'], ['variant', 'danger · primary'], ['loading', 'boolean']],
      events: [['confirm', 'user accepted'], ['cancel', 'user dismissed']],
    },
    {
      name: 'Toast · 4 variants',
      src: 'admin/src/components/ToastContainer.vue',
      demoClass: 'vertical',
      demo: `
        <div class="tst-grp">
          <div class="tst t-success"><i class="ph ph-check-circle"></i><div><strong>Lease activated.</strong><div>Contract now in force — first invoice dispatched.</div></div></div>
          <div class="tst t-error"><i class="ph ph-x-circle"></i><div><strong>Payment failed.</strong><div>Bank declined transfer — tenant notified.</div></div></div>
          <div class="tst t-warning"><i class="ph ph-warning"></i><div><strong>Lease expires in 80 days.</strong><div>Renewal notice window opens today.</div></div></div>
          <div class="tst t-info"><i class="ph ph-info"></i><div><strong>TransUnion report ready.</strong><div>Credit score 742 — see screening tab.</div></div></div>
        </div>`,
      vue: `<span class="k">&lt;script</span> <span class="a">setup</span><span class="k">&gt;</span>
<span class="k">import</span> { useToast } <span class="k">from</span> <span class="s">'@/composables/useToast'</span>
<span class="k">const</span> { push } = useToast()
push({ <span class="a">type</span>: <span class="s">'success'</span>, <span class="a">title</span>: <span class="s">'Lease activated.'</span>, <span class="a">body</span>: <span class="s">'…'</span> })
<span class="k">&lt;/script&gt;</span>`,
      purpose: '4 types · auto-dismiss after 5s · max 4 stacked · bottom-right fixed.',
    },
    {
      name: 'EmptyState',
      src: 'admin/src/components/EmptyState.vue',
      demo: `
        <div class="empty">
          <i class="ph ph-file-dashed"></i>
          <h4>No pending leases</h4>
          <p>Every lease has been actioned. Draft a new one to get started.</p>
          <button class="btn btn-primary btn-sm"><i class="ph ph-plus"></i> New lease</button>
        </div>`,
      vue: `<span class="k">&lt;EmptyState</span>
  <span class="a">title</span>=<span class="s">"No pending leases"</span>
  <span class="a">description</span>=<span class="s">"Every lease has been actioned…"</span>
  <span class="a">:icon</span>=<span class="s">"FileDashed"</span>
<span class="k">&gt;</span>
  <span class="k">&lt;button</span> <span class="a">class</span>=<span class="s">"btn btn-primary"</span><span class="k">&gt;</span>New lease<span class="k">&lt;/button&gt;</span>
<span class="k">&lt;/EmptyState&gt;</span>`,
      props: [['title', 'string'], ['description', 'string'], ['icon', 'Component (Phosphor icon)']],
      notes: ['Every empty list MUST use this — no blank screens.']
    },
  ];

  /* ───────── Navigation ───────── */
  const nav = [
    {
      name: 'Stepper (wizard progress)',
      src: 'ImportLeaseWizard · LeaseBuilderView',
      demo: `
        <div class="stp">
          <div class="s done"><div class="dot"><i class="ph ph-check" style="font-size:12px"></i></div>Upload</div>
          <div class="bar done"></div>
          <div class="s active"><div class="dot">2</div>Review</div>
          <div class="bar"></div>
          <div class="s"><div class="dot">3</div>Confirm</div>
          <div class="bar"></div>
          <div class="s"><div class="dot">4</div>Sign</div>
        </div>`,
      vue: `<span class="k">&lt;Stepper</span> <span class="a">:steps</span>=<span class="s">"steps"</span> <span class="a">:current</span>=<span class="s">"1"</span> <span class="k">/&gt;</span>`,
      purpose: 'Used in ImportLeaseWizard (3 steps), LeaseBuilderView (5 steps), tenant screening (4 steps).',
    },
    {
      name: 'Table row pattern',
      src: 'admin/src/index.css → .table-wrap',
      demoClass: 'vertical',
      demo: `
        <table class="tbl">
          <thead><tr><th>Property</th><th>Tenant</th><th>Rent</th><th>Status</th></tr></thead>
          <tbody>
            <tr><td>34 Oak Lane</td><td>J. Smith</td><td>R15 500</td><td><span class="badge badge-green">active</span></td></tr>
            <tr><td>12 Pine Road</td><td>A. Botha</td><td>R11 200</td><td><span class="badge badge-amber">pending</span></td></tr>
            <tr><td>5 Cedar Cres</td><td>—</td><td>R9 800</td><td><span class="badge badge-gray">vacant</span></td></tr>
          </tbody>
        </table>`,
      purpose: 'Klikk doesn\'t have a dedicated DataTable component yet — repeat this pattern + SearchInput + FilterPills above the table.',
      notes: ['Every row clickable (navigate to detail). Hover-row highlight.','Columns right-align for numeric (rent, arrears, deposit).']
    },
  ];

  /* Lede + token primer */
  const tokenPrimer = `
    <div class="tok-grid">
      <div class="tok"><div class="l">Icon library</div><div class="v">Phosphor Icons (regular)</div></div>
      <div class="tok"><div class="l">Base font</div><div class="v">Inter 15px / 1.5</div></div>
      <div class="tok"><div class="l">Display font</div><div class="v">Fraunces (workbench) · Bricolage (marketing)</div></div>
      <div class="tok"><div class="l">Navy</div><div class="v"><span class="sw" style="background:#2B2D6E"></span>#2B2D6E</div></div>
      <div class="tok"><div class="l">Accent</div><div class="v"><span class="sw" style="background:#FF3D7F"></span>#FF3D7F</div></div>
      <div class="tok"><div class="l">Radius</div><div class="v">6 · 8 · 10 · 12 · 16 px</div></div>
      <div class="tok"><div class="l">Spacing step</div><div class="v">4 / 8 / 12 / 16 / 24 / 32 px</div></div>
      <div class="tok"><div class="l">Shadow tiers</div><div class="v">soft · lifted · phone</div></div>
    </div>`;

  const sectionHtml = (num, title, blurb, items) => `
    <h2><span class="n">${num}</span>${title}</h2>
    <p class="kicker">${blurb}</p>
    ${items.map(card).join('')}`;

  return `
    ${css}
    <div class="cw">
      <div class="doc-badge"><span class="dot"></span> Component catalogue · atoms for the admin SPA</div>
      <h1>Components</h1>
      <p class="lede">Every reusable UI atom in the admin SPA, with a live demo, the Vue snippet, props, events, and the source path. Cloned visually from <code>admin/src/index.css</code> so what you see here is what renders in-app. Icon library is <strong>Phosphor</strong> (locked — see Overview).</p>

      ${tokenPrimer}

      ${sectionHtml('1 ·', 'Buttons',    'Four variants · three sizes · loading uses the Klikk K+dot mark.', buttons)}
      ${sectionHtml('2 ·', 'Inputs',     'Text fields, search, validation states, and the SA-specific inputs (ID number, rand currency, province).', inputs)}
      ${sectionHtml('3 ·', 'Status & badges', 'Ten colour variants · canonical mapping for lease / invoice / inspection states · filter pills.', status)}
      ${sectionHtml('4 ·', 'Cards & surfaces', 'Three shadow tiers · PageHeader · Breadcrumb.', cards)}
      ${sectionHtml('5 ·', 'Overlays',   'Modal · Drawer · ConfirmDialog · Toast · EmptyState.', overlays)}
      ${sectionHtml('6 ·', 'Navigation & data', 'Stepper for wizards · canonical table row pattern.', nav)}

      <h2><span class="n">7 ·</span>Loaders</h2>
      <p class="kicker">The Klikk K+dot loader is the canonical brand-led spinner. See the full variant set on the <a href="/icons" style="color:#FF3D7F">Icons page</a> (Bounce-X · Pulse · Shimmer · Vertical).</p>

      <h2><span class="n">8 ·</span>What's missing (flag for build)</h2>
      <p class="kicker">Components referenced by the flows but not yet built — add these before shipping new flows.</p>
      <div class="comp"><div class="comp-head"><h3>Backlog</h3><div class="src">admin/src/components/*</div></div><div style="padding:18px 20px">
        <ul style="margin:0;padding-left:20px;font-size:13px;color:#6c6e92;line-height:1.75">
          <li><strong>DataTable</strong> · sortable/paginated/virtualised · used in every list view</li>
          <li><strong>MoneyInput</strong> · R-prefixed currency with SA formatting</li>
          <li><strong>IdNumberInput</strong> · 13-digit SA ID with Luhn + DOB/gender parser</li>
          <li><strong>ProvinceSelect</strong> · 9 SA provinces</li>
          <li><strong>PhoneInput</strong> · +27 prefix enforced, local format</li>
          <li><strong>DateRangePicker</strong> · for lease period / reporting date ranges</li>
          <li><strong>FileDropzone</strong> · used by every document upload (FICA, compliance, signed PDFs)</li>
          <li><strong>SignaturePad</strong> · exists in signing flow but not extracted as reusable component</li>
          <li><strong>MapPicker</strong> · pin-drop on SA map for property geolocation</li>
          <li><strong>CommandPalette</strong> · ⌘K open-anything search — brand table-stakes for agents</li>
        </ul>
      </div></div>
    </div>
  `;
}

/* ---------- Server ---------- */
http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  if (u === '/' || u === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('mockups', 'Mockups', pageMockups()));
  }
  if (u === '/app' || u === '/app/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('overview', 'Overview', pageOverview()));
  }
  if (u === '/components' || u === '/components/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('components', 'Components', pageComponents()));
  }
  if (u === '/data-model' || u === '/data-model/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('datamodel', 'Data model', pageDataModel()));
  }
  if (u === '/ia' || u === '/ia/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('ia', 'IA & routes', pageIA()));
  }
  if (u === '/api' || u === '/api/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('api', 'API contracts', pageAPI()));
  }
  if (u === '/rbac' || u === '/rbac/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('rbac', 'RBAC matrix', pageRBAC()));
  }
  if (u === '/rules' || u === '/rules/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('rules', 'Business rules', pageRules()));
  }
  if (u === '/integrations' || u === '/integrations/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('integrations', 'Integrations', pageIntegrations()));
  }
  if (u === '/tests' || u === '/tests/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('tests', 'Test battery', pageTests()));
  }
  if (u === '/env' || u === '/env/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('env', 'Environment', pageEnv()));
  }
  if (u === '/copy' || u === '/copy/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('copy', 'Copy library', pageCopy()));
  }
  if (u === '/design' || u === '/design/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('design', 'Design system', pageDesign()));
  }
  if (u === '/flows' || u === '/flows/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('flows', 'Agent flow', pageFlowsAgent()));
  }
  if (u === '/flows/tenant' || u === '/flows/tenant/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('flows', 'Tenant flow', pageFlowsTenant()));
  }
  if (u === '/flows/owner' || u === '/flows/owner/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('flows', 'Owner flow', pageFlowsOwner()));
  }
  if (u === '/flows/together' || u === '/flows/together/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('flows', 'How flows connect', pageFlowsTogether()));
  }
  if (u === '/icons' || u === '/icons/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('icons', 'Icons', pageIcons()));
  }
  if (u === '/logos' || u === '/logos/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('logos', 'Logos', pageLogos()));
  }
  if (u === '/data' || u === '/data/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(layout('data', 'Data flow', pageDataFlow()));
  }
  const f = path.join(root, u);
  if (!f.startsWith(root)) { res.writeHead(403); return res.end('Forbidden'); }
  fs.readFile(f, (e, d) => {
    if (e) { res.writeHead(404); return res.end('Not found'); }
    const ext = path.extname(f).toLowerCase();
    res.writeHead(200, { 'Content-Type': mime[ext] || 'application/octet-stream' });
    res.end(d);
  });
}).listen(port, () => console.log(`Prototypes workbench on http://localhost:${port}`));
