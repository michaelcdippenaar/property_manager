/**
 * agent preview store — Properties, Tickets, Leases, Suppliers
 *
 * STUB IMPLEMENTATION — returns mock data matching the admin-shell mockup.
 * Used by the /agent/* preview screens only. When we promote these to real
 * routes we'll swap the body of each `load*()` for api.get(...) calls; the
 * shapes are kept 1:1 with what the backend already serves where possible.
 *
 * Kept separate from `stores/dashboard.ts` to avoid any coupling during the
 * preview phase — both stores can live side-by-side, then merge later.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { WhenTone } from './dashboard'

// ── Types ──────────────────────────────────────────────────────────────────

/** Lifecycle states (matches apps/leases/signals.py state machine) */
export type PropertyState =
  | 'active'
  | 'signing'
  | 'vacant'
  | 'marketing'
  | 'applied'
  | 'renewal'
  | 'moveout'
  | 'refund'

export interface Property {
  id: string
  addr: string
  sub: string   // "Erf 1420", "Unit 4A"
  type: string  // "House · 3 bed"
  state: PropertyState
  tenant?: string
  rent: number
  nextAction?: string
  nextActionTone?: 'neutral' | 'warn' | 'danger'
  agent: string
}

export type TicketState =
  | 'new'
  | 'quoted'
  | 'gate3'
  | 'dispatched'
  | 'in_progress'
  | 'awaiting_payment'
  | 'closed'

export interface Ticket {
  id: string          // "#232"
  propertyAddr: string
  issue: string
  category: string    // "Plumbing", "Electrical", …
  urgency: 'Low' | 'Medium' | 'High'
  state: TicketState
  supplier?: string
  amount?: number     // ZAR
  ageLabel: string    // "2h", "1d 1h", "3d"
  bearer: string      // "Owner" / "Tenant"
  ctx?: string        // footer context e.g. "owner silent 25h"
  ctxTone?: 'neutral' | 'warn' | 'ok' | 'danger'
}

export type LeaseStatus =
  | 'executed'
  | 'countersign_pending'
  | 'tenant_pending'
  | 'renewal_due'
  | 'expired'

export interface Lease {
  id: string
  propertyAddr: string
  tenant: string
  startDate: string   // "1 May 2026"
  endDate: string
  rent: number
  status: LeaseStatus
  signedState: string // "Tenant ✓ · Owner ⏳"
}

export interface SupplierVisit {
  when: string
  whenTone: WhenTone
  supplier: string
  addr: string
  ctx: string
  ticketId: string
}

// ── Stub data ──────────────────────────────────────────────────────────────

const STUB_PROPERTIES: Property[] = [
  { id: '15-andringa', addr: '15 Andringa, Stellenbosch', sub: 'Erf 1420',  type: 'House · 3 bed',    state: 'active',    tenant: 'Vink family',         rent: 15200, nextAction: 'Statement 30 Apr', agent: 'Sarah N.' },
  { id: '22-plein',    addr: '22 Plein, Stellenbosch',    sub: 'Unit 4A',   type: 'Apartment · 2 bed',state: 'signing',   tenant: 'Jacobs, K.',          rent: 13500, nextAction: 'Owner countersign · SLA 18h', nextActionTone: 'warn', agent: 'Sarah N.' },
  { id: '12-dorp',     addr: '12 Dorp, Stellenbosch',     sub: 'Erf 892',   type: 'House · 2 bed',    state: 'vacant',    tenant: undefined,             rent: 12500, nextAction: 'Vacant 12d · list for marketing', nextActionTone: 'warn', agent: 'Sarah N.' },
  { id: '33-ryneveld', addr: '33 Ryneveld, Stellenbosch', sub: 'Erf 1701',  type: 'Cottage · 2 bed',  state: 'marketing', tenant: '3 applications',      rent: 14000, nextAction: 'Review applications', agent: 'Dan T.' },
  { id: '4-church',    addr: '4 Church, Franschhoek',     sub: 'Erf 205',   type: 'Cottage · 3 bed',  state: 'active',    tenant: 'Abrahams family',     rent: 18750, nextAction: 'Rent 3d late', nextActionTone: 'danger', agent: 'Dan T.' },
  { id: '19-main',     addr: '19 Main, Stellenbosch',     sub: 'Unit 2',    type: 'Apartment · 1 bed',state: 'renewal',   tenant: 'Mthembu, L.',         rent:  9800, nextAction: 'Send offer (T-60)', agent: 'Sarah N.' },
  { id: '25-bird',     addr: '25 Bird, Stellenbosch',     sub: 'Erf 1180',  type: 'House · 3 bed',    state: 'moveout',   tenant: 'Smit, R.',            rent: 16900, nextAction: 'Book outgoing inspection', agent: 'Dan T.' },
  { id: '3-dorp',      addr: '3 Dorp, Stellenbosch',      sub: 'Erf 54',    type: 'Cottage · 2 bed',  state: 'refund',    tenant: 'Previously: Pienaar', rent: 13200, nextAction: '14 days to refund · Gate 6', nextActionTone: 'danger', agent: 'Sarah N.' },
]

