#!/usr/bin/env python3
"""
Threshold Cartography — Klikk Lifecycle Diagrams
Generates 3 PNG diagrams for the Klikk product lines.
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# ── Brand Tokens ───────────────────────────────────────────
NAVY = (43, 45, 110)        # #2B2D6E
ACCENT = (255, 61, 127)     # #FF3D7F
WHITE = (255, 255, 255)
LIGHT_GRAY = (245, 245, 250)
MID_GRAY = (200, 200, 210)
NAVY_LIGHT = (43, 45, 110, 30)
ACCENT_SOFT = (255, 61, 127, 40)

FONTS_DIR = "/Users/mcdippenaar/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/27337302-9846-440b-9bad-2060ddaf92a0/d2e7002b-aa48-490b-bf6a-61374d117e47/skills/canvas-design/canvas-fonts"
OUTPUT_DIR = "/Users/mcdippenaar/PycharmProjects/tremly_property_manager/content/diagrams"

def load_font(name, size):
    path = os.path.join(FONTS_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

# ── Fonts ──────────────────────────────────────────────────
font_title = load_font("BricolageGrotesque-Bold.ttf", 52)
font_tagline = load_font("InstrumentSans-Italic.ttf", 24)
font_step_num = load_font("BricolageGrotesque-Bold.ttf", 22)
font_step_label = load_font("InstrumentSans-Regular.ttf", 15)
font_step_label_sm = load_font("InstrumentSans-Regular.ttf", 13)
font_section_title = load_font("BricolageGrotesque-Bold.ttf", 20)
font_section_body = load_font("InstrumentSans-Regular.ttf", 14)
font_klikk = load_font("BricolageGrotesque-Regular.ttf", 14)
font_subtitle = load_font("InstrumentSans-Bold.ttf", 18)

def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]

def text_height(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]

def draw_circle(draw, cx, cy, r, fill=None, outline=None, width=2):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=width)

def draw_connector(draw, x1, y1, x2, y2, color=MID_GRAY, width=2):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

def draw_dashed_line(draw, x1, y1, x2, y2, color=MID_GRAY, width=1, dash_len=8, gap_len=6):
    length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    if length == 0:
        return
    dx = (x2 - x1) / length
    dy = (y2 - y1) / length
    pos = 0
    while pos < length:
        end = min(pos + dash_len, length)
        sx = x1 + dx * pos
        sy = y1 + dy * pos
        ex = x1 + dx * end
        ey = y1 + dy * end
        draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
        pos += dash_len + gap_len


# ═══════════════════════════════════════════════════════════════
# DIAGRAM 1: KLIKK RENTALS — 15 stages, one platform
# ═══════════════════════════════════════════════════════════════

def create_rentals_diagram():
    W, H = 1800, 900
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    steps = [
        "Advertise", "Viewing", "Screen", "Contract", "Sign",
        "Onboard", "Deposit", "Inspect", "Live", "Pay Rent",
        "Maintain", "Renew", "Notice", "Out-Inspect", "Refund"
    ]

    statuses = ["PLANNED", "PLANNED", "PLANNED", "BUILT", "BUILT",
                "BUILT", "PLANNED", "PLANNED", "BUILT", "BUILT",
                "BUILT", "BUILT", "PLANNED", "PLANNED", "PLANNED"]

    # ── Title block ────────────────────────────────────────
    draw.text((80, 50), "KLIKK RENTALS", fill=NAVY, font=font_title)
    draw.text((80, 110), "15 stages, one platform", fill=ACCENT, font=font_tagline)

    # ── Decorative top line ────────────────────────────────
    draw.rectangle([80, 148, 500, 150], fill=NAVY)
    draw.rectangle([500, 148, 540, 150], fill=ACCENT)

    # ── Grid baseline ──────────────────────────────────────
    draw_dashed_line(draw, 80, H - 80, W - 80, H - 80, color=MID_GRAY, width=1)

    # ── Step nodes — two rows ──────────────────────────────
    row1_count = 8
    row2_count = 7
    node_r = 28
    row1_y = 310
    row2_y = 530
    margin_x = 120
    spacing1 = (W - 2 * margin_x) / (row1_count - 1)
    spacing2 = (W - 2 * margin_x) / (row2_count - 1)

    positions = []

    # Row 1: steps 1-8
    for i in range(row1_count):
        x = margin_x + i * spacing1
        positions.append((x, row1_y))

    # Row 2: steps 9-15 (reversed direction for flow)
    for i in range(row2_count):
        x = W - margin_x - i * spacing2
        positions.append((x, row2_y))

    # ── Connectors ─────────────────────────────────────────
    for i in range(len(positions) - 1):
        x1, y1 = positions[i]
        x2, y2 = positions[i + 1]

        if i == row1_count - 1:
            # Curved connector between rows
            mid_x = W - margin_x + 40
            draw.arc([x1 - 10, y1, mid_x, y2], start=270, end=90, fill=MID_GRAY, width=2)
        else:
            draw_connector(draw, x1 + node_r + 4, y1, x2 - node_r - 4, y2, color=MID_GRAY, width=2)

    # ── Draw nodes ─────────────────────────────────────────
    for i, (x, y) in enumerate(positions):
        is_built = statuses[i] == "BUILT"
        fill_color = NAVY if is_built else WHITE
        outline_color = NAVY if is_built else MID_GRAY
        text_color = WHITE if is_built else NAVY
        label_color = NAVY if is_built else (150, 150, 160)

        # Accent ring for V1 features
        if is_built:
            draw_circle(draw, x, y, node_r + 4, outline=ACCENT, width=2)

        draw_circle(draw, x, y, node_r, fill=fill_color, outline=outline_color, width=2)

        # Step number
        num_text = str(i + 1)
        tw = text_width(draw, num_text, font_step_num)
        th = text_height(draw, num_text, font_step_num)
        draw.text((x - tw // 2, y - th // 2 - 1), num_text, fill=text_color, font=font_step_num)

        # Step label
        label = steps[i]
        lw = text_width(draw, label, font_step_label_sm)
        draw.text((x - lw // 2, y + node_r + 12), label, fill=label_color, font=font_step_label_sm)

    # ── Legend ─────────────────────────────────────────────
    legend_y = H - 65
    draw_circle(draw, 100, legend_y, 8, fill=NAVY, outline=NAVY)
    draw.text((115, legend_y - 8), "Built (V1)", fill=NAVY, font=font_klikk)

    draw_circle(draw, 250, legend_y, 8, fill=WHITE, outline=MID_GRAY, width=2)
    draw.text((265, legend_y - 8), "Planned", fill=(150, 150, 160), font=font_klikk)

    draw_circle(draw, 380, legend_y, 8, outline=ACCENT, width=2)
    draw.text((395, legend_y - 8), "V1 Release", fill=ACCENT, font=font_klikk)

    # ── Klikk watermark ────────────────────────────────────
    wm = "klikk.co.za"
    ww = text_width(draw, wm, font_klikk)
    draw.text((W - ww - 80, legend_y - 8), wm, fill=MID_GRAY, font=font_klikk)

    # ── Phase labels ───────────────────────────────────────
    draw.text((margin_x, row1_y - 70), "ACQUISITION & ONBOARDING", fill=MID_GRAY, font=font_klikk)
    draw.text((W - margin_x - text_width(draw, "TENANCY & EXIT", font_klikk), row2_y - 70),
              "TENANCY & EXIT", fill=MID_GRAY, font=font_klikk)

    img.save(os.path.join(OUTPUT_DIR, "klikk-rentals-lifecycle.png"), "PNG", dpi=(300, 300))
    print("Created: klikk-rentals-lifecycle.png")


# ═══════════════════════════════════════════════════════════════
# DIAGRAM 2: KLIKK REAL ESTATE — Selling made simple
# ═══════════════════════════════════════════════════════════════

def create_real_estate_diagram():
    W, H = 1800, 900
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    steps = [
        "Prospect", "Valuate", "Sign\nMandate", "List &\nMarket", "Viewings",
        "Negotiate", "Sign\nOTP", "Buyer\nDocs", "Bond\nApproval",
        "Legal &\nCompliance", "Transfer"
    ]

    phases = [
        (0, 2, "ORIGINATION"),
        (3, 5, "MARKETING & NEGOTIATION"),
        (6, 8, "DUE DILIGENCE"),
        (9, 10, "CLOSE")
    ]

    # ── Title block ────────────────────────────────────────
    draw.text((80, 50), "KLIKK REAL ESTATE", fill=NAVY, font=font_title)
    draw.text((80, 110), "Selling made simple", fill=ACCENT, font=font_tagline)

    draw.rectangle([80, 148, 560, 150], fill=NAVY)
    draw.rectangle([560, 148, 600, 150], fill=ACCENT)

    # ── Timeline axis ──────────────────────────────────────
    axis_y = 500
    margin_x = 130
    node_r = 30
    spacing = (W - 2 * margin_x) / (len(steps) - 1)

    # Phase backgrounds
    for start, end, label in phases:
        x1 = margin_x + start * spacing - 40
        x2 = margin_x + end * spacing + 40
        draw.rounded_rectangle([x1, axis_y - 120, x2, axis_y + 100], radius=12, fill=LIGHT_GRAY)
        lw = text_width(draw, label, font_klikk)
        draw.text(((x1 + x2) / 2 - lw / 2, axis_y + 110), label, fill=MID_GRAY, font=font_klikk)

    # ── Axis line ──────────────────────────────────────────
    draw.line([(margin_x - 20, axis_y), (W - margin_x + 20, axis_y)], fill=NAVY, width=2)

    # ── Arrow at end ───────────────────────────────────────
    ax = W - margin_x + 20
    draw.polygon([(ax, axis_y), (ax + 15, axis_y), (ax + 8, axis_y - 8)], fill=NAVY)
    draw.polygon([(ax, axis_y), (ax + 15, axis_y), (ax + 8, axis_y + 8)], fill=NAVY)

    # ── Step nodes ─────────────────────────────────────────
    for i, label in enumerate(steps):
        x = margin_x + i * spacing

        # Alternating above/below for visual rhythm
        if i % 2 == 0:
            label_y = axis_y - node_r - 55
        else:
            label_y = axis_y + node_r + 15

        # Node
        draw_circle(draw, x, axis_y, node_r, fill=NAVY, outline=NAVY)

        # Accent dot for key signing moments
        if i in [2, 6, 10]:  # Sign Mandate, Sign OTP, Transfer
            draw_circle(draw, x, axis_y, node_r + 5, outline=ACCENT, width=2)

        # Step number inside node
        num = str(i + 1)
        tw = text_width(draw, num, font_step_num)
        th = text_height(draw, num, font_step_num)
        draw.text((x - tw // 2, axis_y - th // 2 - 1), num, fill=WHITE, font=font_step_num)

        # Label
        lines = label.split("\n")
        for j, line in enumerate(lines):
            lw = text_width(draw, line, font_step_label)
            draw.text((x - lw // 2, label_y + j * 20), line, fill=NAVY, font=font_step_label)

    # ── Timeline markers ───────────────────────────────────
    # OTP to Transfer bracket
    otp_x = margin_x + 6 * spacing
    transfer_x = margin_x + 10 * spacing
    bracket_y = axis_y + 160
    draw_dashed_line(draw, otp_x, bracket_y, transfer_x, bracket_y, color=ACCENT, width=1)
    draw.line([(otp_x, bracket_y - 5), (otp_x, bracket_y + 5)], fill=ACCENT, width=1)
    draw.line([(transfer_x, bracket_y - 5), (transfer_x, bracket_y + 5)], fill=ACCENT, width=1)
    timeline_text = "8–16 weeks typical"
    tw = text_width(draw, timeline_text, font_klikk)
    draw.text(((otp_x + transfer_x) / 2 - tw / 2, bracket_y + 10), timeline_text, fill=ACCENT, font=font_klikk)

    # ── Legend ─────────────────────────────────────────────
    legend_y = H - 60
    draw_circle(draw, 100, legend_y, 8, fill=NAVY, outline=NAVY)
    draw.text((115, legend_y - 8), "Lifecycle Step", fill=NAVY, font=font_klikk)

    draw_circle(draw, 280, legend_y, 8, outline=ACCENT, width=2)
    draw.text((295, legend_y - 8), "Signing Moment", fill=ACCENT, font=font_klikk)

    wm = "klikk.co.za"
    ww = text_width(draw, wm, font_klikk)
    draw.text((W - ww - 80, legend_y - 8), wm, fill=MID_GRAY, font=font_klikk)

    img.save(os.path.join(OUTPUT_DIR, "klikk-real-estate-lifecycle.png"), "PNG", dpi=(300, 300))
    print("Created: klikk-real-estate-lifecycle.png")


# ═══════════════════════════════════════════════════════════════
# DIAGRAM 3: KLIKK BI — Data-driven property decisions
# ═══════════════════════════════════════════════════════════════

def create_bi_diagram():
    W, H = 1800, 900
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    # ── Title block ────────────────────────────────────────
    draw.text((80, 50), "KLIKK BI", fill=NAVY, font=font_title)
    draw.text((80, 110), "Data-driven property decisions", fill=ACCENT, font=font_tagline)

    draw.rectangle([80, 148, 420, 150], fill=NAVY)
    draw.rectangle([420, 148, 460, 150], fill=ACCENT)

    # ── Three pillars ──────────────────────────────────────
    pillars = [
        {
            "title": "MARKET ANALYTICS",
            "subtitle": "Know the market",
            "items": [
                ("CMA Tools", "Comparative market analysis with recent sales data"),
                ("Price Trends", "Suburb-level price movements and forecasts"),
                ("Comparables", "Automated comparable property matching"),
                ("Supply/Demand", "Area-level inventory and demand indicators"),
            ],
            "accent_bar": True,
        },
        {
            "title": "AGENCY OPERATIONS",
            "subtitle": "Run the business",
            "items": [
                ("Performance", "Agent KPIs, leaderboards, and team metrics"),
                ("Pipeline", "Lead-to-transfer funnel tracking"),
                ("Commission", "Revenue forecasting and commission analytics"),
                ("Team KPIs", "Individual and office benchmarking"),
            ],
            "accent_bar": False,
        },
        {
            "title": "LEAD ANALYTICS",
            "subtitle": "Optimise spend",
            "items": [
                ("Lead Sources", "Channel attribution and source tracking"),
                ("Conversion", "Funnel analysis from lead to close"),
                ("Cost per Lead", "Marketing ROI by channel and campaign"),
                ("Response Time", "Agent response speed and impact metrics"),
            ],
            "accent_bar": False,
        },
    ]

    pillar_w = 480
    pillar_h = 520
    gap = 40
    start_x = (W - (3 * pillar_w + 2 * gap)) // 2
    start_y = 200

    for idx, pillar in enumerate(pillars):
        x = start_x + idx * (pillar_w + gap)
        y = start_y

        # Card background
        draw.rounded_rectangle([x, y, x + pillar_w, y + pillar_h], radius=16, fill=LIGHT_GRAY)

        # Top accent bar
        bar_color = ACCENT if idx == 0 else NAVY
        draw.rounded_rectangle([x, y, x + pillar_w, y + 8], radius=4, fill=bar_color)

        # Pillar number
        num = f"0{idx + 1}"
        draw.text((x + 30, y + 30), num, fill=MID_GRAY, font=font_step_num)

        # Title
        draw.text((x + 30, y + 60), pillar["title"], fill=NAVY, font=font_section_title)

        # Subtitle
        draw.text((x + 30, y + 90), pillar["subtitle"], fill=ACCENT, font=font_klikk)

        # Divider
        draw.line([(x + 30, y + 120), (x + pillar_w - 30, y + 120)], fill=MID_GRAY, width=1)

        # Items
        for j, (item_title, item_desc) in enumerate(pillar["items"]):
            iy = y + 145 + j * 90

            # Item marker
            marker_r = 4
            draw_circle(draw, x + 40, iy + 8, marker_r, fill=bar_color)

            # Item title
            draw.text((x + 55, iy), item_title, fill=NAVY, font=font_subtitle)

            # Item description — wrap text
            desc_x = x + 55
            desc_y = iy + 25
            # Simple word wrap
            words = item_desc.split()
            line = ""
            for word in words:
                test = line + " " + word if line else word
                if text_width(draw, test, font_section_body) > pillar_w - 90:
                    draw.text((desc_x, desc_y), line, fill=(120, 120, 135), font=font_section_body)
                    desc_y += 18
                    line = word
                else:
                    line = test
            if line:
                draw.text((desc_x, desc_y), line, fill=(120, 120, 135), font=font_section_body)

    # ── Bottom connector line ──────────────────────────────
    conn_y = start_y + pillar_h + 30
    for idx in range(3):
        cx = start_x + idx * (pillar_w + gap) + pillar_w // 2
        draw.line([(cx, start_y + pillar_h), (cx, conn_y)], fill=MID_GRAY, width=1)

    draw.line([(start_x + pillar_w // 2, conn_y),
               (start_x + 2 * (pillar_w + gap) + pillar_w // 2, conn_y)], fill=MID_GRAY, width=1)

    # Central label
    center_x = W // 2
    unified = "UNIFIED INTELLIGENCE LAYER"
    uw = text_width(draw, unified, font_klikk)
    # Background pill
    draw.rounded_rectangle([center_x - uw // 2 - 16, conn_y - 12, center_x + uw // 2 + 16, conn_y + 12],
                           radius=12, fill=NAVY)
    draw.text((center_x - uw // 2, conn_y - 8), unified, fill=WHITE, font=font_klikk)

    # ── Legend / watermark ─────────────────────────────────
    legend_y = H - 55
    draw.text((80, legend_y), "All features planned", fill=MID_GRAY, font=font_klikk)

    wm = "klikk.co.za"
    ww = text_width(draw, wm, font_klikk)
    draw.text((W - ww - 80, legend_y), wm, fill=MID_GRAY, font=font_klikk)

    img.save(os.path.join(OUTPUT_DIR, "klikk-bi-overview.png"), "PNG", dpi=(300, 300))
    print("Created: klikk-bi-overview.png")


# ═══════════════════════════════════════════════════════════════
# Generate all three
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    create_rentals_diagram()
    create_real_estate_diagram()
    create_bi_diagram()
    print("\nAll 3 diagrams generated in:", OUTPUT_DIR)
