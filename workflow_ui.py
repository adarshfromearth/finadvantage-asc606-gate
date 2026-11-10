"""Shared presentation helpers for the FinAdvantage month-end workflow."""

from __future__ import annotations

from datetime import datetime
import html
import re
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from forensic_scanner import ScanResult
from journal_generator import journal_entries_to_csv

THEME = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--p:#6D28D9;--deep:#2E1065;--ink:#0F172A;--muted:#64748B;--line:#E9E5F7}
html,body,[class*="css"]{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink)}
.stApp{background:#F8FAFC}
#MainMenu,footer,header[data-testid="stHeader"],[data-testid="stToolbar"],.stDeployButton{display:none!important}
.block-container{max-width:1320px;padding:1.3rem 2rem 3rem}
.fa-header{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:1.45rem 1.6rem;background:var(--p);border-radius:18px;box-shadow:0 16px 38px rgba(109,40,217,.18);color:#fff}
.fa-title{font-size:clamp(1.25rem,2.2vw,1.9rem);font-weight:800;letter-spacing:-.025em;line-height:1.15}
.fa-title span{color:#DDD6FE;font-weight:400}
.fa-sub{margin-top:.32rem;color:#EDE9FE;font-size:.7rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase}
.fa-soc{white-space:nowrap;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.32);border-radius:999px;padding:.55rem .8rem;font-size:.72rem;font-weight:700}
.fa-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.85rem;margin:1rem 0 .35rem}
.fa-kpi{background:#fff;border:1px solid var(--line);border-top:3px solid var(--p);border-radius:15px;padding:1rem 1.05rem;min-width:0}
.fa-kpi b{display:block;margin:.3rem 0 .15rem;font-size:clamp(1.25rem,2vw,1.7rem);line-height:1.1;overflow-wrap:anywhere}
.fa-kpi label{font-size:.58rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.fa-kpi i{display:block;margin-top:.15rem;font-size:.62rem;font-style:normal;color:#94A3B8}
div[data-testid="stVerticalBlockBorderWrapper"]{background:#fff!important;border:1px solid var(--line)!important;border-radius:18px!important;box-shadow:0 10px 30px rgba(46,16,101,.045)}
.fa-step h2{margin:0;color:var(--ink);font-size:1.12rem;font-weight:800;letter-spacing:-.015em}
.fa-step p{margin:.28rem 0 .85rem;color:var(--muted);font-size:.76rem;line-height:1.55}
.fa-gap{height:1.05rem}
div[role="radiogroup"] label{background:#F8FAFC;border:1px solid var(--line);border-radius:11px;padding:.6rem .7rem;margin-bottom:.35rem}
div[role="radiogroup"] label:has(input:checked){background:#F5F3FF;border-color:#C4B5FD}
div[data-testid="stFileUploaderDropzone"]{background:#F8FAFC;border:1.5px dashed #C4B5FD;border-radius:12px}
.fa-note{margin:.1rem 0 .8rem;padding:.62rem .75rem;background:#ECFDF5;border:1px solid #A7F3D0;border-radius:10px;color:#065F46;font-size:.66rem;font-weight:600;line-height:1.5}
.fa-parse{display:inline-block;margin:.3rem 0;padding:.32rem .62rem;border-radius:999px;font-size:.64rem;font-weight:800}
.fa-digital{color:#047857;background:#ECFDF5;border:1px solid #A7F3D0}.fa-scanned{color:#B45309;background:#FFFBEB;border:1px solid #FDE68A}
.fa-hybrid{color:#5B21B6;background:#F5F3FF;border:1px solid #DDD6FE}.fa-fallback{color:#B91C1C;background:#FEF2F2;border:1px solid #FECACA}
.fa-chips{display:flex;flex-wrap:wrap;gap:.3rem;margin:.35rem 0}.fa-chip{background:#F5F3FF;border:1px solid #DDD6FE;color:#5B21B6;border-radius:999px;padding:.22rem .48rem;font-size:.58rem;font-weight:700}
.fa-table-wrap{width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:#fff}
.fa-table{width:100%;min-width:620px;border-collapse:collapse}.fa-table th{background:#F5F3FF;color:#4C1D95;padding:.62rem .55rem;text-align:left;font-size:.55rem;text-transform:uppercase;letter-spacing:.07em}
.fa-table td{padding:.6rem .55rem;border-top:1px solid #F1F5F9;vertical-align:top;font-size:.68rem;line-height:1.45}.fa-table tr:hover td{background:#FCFBFF}
.fa-sub2{display:block;color:#94A3B8;font-size:.56rem;margin-top:.1rem}.fa-num{font-family:"SFMono-Regular",Consolas,monospace;white-space:nowrap}.fa-red{color:#B91C1C;font-weight:700}
.fa-pill{display:inline-block;border-radius:999px;padding:.2rem .45rem;font-size:.56rem;font-weight:800;white-space:nowrap}.fa-bad{background:#FEF2F2;color:#B91C1C;border:1px solid #FECACA}.fa-good{background:#F0FDF4;color:#166534;border:1px solid #BBF7D0}
.fa-wait{background:#FFFBEB;color:#B45309;border:1px solid #FDE68A}.fa-waive{background:#F1F5F9;color:#475569;border:1px solid #CBD5E1}.fa-sign{display:block;margin-top:.22rem}
.fa-gl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.7rem;margin:.35rem 0 .9rem}
.fa-gl div{background:#F8FAFC;border:1px solid var(--line);border-radius:11px;padding:.7rem .8rem;min-width:0}
.fa-gl label{display:block;color:var(--muted);font-size:.55rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}
.fa-gl b{display:block;margin-top:.2rem;color:var(--deep);font-size:1.08rem;line-height:1.15;overflow-wrap:anywhere}
.fa-gl .fa-gl-final{background:#F5F3FF;border-color:#C4B5FD}
.fa-inspector{border:1px solid var(--line);border-radius:14px;padding:.9rem;background:#fff}.fa-inspector h3{margin:0 0 .55rem;font-size:.84rem}
.fa-label{display:block;margin:.75rem 0 .28rem;color:#7C3AED;font-size:.55rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}
.fa-erp{padding:.65rem .7rem;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px}.fa-erp b{font-size:1.08rem}.fa-erp p{margin:.25rem 0 0;font-size:.62rem;color:var(--muted);line-height:1.45}
.fa-quote{margin:.35rem 0;padding:.6rem .7rem;background:#FFFBEB;border-left:3px solid #DC2626;border-radius:0 9px 9px 0;font-size:.65rem;line-height:1.5}.fa-quote mark{background:#FEF08A;color:#7F1D1D;padding:0 .1rem;font-weight:600}
.fa-explain{padding:.65rem .7rem;background:#F5F3FF;border:1px solid #DDD6FE;border-radius:10px;font-size:.66rem;line-height:1.5;color:#3B0764}
.fa-chart-title{margin:1rem 0 .2rem;font-size:.8rem;font-weight:800;color:var(--ink)}
div[data-testid="stDownloadButton"] button[kind="primary"]{background:var(--p)!important;color:#fff!important;border:1px solid var(--p)!important;border-radius:12px!important;min-height:3.35rem;font-weight:800!important;font-size:.8rem!important;line-height:1.35!important;white-space:normal!important;padding:.65rem 1rem!important}
div[data-testid="stDownloadButton"] button[kind="primary"]:hover{background:#5B21B6!important}
.fa-empty{padding:1.8rem;text-align:center;border:1px dashed #C4B5FD;border-radius:12px;background:#FCFBFF;color:var(--muted);font-size:.76rem}
.fa-footer{margin:1.2rem 0 0;color:#94A3B8;font-size:.6rem;text-align:center}
@media(max-width:820px){.block-container{padding:1rem}.fa-header{flex-direction:column;align-items:flex-start}.fa-soc{white-space:normal}}
@media(max-width:640px){.fa-kpis{grid-template-columns:repeat(2,1fr)}}
</style>
"""

PLAIN_ENGLISH = {
    "TERMINATION_CONVENIENCE": "The customer can leave with only 30 days' notice and no penalty, so revenue can only be recognized month by month.",
    "UNDISCLOSED_FREE_MONTHS": "The free months lower the real price of the deal, so revenue must be spread across the whole service period, including free months.",
    "MONEY_BACK_TRIAL": "A trial that can be cancelled for a full refund is not yet a signed revenue contract, so trial-period revenue must wait.",
    "FEATURE_CONTINGENCY": "Revenue for the undelivered feature must wait until the customer actually receives and accepts it.",
}

SIGNOFF_PENDING = "⏳ Pending Review"
SIGNOFF_APPROVED = "✅ Approved for GL Adjustment"
SIGNOFF_WAIVED = "⚠️ Waived as Immaterial"
SIGNOFF_OPTIONS = [SIGNOFF_PENDING, SIGNOFF_APPROVED, SIGNOFF_WAIVED]
SIGNOFF_CSS = {
    SIGNOFF_PENDING: "fa-wait",
    SIGNOFF_APPROVED: "fa-good",
    SIGNOFF_WAIVED: "fa-waive",
}


def inject_theme() -> None:
    st.markdown(THEME, unsafe_allow_html=True)


def esc(value: Any) -> str:
    return html.escape(str(value))


def money(value: float, decimals: int = 0) -> str:
    return f"${value:,.{decimals}f}"


def plain_english(result: ScanResult) -> str:
    if not result.findings:
        return "This contract passes all four ASC 606 checks."
    return PLAIN_ENGLISH.get(
        result.findings[0].loophole_id,
        "Revenue must be deferred until the contract supports recognition.",
    )


EVIDENCE_PATTERNS = {
    "TERMINATION_CONVENIENCE": [
        (r"terminate(?:s|d)?\s+this\s+agreement", 4),
        (r"termination\s+for\s+convenience", 1),
        (r"(?:thirty|30)\s*\(?30?\)?\s*days", 1),
    ],
    "UNDISCLOSED_FREE_MONTHS": [
        (r"first\s+[^.]{0,45}(?:no\s+charge|free\s+of\s+charge|waived)", 6),
        (r"free\s+of\s+charge", 4),
        (r"free\s+months?", 2),
        (r"no\s+charge", 2),
    ],
    "MONEY_BACK_TRIAL": [(r"\btrial\b", 2), (r"refund", 2)],
    "FEATURE_CONTINGENCY": [
        (r"not\s+yet\s+available", 4),
        (r"not\s+(?:yet\s+)?delivered", 3),
        (r"undelivered", 3),
        (r"contingent\s+on\s+written\s+acceptance", 2),
        (r"feature", 1),
    ],
}


def evidence_sentence(result: ScanResult, finding: Any) -> str:
    """Return the exact contract sentence behind a red flag."""
    text = " ".join(str(result.deal.get("contract_text", "")).split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    patterns = EVIDENCE_PATTERNS.get(finding.loophole_id, [])
    scored = []
    for sentence in sentences:
        score = sum(weight for pattern, weight in patterns if re.search(pattern, sentence, re.I))
        if score:
            scored.append((score, len(sentence), sentence))
    if scored:
        return max(scored)[2][:420]
    clean = " ".join(finding.evidence.split())
    return clean[:420] + ("…" if len(clean) > 420 else "")


def kpi_html(results: list[ScanResult], summary: dict[str, Any]) -> str:
    gaap = sum(result.expected_recognized for result in results)
    cards = [
        ("Total ERP Revenue Checked", money(summary["total_recognized"]), "Booked across all contracts"),
        ("Overstated Revenue Caught", money(summary["total_overstated"]), "Unsupported revenue to reverse"),
        ("Contracts Flagged for Review", str(summary["exceptions"]), f"Out of {len(results)} contracts scanned"),
        ("True GAAP Compliant Revenue", money(gaap), "Reported revenue less overstatement"),
    ]
    return '<div class="fa-kpis">' + "".join(
        f'<div class="fa-kpi"><label>{label}</label><b>{value}</b><i>{foot}</i></div>'
        for label, value, foot in cards
    ) + "</div>"


def gl_summary_html(original: float, approved: float, final: float) -> str:
    cards = [
        ("Original Reported Revenue", money(original), ""),
        ("Approved ASC 606 Reversal", money(approved), ""),
        ("Final Certified GL Revenue", money(final), " fa-gl-final"),
    ]
    return '<div class="fa-gl">' + "".join(
        f'<div class="{css.strip()}"><label>{label}</label><b>{value}</b></div>'
        for label, value, css in cards
    ) + "</div>"


def audit_table(results: list[ScanResult], signoffs: dict[str, dict[str, str]] | None = None) -> str:
    signoffs = signoffs or {}
    rows = []
    for result in results:
        pill = (
            '<span class="fa-pill fa-bad">🔴 Action Required</span>'
            if result.has_exception
            else '<span class="fa-pill fa-good">🟢 Compliant</span>'
        )
        if result.has_exception:
            signoff = signoffs.get(result.deal_id, {})
            label = signoff.get("status", SIGNOFF_PENDING)
            css = SIGNOFF_CSS.get(label, "fa-wait")
            stamp = f'<span class="fa-sub2">{esc(signoff["at"])}</span>' if signoff.get("at") else ""
            pill += f'<span class="fa-pill {css} fa-sign">{esc(label)}</span>{stamp}'
        rows.append(
            f'<tr><td><b>{esc(result.customer)}</b><span class="fa-sub2">{esc(result.deal_id)}</span></td>'
            f'<td class="fa-num">{money(result.recognized_to_date)}</td><td>{pill}</td>'
            f'<td>{esc(result.loophole_names)}</td>'
            f'<td class="fa-num fa-red">{money(result.overstated_revenue)}</td></tr>'
        )
    head = (
        "<tr><th>Customer Name</th><th>Booked ERP Revenue ($)</th><th>Status</th>"
        "<th>Issue Found</th><th>Revenue Overstatement ($)</th></tr>"
    )
    return (
        f'<div class="fa-table-wrap"><table class="fa-table"><thead>{head}</thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def inspector_html(result: ScanResult) -> str:
    quotes = "".join(
        f'<div class="fa-label">{esc(finding.name)}</div>'
        f'<div class="fa-quote"><mark>{esc(evidence_sentence(result, finding))}</mark></div>'
        for finding in result.findings
    )
    return (
        '<div class="fa-inspector"><h3>Contract Inspector</h3>'
        f'<div class="fa-label">What {esc(result.erp_source)} says</div>'
        f'<div class="fa-erp"><b>{money(result.recognized_to_date)}</b>'
        f'<p>{esc(result.deal.get("erp_memo", "Booked as recognized revenue."))}</p></div>'
        f'<div class="fa-label">What the PDF contract actually says</div>{quotes}'
        f'<div class="fa-label">Plain-English explanation</div>'
        f'<div class="fa-explain">{esc(plain_english(result))}</div></div>'
    )


def comparison_chart(flagged: list[ScanResult]) -> go.Figure:
    names = [result.customer for result in flagged]
    fig = go.Figure()
    fig.add_bar(
        name="Reported ERP Revenue",
        x=names,
        y=[result.recognized_to_date for result in flagged],
        marker_color="#6D28D9",
        hovertemplate="<b>%{x}</b><br>Reported ERP: $%{y:,.0f}<extra></extra>",
    )
    fig.add_bar(
        name="True Compliant Revenue",
        x=names,
        y=[result.expected_recognized for result in flagged],
        marker_color="#10B981",
        hovertemplate="<b>%{x}</b><br>True GAAP: $%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(
        barmode="group",
        height=340,
        margin=dict(l=8, r=8, t=8, b=90),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Inter", size=10, color="#334155"),
        legend=dict(orientation="h", y=1.12, x=0),
        yaxis=dict(tickprefix="$", gridcolor="#EEF2F7", zeroline=False),
        xaxis=dict(tickangle=-18),
    )
    return fig


def journal_table(entries: pd.DataFrame, results: list[ScanResult]) -> str:
    by_deal = {result.deal_id: result for result in results}
    rows = []
    for _, group in entries.groupby("JE ID", sort=False):
        first = group.iloc[0]
        amount = float(group["Debit"].sum())
        result = by_deal.get(first["Deal ID"])
        memo = (
            f"{result.customer}: reverse {money(amount)} and defer it. {plain_english(result)}"
            if result
            else first["Memo"]
        )
        rows.append(
            '<tr><td><b>Subscription Revenue → Deferred Revenue</b>'
            '<span class="fa-sub2">4000-100 → 2400-100</span></td>'
            f'<td class="fa-num">{money(amount, 2)}</td>'
            f'<td class="fa-num">{money(amount, 2)}</td><td>{esc(memo)}</td></tr>'
        )
    debit = float(entries["Debit"].sum())
    credit = float(entries["Credit"].sum())
    balance = "Balanced" if abs(debit - credit) < 0.01 else "Review required"
    rows.append(
        f'<tr><td><b>Batch total</b><span class="fa-sub2">{balance}</span></td>'
        f'<td class="fa-num">{money(debit, 2)}</td><td class="fa-num">{money(credit, 2)}</td>'
        "<td>Every debit has an equal credit and is pending controller approval.</td></tr>"
    )
    head = (
        "<tr><th>Account</th><th>Debit Revenue</th><th>Credit Deferred Revenue</th>"
        "<th>Plain-English Memo</th></tr>"
    )
    return (
        f'<div class="fa-table-wrap"><table class="fa-table"><thead>{head}</thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def record_signoff(deal_id: str, widget_key: str) -> None:
    """Persist the controller decision and the moment it was made."""
    signoffs = st.session_state.setdefault("signoffs", {})
    status = st.session_state[widget_key]
    entry = signoffs.setdefault(deal_id, {})
    if entry.get("status") != status:
        entry["status"] = status
        entry["at"] = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")


def render_signoff_control(deal_id: str, saved: dict[str, str]) -> None:
    status = saved.get("status", SIGNOFF_PENDING)
    st.markdown('<div class="fa-label">Controller Sign-Off Status</div>', unsafe_allow_html=True)
    st.radio(
        "Controller Sign-Off Status",
        SIGNOFF_OPTIONS,
        index=SIGNOFF_OPTIONS.index(status) if status in SIGNOFF_OPTIONS else 0,
        key=f"signoff_{deal_id}",
        on_change=record_signoff,
        args=(deal_id, f"signoff_{deal_id}"),
        label_visibility="collapsed",
    )
    if saved.get("at"):
        st.caption(f"Status recorded {saved['at']}")


def governance_summary(results: list[ScanResult], signoffs: dict[str, dict[str, str]], original: float) -> dict[str, Any]:
    """Build the controller status map and approved/final GL totals."""
    statuses = {
        result.deal_id: signoffs.get(result.deal_id, {"status": SIGNOFF_PENDING, "at": ""})
        for result in results
    }
    approved = round(
        sum(
            result.overstated_revenue
            for result in results
            if result.has_exception
            and statuses[result.deal_id]["status"] == SIGNOFF_APPROVED
        ),
        2,
    )
    return {
        "statuses": statuses,
        "approved_reversal": approved,
        "certified_revenue": round(float(original) - approved, 2),
        "approved_count": sum(
            1 for result in results
            if result.has_exception and statuses[result.deal_id]["status"] == SIGNOFF_APPROVED
        ),
        "flagged_count": sum(1 for result in results if result.has_exception),
    }


def export_entries_with_signoff(entries: pd.DataFrame, statuses: dict[str, dict[str, str]]) -> pd.DataFrame:
    export = entries.copy()
    if not export.empty:
        export["Controller Sign-Off"] = export["Deal ID"].map(
            lambda deal_id: statuses.get(deal_id, {}).get("status", SIGNOFF_PENDING)
        )
        export["Sign-Off Timestamp"] = export["Deal ID"].map(
            lambda deal_id: statuses.get(deal_id, {}).get("at", "")
        )
    return export


def render_gl_summary(original: float, approved: float, final: float,
                      approved_count: int, flagged_count: int) -> None:
    st.markdown(gl_summary_html(original, approved, final), unsafe_allow_html=True)
    st.caption(
        f"Certified total reflects {approved_count} of {flagged_count} flagged contracts marked "
        "✅ Approved; pending and waived reversals are excluded."
    )


def render_exports(entries: pd.DataFrame, pdf_bytes: bytes, totals: dict[str, Any], batch_date: Any) -> None:
    col_csv, col_pdf = st.columns(2)
    with col_csv:
        st.download_button(
            "📥 Download NetSuite / QuickBooks Fixing Entries (CSV)",
            data=journal_entries_to_csv(entries),
            file_name=f"FinAdvantage_ASC606_Fixing_Entries_{batch_date:%Y%m%d}.csv",
            mime="text/csv", type="primary", width="stretch", disabled=entries.empty,
        )
    with col_pdf:
        st.download_button(
            "📄 Download 1-Page CFO Audit Summary Memo (Report)", data=pdf_bytes,
            file_name=f"FinAdvantage_ASC606_CFO_Summary_{batch_date:%Y%m%d}.pdf",
            mime="application/pdf", type="primary", width="stretch",
        )
    debit_text = money(totals["debit_total"], 2).replace("$", "\\$")
    credit_text = money(totals["credit_total"], 2).replace("$", "\\$")
    st.caption(
        f"Batch {totals['je_count']} entries · {debit_text} Dr = {credit_text} Cr · "
        "no ERP write-back performed."
    )