const STUB_TICKETS: Ticket[] = [
  { id: '#232', propertyAddr: '12 Dorp',         issue: 'Leaking tap — kitchen',  category: 'Plumbing',   urgency: 'Low',    state: 'new',              ageLabel: '2h',   bearer: 'Owner', ctx: 'Triage' },
  { id: '#231', propertyAddr: '4 Church',        issue: 'Gate motor not responding', category: 'Electrical', urgency: 'High', state: 'new',           ageLabel: '5h',   bearer: 'Owner', ctx: 'Request quote' },
  { id: '#229', propertyAddr: 'Unit 5 Kloof',    issue: 'Rats in ceiling',        category: 'Pest',       urgency: 'Medium', state: 'new',              ageLabel: '1d',   bearer: 'Owner', ctx: 'Triage' },
  { id: '#227', propertyAddr: '19 Main',         issue: 'Cupboard door off hinges', category: 'Handyman', urgency: 'Low',    state: 'new',              ageLabel: '1d',   bearer: 'Owner', ctx: 'Triage' },

  { id: '#230', propertyAddr: '22 Plein',        issue: 'Geyser replacement',     category: 'Plumbing',   urgency: 'High',   state: 'gate3',      supplier: 'SAPlumb',     amount: 8200, ageLabel: '1d 1h', bearer: 'Owner', ctx: 'Gate 3 · owner silent 25h', ctxTone: 'warn' },
  { id: '#226', propertyAddr: '33 Ryneveld',     issue: 'Interior paint touch-up',category: 'Handyman',   urgency: 'Low',    state: 'quoted',     supplier: 'Quick Fix Co.', amount: 3600, ageLabel: '2d', bearer: 'Owner', ctx: 'Auto-approved · dispatch', ctxTone: 'ok' },
  { id: '#225', propertyAddr: '8 Lourens',       issue: 'Gutter cleaning + downpipe', category: 'Roofing', urgency: 'Medium',state: 'quoted',     supplier: 'RoofRight',   amount: 4800, ageLabel: '3d', bearer: 'Owner', ctx: 'Sent to owner' },

  { id: '#228', propertyAddr: '15 Andringa',     issue: 'Door lock failure',      category: 'Locks/security', urgency: 'Medium', state: 'dispatched', supplier: 'EZ Locksmith', amount: 1850, ageLabel: '1d', bearer: 'Owner', ctx: 'ETA 11:00 today' },
  { id: '#223', propertyAddr: '7A Paul Kruger',  issue: 'Pool pump service',      category: 'Pool',       urgency: 'Low',    state: 'dispatched', supplier: 'BluWater',    amount: 1200, ageLabel: '4h', bearer: 'Owner', ctx: 'Tomorrow 09:00' },

  { id: '#220', propertyAddr: '8 Lourens',       issue: 'Damp repair — bathroom wall', category: 'Roofing', urgency: 'Medium', state: 'in_progress', supplier: 'Kaap Damp',   amount: 4600, ageLabel: '3d', bearer: 'Owner', ctx: 'Day 2/3 on site', ctxTone: 'ok' },
  { id: '#218', propertyAddr: 'Unit 12 WE',      issue: 'DB board upgrade',       category: 'Electrical', urgency: 'Medium', state: 'in_progress', supplier: 'SparkWise',   amount: 6200, ageLabel: '2d', bearer: 'Owner', ctx: 'Day 1/2', ctxTone: 'ok' },

  { id: '#219', propertyAddr: '15 Andringa',     issue: 'Geyser element',         category: 'Plumbing',   urgency: 'Low',    state: 'awaiting_payment', supplier: 'SAPlumb',  amount: 2400, ageLabel: '21d', bearer: 'Owner', ctx: 'Invoice uploaded · pay' },

  { id: '#217', propertyAddr: '4 Church',        issue: 'Garden service (monthly)', category: 'Garden',   urgency: 'Low',    state: 'closed',     amount: 1850, ageLabel: '32d', bearer: 'Owner', ctx: 'Paid · 4.9★', ctxTone: 'ok' },
  { id: '#214', propertyAddr: '19 Main',         issue: 'Kitchen tap washer',     category: 'Plumbing',   urgency: 'Low',    state: 'closed',     amount: 780,  ageLabel: '45d', bearer: 'Owner', ctx: 'Paid · 5★', ctxTone: 'ok' },
]

