# The Volt — System Architecture

> Sovereign data vault with two-tier consent (Permission to Ask + Permission to Send),
> sealed Request Objects, and Solana anchoring for tamper-proof audit.

---

## Core Concept

The Volt converts the question **"do I trust this server?"** into **"can I verify the math?"**.

Every data exchange leaves three cryptographic artefacts that anyone can verify
without trusting the Volt operator:

1. The **owner's signature** over the exact data delivered
2. The **requester's signature** over the original query
3. A **Solana anchor** binding both signatures to a public timestamp

If any of the three is missing, the exchange is invalid — even if the Volt's own
database says it happened.

---

## The Three Actors

| Actor | Holds | Role |
|---|---|---|
| **Requester** | keypair `(pub_R, prv_R)` + standing API credentials | Asks for data |
| **Dispatch** | server-side encryption key (Fernet, per owner) + JWT signing key | Routes, enforces scope, executes the query |
| **Owner** | keypair `(pub_O, prv_O)` — usually a Solana wallet on mobile | Sovereign of the vault. Approves and signs. |

---

## Two-Tier Consent

Before *any* request can be made, the owner must have already authorised the
requester to *be allowed to ask*. This is the single most important security
property in the system.

| Tier | Question | Recorded as |
|---|---|---|
| **Tier 1 — Permission to Ask** | "Is this requester even allowed to send me requests?" | `PermissionToAsk` anchor on Solana, long-lived, revocable |
| **Tier 2 — Permission to Send** | "For *this specific request*, what (if anything) do I send?" | `CheckoutAnchor` on Solana, per-request, immutable |

Without Tier 1, anyone with an API key can spam the owner. With Tier 1, the
broker rejects unauthorised parties before the owner is even notified.

---

## High-Level Flow

```
   ┌──────────────┐                                       ┌──────────────┐
   │  REQUESTER   │                                       │    OWNER     │
   │ (pub_R/prv_R)│                                       │ (pub_O/prv_O)│
   └──────┬───────┘                                       └──────┬───────┘
          │                                                      │
   ───────┼───────  PHASE 0: ESTABLISH TRUST  ───────────────────┼───────
          │                                                      │
          │  ❶ Register identity                                 │
          │     {org name, KYC, pub_R}                           │
          │  ───────────────────►   ┌──────────────────┐         │
          │                         │     DISPATCH     │         │
          │                         │ (Volt + Solana)  │         │
          │                         └────────┬─────────┘         │
          │                                  │                   │
          │                                  │  ❷ owner reviews ►│
          │                                  │     and signs     │
          │                                  │  ◄ PermissionToAsk│
          │                                  │                   │
          │                                  │  Anchored on chain│
          │                                  │  (max scope,      │
          │                                  │   expires_at,     │
          │                                  │   revocable)      │
          │                                                      │
   ───────┼───────  PHASE 1: SEALED REQUEST  ─────────────────────┼───────
          │                                                      │
          │  ❸ Send Sealed Request Object                        │
          │     {                                                │
          │       query: GraphQL,                                │
          │       requester_pubkey: pub_R,                       │
          │       nonce: <random>,                               │
          │       sig: sign(prv_R, query+nonce)                  │
          │     }                                                │
          │  ─────────────────►     │                            │
          │                         │ ❹ verify sig with pub_R    │
          │                         │ ❺ check Tier-1 permit      │
          │                         │ ❻ check query scope ⊆      │
          │                         │     permit max scope       │
          │                         │                            │
          │                         │ if any check fails: REJECT │
          │                         │ (owner is NOT bothered)    │
          │                         │                            │
   ───────┼───────  PHASE 2: OWNER DECIDES & SIGNS  ──────────────┼───────
          │                         │                            │
          │                         │  ❼ forward to owner ──────►│
          │                         │     (push notification     │
          │                         │      + OTP)                │
          │                         │                            │
          │                         │  ❽ owner sees:             │
          │                         │     • who asked            │
          │                         │     • exact query          │
          │                         │     • exact fields/docs    │
          │                         │                            │
          │                         │  ❾ owner approves          │
          │                         │  ◄ sign(prv_O, request_hash)│
          │                         │                            │
   ───────┼───────  PHASE 3: SEALED RESPONSE  ───────────────────┼───────
          │                         │                            │
          │                         ▼                            │
          │           ┌──────────────────────────────┐           │
          │           │  Authorised Request Object   │           │
          │           │  • original sealed request   │           │
          │           │  • owner_consent_sig         │           │
          │           │  • dispatch JWT (aud=pub_R)  │           │
          │           │  • solana_anchor_tx          │           │
          │           └──────────────┬───────────────┘           │
          │                          │                           │
          │                          │ Dispatch:                 │
          │                          │ • fetch entities (graph)  │
          │                          │ • decrypt docs (Fernet)   │
          │                          │ • build package           │
          │                          │ • encrypt(pub_R, package) │
          │                          │ • anchor on Solana        │
          │                          │                           │
          │  ❿ Sealed Response       │                           │
          │     payload =            │                           │
          │       encrypt(pub_R,     │                           │
          │         { jwt, data })   │                           │
          │  ◄───────────────────────┘                           │
          │                                                      │
          │  ⓫ Decrypt with prv_R                                │
          │     read JWT + data                                  │
          │                                                      │
          │  ⓬ Verify on chain:                                  │
          │     • PermissionToAsk existed at request time        │
          │     • owner signed THIS data hash                    │
          │     • my pub_R is the audience                       │
```

