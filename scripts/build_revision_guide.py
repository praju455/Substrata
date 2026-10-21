# ruff: noqa: E501
"""Build the Substrata A-Z revision guide as a 15-page PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "substrata-a-to-z-revision-guide.pdf"
DIAGRAMS = ROOT / "docs" / "diagrams"

PAGE_W, PAGE_H = A4
M = 38
NAVY = colors.HexColor("#10264B")
TEAL = colors.HexColor("#009B9A")
DARK_TEAL = colors.HexColor("#087A73")
PURPLE = colors.HexColor("#7048E8")
AMBER = colors.HexColor("#F2A900")
RED = colors.HexColor("#E44747")
INK = colors.HexColor("#253247")
MUTED = colors.HexColor("#66758A")
LIGHT_BLUE = colors.HexColor("#EAF3FB")
LIGHT_TEAL = colors.HexColor("#E5F7F5")
LIGHT_PURPLE = colors.HexColor("#F0EBFF")
LIGHT_AMBER = colors.HexColor("#FFF4D7")
LIGHT_RED = colors.HexColor("#FDE8E8")
LINE = colors.HexColor("#D8E0EA")


def style(size=9, leading=None, color=INK, bold=False, align=TA_LEFT):
    return ParagraphStyle(
        "p",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading or size * 1.28,
        textColor=color,
        alignment=align,
        spaceAfter=0,
        spaceBefore=0,
    )


BODY = style(9.1, 12)
SMALL = style(7.7, 10)
TINY = style(6.8, 8.5)


class Guide:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.c = canvas.Canvas(str(path), pagesize=A4)
        self.c.setTitle("Substrata A-Z Project Revision Guide")
        self.c.setAuthor("Team V-Max")
        self.c.setSubject("SAP Hackfest Bengaluru 2026 project study guide and judge question bank")
        self.page = 0

    def start(self, title: str, kicker: str = "SUBSTRATA A-Z REVISION GUIDE"):
        self.page += 1
        c = self.c
        c.setFillColor(TEAL)
        c.rect(0, PAGE_H - 12, PAGE_W, 12, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(TEAL)
        c.drawString(M, PAGE_H - 32, kicker)
        c.setFont("Helvetica-Bold", 19)
        c.setFillColor(NAVY)
        c.drawString(M, PAGE_H - 58, title)
        c.setStrokeColor(LINE)
        c.line(M, PAGE_H - 69, PAGE_W - M, PAGE_H - 69)
        return PAGE_H - 84

    def finish(self):
        c = self.c
        c.setStrokeColor(LINE)
        c.line(M, 28, PAGE_W - M, 28)
        c.setFont("Helvetica", 7)
        c.setFillColor(MUTED)
        c.drawString(
            M,
            17,
            "SAP Hackfest Bengaluru 2026 | Synthetic prototype | Revise current vs planned carefully",
        )
        c.drawRightString(PAGE_W - M, 17, f"{self.page} / 15")
        c.showPage()

    def para(self, text, x, y, w, st=BODY):
        p = Paragraph(text, st)
        _, h = p.wrap(w, PAGE_H)
        p.drawOn(self.c, x, y - h)
        return y - h

    def section(self, text, x, y, w, color=NAVY, size=11.5):
        self.c.setFillColor(color)
        self.c.roundRect(x, y - 21, w, 21, 5, fill=1, stroke=0)
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", size)
        self.c.drawString(x + 9, y - 15, text)
        return y - 29

    def bullets(self, items, x, y, w, st=BODY, gap=4, color=TEAL):
        for item in items:
            self.c.setFillColor(color)
            self.c.circle(x + 3, y - 5, 2.1, fill=1, stroke=0)
            y = self.para(item, x + 12, y, w - 12, st) - gap
        return y

    def callout(self, title, text, x, y, w, fill=LIGHT_TEAL, edge=TEAL, st=BODY):
        p1 = Paragraph(title, style(10, 12, edge, True))
        p2 = Paragraph(text, st)
        _, h1 = p1.wrap(w - 22, PAGE_H)
        _, h2 = p2.wrap(w - 22, PAGE_H)
        h = h1 + h2 + 24
        self.c.setFillColor(fill)
        self.c.setStrokeColor(edge)
        self.c.roundRect(x, y - h, w, h, 8, fill=1, stroke=1)
        p1.drawOn(self.c, x + 11, y - 10 - h1)
        p2.drawOn(self.c, x + 11, y - 16 - h1 - h2)
        return y - h

    def image(self, name, x, y, w, h, pad=4):
        path = DIAGRAMS / name
        img = ImageReader(str(path))
        iw, ih = img.getSize()
        scale = min((w - 2 * pad) / iw, (h - 2 * pad) / ih)
        dw, dh = iw * scale, ih * scale
        dx = x + (w - dw) / 2
        dy = y - h + (h - dh) / 2
        self.c.setFillColor(colors.white)
        self.c.setStrokeColor(LINE)
        self.c.roundRect(x, y - h, w, h, 7, fill=1, stroke=1)
        self.c.drawImage(img, dx, dy, dw, dh, preserveAspectRatio=True, mask="auto")

    def table(self, rows, x, y, widths, header=True, font=7.5, leading=9.4):
        pdata = []
        for ri, row in enumerate(rows):
            pdata.append(
                [
                    Paragraph(
                        str(cell),
                        style(
                            font, leading, NAVY if ri == 0 and header else INK, ri == 0 and header
                        ),
                    )
                    for cell in row
                ]
            )
        t = Table(pdata, colWidths=widths, repeatRows=1 if header else 0)
        ts = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.45, LINE),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE if header else colors.white),
        ]
        for r in range(1, len(rows)):
            if r % 2 == 0:
                ts.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F8FAFC")))
        t.setStyle(TableStyle(ts))
        _, h = t.wrap(sum(widths), PAGE_H)
        t.drawOn(self.c, x, y - h)
        return y - h

    def save(self):
        self.c.save()


def p1(g: Guide):
    y = g.start("Substrata: A-Z Project Revision Guide", "SAP HACKFEST BENGALURU 2026")
    g.c.setFont("Helvetica-Bold", 29)
    g.c.setFillColor(NAVY)
    g.c.drawString(M, y - 35, "Evidence -> Runway -> Governed Action")
    y -= 64
    y = (
        g.callout(
            "One-sentence pitch",
            "Substrata reveals hidden shared Tier-N dependencies, shows how long production remains protected, and keeps every high-impact response evidence-backed, deterministic, and human-approved.",
            M,
            y,
            PAGE_W - 2 * M,
            LIGHT_PURPLE,
            PURPLE,
            style(12, 16),
        )
        - 14
    )
    g.image("19-world-map-tier-n-concentration.png", M, y, PAGE_W - 2 * M, 300)
    y -= 315
    y = g.para(
        "<b>Use this guide in three passes:</b> 1) pages 1-5 for the pitch story, 2) pages 6-13 for technical defence, and 3) pages 14-15 for rapid judge-question rehearsal.",
        M,
        y,
        PAGE_W - 2 * M,
        style(10, 13),
    )
    y -= 10
    g.bullets(
        [
            "<b>Current:</b> synthetic graph discovery, replay, deterministic impact, dry-run approval, audit, and a cited read-only domain assistant.",
            "<b>Orchestration:</b> LangGraph risk-review and assistant workflows, LangChain bounded context assembly, Google Gen AI SDK/Groq adapters, optional Tavily evidence, and an offline fallback.",
            "<b>Never claim:</b> live customer accuracy, live SAP access, autonomous purchasing, or that 10/10 replay consistency means prediction accuracy.",
        ],
        M,
        y,
        PAGE_W - 2 * M,
        style(9, 12),
    )
    g.finish()


def p2(g: Guide):
    y = g.start("A-Z mental model")
    terms = [
        ("A", "Audit", "Hash-linked record of evidence, versions, approver, reason, and result."),
        (
            "B",
            "BOM",
            "Where-used structure connecting materials and components to products and plants.",
        ),
        ("C", "Candidate link", "Evidence-backed relationship proposal; never automatically true."),
        ("D", "Decision runway", "Time between stock-cover exhaustion and alternative readiness."),
        ("E", "Evidence", "Exact cited passage or structured record supporting a claim."),
        (
            "F",
            "False diversification",
            "Several Tier-1 suppliers secretly share an upstream dependency.",
        ),
        (
            "G",
            "GraphStore",
            "Versioned graph interface used for transparent traversal and evidence paths.",
        ),
        ("H", "Human gate", "Named approver accepts or rejects a consequential dry-run action."),
        ("I", "Inferred", "Unconfirmed relationship state that remains visibly uncertain."),
        ("J", "JSON contract", "Schema-constrained model output checked before use."),
        ("K", "Known", "Directly supported information, separated from inferred and unknown."),
        (
            "L",
            "LangGraph",
            "Coordinates governed risk-review and assistant workflows; deterministic services still perform graph and runway math.",
        ),
        ("M", "Mapper", "Proposes cited hidden relationships from records and evidence."),
        ("N", "Tier-N", "Any deeper supplier tier beyond the direct Tier-1 relationship."),
        ("O", "Offline replay", "Seeded local fallback that works without provider or SAP access."),
        ("P", "Policy", "Deterministic rules for allow, review, block, staleness, and authority."),
        ("Q", "Qualification time", "Days required before an alternate source can safely supply."),
        ("R", "Relationship status", "Inferred, confirmed, rejected, expired, or superseded."),
        ("S", "Sensor", "Classifies a disruption and proposes affected entities."),
        (
            "T",
            "Traceability",
            "Ability to follow an answer to evidence, versions, math, and approval.",
        ),
        ("U", "Uncertainty", "Explicit confidence, gaps, ranges, and incomplete states."),
        (
            "V",
            "Version pinning",
            "Calculation and approval refer to an immutable graph/input revision.",
        ),
        ("W", "Warning gained", "Extra decision time versus the same Tier-1-only snapshot."),
        (
            "X",
            "eXecution",
            "Prototype produces approved dry-run payloads, never real procurement writes.",
        ),
        ("Y", "Yielded control", "AI pauses when evidence, authority, or inputs are insufficient."),
        (
            "Z",
            "Zero hidden claims",
            "Every material assertion is cited, labelled, calculated, or marked unknown.",
        ),
    ]
    col_w = (PAGE_W - 2 * M - 14) / 2
    for ci in range(2):
        x = M + ci * (col_w + 14)
        yy = y
        for letter, term, desc in terms[ci * 13 : (ci + 1) * 13]:
            g.c.setFillColor(TEAL if ci == 0 else PURPLE)
            g.c.circle(x + 11, yy - 10, 10, fill=1, stroke=0)
            g.c.setFillColor(colors.white)
            g.c.setFont("Helvetica-Bold", 9)
            g.c.drawCentredString(x + 11, yy - 13, letter)
            yy = g.para(f"<b>{term}:</b> {desc}", x + 27, yy, col_w - 27, style(8.7, 10.7)) - 5
    g.finish()


def p3(g: Guide):
    y = g.start("1. Problem, theme, and case study")
    y = (
        g.callout(
            "Problem statement",
            "Manufacturers often see direct Tier-1 contracts but not the deeper suppliers, facilities, materials, owners, regions, ports, or routes that those suppliers share. A single disruption can therefore hit several apparently independent paths at once.",
            M,
            y,
            PAGE_W - 2 * M,
            LIGHT_RED,
            RED,
        )
        - 10
    )
    g.image("19-world-map-tier-n-concentration.png", M, y, PAGE_W - 2 * M, 245)
    y -= 258
    left = M
    right = M + 264
    y1 = g.section("Why now", left, y, 248, TEAL)
    y1 = g.bullets(
        [
            "More than 80% of merchandise trade by volume moves by sea; ports and routes matter, but Substrata is not maritime-only.",
            "Geopolitical controls, ownership changes, plant incidents, material shortages, and regional shocks can expose shared concentration.",
            "Fragmented ERP, document, news, and supplier evidence delays action until inventory is already low.",
        ],
        left,
        y1,
        248,
        SMALL,
    )
    y2 = g.section("Illustrative Nexperia replay", right, y, 255, RED)
    y2 = g.bullets(
        [
            "Public reporting provides only the disruption context; the supplier graph, stocks, lead times, costs, and actions are synthetic.",
            "The demo assumes 18 days of cover and 90 days to qualify an alternative, producing a 72-day exposure gap.",
            "This case makes the idea concrete; the platform remains industry-neutral and supports many dependency types.",
        ],
        right,
        y2,
        255,
        SMALL,
        color=RED,
    )
    y = min(y1, y2) - 8
    g.callout(
        "Judge-safe sentence",
        "The case study illustrates the decision problem; it does not claim access to a real confidential supplier network or prove real-world accuracy.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_AMBER,
        AMBER,
        SMALL,
    )
    g.finish()


def p4(g: Guide):
    y = g.start("2. Users, current gap, value, and business hypothesis")
    rows = [
        ["User", "Main decision", "Information needed", "Current pain"],
        [
            "Supply-risk analyst",
            "Is the hidden dependency credible and material?",
            "Evidence, path, status, confidence, affected scope",
            "Reconciles fragmented records and explains uncertainty",
        ],
        [
            "Supply planner",
            "When will production become exposed?",
            "Inventory, supply, consumption, qualification time, plant",
            "Risk alerts do not become a decision deadline",
        ],
        [
            "Procurement approver",
            "Which response is justified and authorized?",
            "Options, assumptions, cost/risk, policy reason",
            "Context is split across analysis and approval tools",
        ],
        [
            "Supplier contact",
            "Is the proposed relationship correct?",
            "Narrow claim, source context, deadline, permitted use",
            "Broad questionnaires create effort and confidentiality concern",
        ],
    ]
    y = g.table(rows, M, y, [94, 132, 155, 138], font=7.1, leading=8.8) - 13
    col = (PAGE_W - 2 * M - 14) / 2
    y1 = g.section("Current approach", M, y, col, RED)
    y1 = g.bullets(
        [
            "Tier-1 declarations and questionnaires create only partial visibility.",
            "Analysts manually reconcile ERP records, documents, news, and calls.",
            "Static maps age quickly; names and units differ across sources.",
            "Risk scores often hide the decision deadline and evidence quality.",
        ],
        M,
        y1,
        col,
        SMALL,
        color=RED,
    )
    x2 = M + col + 14
    y2 = g.section("Substrata value", x2, y, col, TEAL)
    y2 = g.bullets(
        [
            "Evidence-backed candidate links with visible uncertainty.",
            "Human confirmation before inference becomes accepted truth.",
            "Deterministic impact and runway instead of vague urgency.",
            "Governed dry-run actions with named approval and audit.",
        ],
        x2,
        y2,
        col,
        SMALL,
    )
    y = min(y1, y2) - 12
    g.callout(
        "Business hypothesis - not validated yet",
        "Primary user: supply-risk analyst or planner. Likely buyers: procurement, supply-chain risk, or resilience leadership. Value hypothesis: earlier, more defensible decisions. Interviews must validate willingness to adopt, data-sharing constraints, buying authority, and reviewer workload.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_PURPLE,
        PURPLE,
        SMALL,
    )
    g.finish()


def p5(g: Guide):
    y = g.start("3. End-to-end operating model")
    g.image("03-system-context.png", M, y, PAGE_W - 2 * M, 285)
    y -= 298
    rows = [
        ["Stage", "System responsibility", "Human responsibility"],
        [
            "1. Ingest",
            "Load ERP-shaped records, documents, declared links, and sourced events",
            "Confirm legal use, source, unit, and freshness",
        ],
        [
            "2. Infer",
            "Mapper proposes a structured relationship with exact evidence",
            "Review ambiguity; do not treat confidence as truth",
        ],
        [
            "3. Confirm",
            "Store candidate as inferred and send a bounded request",
            "Analyst or supplier confirms, rejects, or lets it expire",
        ],
        [
            "4. Sense",
            "Sensor classifies disruption and resolves affected entities",
            "Resolve ambiguous entity or severity matches",
        ],
        [
            "5. Calculate",
            "Deterministic engine traverses a pinned graph and calculates runway",
            "Check incomplete inputs, units, and assumptions",
        ],
        [
            "6. Act",
            "Action prepares options; policy routes approve/review/block",
            "Named approver accepts or rejects with reason",
        ],
    ]
    y = g.table(rows, M, y, [63, 285, 171], font=7.0, leading=8.5) - 10
    g.callout(
        "Core differentiator",
        "Evidence to confirmation, confirmation to runway, and runway to governed action - without allowing uncertain AI output to become supply-chain truth.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_TEAL,
        TEAL,
        style(9.4, 12),
    )
    g.finish()


def p6(g: Guide):
    y = g.start("4. Evidence, hidden-link discovery, and confirmation")
    g.image("01-visibility-gap.png", M, y, PAGE_W - 2 * M, 270)
    y -= 282
    col = (PAGE_W - 2 * M - 14) / 2
    y1 = g.section("How a candidate link is formed", M, y, col, PURPLE)
    y1 = g.bullets(
        [
            "Normalize names, sites, identifiers, units, and dates.",
            "Combine deterministic signals such as exact IDs, BOM references, addresses, ownership, and declared links.",
            "Use pretrained models only for structured extraction, similarity, and explanation.",
            "Attach exact evidence spans, source, observation time, model/prompt version, and confidence components.",
        ],
        M,
        y1,
        col,
        SMALL,
        color=PURPLE,
    )
    x2 = M + col + 14
    y2 = g.section("Relationship state machine", x2, y, col, AMBER)
    y2 = g.bullets(
        [
            "<b>Inferred:</b> candidate only; may influence a range but stays visibly uncertain.",
            "<b>Confirmed:</b> accepted by an authorized analyst or supplier response.",
            "<b>Rejected:</b> negative evidence is preserved for review and learning.",
            "<b>Expired/superseded:</b> stale claims never silently remain current.",
        ],
        x2,
        y2,
        col,
        SMALL,
        color=AMBER,
    )
    y = min(y1, y2) - 10
    g.callout(
        "What link prediction means here",
        "Substrata can predict candidate relationships, but it does not claim a new link-prediction algorithm. The innovation is the operational chain around prediction: cited evidence, bounded confirmation, deterministic impact, decision runway, policy, and audit.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_RED,
        RED,
        SMALL,
    )
    g.finish()


def p7(g: Guide):
    y = g.start("5. What is agentic, and what is not")
    g.image("05-agent-collaboration.png", M, y, PAGE_W - 2 * M, 340)
    y -= 352
    rows = [
        ["Role", "Agentic contribution", "Hard boundary"],
        [
            "Mapper",
            "Finds and explains evidence-backed candidate links",
            "Cannot confirm a relationship",
        ],
        ["Sensor", "Classifies events and proposes affected entities", "Ambiguity goes to review"],
        [
            "Domain assistant",
            "Answers path-specific questions with citations and known/inferred/unknown labels",
            "Cannot change graph truth or perform impact math",
        ],
        [
            "Action",
            "Prepares and compares mitigation drafts",
            "No real purchasing or shipment execution",
        ],
        [
            "Compliance/Audit",
            "Routes policy decisions and records provenance",
            "Rules, versions, and authority are deterministic",
        ],
    ]
    y = g.table(rows, M, y, [91, 257, 171], font=7.1, leading=8.7) - 10
    g.callout(
        "LangGraph and LangChain",
        "LangGraph coordinates the governed risk-review stages and the assistant's retrieve, optional-web, generate, and validate steps. LangChain assembles bounded graph, evidence, report, and optional Tavily context for the assistant. Neither replaces deterministic calculations, confirms relationships automatically, or grants approval.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_PURPLE,
        PURPLE,
        SMALL,
    )
    g.finish()


def p8(g: Guide):
    y = g.start("6. Deterministic impact and decision runway")
    g.image("02-runway-timeline.png", M, y, PAGE_W - 2 * M, 285)
    y -= 297
    y = (
        g.callout(
            "Synthetic worked example",
            "Available stock = 1,200 units; confirmed incoming supply = 600 units; daily consumption = 100 units. Stock cover = (1,200 + 600) / 100 = 18 days. Alternate qualification = 90 days. Exposure gap = 90 - 18 = 72 days.",
            M,
            y,
            PAGE_W - 2 * M,
            LIGHT_PURPLE,
            PURPLE,
            style(9.2, 12),
        )
        - 12
    )
    col = (PAGE_W - 2 * M - 14) / 2
    y1 = g.section("Deterministic engine owns", M, y, col, NAVY)
    y1 = g.bullets(
        [
            "Version-pinned graph traversal and affected paths.",
            "BOM where-used, plants, products, and dependency support.",
            "Unit validation, stock cover, qualification time, ranges, and truncation.",
            "Policy thresholds, staleness checks, and approval validity.",
        ],
        M,
        y1,
        col,
        SMALL,
    )
    x2 = M + col + 14
    y2 = g.section("AI may assist with", x2, y, col, TEAL)
    y2 = g.bullets(
        [
            "Extracting evidence into a strict schema.",
            "Explaining why a path is relevant.",
            "Drafting a rationale or supplier message.",
            "Never inventing quantities, paths, authority, or arithmetic.",
        ],
        x2,
        y2,
        col,
        SMALL,
    )
    y = min(y1, y2) - 9
    g.callout(
        "Important distinction",
        "The 72-day figure is an operational exposure gap in a synthetic scenario. It is not a project schedule, forecast accuracy claim, or real Nexperia inventory estimate.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_RED,
        RED,
        SMALL,
    )
    g.finish()


def p9(g: Guide):
    y = g.start("7. Governance, safety, privacy, and audit")
    g.image("06-autonomy-matrix.png", M, y, PAGE_W - 2 * M, 310)
    y -= 323
    rows = [
        ["Risk", "Control"],
        [
            "Incomplete or conflicting Tier-N data",
            "Preserve provenance, show uncertainty, request confirmation",
        ],
        [
            "Model hallucination or malformed output",
            "Structured JSON, exact evidence spans, schema validation, review",
        ],
        [
            "Confidentiality and source licensing",
            "Tenant isolation, minimum excerpts, access control, approved sources",
        ],
        ["False urgency from assumptions", "Show unit, source, time, range, and incomplete status"],
        [
            "Unsafe automation",
            "Real procurement changes prohibited; named approval and dry-run only",
        ],
        ["SAP/provider unavailable", "Core seeded replay stays offline and deterministic"],
    ]
    y = g.table(rows, M, y, [182, 337], font=7.5, leading=9.1) - 10
    g.callout(
        "Audit limitation",
        "A SHA-256 chain can reveal later record changes. It does not prove that the original source, inference, or human decision was correct. Truth still depends on evidence quality and authorized confirmation.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_AMBER,
        AMBER,
        SMALL,
    )
    g.finish()


def p10(g: Guide):
    y = g.start("8. Architecture, data model, reliability, and security")
    g.image("04-layered-architecture.png", M, y, PAGE_W - 2 * M, 300)
    y -= 312
    rows = [
        ["Layer", "Key design"],
        [
            "Data and provenance",
            "Entities, relationships, evidence, events, scenarios, actions, approvals; each material record is versioned and sourced",
        ],
        [
            "Persistence",
            "SQLAlchemy + Alembic; SQLite WAL for local demo; PostgreSQL/pgvector for tenant platform",
        ],
        [
            "Graph",
            "GraphStore abstraction; NetworkX and PostgreSQL traversal now; HANA property graph only if entitled",
        ],
        [
            "Application",
            "FastAPI/Pydantic owns domain logic; Next.js/TypeScript/Cytoscape renders the workspace; SSE carries updates",
        ],
        [
            "Reliability",
            "Seeded fixtures, retries, checkpoints, stale-input rejection, offline provider fallback, and repeatable replay",
        ],
        [
            "Security",
            "Tenant isolation, role checks, minimum source excerpts, signed expiring supplier links, bounded requests, and no secrets in logs",
        ],
    ]
    y = g.table(rows, M, y, [102, 417], font=7.4, leading=9.0) - 10
    g.callout(
        "Data-model rule",
        "Keep legal entity, supplier site, facility, material, component, product, plant, owner, region, port, and route distinct. Collapsing them creates false paths and misleading impact.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_BLUE,
        NAVY,
        SMALL,
    )
    g.finish()


def p11(g: Guide):
    y = g.start("9. Technology map: current, planned, optional")
    g.image("12-tech-stack.png", M, y, PAGE_W - 2 * M, 335)
    y -= 348
    rows = [
        ["Status", "Technology", "Purpose"],
        ["Current", "Next.js, TypeScript, Cytoscape.js", "Interactive graph and workspace"],
        ["Current", "FastAPI, Pydantic, SSE", "Typed API, domain services, live updates"],
        [
            "Current",
            "NetworkX, SQLAlchemy, Alembic, SQLite/PostgreSQL",
            "Graph traversal, persistence, migrations",
        ],
        [
            "Current",
            "Provider-neutral LLMClient, Gemini/Groq transport, offline mock",
            "Structured extraction and fallback",
        ],
        [
            "Current",
            "LangGraph + LangChain + Google Gen AI SDK",
            "Read-only cited assistant and Gemini adapter",
        ],
        [
            "Optional",
            "Tavily public-web retrieval",
            "Current public evidence; always labelled inferred",
        ],
        [
            "Optional",
            "MCP/A2A, MapLibre, OpenTelemetry",
            "Bounded interoperability, map view, observability",
        ],
        [
            "SAP stretch",
            "BTP, Integration Suite, HANA graph/vector, AI Core",
            "Read-only clean-core integration if access exists",
        ],
    ]
    y = g.table(rows, M, y, [66, 222, 231], font=7.2, leading=8.8) - 10
    g.callout(
        "Training answer",
        "There is no custom LLM training or fine-tuning. A separate classical gradient-boosted link scorer can learn from reviewed labels under activation gates; it is not the generative model and is not required for the finale proof.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_RED,
        RED,
        SMALL,
    )
    g.finish()


def p12(g: Guide):
    y = g.start("10. SAP alignment and honest integration path")
    g.image("13-deployment-topology.png", M, y, PAGE_W - 2 * M, 295)
    y -= 307
    rows = [
        ["SAP technology/concept", "Role in Substrata", "Status"],
        [
            "SAP S/4HANA released APIs",
            "Read-only procurement, BOM, inventory, and lead-time context",
            "Access-dependent",
        ],
        [
            "SAP Business Network / Ariba APIs",
            "Supplier and trading-partner relationships",
            "Access-dependent",
        ],
        [
            "SAP BTP + Integration Suite",
            "API-first, side-by-side clean-core extension",
            "Finale stretch",
        ],
        [
            "SAP HANA Cloud graph/vector",
            "Dependency traversal and grounded retrieval",
            "Entitlement-dependent",
        ],
        ["SAP AI Core generative AI hub", "Governed pretrained-model adapter", "Optional"],
        ["Joule, MCP, and A2A", "User interaction and agent interoperability adapters", "Optional"],
    ]
    y = g.table(rows, M, y, [130, 276, 113], font=7.2, leading=8.8) - 10
    y = g.section("Learning Hub connection", M, y, PAGE_W - 2 * M, TEAL)
    g.bullets(
        [
            "Purchasing in SAP S/4HANA: procurement master data, sources of supply, and approvals.",
            "SAP Business Network: supplier collaboration and multi-tier visibility.",
            "Clean Core: API-first side-by-side extension instead of ERP modification.",
            "Responsible AI: evidence, uncertainty, human oversight, traceability, and governed automation.",
        ],
        M,
        y,
        PAGE_W - 2 * M,
        SMALL,
    )
    g.finish()


def p13(g: Guide):
    y = g.start("11. Demo, evaluation, feasibility, and roadmap")
    col = (PAGE_W - 2 * M - 12) / 2
    g.image("10-demo-replay.png", M, y, col, 218)
    g.image("14-evaluation-roadmap.png", M + col + 12, y, col, 218)
    y -= 230
    rows = [
        ["Measure", "Proposed target", "Meaning"],
        ["Hidden-link precision", ">= 0.80", "Correct candidates at review threshold"],
        ["Hidden-link recall", ">= 0.70", "Held-out synthetic links found"],
        ["Impact fixtures", "100% exact", "Hand-calculated deterministic cases"],
        ["Prohibited actions", "100% blocked", "Policy safety tests"],
        ["Offline replay", "10/10 identical", "Reproducibility, not accuracy"],
    ]
    y = g.table(rows, M, y, [160, 96, 263], font=7.4, leading=9.0) - 12
    rows2 = [
        ["Gate", "Compact deliverable", "Exit condition"],
        [
            "Plan",
            "Validate persona, decision, data, uncertainty, SAP access",
            "One practitioner validates workflow and runway",
        ],
        [
            "Design",
            "Freeze contracts, boundaries, failure behavior, fixture",
            "Every input, output, assumption, and authority is explainable",
        ],
        [
            "Build",
            "Harden orchestration, citations, impact, approval, audit, fallback",
            "Fresh environment runs the complete scenario",
        ],
        [
            "Test",
            "Measure links, answers, math, policy, failures, usability",
            "Repeatable demo; every result is traceable",
        ],
    ]
    y = g.table(rows2, M, y, [62, 283, 174], font=7.1, leading=8.7) - 10
    g.callout(
        "Smallest credible finale proof",
        "Discover one hidden dependency, confirm it, replay one event, calculate runway, compare simulated actions, approve one, and verify the audit chain. Exclude autonomous purchasing, production SAP writes, unbounded crawling, customer-accuracy claims, and a custom GNN.",
        M,
        y,
        PAGE_W - 2 * M,
        LIGHT_AMBER,
        AMBER,
        SMALL,
    )
    g.finish()


def qa_block(g, items, x, y, w, accent):
    for q, a in items:
        g.c.setFillColor(accent)
        g.c.roundRect(x, y - 14, 18, 14, 3, fill=1, stroke=0)
        g.c.setFillColor(colors.white)
        g.c.setFont("Helvetica-Bold", 6.6)
        g.c.drawCentredString(x + 9, y - 10, "Q")
        y = g.para(f"<b>{q}</b><br/>{a}", x + 24, y, w - 24, style(8.3, 10.1)) - 8
    return y


def p14(g: Guide):
    y = g.start("12. Judge Q&A - problem, user, value, and SAP")
    col = (PAGE_W - 2 * M - 16) / 2
    left = [
        (
            "What exact problem do you solve?",
            "False diversification: Tier-1 suppliers can share a deeper dependency. We surface evidence, quantify runway, and govern response.",
        ),
        (
            "Who is the primary user?",
            "A supply-risk analyst or planner; procurement approvers and supplier contacts participate at specific gates.",
        ),
        (
            "Why is this urgent?",
            "A hidden dependency can affect multiple paths simultaneously, while fragmented evidence delays action until stock is low.",
        ),
        (
            "Is the maritime statistic your whole problem?",
            "No. Ports and routes are one dependency class alongside suppliers, facilities, materials, owners, and regions.",
        ),
        (
            "How is this different from Cambridge link prediction?",
            "Cambridge supports the technical plausibility of reconstruction. Substrata adds citations, confirmation, deterministic impact/runway, action governance, and audit.",
        ),
        (
            "Is link prediction already implemented elsewhere?",
            "Research and commercial tools exist. We do not claim novelty in the algorithm; our thesis is the verifiable decision workflow around it.",
        ),
        (
            "How is this different from SAP or risk platforms?",
            "We position it as a complementary, narrow experiment - not as proof that they lack multi-tier visibility or orchestration.",
        ),
        (
            "What value do users receive?",
            "Earlier investigation, a decision deadline instead of a vague score, less false certainty, and a reviewable action record.",
        ),
        (
            "What is your business model?",
            "Still a hypothesis: likely enterprise software or an add-on for risk/procurement teams. Buyer, pricing, and data-sharing must be validated.",
        ),
    ]
    right = [
        (
            "Why SAP?",
            "The workflow naturally consumes procurement, BOM, inventory, planning, supplier-network, and approval context.",
        ),
        (
            "Do you have live SAP access?",
            "No. Current data is synthetic and SAP-shaped. Any SAP adapter remains read-only and subject to verified access.",
        ),
        (
            "Which SAP technologies fit?",
            "S/4 APIs, Business Network/Ariba, BTP Integration Suite, HANA graph/vector, AI Core, and optional Joule/MCP/A2A adapters.",
        ),
        (
            "What is clean core here?",
            "Use released APIs and side-by-side extension on BTP; do not modify the ERP core.",
        ),
        (
            "What if SAP services are unavailable?",
            "The seeded local replay remains the core path; the pitch does not depend on internet or entitlement.",
        ),
        (
            "Why use the Nexperia case?",
            "It is a public, understandable disruption context. The graph, inventory, lead times, and actions remain explicitly synthetic.",
        ),
        (
            "Is the 72-day result real?",
            "No. It is the synthetic difference between assumed 90-day qualification and calculated 18-day cover.",
        ),
        (
            "What must be validated next?",
            "Practitioner need, acceptable uncertainty, data access/licensing, reviewer burden, SAP entitlements, and measured held-out performance.",
        ),
        (
            "Why should this advance?",
            "The proof is narrow, explainable, safe, and feasible: one link, one event, one deterministic result, one approval, one audit trail.",
        ),
    ]
    qa_block(g, left, M, y, col, TEAL)
    qa_block(g, right, M + col + 16, y, col, PURPLE)
    g.finish()


def p15(g: Guide):
    y = g.start("13. Judge Q&A - AI, math, safety, validation, and final recall")
    col = (PAGE_W - 2 * M - 16) / 2
    left = [
        (
            "What is agentic?",
            "Bounded roles interpret evidence, call tools, pause for confirmation, prepare options, and preserve state across human gates.",
        ),
        (
            "Why LangGraph?",
            "It coordinates resumable risk-review stages and the assistant's retrieval and validation flow. It does not perform graph math or approve anything.",
        ),
        (
            "Why LangChain?",
            "It assembles bounded graph, evidence, report, and web context for cited answers labelled known, inferred, or unknown.",
        ),
        (
            "Do you train an LLM?",
            "No custom LLM training or fine-tuning. Pretrained models sit behind a provider-neutral gateway.",
        ),
        (
            "What is Google Gen AI SDK?",
            "The implemented optional client adapter for Gemini assistant access; Gemini is the model service, while the SDK is the integration library.",
        ),
        (
            "Can AI confirm a relationship?",
            "No. AI can propose and explain a candidate; an authorized analyst or supplier confirms or rejects it.",
        ),
        (
            "Who calculates impact?",
            "Deterministic NetworkX/PostgreSQL services perform traversal, units, exposure, runway, and policy checks.",
        ),
        (
            "What does the assistant cite?",
            "Graph records, exact evidence, saved reports, and optional Tavily results. No vector DB is required; web evidence stays inferred.",
        ),
        (
            "Can the system buy anything?",
            "No. It produces dry-run SAP-shaped drafts; real procurement writes are prohibited.",
        ),
    ]
    right = [
        (
            "How do you prevent hallucination?",
            "Strict JSON, schema validation, exact evidence spans, status labels, bounded tools, and human review.",
        ),
        (
            "What if evidence conflicts?",
            "Preserve both sources, keep the relationship inferred, show uncertainty, and request confirmation.",
        ),
        (
            "How is confidentiality handled?",
            "Tenant isolation, access control, minimum excerpts, approved sources, signed expiring requests, and no sensitive logs.",
        ),
        (
            "Does audit prove truth?",
            "No. It proves integrity of the recorded sequence, not correctness of the original evidence or decision.",
        ),
        (
            "Is accuracy proven?",
            "No. Current measurements are synthetic regression evidence. Targets become claims only after versioned held-out runs.",
        ),
        (
            "What does 10/10 mean?",
            "Ten identical seeded replays demonstrate reproducibility only, not prediction quality.",
        ),
        (
            "What if inputs are stale?",
            "The action expires or returns for review; approval is bound to versions and deadlines.",
        ),
        (
            "What is the biggest product risk?",
            "Poor evidence or too many false positives could create analyst distrust and review overload.",
        ),
        (
            "What is the final takeaway?",
            "Substrata turns hidden uncertainty into cited evidence, quantified runway, and accountable human action.",
        ),
    ]
    yl = qa_block(g, left, M, y, col, TEAL)
    yr = qa_block(g, right, M + col + 16, y, col, RED)
    yb = min(yl, yr) - 2
    g.callout(
        "Five numbers and labels to remember",
        "18 days cover | 90 days qualification | 72 days exposure | targets: precision >= 0.80, recall >= 0.70 | 10/10 identical replay = reproducibility only. Always say synthetic, target, planned, optional, or access-dependent where applicable.",
        M,
        yb,
        PAGE_W - 2 * M,
        LIGHT_AMBER,
        AMBER,
        TINY,
    )
    g.c.setFont("Helvetica", 5.8)
    g.c.setFillColor(MUTED)
    sources = (
        "Sources: <link href='https://events.sap.com/in-hackfest-bangalore-2026/en_us/home.html'>SAP Hackfest</link>; "
        "<link href='https://learning.sap.com/students'>SAP Learning Hub</link>; "
        "<link href='https://architecture.learning.sap.com/docs/golden-path/ai-golden-path/build-and-deliver/build-ai-agents'>SAP AI-agent guidance</link>; "
        "<link href='https://news.sap.com/2025/10/sap-connect-innovative-updates-supply-chain-management/'>SAP Supply Chain Orchestration</link>; "
        "<link href='https://www.ifm.eng.cam.ac.uk/research/supply-chain-ai-lab/current-themes/supply-chain-link-prediction/'>Cambridge Supply Chain AI Lab</link>; "
        "<link href='https://www.acea.auto/press-release/acea-calls-for-quick-resolution-to-critical-chip-supply-shortage/'>ACEA Nexperia statement</link>; "
        "<link href='https://unctad.org/system/files/official-document/rmt2022_en.pdf'>UNCTAD maritime review</link>; "
        "SAP Business Network multitier collaboration; SAP HANA property graph; SAP Clean Core; NIST AI 600-1. Full links are in README.md and docs/RESEARCH.md."
    )
    g.para(sources, M, 60, PAGE_W - 2 * M, style(5.8, 7, MUTED))
    g.finish()


def build():
    g = Guide(OUT)
    for page in (p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15):
        page(g)
    g.save()
    print(OUT)


if __name__ == "__main__":
    build()
