/**
 * Seed fixture for QA-002: Agent Golden Path E2E.
 *
 * Creates a fresh, isolated agency + agent + owner + tenant for each test run.
 * All seed data is tagged with a unique run ID so parallel runs don't collide
 * and cleanup is idempotent (delete by tag prefix).
 *
 * Usage:
 *   import { seedGoldenPath, SeedData } from "./fixtures/seed";
 *   const seed = await seedGoldenPath(apiClient);
 *
 * Cleanup:
 *   await cleanupGoldenPath(apiClient, seed.runId);
 */

export interface SeedData {
  runId: string;
  agentEmail: string;
  agentPassword: string;
  agentTokens: { access: string; refresh: string };
  ownerEmail: string;
  landlordId: number;
  propertyId: number;
  unitId: number;
  tenantPersonId: number;
  tenantEmail: string;
  tenantPassword: string;
}

export interface ApiClient {
  post(path: string, body: unknown, token?: string): Promise<{ ok: boolean; status: number; data: unknown }>;
  get(path: string, token: string): Promise<{ ok: boolean; status: number; data: unknown }>;
  patch(path: string, body: unknown, token: string): Promise<{ ok: boolean; status: number; data: unknown }>;
  delete(path: string, token: string): Promise<{ ok: boolean; status: number }>;
}

// ---------------------------------------------------------------------------
// Minimal HTTP client wired to the backend API
// ---------------------------------------------------------------------------