---

## The Lifecycle of a Request Object

The Request Object is a passport that gets stamped at each phase. Every stamp
adds a new cryptographic attestation — none are removed. By the time it lands
back with the requester it carries proof of every party's involvement.

```
   ┌────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
   │  Sealed Request    │ →  │ Authorised Request │ →  │  Sealed Response   │
   │  (by requester)    │    │  (by owner)        │    │  (by dispatch)     │
   ├────────────────────┤    ├────────────────────┤    ├────────────────────┤
   │ query              │    │ everything left +  │    │ encrypt(pub_R,     │
   │ requester_pubkey   │    │ jwt (aud=pub_R)    │    │   { jwt, data })   │
   │ nonce              │    │ owner_consent_sig  │    │                    │
   │ sig (prv_R)        │    │ solana_anchor_tx   │    │                    │
   └────────────────────┘    └────────────────────┘    └────────────────────┘
   ▲ requester signs          ▲ owner approves          ▲ dispatch seals
```

By the time the response arrives, the requester holds a package that proves:

| Proof | Provided by |
|---|---|
| The request was made by them | Their own `sig (prv_R)` |
| The owner approved this exact thing | `owner_consent_sig` |
| Dispatch executed it within scope | `jwt` (aud=pub_R, scope, exp) |
| All of the above happened publicly | `solana_anchor_tx` |

---

## Cryptographic Direction Reference

The asymmetric crypto in this system always works the same way:

