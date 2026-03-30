"""
Seed the MaintenanceSkill library with essential skills.

Includes:
  - Maintenance-specific skills (plumbing, electrical, HVAC, etc.)
  - Monitoring skills (RAG health, token audit, MCP diagnostics)
  - Template creation skills (lease generation, clause management)

Usage:
    python manage.py seed_skills          # add missing skills only
    python manage.py seed_skills --reset  # clear and re-seed all skills
"""
from django.core.management.base import BaseCommand

from apps.maintenance.models import MaintenanceSkill

SKILLS = [
    # ── Plumbing ──
    {
        "name": "Fix Leaking Tap",
        "trade": "plumbing",
        "difficulty": "easy",
        "symptom_phrases": ["dripping tap", "leaking faucet", "tap won't close", "water dripping from tap"],
        "steps": [
            "Turn off water supply under the basin",
            "Remove the tap handle and cover plate",
            "Replace worn washer or cartridge",
            "Reassemble and test for leaks",
        ],
    },
    {
        "name": "Unblock Drain",
        "trade": "plumbing",
        "difficulty": "easy",
        "symptom_phrases": ["drain blocked", "water not draining", "slow drain", "sink clogged", "bath not draining"],
        "steps": [
            "Try boiling water and baking soda first",
            "Use a plunger to dislodge the blockage",
            "If persistent, use a drain snake",
            "Check and clean the P-trap if accessible",
            "Call plumber if blockage is in main line",
        ],
    },
    {
        "name": "Fix Running Toilet",
        "trade": "plumbing",
        "difficulty": "medium",
        "symptom_phrases": ["toilet keeps running", "toilet won't stop flushing", "water running in toilet", "toilet cistern overflow"],
        "steps": [
            "Check the flapper valve for wear or debris",
            "Adjust the float arm or fill valve",
            "Replace the flush valve seal if damaged",
            "Check overflow tube height",
            "Replace fill valve if adjustment doesn't work",
        ],
    },
    {
        "name": "Fix Burst Pipe",
        "trade": "plumbing",
        "difficulty": "hard",
        "symptom_phrases": ["burst pipe", "pipe burst", "water flooding", "pipe leaking badly", "water spraying from pipe"],
        "steps": [
            "EMERGENCY: Turn off main water supply immediately",
            "Open taps to drain remaining water",
            "Identify the location of the burst",
            "Apply temporary repair clamp if possible",
            "Call licensed plumber for permanent repair",
            "Document damage for insurance",
        ],
    },
    {
        "name": "Repair Geyser/Hot Water",
        "trade": "plumbing",
        "difficulty": "hard",
        "symptom_phrases": ["no hot water", "geyser not working", "geyser leaking", "water not heating", "hot water cylinder"],
        "steps": [
            "Check geyser circuit breaker hasn't tripped",
            "Test thermostat setting (should be ~60°C)",
            "Check for visible leaks around geyser",
            "If leaking, turn off water supply and power",
            "Call certified plumber — geyser work requires COC",
        ],
    },

    # ── Electrical ──
    {
        "name": "Tripped Circuit Breaker",
        "trade": "electrical",
        "difficulty": "easy",
        "symptom_phrases": ["power out", "electricity off", "breaker tripped", "no power", "lights off", "plug not working"],
        "steps": [
            "Locate the DB board (distribution board)",
            "Identify which breaker has tripped (switch in middle position)",
            "Unplug appliances on that circuit",
            "Reset the breaker firmly to ON",
            "If it trips again, call electrician — possible short circuit",
        ],
    },
    {
        "name": "Replace Light Fitting",
        "trade": "electrical",
        "difficulty": "medium",
        "symptom_phrases": ["light not working", "light fitting broken", "bulb won't turn on", "flickering light"],
        "steps": [
            "Turn off the light switch and circuit breaker",
            "Remove the old fitting carefully",
            "Check wiring connections (live, neutral, earth)",
            "Install new fitting per manufacturer instructions",
            "Restore power and test",
        ],
    },
    {
        "name": "Faulty Plug Socket",
        "trade": "electrical",
        "difficulty": "medium",
        "symptom_phrases": ["plug not working", "socket sparking", "socket loose", "outlet broken", "burnt smell from plug"],
        "steps": [
            "Turn off circuit breaker for that socket",
            "Test with a different appliance to confirm socket is faulty",
            "Remove socket face plate and inspect wiring",
            "Tighten loose connections or replace socket",
            "Call licensed electrician if wiring is damaged",
        ],
    },

    # ── HVAC ──
    {
        "name": "Aircon Not Cooling",
        "trade": "hvac",
        "difficulty": "medium",
        "symptom_phrases": ["aircon not cooling", "AC not cold", "air conditioner warm", "aircon blowing hot air"],
        "steps": [
            "Check thermostat settings and mode (should be on COOL)",
            "Clean or replace air filters",
            "Check outdoor unit for debris or obstruction",
            "Verify refrigerant levels (technician required)",
            "If compressor is noisy or not running, call HVAC tech",
        ],
    },
    {
        "name": "Aircon Leaking Water",
        "trade": "hvac",
        "difficulty": "medium",
        "symptom_phrases": ["aircon leaking", "water dripping from aircon", "AC leaking inside", "aircon water damage"],
        "steps": [
            "Turn off the aircon immediately",
            "Check if the drain pipe is blocked",
            "Clean the condensate drain line",
            "Check if the drip tray is cracked or overflowing",
            "Call HVAC technician if drain line is inaccessible",
        ],
    },

    # ── Roofing ──
    {
        "name": "Roof Leak Repair",
        "trade": "roofing",
        "difficulty": "hard",
        "symptom_phrases": ["roof leaking", "water coming through ceiling", "damp ceiling", "roof leak", "water stain on ceiling"],
        "steps": [
            "Place buckets to catch water and protect belongings",
            "Identify entry point from attic if accessible",
            "Temporary fix: apply waterproof sealant or tarpaulin",
            "Check flashing around vents, chimneys, skylights",
            "Call roofing contractor for permanent repair",
            "Document with photos for landlord/insurance",
        ],
    },

    # ── Appliance ──
    {
        "name": "Stove/Oven Not Working",
        "trade": "appliance",
        "difficulty": "medium",
        "symptom_phrases": ["stove not working", "oven not heating", "burner not lighting", "hob not working"],
        "steps": [
            "Check power supply and circuit breaker",
            "For gas: check gas supply valve is open",
            "Test individual elements/burners",
            "Check oven thermostat and heating element",
            "Call appliance technician for replacement parts",
        ],
    },
    {
        "name": "Washing Machine Issues",
        "trade": "appliance",
        "difficulty": "medium",
        "symptom_phrases": ["washing machine not working", "washing machine leaking", "machine not spinning", "washer won't drain"],
        "steps": [
            "Check power supply and water connections",
            "Clean the lint filter and drain pump filter",
            "Check inlet hoses for kinks or blockages",
            "Verify door seal is intact (front loaders)",
            "Call technician if motor or drum issues",
        ],
    },

    # ── Security ──
    {
        "name": "Lock Replacement",
        "trade": "security",
        "difficulty": "easy",
        "symptom_phrases": ["lock broken", "can't lock door", "key stuck", "lock jammed", "need new locks"],
        "steps": [
            "Identify lock type (deadbolt, lever, padlock)",
            "Purchase replacement of same type and size",
            "Remove old lock mechanism",
            "Install new lock, test with all keys",
            "Provide new keys to tenant and keep spare",
        ],
    },
    {
        "name": "Security Gate Repair",
        "trade": "security",
        "difficulty": "medium",
        "symptom_phrases": ["security gate stuck", "gate not closing", "gate lock broken", "trellis gate jammed"],
        "steps": [
            "Inspect track and rollers for debris or damage",
            "Lubricate tracks and hinges with silicone spray",
            "Check and adjust alignment of gate on track",
            "Replace broken rollers or latch mechanism",
            "Call security gate specialist for major repairs",
        ],
    },

    # ── Pest Control ──
    {
        "name": "Pest Infestation Treatment",
        "trade": "pest_control",
        "difficulty": "medium",
        "symptom_phrases": ["cockroaches", "ants", "rats", "mice", "pest problem", "insects", "termites", "bed bugs"],
        "steps": [
            "Identify the type of pest",
            "Remove food sources and seal entry points",
            "Apply appropriate bait or treatment for pest type",
            "For severe infestations, call licensed pest control",
            "Schedule follow-up treatment in 2-4 weeks",
            "Check neighbouring units if in a complex",
        ],
    },

    # ── Landscaping ──
    {
        "name": "Garden Irrigation Repair",
        "trade": "landscaping",
        "difficulty": "easy",
        "symptom_phrases": ["sprinkler broken", "irrigation not working", "garden dry", "sprinkler leaking"],
        "steps": [
            "Check controller/timer settings",
            "Inspect sprinkler heads for damage or clogging",
            "Check for leaks in supply lines",
            "Replace damaged heads or fittings",
            "Adjust coverage angles and watering schedule",
        ],
    },

    # ── General ──
    {
        "name": "Door Won't Close Properly",
        "trade": "general",
        "difficulty": "easy",
        "symptom_phrases": ["door won't close", "door sticking", "door misaligned", "door dragging"],
        "steps": [
            "Check hinges for loose screws — tighten all",
            "Inspect for swelling (common in humid weather)",
            "Plane or sand the edge if door is sticking",
            "Adjust striker plate on frame if needed",
            "Replace hinges if worn or bent",
        ],
    },
    {
        "name": "Window Won't Open/Close",
        "trade": "general",
        "difficulty": "easy",
        "symptom_phrases": ["window stuck", "window won't open", "window won't close", "window handle broken"],
        "steps": [
            "Clean track and frame of debris",
            "Lubricate track with silicone spray",
            "Check if window handle mechanism is intact",
            "Adjust or replace window stay arms",
            "Call glazier for broken glass or frame damage",
        ],
    },
    {
        "name": "Damp and Mould Treatment",
        "trade": "general",
        "difficulty": "medium",
        "symptom_phrases": ["damp wall", "mould", "mold", "musty smell", "black spots on wall", "condensation"],
        "steps": [
            "Identify source: rising damp, penetrating damp, or condensation",
            "Improve ventilation (open windows, extractor fans)",
            "Clean mould with diluted bleach solution (1:10)",
            "Apply anti-mould paint after cleaning and drying",
            "For rising/penetrating damp: call waterproofing specialist",
            "Check gutters and downpipes for blockages",
        ],
    },

    # ── Monitoring Skills (agent-specific) ──
    {
        "name": "RAG Health Check",
        "trade": "other",
        "difficulty": "easy",
        "symptom_phrases": ["rag not working", "search not returning results", "knowledge base empty", "vector store issues"],
        "steps": [
            "Run GET /maintenance/monitor/health/ to check RAG status",
            "Verify chunk counts across all 3 collections",
            "Check embedding model is loading correctly",
            "Re-ingest if collections are empty: manage.py ingest_contract_documents --reset",
            "Verify documents exist in CONTRACT_DOCUMENTS_ROOT",
        ],
        "notes": "Monitor skill — used by AI agents to diagnose RAG issues",
    },
    {
        "name": "Token Usage Audit",
        "trade": "other",
        "difficulty": "easy",
        "symptom_phrases": ["high token usage", "expensive api calls", "context too large", "oversized prompt"],
        "steps": [
            "Check GET /maintenance/monitor/dashboard/ for token_usage.oversized_context_alerts",
            "Review by_endpoint stats — look for avg_input > 30k tokens",
            "If tenant_chat is high: verify MAX_CHAT_WINDOW is set to 20",
            "If agent_assist is high: check RAG_QUERY_CHUNKS setting",
            "Review recent token logs with GET /maintenance/monitor/token-logs/?min_input=50000",
        ],
        "notes": "Monitor skill — helps identify and fix oversized LLM context",
    },
    {
        "name": "MCP Server Diagnostics",
        "trade": "other",
        "difficulty": "medium",
        "symptom_phrases": ["mcp not connecting", "external agent can't connect", "tools not available"],
        "steps": [
            "Verify mcp_server/server.py exists",
            "Check Django settings are importable from the MCP server path",
            "Test with: python backend/mcp_server/server.py (should start stdio server)",
            "Verify all tools are registered (11 tools, 4 resources expected)",
            "Check Cursor/Claude Desktop MCP config points to correct server.py path",
        ],
        "notes": "Monitor skill — diagnose MCP server connection issues",
    },
    {
        "name": "Agent Response Quality Check",
        "trade": "other",
        "difficulty": "medium",
        "symptom_phrases": ["agent giving wrong answers", "ai not helpful", "bad responses", "agent confused"],
        "steps": [
            "Run progressive tests: POST /maintenance/monitor/tests/ with level 3+",
            "Check RAG retrieval quality — are relevant documents being returned?",
            "Review AgentQuestion backlog — unanswered questions indicate knowledge gaps",
            "Check skills digest — ensure symptom_phrases match common tenant queries",
            "Review chat logs at MAINTENANCE_CHAT_LOG for patterns in poor responses",
        ],
        "notes": "Monitor skill — diagnose poor agent response quality",
    },

    # ── Template Creation Skills ──
    {
        "name": "Lease Template Generation",
        "trade": "other",
        "difficulty": "hard",
        "symptom_phrases": ["create lease template", "new lease", "lease template needed", "generate rental agreement"],
        "steps": [
            "Use POST /leases/templates/ to create a new template",
            "Include required fields: name, content_html, province",
            "Define variable fields (tenant_name, property_address, etc.)",
            "Set header_html and footer_html for consistent branding",
            "Test with the Lease Builder at /leases/build/",
        ],
        "notes": "Template skill — creating new lease templates via API",
    },
    {
        "name": "Clause Management",
        "trade": "other",
        "difficulty": "medium",
        "symptom_phrases": ["add clause", "modify lease clause", "reusable clause", "clause library"],
        "steps": [
            "List existing clauses with GET /leases/clauses/",
            "Create new reusable clause with POST /leases/clauses/",
            "Include: title, content_html, category, and source_templates",
            "Extract clauses from existing templates with POST /leases/clauses/extract/",
            "Generate AI clause with POST /leases/clauses/generate/",
        ],
        "notes": "Template skill — managing reusable lease clauses",
    },
    {
        "name": "Maintenance Report Template",
        "trade": "other",
        "difficulty": "easy",
        "symptom_phrases": ["maintenance report", "inspection report", "property condition report"],
        "steps": [
            "Export maintenance request history for a property",
            "Include: category breakdown, resolution times, supplier performance",
            "Use GET /maintenance/?unit__property={id} for filtered data",
            "Cross-reference with tenant intelligence profiles",
            "Generate summary using agent assist chat",
        ],
        "notes": "Template skill — generating maintenance reports",
    },
]


class Command(BaseCommand):
    help = "Seed the MaintenanceSkill library with essential skills"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Clear all skills before seeding")

    def handle(self, *args, **options):
        if options["reset"]:
            count = MaintenanceSkill.objects.count()
            MaintenanceSkill.objects.all().delete()
            self.stdout.write(f"Cleared {count} existing skills")

        created = 0
        skipped = 0
        for skill_data in SKILLS:
            name = skill_data["name"]
            trade = skill_data["trade"]
            _, was_created = MaintenanceSkill.objects.get_or_create(
                name=name,
                trade=trade,
                defaults={
                    "difficulty": skill_data.get("difficulty", "medium"),
                    "symptom_phrases": skill_data.get("symptom_phrases", []),
                    "steps": skill_data.get("steps", []),
                    "notes": skill_data.get("notes", ""),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created} new skills, {skipped} already existed ({len(SKILLS)} total defined)")
        )