export function makeApiClient(apiUrl: string): ApiClient {
  const base = apiUrl.endsWith("/") ? apiUrl.slice(0, -1) : apiUrl;

  async function call(method: string, path: string, body?: unknown, token?: string) {
    const url = `${base}/${path.startsWith("/") ? path.slice(1) : path}`;
    const headers: Record<string, string> = { "Content-Type": "application/json", Accept: "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    let data: unknown = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }
    return { ok: res.ok, status: res.status, data };
  }

  return {
    post: (p, b, t) => call("POST", p, b, t),
    get: (p, t) => call("GET", p, undefined, t),
    patch: (p, b, t) => call("PATCH", p, b, t),
    delete: (p, t) => call("DELETE", p, undefined, t),
  };
}

// ---------------------------------------------------------------------------
// Seed helpers
// ---------------------------------------------------------------------------

function runTag(): string {
  return `qa002-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

/**
 * Creates all seed data required for the agent golden path:
 *   admin login → create agent → create landlord (owner) → create property
 *   → create unit → create tenant person
 *
 * Requires an admin account already present on the environment:
 *   E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD (default to local dev credentials).
 */
export async function seedGoldenPath(api: ApiClient): Promise<SeedData> {
  const runId = runTag();
  const adminEmail = process.env.E2E_ADMIN_EMAIL ?? "admin@klikk.local";
  const adminPassword = process.env.E2E_ADMIN_PASSWORD ?? "admin123";

  // 1. Log in as admin to get a token for seed writes
  const loginRes = await api.post("auth/login/", { email: adminEmail, password: adminPassword });
  if (!loginRes.ok) {
    throw new Error(`Seed: admin login failed (${loginRes.status}): ${JSON.stringify(loginRes.data)}`);
  }
  const adminToken = (loginRes.data as { access: string }).access;

  // 2. Create agent user
  const agentEmail = `agent+${runId}@klikk-e2e.test`;
  const agentPassword = "E2eTest!Password1";
  const agentRes = await api.post(
    "auth/register/",
    { email: agentEmail, password: agentPassword, first_name: "E2E", last_name: "Agent", role: "agent" },
    adminToken,
  );
  if (!agentRes.ok) {
    throw new Error(`Seed: agent create failed (${agentRes.status}): ${JSON.stringify(agentRes.data)}`);
  }
  const agentUser = agentRes.data as { id: number };

  // 3. Get agent JWT tokens
  const agentLoginRes = await api.post("auth/login/", { email: agentEmail, password: agentPassword });
  if (!agentLoginRes.ok) {
    throw new Error(`Seed: agent login failed (${agentLoginRes.status}): ${JSON.stringify(agentLoginRes.data)}`);
  }
  const agentTokens = agentLoginRes.data as { access: string; refresh: string };

  // 4. Create landlord (owner / mandate counterparty)
  const ownerEmail = `owner+${runId}@klikk-e2e.test`;
  const landlordRes = await api.post(
    "properties/landlords/",
    {
      name: `E2E Owner ${runId}`,
      landlord_type: "individual",
      email: ownerEmail,
      phone: "0821234567",
      representative_name: "E2E Owner Rep",
      representative_id_number: "8001015800083",
      representative_email: ownerEmail,
      representative_phone: "0821234567",
      address: { street: "1 E2E Road", city: "Cape Town", province: "Western Cape", postal_code: "8001" },
    },
    agentTokens.access,
  );
  if (!landlordRes.ok) {
    throw new Error(`Seed: landlord create failed (${landlordRes.status}): ${JSON.stringify(landlordRes.data)}`);
  }
  const landlordId = (landlordRes.data as { id: number }).id;

  // 5. Create property
  const propRes = await api.post(
    "properties/",
    {
      name: `E2E Property ${runId}`,
      property_type: "apartment",
      address: "1 E2E Road",
      suburb: "Gardens",
      city: "Cape Town",
      province: "Western Cape",
      postal_code: "8001",
    },
    agentTokens.access,
  );
  if (!propRes.ok) {
    throw new Error(`Seed: property create failed (${propRes.status}): ${JSON.stringify(propRes.data)}`);
  }
  const propertyId = (propRes.data as { id: number }).id;

  // 6. Link landlord as owner of property
  await api.post(
    "properties/ownerships/",
    {
      property: propertyId,
      landlord: landlordId,
      owner_name: `E2E Owner ${runId}`,
      owner_type: "individual",
      owner_email: ownerEmail,
      is_current: true,
      start_date: new Date().toISOString().slice(0, 10),
    },
    agentTokens.access,
  );

  // 7. Create unit
  const unitRes = await api.post(
    "properties/units/",
    {
      property: propertyId,
      unit_number: "101",
      bedrooms: 2,
      bathrooms: 1,
      rent_amount: "8500.00",
      status: "available",
    },
    agentTokens.access,
  );
  if (!unitRes.ok) {
    throw new Error(`Seed: unit create failed (${unitRes.status}): ${JSON.stringify(unitRes.data)}`);
  }
  const unitId = (unitRes.data as { id: number }).id;

  // 8. Create tenant person (no user account yet — agent will invite)
  const tenantEmail = `tenant+${runId}@klikk-e2e.test`;
  const personRes = await api.post(
    "auth/persons/",
    {
      full_name: `E2E Tenant ${runId}`,
      email: tenantEmail,
      phone: "0839876543",
      id_number: "9001015800087",
    },
    agentTokens.access,
  );
  if (!personRes.ok) {
    throw new Error(`Seed: tenant person create failed (${personRes.status}): ${JSON.stringify(personRes.data)}`);
  }
  const tenantPersonId = (personRes.data as { id: number }).id;

  const tenantPassword = "E2eTenant!Pwd1";

  return {
    runId,
    agentEmail,
    agentPassword,
    agentTokens,
    ownerEmail,
    landlordId,
    propertyId,
    unitId,
    tenantPersonId,
    tenantEmail,
    tenantPassword,
  };
}

/**
 * Best-effort cleanup: deletes objects created by the seed run.
 * Called in test teardown. Failures are logged but not re-thrown so a cleanup
 * glitch doesn't mask test failures.
 */
export async function cleanupGoldenPath(api: ApiClient, seed: SeedData): Promise<void> {
  const t = seed.agentTokens.access;
  const tryDelete = async (path: string) => {
    try {
      await api.delete(path, t);
    } catch (e) {
      console.warn(`Cleanup: delete ${path} failed —`, e);
    }
  };

  // Delete in reverse-dependency order
  await tryDelete(`properties/units/${seed.unitId}/`);
  await tryDelete(`properties/ownerships/?property=${seed.propertyId}`);
  await tryDelete(`properties/${seed.propertyId}/`);
  await tryDelete(`properties/landlords/${seed.landlordId}/`);
  await tryDelete(`auth/persons/${seed.tenantPersonId}/`);
}