const STUB_LEASES: Lease[] = [
  { id: 'L-22P',  propertyAddr: '22 Plein, Stellenbosch',    tenant: 'Jacobs, K.',       startDate: '1 May 2026', endDate: '30 Apr 2027', rent: 13500, status: 'countersign_pending', signedState: 'Tenant ✓ · Owner ⏳' },
  { id: 'L-15A',  propertyAddr: '15 Andringa, Stellenbosch', tenant: 'Vink family',      startDate: '1 Mar 2026', endDate: '28 Feb 2027', rent: 15200, status: 'executed',            signedState: 'All parties ✓' },
  { id: 'L-4C',   propertyAddr: '4 Church, Franschhoek',     tenant: 'Abrahams family',  startDate: '1 Sep 2025', endDate: '31 Aug 2026', rent: 18750, status: 'executed',            signedState: 'All parties ✓' },
  { id: 'L-19M',  propertyAddr: '19 Main, Stellenbosch',     tenant: 'Mthembu, L.',      startDate: '1 Jul 2025', endDate: '30 Jun 2026', rent:  9800, status: 'renewal_due',         signedState: 'All parties ✓' },
]

const STUB_SUPPLIER_VISITS: SupplierVisit[] = [
  { when: 'Today 11:00',      whenTone: 'today',    supplier: 'EZ Locksmith', addr: '15 Andringa',     ctx: 'door lock #228 · tenant P. Vink on site',     ticketId: '#228' },
  { when: 'Today 14:00',      whenTone: 'today',    supplier: 'Kaap Damp',    addr: '8 Lourens',       ctx: 'damp repair #220 · day 2/3 · no tenant access', ticketId: '#220' },
  { when: 'Fri 19 Apr 09:00', whenTone: 'soon',     supplier: 'BluWater',     addr: '7A Paul Kruger',  ctx: 'pump service #223 · coordinate key pickup',  ticketId: '#223' },
  { when: 'Sat 20 Apr 10:00', whenTone: 'soon',     supplier: 'Quick Fix Co.',addr: '33 Ryneveld',     ctx: 'paint touch-up #226 · vacant property',      ticketId: '#226' },
  { when: 'Mon 22 Apr 08:00', whenTone: 'future',   supplier: 'SparkWise',    addr: 'Unit 12 WE',      ctx: 'DB board #218 · day 2/2 · power off 2h',     ticketId: '#218' },
]

// ── Store ─────────────────────────────────────────────────────────────────

export const useAgentStore = defineStore('agent', () => {
  const loading = ref(false)
  const loaded  = ref(false)
  const error   = ref<string | null>(null)

  const properties     = ref<Property[]>([])
  const tickets        = ref<Ticket[]>([])
  const leases         = ref<Lease[]>([])
  const supplierVisits = ref<SupplierVisit[]>([])

  async function load() {
    if (loaded.value) return
    loading.value = true
    error.value = null
    try {
      await new Promise(r => setTimeout(r, 120))
      properties.value     = STUB_PROPERTIES
      tickets.value        = STUB_TICKETS
      leases.value         = STUB_LEASES
      supplierVisits.value = STUB_SUPPLIER_VISITS
      loaded.value = true
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to load'
    } finally {
      loading.value = false
    }
  }

  return { loading, loaded, error, properties, tickets, leases, supplierVisits, load }
})
