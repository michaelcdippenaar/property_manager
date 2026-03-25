#!/usr/bin/env python3
"""Regenerate tenant_ai_training_cases.json. Run from repo: python backend/apps/tenant_portal/fixtures/generate_tenant_ai_training_cases.py"""

from __future__ import annotations

import json
from pathlib import Path


def j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def main() -> None:
    out = Path(__file__).resolve().parent / "tenant_ai_training_cases.json"
    cases: list[dict] = []

    def t(
        cid: str,
        summary: str,
        transcript: str,
        tags: list[str] | None = None,
        *,
        chat_raw: str | None = None,
        expect_chat: dict | None = None,
        draft_raw: str | None = None,
        expect_draft: dict | None = None,
        expected_chat_json: dict | None = None,
        expected_draft_fields: dict | None = None,
    ) -> None:
        row: dict = {
            "id": cid,
            "summary": summary,
            "sample_transcript": transcript,
        }
        if tags:
            row["tags"] = tags
        if expected_chat_json:
            row["expected_chat_json"] = expected_chat_json
        if expected_draft_fields:
            row["expected_draft_fields"] = expected_draft_fields
        if chat_raw is not None:
            row["sample_chat_assistant_raw"] = chat_raw
        if expect_chat is not None:
            row["expect_chat_parse"] = expect_chat
        if draft_raw is not None:
            row["sample_draft_model_raw"] = draft_raw
        if expect_draft is not None:
            row["expect_draft_parse"] = expect_draft
        cases.append(row)

    # --- Plumbing ---
    t(
        "plumbing_kitchen_tap_drip",
        "Dripping mixer tap — ticket + plumbing draft.",
        "Tenant: The kitchen mixer tap won't stop dripping.\nAssistant: Thanks — I'll note that for a plumber visit.",
        ["plumbing", "leak"],
        chat_raw=j(
            {
                "reply": "I've flagged a leaking kitchen tap for the maintenance team.",
                "conversation_title": "Kitchen tap leak",
                "maintenance_ticket": {
                    "title": "Kitchen mixer tap dripping",
                    "description": "Tenant reports continuous drip from kitchen mixer tap.",
                    "priority": "medium",
                },
            }
        ),
        expect_chat={
            "json_ok": True,
            "maintenance_ticket_non_null": True,
            "ticket_priority": "medium",
            "ticket_title_contains": "tap",
        },
        draft_raw=j(
            {
                "title": "Kitchen mixer tap dripping",
                "description": "Continuous drip; tenant requests plumber.",
                "priority": "medium",
                "category": "plumbing",
            }
        ),
        expect_draft={"non_null": True, "category": "plumbing", "title_contains": "tap"},
        expected_chat_json={"maintenance_ticket_non_null": True},
        expected_draft_fields={"category": "plumbing"},
    )
    t(
        "plumbing_toilet_running",
        "Running toilet cistern.",
        "Tenant: The toilet keeps running after flush.\nAssistant: That's usually a faulty float or seal — worth logging.",
        ["plumbing"],
        chat_raw=j(
            {
                "reply": "Please log this so we can send someone to check the cistern.",
                "conversation_title": None,
                "maintenance_ticket": {
                    "title": "Toilet cistern runs continuously",
                    "description": "Water runs after flush; possible seal or float issue.",
                    "priority": "medium",
                },
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_non_null": True, "ticket_title_contains": "toilet"},
        draft_raw=j(
            {
                "title": "Toilet cistern running",
                "description": "Continuous water noise after flush.",
                "priority": "medium",
                "category": "plumbing",
            }
        ),
        expect_draft={"non_null": True, "category": "plumbing"},
    )
    t(
        "plumbing_burst_pipe_urgent",
        "Burst pipe / major leak — urgent.",
        "Tenant: Water is gushing from under the bathroom basin pipe!\nAssistant: Turn off the stopcock if you can; this is urgent.",
        ["plumbing", "urgent"],
        chat_raw=j(
            {
                "reply": "Turn off the main stopcock if safe. We're logging this as urgent.",
                "conversation_title": "Burst pipe",
                "maintenance_ticket": {
                    "title": "Burst pipe under bathroom basin",
                    "description": "Active water escape; tenant to isolate if possible.",
                    "priority": "urgent",
                },
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_non_null": True, "ticket_priority": "urgent"},
        draft_raw=j(
            {
                "title": "Burst pipe bathroom basin",
                "description": "Gushing water; stopcock advice given.",
                "priority": "urgent",
                "category": "plumbing",
            }
        ),
        expect_draft={"non_null": True, "priority": "urgent", "category": "plumbing"},
    )
    t(
        "plumbing_blocked_drain",
        "Blocked kitchen drain.",
        "Tenant: Kitchen sink won't drain at all.\nAssistant: I'll add a drain blockage job.",
        ["plumbing"],
        chat_raw=j(
            {
                "reply": "Logged for drainage clearance.",
                "conversation_title": None,
                "maintenance_ticket": {
                    "title": "Blocked kitchen sink drain",
                    "description": "No drainage from kitchen sink.",
                    "priority": "high",
                },
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_non_null": True, "ticket_priority": "high"},
        draft_raw=j(
            {
                "title": "Kitchen sink blocked",
                "description": "Standing water; full blockage.",
                "priority": "high",
                "category": "plumbing",
            }
        ),
        expect_draft={"non_null": True, "category": "plumbing"},
    )
    t(
        "plumbing_geyser_drip",
        "Geyser / hot water drip (SA).",
        "Tenant: There's water dripping from the geyser outlet pipe in the ceiling cavity.\nAssistant: That needs a plumber urgently — possible geyser failure.",
        ["plumbing", "geyser"],
        expected_chat_json={"maintenance_ticket_non_null": True, "priority_urgent_or_high": True},
        expected_draft_fields={"category": "plumbing", "priority_in": ["high", "urgent"]},
    )

    # --- Electrical ---
    t(
        "electrical_db_tripping",
        "DB tripping repeatedly.",
        "Tenant: The earth leakage keeps tripping when we use the kettle.\nAssistant: Unplug devices and we'll log an electrician.",
        ["electrical"],
        chat_raw=j(
            {
                "reply": "Safety first — unplug the kettle. Logging electrical fault.",
                "conversation_title": "DB tripping",
                "maintenance_ticket": {
                    "title": "Earth leakage trips with kettle",
                    "description": "DB trips; tenant suspects kettle circuit.",
                    "priority": "high",
                },
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_non_null": True, "ticket_priority": "high"},
        draft_raw=j(
            {
                "title": "Earth leakage tripping",
                "description": "Trips when kettle used; advise unplug.",
                "priority": "high",
                "category": "electrical",
            }
        ),
        expect_draft={"non_null": True, "category": "electrical"},
    )
    t(
        "electrical_no_power_unit",
        "No power whole unit.",
        "Tenant: We have no electricity at all in the flat since this morning.\nAssistant: Check prepaid — if not that, we'll escalate.",
        ["electrical", "urgent"],
        chat_raw=j(
            {
                "reply": "If prepaid is fine, this is urgent — logging now.",
                "conversation_title": None,
                "maintenance_ticket": {
                    "title": "Total loss of power to unit",
                    "description": "No electricity; prepaid ruled out by tenant.",
                    "priority": "urgent",
                },
            }
        ),
        expect_chat={"json_ok": True, "ticket_priority": "urgent"},
        draft_raw=j(
            {
                "title": "No power to unit",
                "description": "Complete outage; prepaid not cause.",
                "priority": "urgent",
                "category": "electrical",
            }
        ),
        expect_draft={"non_null": True, "priority": "urgent"},
    )
    t(
        "electrical_sparking_socket",
        "Socket sparking — urgent.",
        "Tenant: The lounge wall socket sparked when I plugged in the TV.\nAssistant: Do not use that socket. Logging urgent electrical.",
        ["electrical", "safety"],
        expected_chat_json={"maintenance_ticket_non_null": True},
        expected_draft_fields={"category": "electrical"},
    )

    # --- Roof / water ingress ---
    t(
        "roof_ceiling_stain_rain",
        "Ceiling stain after rain.",
        "Tenant: Brown stain on bedroom ceiling after last night's storm.\nAssistant: Sounds like roof or waterproofing — we'll inspect.",
        ["roof", "water"],
        chat_raw=j(
            {
                "reply": "Logged for roof/ceiling inspection after storm damage report.",
                "conversation_title": "Ceiling stain",
                "maintenance_ticket": {
                    "title": "Ceiling water stain after storm",
                    "description": "Bedroom ceiling stain following heavy rain.",
                    "priority": "high",
                },
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_non_null": True},
        draft_raw=j(
            {
                "title": "Ceiling stain after storm",
                "description": "Bedroom; post-rain ingress suspected.",
                "priority": "high",
                "category": "roof",
            }
        ),
        expect_draft={"non_null": True, "category": {"one_of": ["roof", "plumbing", "other"]}},
    )

    # --- Appliance ---
    t(
        "appliance_oven_not_heating",
        "Oven not heating.",
        "Tenant: The built-in oven doesn't heat up.\nAssistant: I'll log appliance repair.",
        ["appliance"],
        chat_raw=j(
            {
                "reply": "Maintenance will arrange appliance inspection.",
                "conversation_title": None,
                "maintenance_ticket": {
                    "title": "Built-in oven not heating",
                    "description": "Oven powers on but no heat.",
                    "priority": "medium",
                },
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_non_null": True},
        draft_raw=j(
            {
                "title": "Oven not heating",
                "description": "Built-in oven; no heat.",
                "priority": "medium",
                "category": "appliance",
            }
        ),
        expect_draft={"non_null": True, "category": "appliance"},
    )
    t(
        "appliance_dishwasher_leak",
        "Dishwasher leaking.",
        "Tenant: Water pools in front of the dishwasher.\nAssistant: Don't run cycles until checked.",
        ["appliance", "plumbing"],
        draft_raw=j(
            {
                "title": "Dishwasher leaking",
                "description": "Dishwasher — water pools in front of unit; stop use.",
                "priority": "medium",
                "category": "appliance",
            }
        ),
        expect_draft={"non_null": True, "category": "appliance", "description_contains": "dishwasher"},
    )

    # --- Security ---
    t(
        "security_break_in",
        "Break-in — urgent + security.",
        "Tenant: Someone broke into our flat last night through the kitchen door.\nAssistant: Call SAPS 10111 if needed; logging urgent security.",
        ["security", "urgent"],
        chat_raw=j(
            {
                "reply": "I'm very sorry. If in danger call 10111. We've logged urgent security repairs.",
                "conversation_title": "Break-in",
                "maintenance_ticket": {
                    "title": "Forced entry — door damage",
                    "description": "Break-in via kitchen door; secure premises.",
                    "priority": "urgent",
                },
            }
        ),
        expect_chat={"json_ok": True, "ticket_priority": "urgent", "ticket_title_contains": "door"},
        draft_raw=j(
            {
                "title": "Break-in door damage",
                "description": "Forced entry kitchen door; police advice given.",
                "priority": "urgent",
                "category": "security",
            }
        ),
        expect_draft={"non_null": True, "category": "security", "priority": "urgent"},
    )
    t(
        "security_deadlock_jammed",
        "Front door lock jammed.",
        "Tenant: I can't lock the front door — cylinder turns but bolt won't throw.\nAssistant: High priority — you need a locksmith path.",
        ["security"],
        chat_raw=j(
            {
                "reply": "Logging faulty door lock as high priority.",
                "conversation_title": None,
                "maintenance_ticket": {
                    "title": "Front door lock not engaging",
                    "description": "Cylinder turns; bolt won't throw.",
                    "priority": "high",
                },
            }
        ),
        expect_chat={"json_ok": True, "ticket_priority": "high"},
        draft_raw=j(
            {
                "title": "Front door lock jammed",
                "description": "Bolt won't throw.",
                "priority": "high",
                "category": "security",
            }
        ),
        expect_draft={"non_null": True, "category": "security"},
    )
    t(
        "security_gate_motor",
        "Complex gate / intercom (often security).",
        "Tenant: The estate gate motor beeps but won't open my tag.\nAssistant: I'll log access control for the estate.",
        ["security"],
        expected_draft_fields={"category_one_of": ["security", "other"]},
    )

    # --- Pest ---
    t(
        "pest_cockroaches",
        "Cockroach infestation.",
        "Tenant: We're seeing cockroaches every night in the kitchen.\nAssistant: I'll schedule pest control.",
        ["pest"],
        chat_raw=j(
            {
                "reply": "Logged for pest treatment.",
                "conversation_title": "Pests",
                "maintenance_ticket": {
                    "title": "Cockroaches in kitchen",
                    "description": "Nightly activity in kitchen.",
                    "priority": "medium",
                },
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_non_null": True},
        draft_raw=j(
            {
                "title": "Cockroaches kitchen",
                "description": "Nightly sightings; treatment needed.",
                "priority": "medium",
                "category": "pest",
            }
        ),
        expect_draft={"non_null": True, "category": "pest"},
    )
    t(
        "pest_rodents",
        "Rodents in roof.",
        "Tenant: Scratching noises in the ceiling — think it's rats.\nAssistant: Pest control needed.",
        ["pest"],
        draft_raw=j(
            {
                "title": "Rodents in ceiling void",
                "description": "Scratching; possible rats.",
                "priority": "high",
                "category": "pest",
            }
        ),
        expect_draft={"non_null": True, "category": "pest"},
    )

    # --- Garden / exterior ---
    t(
        "garden_irrigation_broken",
        "Broken irrigation / communal garden.",
        "Tenant: The sprinkler in our small garden zone is shooting water onto the wall.\nAssistant: I'll log landscaping irrigation.",
        ["garden"],
        chat_raw=j(
            {
                "reply": "Logged irrigation repair.",
                "conversation_title": None,
                "maintenance_ticket": {
                    "title": "Irrigation sprinkler misdirected",
                    "description": "Water hitting wall; adjust or repair head.",
                    "priority": "low",
                },
            }
        ),
        expect_chat={"json_ok": True, "ticket_priority": "low"},
        draft_raw=j(
            {
                "title": "Sprinkler hitting wall",
                "description": "Irrigation misaligned.",
                "priority": "low",
                "category": "garden",
            }
        ),
        expect_draft={"non_null": True, "category": "garden"},
    )
    t(
        "garden_tree_branch",
        "Overhanging branch concern.",
        "Tenant: A big branch from the complex tree is scraping our bedroom window.\nAssistant: I'll log for arborist/estate team.",
        ["garden"],
        expected_chat_json={"maintenance_ticket_non_null": True},
    )

    # --- Gas / fire / emergency wording ---
    t(
        "urgent_gas_smell",
        "Gas smell — urgent.",
        "Tenant: I smell gas near the stove when it's off.\nAssistant: Open windows, no flames, call emergency gas line if strong.",
        ["urgent", "safety"],
        chat_raw=j(
            {
                "reply": "Ventilate and avoid sparks. Logging urgent gas check.",
                "conversation_title": "Gas smell",
                "maintenance_ticket": {
                    "title": "Suspected gas leak near stove",
                    "description": "Odor when stove off; safety advice given.",
                    "priority": "urgent",
                },
            }
        ),
        expect_chat={"ticket_priority": "urgent"},
        draft_raw=j(
            {
                "title": "Gas smell at stove",
                "description": "Ventilation advised; urgent inspection.",
                "priority": "urgent",
                "category": "other",
            }
        ),
        expect_draft={"non_null": True, "priority": "urgent"},
    )
    t(
        "urgent_minor_fire_kitchen",
        "Small fire extinguished — damage.",
        "Tenant: We had a small pan fire, extinguished, but ceiling is black above stove.\nAssistant: Glad you're safe — logging fire/smoke damage.",
        ["urgent"],
        expected_chat_json={"maintenance_ticket_non_null": True},
    )

    # --- Non-maintenance (no ticket) ---
    t(
        "no_ticket_rubbish_schedule",
        "Rubbish collection info — no ticket.",
        "Tenant: What day is refuse collected?\nAssistant: Check your house rules PDF for estate schedule.",
        ["faq"],
        chat_raw=j(
            {
                "reply": "Collection days are in your house rules — usually under refuse.",
                "conversation_title": None,
                "maintenance_ticket": None,
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_null": True},
    )
    t(
        "no_ticket_wifi_password",
        "WiFi password question.",
        "Tenant: What's the WiFi password for the complex guest network?\nAssistant: That's usually in your welcome pack — I don't have live credentials.",
        ["faq"],
        chat_raw=j(
            {
                "reply": "Check welcome pack or ask your agent.",
                "conversation_title": None,
                "maintenance_ticket": None,
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_null": True},
    )
    t(
        "no_ticket_deposit",
        "Deposit dispute — not a repair ticket.",
        "Tenant: When will I get my deposit back?\nAssistant: That's an accounts/agent question per your lease notice period.",
        ["rent", "legal_adjacent"],
        chat_raw=j(
            {
                "reply": "Deposit timing follows lease and inspection — contact your agent.",
                "conversation_title": "Deposit question",
                "maintenance_ticket": None,
            }
        ),
        expect_chat={"json_ok": True, "maintenance_ticket_null": True, "conversation_title_non_null": True},
    )
    t(
        "no_ticket_parking_rules",
        "Parking rules.",
        "Tenant: Can I park a second car in visitor bays overnight?\nAssistant: House rules usually limit that — check annexure.",
        ["faq"],
        expected_chat_json={"maintenance_ticket_null": True},
    )
    t(
        "no_ticket_greeting",
        "Pure greeting.",
        "Tenant: Hi there!\nAssistant: Hi — how can I help today?",
        ["chit_chat"],
        chat_raw=j(
            {
                "reply": "Hello! What do you need?",
                "conversation_title": None,
                "maintenance_ticket": None,
            }
        ),
        expect_chat={"maintenance_ticket_null": True, "reply_nonempty": True},
    )

    # --- Passing mention (no current problem) ---
    t(
        "no_ticket_mention_maintenance_generically",
        "Mentions maintenance in passing, no current issue.",
        "Tenant: Last year we had a leak but it's fixed now — just asking about rent increase.\nAssistant: For rent, see your lease escalation clause.",
        ["edge"],
        chat_raw=j(
            {
                "reply": "Rent increases are per lease terms.",
                "conversation_title": None,
                "maintenance_ticket": None,
            }
        ),
        expect_chat={"maintenance_ticket_null": True},
    )

    # --- Multi-turn ---
    t(
        "multiturn_damp_escalation",
        "Damp patch grows — multi-turn.",
        "Tenant: Damp spot on wall.\nAssistant: Which room?\nTenant: Main bedroom, north wall, bigger than last week.\nAssistant: Logging for inspection.",
        ["multi_turn", "plumbing"],
        expected_draft_fields={"description_mentions": ["bedroom", "wall"]},
    )
    t(
        "multiturn_photo_then_detail",
        "Photo marker then text detail.",
        (
            "Tenant: (Photo attached) [Photo attached]\n"
            "Assistant: I see water damage on skirting.\n"
            "Tenant: Yes, after upstairs geyser burst.\n"
            "Assistant: Logging urgent water damage."
        ),
        ["multi_turn", "photo"],
        expected_chat_json={"maintenance_ticket_non_null": True},
    )

    # --- Parse edge: markdown fence chat ---
    t(
        "parse_chat_markdown_fence",
        "Model wrongly wraps JSON in fence — parser must strip.",
        "Tenant: Window cracked.\nAssistant: Logging.",
        ["parse_regression"],
        chat_raw='```json\n{"reply": "Logged.", "conversation_title": "Window", "maintenance_ticket": {"title": "Cracked window", "description": "Glass crack", "priority": "medium"}}\n```',
        expect_chat={"json_ok": True, "maintenance_ticket_non_null": True, "ticket_title_contains": "window"},
    )

    # --- Parse edge: invalid draft → null ---
    t(
        "parse_draft_empty_title",
        "Draft model returns empty title — parser returns null.",
        "N/A",
        ["parse_regression"],
        draft_raw=j({"title": "", "description": "x", "priority": "low", "category": "other"}),
        expect_draft={"null": True},
    )
    t(
        "parse_draft_bad_category_normalized",
        "Unknown category maps to other.",
        "N/A",
        ["parse_regression"],
        draft_raw=j(
            {
                "title": "Something weird",
                "description": "Unknown system beeping",
                "priority": "low",
                "category": "alien_technology",
            }
        ),
        expect_draft={"non_null": True, "category": "other"},
    )

    # --- JSON invalid chat ---
    t(
        "parse_chat_invalid_json",
        "Non-JSON assistant output.",
        "Tenant: Help\nAssistant: Sure thing!",
        ["parse_regression"],
        chat_raw="Here is my answer without JSON sorry",
        expect_chat={"json_ok": False, "maintenance_ticket_null": True},
    )

    # --- Afrikaans / mixed (transcript for human eval) ---
    t(
        "afrikaans_lekkende_kraan",
        "Afrikaans leak report (human prompt tuning).",
        "Tenant: Die kraan in die badkamer lek die hele nag.\nAssistant: Ek sal dit vir loodgieter aanmeld.",
        ["afrikaans", "plumbing"],
        expected_chat_json={"maintenance_ticket_non_null": True},
        expected_draft_fields={"category": "plumbing"},
    )
    t(
        "mixed_english_afrikaans",
        "Mixed language.",
        "Tenant: No power in kitchen plugs maar bedroom is fine.\nAssistant: Likely circuit issue — logging electrician.",
        ["mixed", "electrical"],
        expected_chat_json={"maintenance_ticket_non_null": True},
    )

    # --- More volume: transcript-only training scenarios ---
    extras = [
        ("hvac_ac_not_cooling", "Air con not cooling", "Tenant: The bedroom aircon runs but blows warm.\nAssistant: I'll log HVAC service.", ["hvac"], {"maintenance_ticket_non_null": True}, {"category_one_of": ["appliance", "other"]}),
        ("windows_broken_latch", "Window won't close", "Tenant: Bedroom window latch broken — won't stay shut.\nAssistant: Logging carpentry/glazing.", ["windows"], {"maintenance_ticket_non_null": True}, {"category": "other"}),
        ("mould_bathroom", "Mould growth", "Tenant: Black mould on bathroom ceiling corners.\nAssistant: Ventilation + treatment job.", ["health", "plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("noise_neighbor_not_ticket", "Neighbor noise — not property repair", "Tenant: Upstairs stomping at 2am.\nAssistant: That's a neighbor conduct issue — contact estate manager.", ["edge"], {"maintenance_ticket_null": True}, {}),
        ("keys_lost_locksmith", "Lost keys", "Tenant: I lost my keys — need lock change.\nAssistant: Logging locksmith for security.", ["security"], {"maintenance_ticket_non_null": True}, {"category": "security"}),
        ("garage_door_remote", "Garage remote", "Tenant: Garage motor remote not working.\nAssistant: Battery or motor — logging.", ["security"], {"maintenance_ticket_non_null": True}, {}),
        ("smoke_alarm_chirp", "Smoke alarm chirping", "Tenant: Smoke alarm chirps every minute.\nAssistant: Likely battery — still log check.", ["safety"], {"maintenance_ticket_non_null": True}, {}),
        ("fence_panel_wind", "Fence panel down", "Tenant: Back fence panel blew down in wind.\nAssistant: Estate perimeter repair.", ["garden"], {"maintenance_ticket_non_null": True}, {"category": "garden"}),
        ("pool_pump_noise", "Communal pool pump", "Tenant: Pool pump grinding noise all day.\nAssistant: Logging estate maintenance.", ["other"], {"maintenance_ticket_non_null": True}, {}),
        ("lift_stuck_not_unit", "Lift stuck — common property", "Tenant: Lift stuck between floors with me inside — I'm out now.\nAssistant: Escalate to body corporate urgently.", ["urgent"], {"maintenance_ticket_non_null": True}, {}),
        ("balcony_railing_loose", "Loose railing", "Tenant: Balcony railing moves when leaned on.\nAssistant: Safety issue — high priority.", ["safety"], {"maintenance_ticket_non_null": True}, {"priority_in": ["high", "urgent"]}),
        ("extractor_fan_dead", "Extractor not working", "Tenant: Kitchen extractor fan dead.\nAssistant: Appliance/electrical check.", ["appliance"], {"maintenance_ticket_non_null": True}, {}),
        ("shower_pressure_low", "Low pressure", "Tenant: Shower pressure dropped to a trickle.\nAssistant: Possible blockage or municipal — log inspection.", ["plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("tile_cracked_floor", "Cracked tile trip hazard", "Tenant: Kitchen floor tile cracked and sharp edge.\nAssistant: Trip hazard — medium priority.", ["other"], {"maintenance_ticket_non_null": True}, {}),
        ("intercom_static", "Intercom static", "Tenant: Can't hear visitors on intercom.\nAssistant: Log access comms repair.", ["security"], {"maintenance_ticket_non_null": True}, {}),
        ("mailbox_broken", "Mailbox damaged", "Tenant: Mailbox door fell off.\nAssistant: Minor — logging.", ["other"], {"maintenance_ticket_non_null": True}, {}),
        ("stairwell_light_out", "Common stair light", "Tenant: Stairwell light bulb out — dark at night.\nAssistant: Common area — log.", ["electrical"], {"maintenance_ticket_non_null": True}, {}),
        ("water_heater_pilot", "Gas geyser pilot", "Tenant: Gas geyser pilot won't stay lit.\nAssistant: Gas technician required.", ["plumbing", "urgent"], {"maintenance_ticket_non_null": True}, {}),
        ("rent_increase_question", "Rent question", "Tenant: Can landlord increase mid-lease?\nAssistant: General info only — not legal advice.", ["faq"], {"maintenance_ticket_null": True}, {}),
        ("tribunal_mention", "RHT mention", "Tenant: Should I go to Rental Housing Tribunal?\nAssistant: For disputes that's an option — suggest qualified advice.", ["legal_adjacent"], {"maintenance_ticket_null": True}, {}),
        ("pet_policy", "Pet policy", "Tenant: Can I get a cat?\nAssistant: Check lease pet clause and agent approval.", ["faq"], {"maintenance_ticket_null": True}, {}),
        ("parking_scratch_claim", "Damage claim narrative", "Tenant: Someone scratched my car in the bay — CCTV?\nAssistant: Estate security query — not a unit repair ticket.", ["edge"], {"maintenance_ticket_null": True}, {}),
        ("leak_upstairs_neighbor", "Upstream neighbor leak", "Tenant: Water dripping from our ceiling — flat above.\nAssistant: Log leak + possible common pipe issue.", ["plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("vacant_possession_clean", "End of lease clean", "Tenant: Do I need professional clean?\nAssistant: Per lease handover clause.", ["faq"], {"maintenance_ticket_null": True}, {}),
        ("smart_meter_error", "Prepaid meter error", "Tenant: Prepaid meter shows error E04.\nAssistant: Municipality or landlord meter contractor.", ["electrical"], {"maintenance_ticket_non_null": True}, {}),
        ("borehole_water_smell", "Water smell (estate)", "Tenant: Tap water smells earthy this week.\nAssistant: Could be estate borehole — log water quality check.", ["plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("ceiling_fan_wobble", "Ceiling fan wobbling", "Tenant: Bedroom ceiling fan wobbles badly on high speed.\nAssistant: Safety risk — log to secure or replace.", ["electrical"], {"maintenance_ticket_non_null": True}, {}),
        ("gutter_overflow", "Gutter overflowing", "Tenant: Gutters overflow in heavy rain onto patio.\nAssistant: Blocked downpipe likely — log.", ["roof"], {"maintenance_ticket_non_null": True}, {"category_one_of": ["roof", "garden", "other"]}),
        ("sagging_gate_estate", "Pedestrian gate sagging", "Tenant: Estate pedestrian gate scrapes ground when opening.\nAssistant: Log estate maintenance.", ["security"], {"maintenance_ticket_non_null": True}, {}),
        ("balcony_drain_blocked", "Balcony drain blocked", "Tenant: Balcony doesn't drain after rain — puddles for days.\nAssistant: Clear drain outlet — log.", ["plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("mirror_cabinet_loose", "Bathroom cabinet loose", "Tenant: Medicine cabinet pulling off wall.\nAssistant: Re-secure — medium priority.", ["other"], {"maintenance_ticket_non_null": True}, {}),
        ("underfloor_heating_fault", "Underfloor heating cold", "Tenant: Underfloor heating not warming lounge tiles.\nAssistant: Electrician/UFH specialist.", ["electrical"], {"maintenance_ticket_non_null": True}, {}),
        ("solar_geyser_pump", "Solar pump noise", "Tenant: Solar geyser circulation pump grinding.\nAssistant: Log plumber/solar tech.", ["plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("boundary_wall_crack", "Boundary wall crack", "Tenant: Large crack appeared in rear boundary wall after rains.\nAssistant: Structural inspection — log.", ["other"], {"maintenance_ticket_non_null": True}, {}),
        ("carport_roof_sheet", "Carport sheet loose", "Tenant: Corrugated sheet on carport lifting in wind.\nAssistant: Urgent secure — safety.", ["roof"], {"maintenance_ticket_non_null": True}, {"priority_in": ["high", "urgent"]}),
        ("septic_smell", "Drain smell in yard", "Tenant: Sewer smell near manhole in garden.\nAssistant: Possible septic/drainage — log urgent if strong.", ["plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("electric_fence_click", "Electric fence clicking", "Tenant: Perimeter fence clicks constantly at night.\nAssistant: Estate security electrics.", ["security"], {"maintenance_ticket_non_null": True}, {}),
        ("sliding_door_track", "Sliding door stuck", "Tenant: Patio sliding door jumps off track.\nAssistant: Hardware repair — log.", ["other"], {"maintenance_ticket_non_null": True}, {}),
        ("skylight_leak", "Skylight drip", "Tenant: Dripping through skylight in stairwell when it rains.\nAssistant: Seal or replace — roof.", ["roof"], {"maintenance_ticket_non_null": True}, {}),
        ("heat_pump_error", "Heat pump error code", "Tenant: Outdoor heat pump shows E3 and stops.\nAssistant: HVAC technician.", ["appliance"], {"maintenance_ticket_non_null": True}, {}),
        ("termite_mud_tubes", "Termite tubes", "Tenant: Mud tubes on garage wall — worried about termites.\nAssistant: Pest inspection urgent.", ["pest"], {"maintenance_ticket_non_null": True}, {}),
        ("bird_nest_extract", "Birds in vent", "Tenant: Birds nesting in bathroom vent outlet.\nAssistant: Clear humanely + mesh — log.", ["pest"], {"maintenance_ticket_non_null": True}, {}),
        ("sump_pump_alarm", "Sump pump beeping", "Tenant: Basement sump pump alarm won't stop.\nAssistant: If flooding risk — urgent.", ["plumbing", "urgent"], {"maintenance_ticket_non_null": True}, {}),
        ("led_downlight_flicker", "Lights flicker whole unit", "Tenant: All LED downlights flicker together.\nAssistant: Possible neutral fault — urgent electrical.", ["electrical", "urgent"], {"maintenance_ticket_non_null": True}, {}),
        ("insurance_claim_question", "Insurance question", "Tenant: Does landlord insure my contents?\nAssistant: Usually tenant contents are separate — check lease.", ["faq"], {"maintenance_ticket_null": True}, {}),
        ("subletting_question", "Sublet question", "Tenant: Can I Airbnb my spare room?\nAssistant: Lease/subletting clause — ask agent.", ["faq"], {"maintenance_ticket_null": True}, {}),
        ("noise_after_hours_work", "After hours construction noise", "Tenant: Renovation noise from neighbor unit after 8pm.\nAssistant: Body corporate rules / estate manager.", ["edge"], {"maintenance_ticket_null": True}, {}),
        ("visitor_parking_fine", "Parking fine dispute", "Tenant: Got fined for parking in visitor bay.\nAssistant: Estate office — not a repair ticket.", ["edge"], {"maintenance_ticket_null": True}, {}),
        ("load_shedding_schedule", "Loadshedding info", "Tenant: What stage is loadshedding today?\nAssistant: Check Eskom/municipality app — not property repair.", ["faq"], {"maintenance_ticket_null": True}, {}),
        ("water_outage_area", "Area outage", "Tenant: No water in whole street — neighbors too.\nAssistant: Likely municipal outage — check city alerts.", ["plumbing"], {"maintenance_ticket_null": True}, {}),
        ("keys_locked_inside", "Locked out", "Tenant: I locked keys inside — need access.\nAssistant: Locksmith/estate security — may be billable.", ["security"], {"maintenance_ticket_non_null": True}, {}),
        ("paint_peeling_bathroom", "Peeling paint steam", "Tenant: Bathroom ceiling paint peeling from steam.\nAssistant: Ventilation + repaint — log.", ["other"], {"maintenance_ticket_non_null": True}, {}),
        ("wardrobe_rail_collapsed", "Built-in rail collapsed", "Tenant: Built-in cupboard rail snapped under weight.\nAssistant: Carpentry repair.", ["other"], {"maintenance_ticket_non_null": True}, {}),
        ("jacuzzi_jets_weak", "Jacuzzi weak jets", "Tenant: Spa bath jets very weak.\nAssistant: Pump or blockage — log.", ["plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("steam_shower_fault", "Steam shower error", "Tenant: Steam shower shows error and won't start.\nAssistant: Specialist appliance.", ["appliance"], {"maintenance_ticket_non_null": True}, {}),
        ("borehole_pump_cycling", "Pump short cycling", "Tenant: Estate water pump cycles every minute — noisy at night.\nAssistant: Log estate infrastructure.", ["plumbing"], {"maintenance_ticket_non_null": True}, {}),
        ("copper_theft_lines", "Stolen aircon pipes", "Tenant: Copper pipes stripped from outdoor unit overnight.\nAssistant: Crime + insurance — urgent security repair.", ["security", "urgent"], {"maintenance_ticket_non_null": True}, {}),
        ("vandalism_graffiti_common", "Graffiti common wall", "Tenant: Graffiti appeared on passage wall near my door.\nAssistant: Estate cleanup — log.", ["other"], {"maintenance_ticket_non_null": True}, {}),
    ]
    for eid, summ, trans, tags, ecj, edf in extras:
        row = {
            "id": eid,
            "summary": summ,
            "sample_transcript": trans,
            "tags": tags,
            "expected_chat_json": ecj,
        }
        if edf:
            row["expected_draft_fields"] = edf
        cases.append(row)

    payload = {
        "version": 2,
        "description": "Tenant AI training & regression: chat JSON (maintenance_ticket), maintenance-draft JSON, and parser edge cases. "
        "Re-run: python backend/apps/tenant_portal/fixtures/generate_tenant_ai_training_cases.py",
        "endpoints": {
            "chat_message": "POST /api/v1/tenant-portal/conversations/{id}/messages/",
            "maintenance_draft": "POST /api/v1/tenant-portal/conversations/{id}/maintenance-draft/",
        },
        "commands": {
            "validate": "python manage.py tenant_ai_training --parse-check",
        },
        "cases": cases,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {out}")


if __name__ == "__main__":
    main()
