"""FinAdvantage ASC 606 single-page month-end close workflow."""

from __future__ import annotations

from datetime import date
import streamlit as st

from executive_report import build_report_data, cfo_summary_pdf
from forensic_scanner import ScanResult, portfolio_summary, scan_all
from journal_generator import generate_journal_entries, journal_entries_to_csv, journal_totals
from sample_data import AS_OF_DATE, get_deals
from upload_parser import (
    extract_pdf_document, first_ledger_row, infer_contract_facts, make_custom_result, read_ledger,
)
from workflow_ui import (
    audit_table, comparison_chart, inject_theme, inspector_html, journal_table, kpi_html,
    money,
)

st.set_page_config(page_title="FinAdvantage | ASC 606 Month-End Contract Check", page_icon="◆", layout="wide")
inject_theme()

A = "Option A (Default): Use Pre-Loaded Q4 SaaS Audit Batch (12 Sample Deals)"
B = "Option B: Upload Custom Client Contract (PDF) + ERP Ledger (CSV)"


def reset_custom_scan() -> None:
    for key in ("custom_result", "custom_sig", "custom_booked"):
        st.session_state.pop(key, None)


source_mode = st.session_state.get("source_mode", A)
custom_result = st.session_state.get("custom_result")
results: list[ScanResult] = scan_all(get_deals()) if source_mode == A else ([custom_result] if custom_result else [])
summary = portfolio_summary(results)
entries = generate_journal_entries(results)
totals = journal_totals(entries)

st.markdown(
    '<div class="fa-header"><div><div class="fa-title">FinAdvantage <span>|</span> '
    "ASC 606 Month-End Contract Check</div><div class=\"fa-sub\">Three steps from contract "
    'evidence to balanced fixing entries</div></div><div class="fa-soc">🔒 Zero Data Retention '
    "(In-Memory RAM Only)</div></div>",
    unsafe_allow_html=True,
)
st.markdown(kpi_html(results, summary), unsafe_allow_html=True)

with st.container(border=True):
    st.markdown(
        '<div class="fa-step"><h2>Step 1: Select Data Source</h2><p>Audit the pre-loaded batch '
        "instantly, or upload one client contract and its ERP ledger.</p></div>",
        unsafe_allow_html=True,
    )
    source_mode = st.radio("Data source", [A, B], index=0, key="source_mode", label_visibility="collapsed")
    if source_mode == A:
        st.caption("Loaded automatically: 12 Q4 SaaS arrangements, 7 flagged for review.")
    else:
        st.markdown(
            '<div class="fa-note">🔒 SOC-Compliant Zero Data Retention: contracts and ledgers are '
            "processed in volatile RAM and purged when the session closes.</div>",
            unsafe_allow_html=True,
        )
        col_pdf, col_csv = st.columns(2)
        with col_pdf:
            pdf_file = st.file_uploader("Custom client contract (PDF)", type=["pdf"], key="custom_pdf", on_change=reset_custom_scan)
        with col_csv:
            csv_file = st.file_uploader("ERP ledger (CSV, optional)", type=["csv"], key="custom_csv", on_change=reset_custom_scan)
        extraction, facts, ledger = None, {}, {}
        if pdf_file is not None:
            with st.spinner("Auto-detecting digital pages and scanned pages…"):
                extraction = extract_pdf_document(pdf_file.getvalue())
            if not extraction["ok"]:
                st.error(f"Could not read {pdf_file.name}. {extraction['error']}")
            else:
                css = {"digital": "fa-digital", "scanned": "fa-scanned", "hybrid": "fa-hybrid"}.get(
                    extraction["mode"], "fa-fallback"
                )
                st.markdown(f'<span class="fa-parse {css}">{extraction["status"]}</span>', unsafe_allow_html=True)
                facts = infer_contract_facts(extraction["text"])
                if extraction["ocr_errors"]:
                    st.warning(f"OCR was unavailable for {extraction['ocr_failed_pages']} page(s). Digital pages still parsed.", icon="⚠️")
        if csv_file is not None:
            try:
                frame = read_ledger(csv_file.getvalue())
                ledger = first_ledger_row(frame)
                st.caption(f"Ledger loaded: {len(frame)} row(s). Using the first row for this scan.")
            except Exception as exc:
                st.error(f"Could not read the CSV ledger. {exc}")
        default_booked = float(ledger.get("recognized", facts.get("recognized", 0.0)))
        signature = (
            pdf_file.name if pdf_file else None,
            pdf_file.size if pdf_file else None,
            csv_file.name if csv_file else None,
            csv_file.size if csv_file else None,
        )
        if st.session_state.get("custom_sig") != signature:
            st.session_state["custom_sig"] = signature
            st.session_state["custom_booked"] = default_booked
        booked = st.number_input(
            "Booked ERP revenue to check ($)", min_value=0.0, step=1000.0, format="%.2f",
            key="custom_booked", help="Revenue QuickBooks or NetSuite has already recognized for this contract.",
        )
        chips = [
            ("Customer", ledger.get("customer") or facts.get("customer")),
            ("Term", f"{ledger.get('term') or facts.get('term', 12)} months"),
            ("Monthly", money(float(ledger.get("monthly") or facts.get("monthly", 0)))),
            ("TCV", money(float(ledger.get("tcv") or facts.get("tcv", 0)))),
        ]
        st.markdown(
            '<div class="fa-chips">' + "".join(
                f'<span class="fa-chip">{label}: {value}</span>' for label, value in chips if value
            ) + "</div>",
            unsafe_allow_html=True,
        )
        if extraction and extraction["text"]:
            with st.expander("View extracted contract text"):
                st.text_area("Extracted text", extraction["text"][:12000], height=180, disabled=True, label_visibility="collapsed")
        if st.button("Run ASC 606 scan", type="primary", width="stretch"):
            if pdf_file is None:
                st.error("Upload a contract PDF first.")
            elif not extraction or not extraction["ok"] or not extraction["text"].strip():
                st.error("No readable contract text was found. Try another PDF or upload a text-based copy.")
            else:
                text = extraction["text"] or ledger.get("text", "")
                customer = ledger.get("customer") or facts.get("customer") or pdf_file.name.rsplit(".", 1)[0]
                start = ledger.get("start") or facts.get("start") or date(AS_OF_DATE.year, 1, 1)
                term = int(ledger.get("term") or facts.get("term") or 12)
                monthly = float(ledger.get("monthly") or facts.get("monthly") or 0)
                tcv = float(ledger.get("tcv") or facts.get("tcv") or monthly * term)
                monthly = monthly or (tcv / term if tcv else 0)
                st.session_state["custom_result"] = make_custom_result(
                    contract_text=text, customer=customer, erp=ledger.get("erp", "NetSuite"),
                    start=start, term=term, monthly=monthly, tcv=tcv, booked=booked,
                )
                st.rerun()

