"""CFO-ready executive audit memo and exception schedule generation.

The report is intentionally deterministic and self-contained: it can be viewed
in the Streamlit app, downloaded as a print-ready PDF, or exported as a
standalone HTML memo for the audit committee.
"""

from __future__ import annotations

import csv
from datetime import date
from html import escape
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape as xml_escape

from forensic_scanner import ScanResult
from journal_generator import BATCH_ID

REPORT_PERIOD = "October 2026"
REPORT_AS_OF = "October 31, 2026"
REPORT_PREPARED = "November 9, 2026"
REPORT_CLASSIFICATION = "Internal - Audit Committee"
REPORT_STATUS = "Draft for CFO review"
REPORT_TITLE = "Executive Audit Memo"
REPORT_SUBTITLE = "ASC 606 Contract-to-Ledger Exception Gate"
REPORT_BATCH = BATCH_ID

RECOMMENDED_ACTIONS = {
    "TERMINATION_CONVENIENCE": (
        "Reflect the enforceable notice period in the revenue schedule and obtain "
        "a signed waiver or non-cancelable order form before recognizing revenue "
        "beyond delivered monthly service."
    ),
    "UNDISCLOSED_FREE_MONTHS": (
        "Incorporate all side-letter concessions into the transaction price at "
        "contract inception and reallocate revenue across the total service period, "
        "including free months."
    ),
    "MONEY_BACK_TRIAL": (
        "Gate trial billing and revenue recognition until written conversion "
        "evidence is attached to the opportunity; reverse any trial-period entries."
    ),
    "FEATURE_CONTINGENCY": (
        "Track undelivered feature obligations separately and defer the allocated "
        "transaction price until written customer acceptance is obtained."
    ),
}

CONTROL_RECOMMENDATIONS = [
    "Require deal-desk attestation that no undisclosed side letters, free months, or refund rights exist before the revenue schedule is locked.",
    "Move termination-right and substantive-penalty review into the contract-to-ledger close checklist.",
    "Gate trial billing until written conversion evidence is attached to the opportunity record.",
    "Track undelivered feature obligations in a controlled sub-ledger and defer the allocated transaction price until acceptance.",
    "Require controller sign-off on all manual revenue schedules and retain the ASC 606 evidence pack for audit.",
    "Post the attached adjusting entries before the close is locked and link each entry to the contract evidence.",
]

# ReportLab palette
DEEP = colors.HexColor("#2E1065")
INDIGO = colors.HexColor("#4C1D95")
PURPLE = colors.HexColor("#6D28D9")
LAVENDER = colors.HexColor("#A78BFA")
INK = colors.HexColor("#0F172A")
SLATE = colors.HexColor("#64748B")
LINE = colors.HexColor("#E9E5F7")
LIGHT = colors.HexColor("#F8FAFC")
PALE = colors.HexColor("#F5F3FF")
WHITE = colors.white


# ---------------------------------------------------------------------------
# Report data
# ---------------------------------------------------------------------------


def _money(value: float, decimals: int = 0) -> str:
    return f"${value:,.{decimals}f}"


def _exception_results(results: list[ScanResult]) -> list[ScanResult]:
    return [
        result
        for result in results
        if result.has_exception and result.overstated_revenue > 0.01
    ]


def _severity_rank(severity: str) -> int:
    return {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}.get(severity, 4)