| Operation | Key used | By whom |
|---|---|---|
| **Encrypt** package for delivery | `pub_R` (requester's public key) | Dispatch |
| **Decrypt** delivered package | `prv_R` (requester's private key) | Requester |
| **Sign** original request | `prv_R` | Requester |
| **Verify** request signature | `pub_R` | Dispatch + Owner |
| **Sign** consent / approval | `prv_O` (owner's private key) | Owner |
| **Verify** consent signature | `pub_O` | Dispatch + Requester + Solana |
| **Seal** at-rest documents | Fernet symmetric key derived per owner | Dispatch (server-side) |

The package travelling out the door is **encrypted to the requester's public key**
— meaning even Dispatch cannot read it back once sealed.

---

## The Four Gatekeepers

A request must pass *all four* in series before any data leaves the vault:

| # | Gatekeeper | Lives Where | What It Proves |
|---|---|---|---|
| **1** | **API Auth + Signature** | Dispatch (verifies `sig` with `pub_R`) | Request came from the registered requester, untampered |
| **2** | **Tier-1 Permit** | Solana `PermissionToAsk` anchor | Owner has previously authorised this requester to ask |
| **3** | **Owner Consent** | Owner's mobile + `prv_O` signature | The human owner actively chose to share *this specific package* |
| **4** | **Solana CheckoutAnchor** | On-chain | The exchange and consent are publicly verifiable forever |

There is no admin override and no bypass. The chain is the trust root; Dispatch
is just the execution engine.

---

## Solana Programs

Two on-chain artefacts:

### `PermissionToAsk`
Long-lived, revocable. Records that the owner has authorised a requester to
make requests within a maximum scope.

```rust
pub struct PermissionToAsk {
    pub owner_pubkey: Pubkey,         // pub_O
    pub requester_pubkey: Pubkey,     // pub_R
    pub max_scope: String,            // GraphQL sub-schema the requester may use
    pub mode: u8,                     // 0=strict, 1=auto-within-scope, 2=read-only, 3=time-window
    pub expires_at: i64,              // unix time
    pub owner_signature: [u8; 64],    // sign(prv_O, hash(everything above))
    pub revoked_at: Option<i64>,      // null until revoked
}
```

### `CheckoutAnchor`
Per-request, immutable. Records the exchange and the owner's consent over the
exact data delivered.

```rust
pub struct CheckoutAnchor {
    pub permit_pda: Pubkey,           // PDA of the PermissionToAsk used
    pub request_token: [u8; 16],      // UUID of the Request Object
    pub request_hash: [u8; 32],       // SHA-256 of the Sealed Request
    pub data_hash: [u8; 32],          // SHA-256 of the delivered package
    pub owner_consent_sig: [u8; 64],  // sign(prv_O, request_hash || data_hash)
    pub requester_pubkey: Pubkey,     // pub_R (audience of the encrypted payload)
    pub scope: String,                // human-readable scope ("personal,company")
    pub timestamp: i64,
    pub delivery_method: u8,          // 0=REST, 1=MCP, 2=GraphQL
}
```

A subscriber (or any third party) can independently verify:

1. The `permit_pda` references a non-revoked `PermissionToAsk` valid at `timestamp`
2. The `owner_consent_sig` verifies against the owner's `pub_O`
3. The `data_hash` matches the SHA-256 of the package they received
4. Their own `pub_R` is the audience

Pass all four → the exchange is provably legitimate. Fail any one → it isn't.

---

## Dispatch JWT Claims

The JWT issued by Dispatch and sealed inside the response payload:

```json
{
  "iss": "volt.dispatch",
  "sub": "request_token",
  "aud": "<pub_R as base58>",
  "iat": 1745000000,
  "exp": 1745000300,
  "scope": {
    "entities": ["personal:1", "company:5"],
    "fields": {"personal": ["id_number", "address"], "company": ["reg_number"]},
    "documents": ["id_document", "cipc_certificate"]
  },
  "request_hash": "sha256:...",
  "data_hash": "sha256:...",
  "owner_consent_sig": "ed25519:...",
  "solana_tx": "...",
  "delivery_method": "graphql"
}
```

- **Short expiry** (5 min) — enough to fetch and verify, not enough for replay
- **Audience-bound** to `pub_R` — useless if intercepted by anyone else
- **Sealed inside** the encrypted payload — only the requester ever sees it

---

## Why GraphQL Maps Cleanly Onto This

The `scope.fields` claim in the JWT is structurally identical to a GraphQL
query's selection set. This means:

- The **PermissionToAsk** records the maximum sub-schema the requester may query
- The **owner approval screen** can show the actual GraphQL query being approved
- The **JWT** can encode the approved selection set as a precise contract
- Dispatch can **reject** any GraphQL query whose selection set isn't a subset
  of the approved scope — at parse time, before any data is touched

The consent record and the executed query become the same artefact.

---

## Trust Boundary Map

```
   ┌───────────────────────────────────────────────────────────┐
   │  TRUSTED  (Dispatch / Volt server)                        │
   │  • Postgres data + relationships                          │
   │  • Encrypted documents at rest                            │
   │  • Pre-checkout business logic                            │
   │  • JWT signing key                                        │
   └───────────────────────────────────────────────────────────┘
                          ▲
                          │ trust boundary
                          ▼
   ┌───────────────────────────────────────────────────────────┐
   │  ZERO-TRUST OUTPUT                                        │
   │  • Owner consent signature (prv_O — never on server)      │
   │  • Encrypted response (only prv_R can decrypt)            │
   │  • Solana anchors (immutable, public)                     │
   └───────────────────────────────────────────────────────────┘
```

Even if Dispatch is fully compromised, an attacker cannot:

| Attack | Why it fails |
|---|---|
| Forge owner consent | No access to `prv_O` (lives on owner's phone) |
| Read past responses | Sealed to `pub_R` — attacker doesn't have `prv_R` |
| Backdate audit records | Solana timestamps are consensus-confirmed |
| Deliver tampered package | Subscriber will see `data_hash` mismatch on chain |
| Spoof a different requester | Requester's signature uses `prv_R` they don't have |

The only thing the operator could plausibly do is **refuse to operate** — and
even then, the on-chain history of past exchanges remains intact.

---

## Why Solana

| Property | Why it matters here |
|---|---|
| **Immutable audit trail** | Postgres can be edited by whoever runs the database. On-chain anchors cannot. |
| **Owner-held key** | The owner's wallet signs consent. Even a compromised Volt cannot forge consent records. |
| **Cheap & fast** | ~400ms confirms at fractions of a cent — works at FICA/KYC volume. |
| **Verifiable by 3rd parties** | A bank receiving FICA docs can independently verify on-chain that the owner consented and the package hash matches. |
| **Portable identity** | The same owner pubkey can authorise data flows across vaults, apps, jurisdictions. |

---

## Bootstrap: How Does a Requester Get on the Whitelist?

Three patterns, in order of how I'd implement them:

1. **Owner-initiated** — owner picks from a verified directory of orgs (Investec, STBB, Moore Stellenbosch) and grants standing permit. *(Easiest for v1)*
2. **Requester-initiated invite** — requester sends a "may I be added to your trusted list?" message; owner approves/denies. *(LinkedIn-style)*
3. **Pre-shared QR** — the requester shows a QR at, say, account opening; the owner scans and grants permit on the spot. *(Best UX in person)*

---

## Permit Modes (granularity for the owner)

The standing permit defines the **maximum** the requester may ever ask for; the
per-request layer is a **subset** of that. The mode controls how often the owner
is asked:

| Permit Mode | Owner action per request |
|---|---|
| **Strict** | Every request needs explicit approval |
| **Pre-authorised within scope** | Auto-approve if request fits standing scope; only ask if outside |
| **Read-only** | Subscriber may query metadata (entity exists, types) but never actual fields |
| **Time-window** | Auto-approve for 24h after a manual approval, then revert to strict |

---

## Open Design Questions

1. **Where does `prv_O` live?**
   - Mobile app secure enclave (best UX)
   - Hardware wallet pairing (best security for high-value vaults)
   - Custodial wallet (easiest, weakest sovereignty claim — discouraged)

2. **Pay model:**
   - On-chain anchor cost (~0.000005 SOL) passed through to subscriber, or
   - Amortised in a monthly subscription, or
   - Owner monetisation (anchor program routes lamports to owner wallet per checkout)

3. **Cross-chain mirroring:** mirror anchors to Bitcoin (via OP_RETURN) for ultra-long-term durability — probably overkill for v1.

4. **Permit granularity:** should Tier-1 permit specify which **relationship types** the requester may traverse (`director_of`, `trustee_of`), not just entity types and field keys? My instinct: **yes** — the permit is essentially a sub-schema of the GraphQL schema, including allowed edges.

5. **Persisted queries** as consent contracts: requester pre-registers a query hash; owner approves the hash with a human description; subsequent checkouts reference only the hash. Cleaner audit, cacheable, prevents query widening post-approval.