st.markdown('<div class="fa-gap"></div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown(
        '<div class="fa-step"><h2>Step 2: Review ASC 606 Red Flags</h2><p>Read the contract '
        "evidence next to the ERP number before posting any adjustment.</p></div>",
        unsafe_allow_html=True,
    )
    if not results:
        st.markdown('<div class="fa-empty">Upload and scan a contract in Step 1 to see its ASC 606 review here.</div>', unsafe_allow_html=True)
    else:
        flagged = [result for result in results if result.has_exception]
        left, right = st.columns([3, 2], gap="large")
        with left:
            st.markdown(audit_table(results), unsafe_allow_html=True)
        with right:
            if flagged:
                ids = [result.deal_id for result in flagged]
                by_id = {result.deal_id: result for result in flagged}
                if st.session_state.get("_inspector_ids") != ids:
                    st.session_state["_inspector_ids"] = ids
                    st.session_state.pop("inspect_deal", None)
                selected = st.selectbox(
                    "Flagged contract to inspect", ids,
                    format_func=lambda key: f"{by_id[key].customer} · {money(by_id[key].overstated_revenue)} over",
                    key="inspect_deal",
                )
                st.markdown(inspector_html(by_id[selected]), unsafe_allow_html=True)
            else:
                st.success("No red flags. Every contract in this view passes the four ASC 606 checks.")
        if flagged:
            st.markdown('<div class="fa-chart-title">Reported ERP Revenue vs. True Compliant Revenue — Flagged Contracts</div>', unsafe_allow_html=True)
            st.plotly_chart(comparison_chart(flagged), use_container_width=True)
        else:
            st.success("Nothing to fix. No correcting entries are required for this view.")

st.markdown('<div class="fa-gap"></div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown(
        '<div class="fa-step"><h2>Step 3: Resolve &amp; Export to Accounting Software</h2>'
        "<p>Download the balanced fixing entries and a one-page CFO sign-off memo.</p></div>",
        unsafe_allow_html=True,
    )
    if not results:
        st.markdown('<div class="fa-empty">Run a scan in Step 1 to generate correcting journal entries.</div>', unsafe_allow_html=True)
    else:
        if entries.empty:
            st.success("No correcting journal entries are needed for this view.")
        else:
            st.markdown(journal_table(entries, results), unsafe_allow_html=True)
            st.caption("Preview is summarized by customer. The CSV contains full line-level entries ready for NetSuite or QuickBooks import.")
        report_data = build_report_data(results, summary, totals)
        pdf_bytes = cfo_summary_pdf(report_data)
        col_csv_btn, col_pdf_btn = st.columns(2)
        with col_csv_btn:
            st.download_button(
                "📥 Download NetSuite / QuickBooks Fixing Entries (CSV)",
                data=journal_entries_to_csv(entries),
                file_name=f"FinAdvantage_ASC606_Fixing_Entries_{AS_OF_DATE:%Y%m%d}.csv",
                mime="text/csv", type="primary", width="stretch", disabled=entries.empty,
            )
        with col_pdf_btn:
            st.download_button(
                "📄 Download 1-Page CFO Audit Summary Memo (Report)", data=pdf_bytes,
                file_name=f"FinAdvantage_ASC606_CFO_Summary_{AS_OF_DATE:%Y%m%d}.pdf",
                mime="application/pdf", type="primary", width="stretch",
            )
        debit_text = money(totals["debit_total"], 2).replace("$", "\\$")
        credit_text = money(totals["credit_total"], 2).replace("$", "\\$")
        st.caption(
            f"Batch {totals['je_count']} entries · {debit_text} Dr = "
            f"{credit_text} Cr · no ERP write-back performed."
        )

st.markdown('<div class="fa-footer">FinAdvantage AI Digital Controllership · ASC 606 Month-End Contract Check · Confidential</div>', unsafe_allow_html=True)