def _exposure_rows(results: list[ScanResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in sorted(
        _exception_results(results),
        key=lambda item: (-item.overstated_revenue, item.deal_id),
    ):
        citations: list[str] = []
        for finding in result.findings:
            if finding.citation not in citations:
                citations.append(finding.citation)
        rows.append(
            {
                "deal_id": result.deal_id,
                "customer": result.customer,
                "erp": result.erp_source,
                "contract_id": result.contract_id,
                "loophole": result.loophole_names,
                "recognized": result.recognized_to_date,
                "supportable": result.expected_recognized,
                "overstated": result.overstated_revenue,
                "severity": result.severity,
                "citation": " | ".join(citations),
            }
        )
    return rows


def _finding_rows(results: list[ScanResult]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for result in results:
        for finding in result.findings:
            bucket = buckets.setdefault(
                finding.loophole_id,
                {
                    "loophole_id": finding.loophole_id,
                    "loophole": finding.name,
                    "citation": finding.citation,
                    "exposure": 0.0,
                    "deals": [],
                    "severities": [],
                },
            )
            bucket["exposure"] += finding.impact
            bucket["deals"].append(result.deal_id)
            bucket["severities"].append(result.severity)

    rows: list[dict[str, Any]] = []
    for bucket in buckets.values():
        severity = min(bucket["severities"], key=_severity_rank)
        rows.append(
            {
                "loophole_id": bucket["loophole_id"],
                "loophole": bucket["loophole"],
                "citation": bucket["citation"],
                "exposure": round(bucket["exposure"], 2),
                "count": len(bucket["deals"]),
                "deals": sorted(bucket["deals"]),
                "severity": severity,
                "action": RECOMMENDED_ACTIONS.get(
                    bucket["loophole_id"],
                    "Evaluate the contract terms and defer unsupported revenue until remediated.",
                ),
            }
        )
    return sorted(rows, key=lambda row: (-row["exposure"], row["loophole"]))


def _executive_summary(data: dict[str, Any]) -> str:
    top = data["exposures"][0] if data["exposures"] else None
    exception_rate = (
        data["exceptions"] / data["arrangements"] * 100 if data["arrangements"] else 0.0
    )
    summary = (
        f"During the {data['period']} close, FinAdvantage scanned "
        f"{data['arrangements']} SaaS arrangements, pairing executed contract "
        f"language and sales side-letters with NetSuite and QuickBooks revenue "
        f"schedules. {data['exceptions']} arrangements ({exception_rate:.1f}%) "
        f"contain at least one ASC 606 exception, and cumulative revenue recognized "
        f"exceeds supportable revenue by {_money(data['overstated'], 2)}. The "
        f"portfolio includes {data['critical']} Critical, {data['high']} High, and "
        f"{data['medium']} Medium exposures; {data['compliant']} arrangements passed "
        f"all four controls."
    )
    if top:
        summary += (
            f" The largest single exposure is {top['customer']} at "
            f"{_money(top['overstated'], 2)}, driven by {top['loophole']}."
        )
    summary += (
        f" The adjusting journal entry batch contains {data['journal_count']} "
        f"balanced entries totaling {_money(data['debit_total'], 2)}; entries remain "
        "pending controller approval and no ERP write-back has been performed."
    )
    return summary


def build_report_data(
    results: list[ScanResult],
    summary: dict[str, Any],
    totals: dict[str, Any],
    signoffs: dict[str, dict[str, str]] | None = None,
    approved_reversal: float | None = None,
    certified_revenue: float | None = None,
) -> dict[str, Any]:
    """Build the complete memo payload from the scanned portfolio and JE batch."""
    exposures = _exposure_rows(results)
    signoff_map = {
        result.deal_id: signoffs[result.deal_id]
        for result in results
        if result.has_exception and signoffs and result.deal_id in signoffs
    }
    data: dict[str, Any] = {
        "title": REPORT_TITLE,
        "subtitle": REPORT_SUBTITLE,
        "period": REPORT_PERIOD,
        "as_of": REPORT_AS_OF,
        "prepared": REPORT_PREPARED,
        "classification": REPORT_CLASSIFICATION,
        "status": REPORT_STATUS,
        "batch": REPORT_BATCH,
        "arrangements": int(summary["arrangements"]),
        "exceptions": int(summary["exceptions"]),
        "critical": int(summary["critical"]),
        "high": int(summary["high"]),
        "medium": int(summary["medium"]),
        "compliant": int(summary["compliant"]),
        "compliance_rate": float(summary["compliance_rate"]),
        "overstated": float(summary["total_overstated"]),
        "recognized": float(summary["total_recognized"]),
        "journal_count": int(totals["je_count"]),
        "line_count": int(totals["line_count"]),
        "debit_total": float(totals["debit_total"]),
        "credit_total": float(totals["credit_total"]),
        "variance": float(totals["difference"]),
        "balanced": bool(totals["balanced"]),
        "exposures": exposures,
        "findings": _finding_rows(results),
        "recommendations": CONTROL_RECOMMENDATIONS,
        "signoffs": signoff_map,
        "approved_reversal": float(approved_reversal or 0.0),
        "certified_revenue": float(
            certified_revenue if certified_revenue is not None else summary["total_recognized"]
        ),
    }
    data["executive_summary"] = _executive_summary(data)
    return data


def exception_schedule_csv(data: dict[str, Any]) -> str:
    """Flatten the exception schedule for a CFO or audit-committee download."""
    output = StringIO()
    fieldnames = [
        "Deal ID",
        "Customer",
        "ERP",
        "Contract ID",
        "Loophole",
        "Recognized To Date",
        "Supportable Revenue",
        "Overstated Revenue",
        "Risk Severity",
        "ASC 606 Citation",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data["exposures"]:
        writer.writerow(
            {
                "Deal ID": row["deal_id"],
                "Customer": row["customer"],
                "ERP": row["erp"],
                "Contract ID": row["contract_id"],
                "Loophole": row["loophole"],
                "Recognized To Date": f"{row['recognized']:.2f}",
                "Supportable Revenue": f"{row['supportable']:.2f}",
                "Overstated Revenue": f"{row['overstated']:.2f}",
                "Risk Severity": row["severity"],
                "ASC 606 Citation": row["citation"],
            }
        )
    return output.getvalue()


# ---------------------------------------------------------------------------
# Standalone HTML memo
# ---------------------------------------------------------------------------


def executive_memo_html(data: dict[str, Any]) -> str:
    """Return a self-contained, print-friendly HTML executive memo."""
    findings_html = ""
    for row in data["findings"]:
        findings_html += (
            "<tr>"
            f"<td><strong>{escape(row['loophole'])}</strong><br><span class='muted'>{escape(row['citation'])}</span></td>"
            f"<td class='num'>{row['count']}</td>"
            f"<td class='num'>{_money(row['exposure'], 0)}</td>"
            f"<td>{escape(row['severity'])}</td>"
            f"<td>{escape(row['action'])}</td>"
            "</tr>"
        )
    if not findings_html:
        findings_html = "<tr><td colspan='5'>No ASC 606 exceptions identified.</td></tr>"

    exposure_html = ""
    for row in data["exposures"]:
        exposure_html += (
            "<tr>"
            f"<td class='mono'>{escape(row['deal_id'])}</td>"
            f"<td><strong>{escape(row['customer'])}</strong><br><span class='muted'>{escape(row['erp'])}</span></td>"
            f"<td>{escape(row['loophole'])}</td>"
            f"<td class='num'>{_money(row['recognized'], 0)}</td>"
            f"<td class='num'>{_money(row['supportable'], 0)}</td>"
            f"<td class='num danger'>{_money(row['overstated'], 0)}</td>"
            f"<td>{escape(row['severity'])}</td>"
            "</tr>"
        )
    if not exposure_html:
        exposure_html = "<tr><td colspan='7'>No exceptions in scope.</td></tr>"

    recommendations_html = "".join(
        f"<li>{escape(recommendation)}</li>" for recommendation in data["recommendations"]
    )
    signoff_html = """
    <div class="signoff">
        <div><span>Prepared by</span><strong>FinAdvantage AI Digital Controllership</strong><div class="signline"></div></div>
        <div><span>Reviewed by</span><strong>Revenue Controller</strong><div class="signline"></div></div>
        <div><span>Approved by</span><strong>Chief Financial Officer</strong><div class="signline"></div></div>
    </div>
    """

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FinAdvantage | Executive Audit Memo | {escape(data['period'])}</title>
<style>
    @page {{ size: Letter; margin: 0.55in; }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0;
        background: #ede9fe;
        color: #0F172A;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial, sans-serif;
        line-height: 1.5;
    }}
    .paper {{
        width: min(920px, calc(100% - 32px));
        margin: 28px auto;
        padding: 46px 52px;
        background: #FFFFFF;
        border: 1px solid #E9E5F7;
        border-radius: 16px;
        box-shadow: 0 20px 60px rgba(46, 16, 101, 0.14);
    }}
    .brandbar {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 24px;
        margin: -46px -52px 28px -52px;
        padding: 22px 52px;
        color: #FFFFFF;
        background: linear-gradient(105deg, #2E1065, #4C1D95 55%, #6D28D9);
    }}
    .brand {{ font-size: 18px; font-weight: 800; letter-spacing: -0.02em; }}
    .brand span {{ color: #DDD6FE; font-weight: 500; }}
    .brand-sub {{ margin-top: 4px; color: rgba(255,255,255,0.66); font-size: 9px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; }}
    .confidential {{ border: 1px solid rgba(255,255,255,0.3); border-radius: 999px; padding: 5px 9px; font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; white-space: nowrap; }}
    h1 {{ margin: 0 0 5px 0; color: #1E1B4B; font-size: 31px; line-height: 1.1; letter-spacing: -0.04em; }}
    .subtitle {{ margin: 0; color: #6D28D9; font-size: 13px; font-weight: 700; }}
    .meta {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 24px 0 28px 0; }}
    .meta div {{ background: #F8FAFC; border: 1px solid #E9E5F7; border-radius: 10px; padding: 10px 12px; }}
    .meta span {{ display: block; color: #94A3B8; font-size: 8px; font-weight: 800; letter-spacing: 0.11em; text-transform: uppercase; }}
    .meta strong {{ display: block; margin-top: 4px; color: #1E1B4B; font-size: 11px; }}
    h2 {{ margin: 28px 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid #E9E5F7; color: #4C1D95; font-size: 13px; letter-spacing: 0.02em; text-transform: uppercase; }}
    p {{ margin: 0 0 10px 0; font-size: 11px; }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 14px 0 8px 0; }}
    .kpi {{ border: 1px solid #E9E5F7; border-top: 3px solid #6D28D9; border-radius: 10px; padding: 12px 13px; background: #FFFFFF; }}
    .kpi .value {{ color: #1E1B4B; font-size: 22px; font-weight: 800; letter-spacing: -0.03em; line-height: 1; }}
    .kpi .label {{ margin-top: 5px; color: #64748B; font-size: 8px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0 4px 0; font-size: 9.5px; }}
    th {{ padding: 8px 8px; border-bottom: 1px solid #E9E5F7; background: #F5F3FF; color: #64748B; font-size: 8px; font-weight: 800; letter-spacing: 0.07em; text-align: left; text-transform: uppercase; }}
    td {{ padding: 8px 8px; border-bottom: 1px solid #F1F5F9; vertical-align: top; }}
    tr:last-child td {{ border-bottom: none; }}
    .num {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-weight: 600; white-space: nowrap; }}
    .mono {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; color: #6D28D9; font-size: 8.5px; white-space: nowrap; }}
    .danger {{ color: #B91C1C; }}
    .muted {{ color: #94A3B8; font-size: 8.5px; }}
    .callout {{ margin-top: 12px; padding: 14px 16px; border: 1px solid #DDD6FE; border-left: 4px solid #6D28D9; border-radius: 9px; background: #F5F3FF; }}
    .callout strong {{ color: #2E1065; }}
    ol {{ margin: 8px 0 0 20px; padding: 0; }}
    li {{ margin-bottom: 6px; font-size: 10.5px; }}
    .signoff {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 34px; }}
    .signoff span {{ display: block; color: #94A3B8; font-size: 8px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }}
    .signoff strong {{ display: block; margin-top: 4px; color: #1E1B4B; font-size: 10px; }}
    .signline {{ height: 28px; margin-top: 8px; border-bottom: 1px solid #94A3B8; }}
    .footer {{ margin-top: 34px; padding-top: 10px; border-top: 1px solid #E9E5F7; color: #94A3B8; font-size: 8px; display: flex; justify-content: space-between; gap: 12px; }}
    @media print {{
        body {{ background: #FFFFFF; }}
        .paper {{ width: auto; margin: 0; padding: 0; border: none; border-radius: 0; box-shadow: none; }}
        .brandbar {{ margin: 0 0 24px 0; padding: 18px 20px; }}
        h2 {{ page-break-after: avoid; }}
        table {{ page-break-inside: auto; }}
        tr {{ page-break-inside: avoid; }}
    }}
</style>
</head>
<body>
<div class="paper">
    <div class="brandbar">
        <div>
            <div class="brand">FinAdvantage <span>| AI Digital Controllership</span></div>
            <div class="brand-sub">Revenue assurance for the modern finance stack</div>
        </div>
        <div class="confidential">Confidential · Internal use only</div>
    </div>

    <h1>{escape(data['title'])}</h1>
    <p class="subtitle">{escape(data['subtitle'])}</p>

    <div class="meta">
        <div><span>Reporting period</span><strong>{escape(data['period'])}</strong></div>
        <div><span>As of</span><strong>{escape(data['as_of'])}</strong></div>
        <div><span>Prepared</span><strong>{escape(data['prepared'])}</strong></div>
        <div><span>Status</span><strong>{escape(data['status'])}</strong></div>
    </div>

    <h2>Executive summary</h2>
    <p>{escape(data['executive_summary'])}</p>

    <div class="kpis">
        <div class="kpi"><div class="value">{data['arrangements']}</div><div class="label">Arrangements scanned</div></div>
        <div class="kpi"><div class="value">{data['exceptions']}</div><div class="label">Exceptions flagged</div></div>
        <div class="kpi"><div class="value">{_money(data['overstated'])}</div><div class="label">Overstated revenue</div></div>
        <div class="kpi"><div class="value">{data['journal_count']}</div><div class="label">Balanced journal entries</div></div>
    </div>

    <h2>Findings by ASC 606 loophole</h2>
    <table>
        <thead><tr><th>Loophole</th><th>Deals</th><th>Exposure</th><th>Severity</th><th>Required remediation</th></tr></thead>
        <tbody>{findings_html}</tbody>
    </table>

    <h2>Largest exposures</h2>
    <table>
        <thead><tr><th>Deal</th><th>Customer</th><th>Loophole</th><th>Recognized</th><th>Supportable</th><th>Overstated</th><th>Severity</th></tr></thead>
        <tbody>{exposure_html}</tbody>
    </table>

    <h2>Journal entry impact</h2>
    <div class="callout">
        <strong>Batch {escape(data['batch'])}</strong> · {data['journal_count']} entries ·
        {data['line_count']} lines · {_money(data['debit_total'], 2)} Dr =
        {_money(data['credit_total'], 2)} Cr · variance {_money(data['variance'], 2)}.
        Status: <strong>{'Balanced' if data['balanced'] else 'Review required'}</strong> and
        pending controller approval. No ERP write-back has been performed.
    </div>

    <h2>Recommended actions</h2>
    <ol>{recommendations_html}</ol>

    <h2>Sign-off</h2>
    {signoff_html}

    <div class="footer">
        <span>FinAdvantage AI Digital Controllership · ASC 606 Contract-to-Ledger Exception Gate</span>
        <span>Generated {escape(data['prepared'])} · Confidential</span>
    </div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# PDF memo
# ---------------------------------------------------------------------------


def _pdf_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="FABrand",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=PURPLE,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FABrandSub",
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=SLATE,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FATitle",
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=25,
            textColor=INK,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FASubtitle",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=PURPLE,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FAH2",
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=INDIGO,
            spaceBefore=13,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FABody",
            fontName="Helvetica",
            fontSize=8.4,
            leading=12,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FAMetaLabel",
            fontName="Helvetica-Bold",
            fontSize=6.4,
            leading=8,
            textColor=SLATE,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FAMetaValue",
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FAKpi",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=INK,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FATH",
            fontName="Helvetica-Bold",
            fontSize=6.4,
            leading=8,
            textColor=WHITE,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FATD",
            fontName="Helvetica",
            fontSize=6.7,
            leading=8.5,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FATDMon",
            fontName="Courier",
            fontSize=6.5,
            leading=8.5,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FARecommendation",
            fontName="Helvetica",
            fontSize=8.1,
            leading=11,
            textColor=INK,
            leftIndent=13,
            firstLineIndent=-13,
            spaceAfter=4,
        )
    )
    return styles


def _pdf_escape(value: Any) -> str:
    return xml_escape(str(value)).replace("\n", "<br/>")


def _pdf_money(value: float, decimals: int = 0) -> str:
    return f"${value:,.{decimals}f}"


def _draw_header_footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    width, height = letter

    # Top brand bar
    canvas.setFillColor(PURPLE)
    canvas.rect(0, height - 0.20 * inch, width, 0.075 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(PURPLE)
    canvas.drawString(0.58 * inch, height - 0.38 * inch, "FINADVANTAGE")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SLATE)
    canvas.drawRightString(
        width - 0.58 * inch,
        height - 0.38 * inch,
        "Executive Audit Memo · October 2026",
    )

    # Footer
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(0.58 * inch, 0.52 * inch, width - 0.58 * inch, 0.52 * inch)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(SLATE)
    canvas.drawString(0.58 * inch, 0.36 * inch, "Confidential - Internal use only")
    canvas.drawRightString(width - 0.58 * inch, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _pdf_meta_table(styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [
            Paragraph("REPORTING PERIOD", styles["FAMetaLabel"]),
            Paragraph(REPORT_PERIOD, styles["FAMetaValue"]),
            Paragraph("AS OF", styles["FAMetaLabel"]),
            Paragraph(REPORT_AS_OF, styles["FAMetaValue"]),
        ],
        [
            Paragraph("PREPARED", styles["FAMetaLabel"]),
            Paragraph(REPORT_PREPARED, styles["FAMetaValue"]),
            Paragraph("STATUS", styles["FAMetaLabel"]),
            Paragraph(REPORT_STATUS, styles["FAMetaValue"]),
        ],
    ]
    table = Table(data, colWidths=[1.05 * inch, 2.35 * inch, 0.75 * inch, 2.15 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _pdf_kpi_table(data: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    def cell(value: str, label: str) -> Paragraph:
        return Paragraph(
            f"<font size='16' color='#1E1B4B'><b>{_pdf_escape(value)}</b></font>"
            f"<br/><font size='6' color='#64748B'>{_pdf_escape(label)}</font>",
            styles["FAKpi"],
        )

    table = Table(
        [
            [
                cell(str(data["arrangements"]), "ARRANGEMENTS SCANNED"),
                cell(str(data["exceptions"]), "EXCEPTIONS FLAGGED"),
                cell(_pdf_money(data["overstated"]), "OVERSTATED REVENUE"),
                cell(str(data["journal_count"]), "BALANCED JOURNALS"),
            ]
        ],
        colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.8 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("LINEABOVE", (0, 0), (-1, 0), 2.5, PURPLE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _pdf_findings_table(data: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    rows: list[list[Any]] = [
        [
            Paragraph("LOOPHOLE", styles["FATH"]),
            Paragraph("DEALS", styles["FATH"]),
            Paragraph("EXPOSURE", styles["FATH"]),
            Paragraph("SEVERITY", styles["FATH"]),
            Paragraph("REQUIRED REMEDIATION", styles["FATH"]),
        ]
    ]
    if data["findings"]:
        for row in data["findings"]:
            rows.append(
                [
                    Paragraph(
                        f"<b>{_pdf_escape(row['loophole'])}</b><br/>"
                        f"<font size='5.8' color='#7C3AED'>{_pdf_escape(row['citation'])}</font>",
                        styles["FATD"],
                    ),
                    Paragraph(str(row["count"]), styles["FATDMon"]),
                    Paragraph(_pdf_money(row["exposure"]), styles["FATDMon"]),
                    Paragraph(_pdf_escape(row["severity"]), styles["FATD"]),
                    Paragraph(_pdf_escape(row["action"]), styles["FATD"]),
                ]
            )
    else:
        rows.append([Paragraph("No ASC 606 exceptions identified.", styles["FATD"]), "", "", "", ""])

    table = Table(
        rows,
        colWidths=[1.55 * inch, 0.45 * inch, 0.8 * inch, 0.65 * inch, 3.75 * inch],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
            ]
        )
    )
    return table


def _pdf_exposure_table(data: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    rows: list[list[Any]] = [
        [
            Paragraph("DEAL", styles["FATH"]),
            Paragraph("CUSTOMER / ERP", styles["FATH"]),
            Paragraph("LOOPHOLE", styles["FATH"]),
            Paragraph("RECOGNIZED", styles["FATH"]),
            Paragraph("SUPPORTABLE", styles["FATH"]),
            Paragraph("OVERSTATED", styles["FATH"]),
            Paragraph("SEVERITY", styles["FATH"]),
        ]
    ]
    if data["exposures"]:
        for row in data["exposures"]:
            rows.append(
                [
                    Paragraph(_pdf_escape(row["deal_id"]), styles["FATDMon"]),
                    Paragraph(
                        f"<b>{_pdf_escape(row['customer'])}</b><br/>"
                        f"<font size='5.8' color='#64748B'>{_pdf_escape(row['erp'])}</font>",
                        styles["FATD"],
                    ),
                    Paragraph(_pdf_escape(row["loophole"]), styles["FATD"]),
                    Paragraph(_pdf_money(row["recognized"]), styles["FATDMon"]),
                    Paragraph(_pdf_money(row["supportable"]), styles["FATDMon"]),
                    Paragraph(
                        f"<font color='#B91C1C'><b>{_pdf_money(row['overstated'])}</b></font>",
                        styles["FATDMon"],
                    ),
                    Paragraph(_pdf_escape(row["severity"]), styles["FATD"]),
                ]
            )
    else:
        rows.append([Paragraph("No exceptions in scope.", styles["FATD"]), "", "", "", "", "", ""])

    table = Table(
        rows,
        colWidths=[0.62 * inch, 1.35 * inch, 1.45 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 0.7 * inch],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DEEP),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
            ]
        )
    )
    return table


def _pdf_journal_callout(data: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    text = (
        f"<b>Batch {REPORT_BATCH}</b> · {data['journal_count']} entries · "
        f"{data['line_count']} lines · {_pdf_money(data['debit_total'], 2)} Dr = "
        f"{_pdf_money(data['credit_total'], 2)} Cr · variance "
        f"{_pdf_money(data['variance'], 2)}. Status: "
        f"<b>{'Balanced' if data['balanced'] else 'Review required'}</b> and pending "
        "controller approval. No ERP write-back has been performed."
    )
    table = Table([[Paragraph(text, styles["FABody"])]], colWidths=[7.2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDD6FE")),
                ("LINEBEFORE", (0, 0), (0, -1), 3, PURPLE),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _pdf_signoff_table(styles: dict[str, ParagraphStyle]) -> Table:
    def cell(role: str, name: str) -> Paragraph:
        return Paragraph(
            f"<font size='6' color='#94A3B8'>{_pdf_escape(role.upper())}</font>"
            f"<br/><br/><br/><font size='7.5' color='#1E1B4B'><b>{_pdf_escape(name)}</b></font>",
            styles["FATD"],
        )

    table = Table(
        [[cell("Prepared by", "FinAdvantage AI Digital Controllership"),
          cell("Reviewed by", "Revenue Controller"),
          cell("Approved by", "Chief Financial Officer")]],
        colWidths=[2.4 * inch, 2.4 * inch, 2.4 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, SLATE),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return table


def executive_memo_pdf(data: dict[str, Any]) -> bytes:
    """Render a print-ready PDF executive memo and return its bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.58 * inch,
        rightMargin=0.58 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title=f"FinAdvantage {REPORT_TITLE}",
        author="FinAdvantage AI Digital Controllership",
        subject=REPORT_SUBTITLE,
    )
    styles = _pdf_styles()
    story: list[Any] = []

    story.append(Paragraph("FINADVANTAGE", styles["FABrand"]))
    story.append(Paragraph("AI Digital Controllership", styles["FABrandSub"]))
    story.append(Paragraph(REPORT_TITLE, styles["FATitle"]))
    story.append(Paragraph(REPORT_SUBTITLE, styles["FASubtitle"]))
    story.append(
        HRFlowable(width="100%", thickness=1.4, color=PURPLE, spaceBefore=1, spaceAfter=10)
    )
    story.append(_pdf_meta_table(styles))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive Summary", styles["FAH2"]))
    story.append(Paragraph(_pdf_escape(data["executive_summary"]), styles["FABody"]))
    story.append(Spacer(1, 7))
    story.append(_pdf_kpi_table(data, styles))

    story.append(Paragraph("Findings by ASC 606 Loophole", styles["FAH2"]))
    story.append(_pdf_findings_table(data, styles))

    story.append(Paragraph("Largest Exposures", styles["FAH2"]))
    story.append(_pdf_exposure_table(data, styles))

    story.append(Paragraph("Journal Entry Impact", styles["FAH2"]))
    story.append(_pdf_journal_callout(data, styles))

    story.append(Paragraph("Recommended Actions", styles["FAH2"]))
    for index, recommendation in enumerate(data["recommendations"], start=1):
        story.append(
            Paragraph(
                f"<b>{index}.</b> {_pdf_escape(recommendation)}",
                styles["FARecommendation"],
            )
        )

    story.append(Paragraph("Sign-off", styles["FAH2"]))
    story.append(_pdf_signoff_table(styles))
    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            "FinAdvantage AI Digital Controllership · ASC 606 Contract-to-Ledger "
            "Exception Gate · Confidential",
            styles["FABrandSub"],
        )
    )

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
    return buffer.getvalue()


def cfo_summary_pdf(data: dict[str, Any]) -> bytes:
    """Render the compact, one-page CFO audit summary.

    The full executive memo intentionally spans multiple pages. This variant
    keeps the headline numbers, flagged contracts, journal impact, and sign-off
    on a single page for a CFO review packet.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.48 * inch,
        title="FinAdvantage CFO Audit Summary",
        author="FinAdvantage AI Digital Controllership",
        subject=REPORT_SUBTITLE,
    )
    styles = _pdf_styles()
    styles.add(
        ParagraphStyle(
            name="FACfoTitle",
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=21,
            textColor=INK,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FACfoSub",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=PURPLE,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FACfoH2",
            fontName="Helvetica-Bold",
            fontSize=8.6,
            leading=10,
            textColor=INDIGO,
            spaceBefore=7,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FACfoBody",
            fontName="Helvetica",
            fontSize=7.3,
            leading=10,
            textColor=INK,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FACfoCell",
            fontName="Helvetica",
            fontSize=6.2,
            leading=7.6,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FACfoCellMono",
            fontName="Courier",
            fontSize=6.0,
            leading=7.6,
            textColor=INK,
        )
    )

    def kpi_cell(value: str, label: str) -> Paragraph:
        return Paragraph(
            f"<font size='13' color='#1E1B4B'><b>{_pdf_escape(value)}</b></font>"
            f"<br/><font size='5.5' color='#64748B'>{_pdf_escape(label)}</font>",
            styles["FAKpi"],
        )

    story: list[Any] = []
    story.append(Paragraph("FINADVANTAGE", styles["FABrand"]))
    story.append(Paragraph("AI Digital Controllership", styles["FABrandSub"]))
    story.append(Paragraph("CFO Audit Summary", styles["FACfoTitle"]))
    story.append(Paragraph("ASC 606 Month-End Contract Check", styles["FACfoSub"]))
    story.append(
        HRFlowable(width="100%", thickness=1.2, color=PURPLE, spaceBefore=0, spaceAfter=5)
    )

    meta = Table(
        [[
            Paragraph("REPORTING PERIOD", styles["FAMetaLabel"]),
            Paragraph(REPORT_PERIOD, styles["FAMetaValue"]),
            Paragraph("AS OF", styles["FAMetaLabel"]),
            Paragraph(REPORT_AS_OF, styles["FAMetaValue"]),
            Paragraph("STATUS", styles["FAMetaLabel"]),
            Paragraph(REPORT_STATUS, styles["FAMetaValue"]),
        ]],
        colWidths=[0.95 * inch, 1.3 * inch, 0.55 * inch, 1.3 * inch, 0.55 * inch, 1.75 * inch],
    )
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta)

    kpis = Table(
        [[
            kpi_cell(_pdf_money(data["recognized"]), "TOTAL ERP REVENUE CHECKED"),
            kpi_cell(_pdf_money(data["overstated"]), "OVERSTATED REVENUE CAUGHT"),
            kpi_cell(str(data["exceptions"]), "CONTRACTS FLAGGED"),
            kpi_cell(
                _pdf_money(data["recognized"] - data["overstated"]),
                "TRUE GAAP COMPLIANT REVENUE",
            ),
        ]],
        colWidths=[1.85 * inch, 1.85 * inch, 1.5 * inch, 2.1 * inch],
    )
    kpis.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
                ("LINEABOVE", (0, 0), (-1, 0), 2.2, PURPLE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(Spacer(1, 5))
    story.append(kpis)

    story.append(Paragraph("Executive Summary", styles["FACfoH2"]))
    story.append(Paragraph(_pdf_escape(data["executive_summary"]), styles["FACfoBody"]))

    story.append(Paragraph("Flagged Contracts", styles["FACfoH2"]))
    rows: list[list[Any]] = [
        [
            Paragraph("CUSTOMER / ERP", styles["FATH"]),
            Paragraph("ASC 606 ISSUE", styles["FATH"]),
            Paragraph("REPORTED", styles["FATH"]),
            Paragraph("GAAP", styles["FATH"]),
            Paragraph("OVERSTATED", styles["FATH"]),
        ]
    ]
    exposures = data["exposures"][:8]
    for row in exposures:
        rows.append(
            [
                Paragraph(
                    f"<b>{_pdf_escape(row['customer'])}</b><br/>"
                    f"<font size='5.4' color='#64748B'>{_pdf_escape(row['erp'])}</font>",
                    styles["FACfoCell"],
                ),
                Paragraph(_pdf_escape(row["loophole"]), styles["FACfoCell"]),
                Paragraph(_pdf_money(row["recognized"]), styles["FACfoCellMono"]),
                Paragraph(_pdf_money(row["supportable"]), styles["FACfoCellMono"]),
                Paragraph(
                    f"<font color='#B91C1C'><b>{_pdf_money(row['overstated'])}</b></font>",
                    styles["FACfoCellMono"],
                ),
            ]
        )
    if not exposures:
        rows.append(
            [Paragraph("No ASC 606 exceptions identified.", styles["FACfoCell"]), "", "", "", ""]
        )
    flagged = Table(
        rows,
        colWidths=[1.85 * inch, 2.65 * inch, 0.75 * inch, 0.75 * inch, 0.8 * inch],
        repeatRows=1,
    )
    flagged.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DEEP),
                ("GRID", (0, 0), (-1, -1), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
            ]
        )
    )
    story.append(flagged)
    remaining = len(data["exposures"]) - len(exposures)
    if remaining > 0:
        story.append(
            Paragraph(
                f"+ {remaining} additional flagged contract(s) included in the full exception schedule.",
                styles["FABrandSub"],
            )
        )

    story.append(Paragraph("Journal Entry Impact", styles["FACfoH2"]))
    story.append(_pdf_journal_callout(data, styles))

    story.append(Paragraph("Recommended Next Actions", styles["FACfoH2"]))
    for index, recommendation in enumerate(data["recommendations"][:3], start=1):
        story.append(
            Paragraph(
                f"<b>{index}.</b> {_pdf_escape(recommendation)}",
                styles["FACfoBody"],
            )
        )

    story.append(Paragraph("Sign-off", styles["FACfoH2"]))
    signoffs = list((data.get("signoffs") or {}).values())
    if signoffs:
        approved = sum(1 for item in signoffs if str(item.get("status", "")).startswith("✅"))
        pending = sum(1 for item in signoffs if str(item.get("status", "")).startswith("⏳"))
        waived = sum(1 for item in signoffs if str(item.get("status", "")).startswith("⚠️"))
        stamps = [str(item.get("at")) for item in signoffs if item.get("at")]
        latest = max(stamps) if stamps else "No controller action recorded"
        story.append(
            Paragraph(
                f"Controller status: <b>{approved} approved</b> · {pending} pending · "
                f"{waived} waived. Latest action: {_pdf_escape(latest)}. "
                f"Approved reversal: {_pdf_money(data['approved_reversal'], 2)}; "
                f"certified GL revenue: {_pdf_money(data['certified_revenue'], 2)}.",
                styles["FACfoBody"],
            )
        )
    story.append(_pdf_signoff_table(styles))

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
    return buffer.getvalue()


def report_filename(extension: str) -> str:
    extension = extension.lstrip(".").lower()
    return f"FinAdvantage_ASC606_Executive_Audit_Memo_20261031.{extension}"
