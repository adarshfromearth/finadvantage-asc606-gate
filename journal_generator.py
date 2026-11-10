"""Balanced month-end ASC 606 audit adjusting journal entries.

Each exception produces a two-line reclassification:

    Dr  Subscription Revenue - Adjustment    $X
        Cr  Deferred Revenue - Current       $X

The memo carries the customer, contract, evidence summary, and the specific
ASC 606 citation so the entry can move through the controller review queue.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from forensic_scanner import ScanResult

JE_DATE = date(2026, 10, 31)
BATCH_ID = "OCT-2026-ASC606"
PREPARER = "FinAdvantage AI Controllership"
REVENUE_ACCOUNT = "4000-100"
REVENUE_ACCOUNT_NAME = "Subscription Revenue - Adjustment"
DEFERRED_ACCOUNT = "2400-100"
DEFERRED_ACCOUNT_NAME = "Deferred Revenue - Current"

JOURNAL_COLUMNS = [
    "JE ID",
    "Batch",
    "Entry Date",
    "Deal ID",
    "Customer",
    "ERP",
    "Contract ID",
    "Line",
    "Account Code",
    "Account Name",
    "Debit",
    "Credit",
    "Memo",
    "ASC 606 Citation",
    "Risk Severity",
    "Status",
    "Prepared By",
]


def _exception_results(results: list[ScanResult]) -> list[ScanResult]:
    return [
        result
        for result in results
        if result.has_exception and result.overstated_revenue > 0.01
    ]


def _citations(result: ScanResult) -> str:
    seen: list[str] = []
    for finding in result.findings:
        if finding.citation not in seen:
            seen.append(finding.citation)
    return " | ".join(seen) if seen else "ASC 606-10-25-1"


def build_memo(result: ScanResult) -> str:
    """Create an audit-ready memo for one exception."""
    citations = _citations(result)
    return (
        f"Month-end ASC 606 reclass: {result.loophole_names}. "
        f"Cumulative revenue through 31-Oct-2026 exceeds supportable recognition "
        f"by ${result.overstated_revenue:,.2f}. Reverse the unsupported subscription "
        f"revenue and defer it pending resolution of the contract exception. "
        f"Evidence: {result.contract_id} ({result.erp_source}). "
        f"ASC 606: {citations}."
    )


def generate_journal_entries(results: list[ScanResult]) -> pd.DataFrame:
    """Return the line-level journal entry dataframe for all exceptions."""
    rows: list[dict[str, Any]] = []
    exceptions = _exception_results(results)

    for index, result in enumerate(exceptions, start=1):
        je_id = f"JE-2026-10-{index:03d}"
        amount = round(result.overstated_revenue, 2)
        memo = build_memo(result)
        common = {
            "JE ID": je_id,
            "Batch": BATCH_ID,
            "Entry Date": JE_DATE.isoformat(),
            "Deal ID": result.deal_id,
            "Customer": result.customer,
            "ERP": result.erp_source,
            "Contract ID": result.contract_id,
            "Memo": memo,
            "ASC 606 Citation": _citations(result),
            "Risk Severity": result.severity,
            "Status": "Pending Controller Approval",
            "Prepared By": PREPARER,
        }
        rows.append(
            {
                **common,
                "Line": "1 - Debit",
                "Account Code": REVENUE_ACCOUNT,
                "Account Name": REVENUE_ACCOUNT_NAME,
                "Debit": amount,
                "Credit": 0.0,
            }
        )
        rows.append(
            {
                **common,
                "Line": "2 - Credit",
                "Account Code": DEFERRED_ACCOUNT,
                "Account Name": DEFERRED_ACCOUNT_NAME,
                "Debit": 0.0,
                "Credit": amount,
            }
        )

    if not rows:
        return pd.DataFrame(columns=JOURNAL_COLUMNS)
    return pd.DataFrame(rows, columns=JOURNAL_COLUMNS)


def summarize_journal_entries(entries: pd.DataFrame) -> pd.DataFrame:
    """Collapse line-level entries into one review row per journal entry."""
    summary_columns = [
        "JE ID",
        "Deal ID",
        "Customer",
        "Amount",
        "ASC 606 Citation",
        "Risk Severity",
        "Status",
        "Balanced",
        "Memo",
    ]
    if entries.empty:
        return pd.DataFrame(columns=summary_columns)

    rows: list[dict[str, Any]] = []
    for je_id, group in entries.groupby("JE ID", sort=False):
        first = group.iloc[0]
        debit = round(float(group["Debit"].sum()), 2)
        credit = round(float(group["Credit"].sum()), 2)
        rows.append(
            {
                "JE ID": je_id,
                "Deal ID": first["Deal ID"],
                "Customer": first["Customer"],
                "Amount": debit,
                "ASC 606 Citation": first["ASC 606 Citation"],
                "Risk Severity": first["Risk Severity"],
                "Status": first["Status"],
                "Balanced": abs(debit - credit) < 0.01,
                "Memo": first["Memo"],
            }
        )
    return pd.DataFrame(rows, columns=summary_columns)


def journal_totals(entries: pd.DataFrame) -> dict[str, Any]:
    """Return batch control totals used by the validation card."""
    if entries.empty:
        return {
            "je_count": 0,
            "line_count": 0,
            "debit_total": 0.0,
            "credit_total": 0.0,
            "difference": 0.0,
            "balanced": True,
            "exceptions": 0,
        }
    debit_total = round(float(entries["Debit"].sum()), 2)
    credit_total = round(float(entries["Credit"].sum()), 2)
    return {
        "je_count": int(entries["JE ID"].nunique()),
        "line_count": int(len(entries)),
        "debit_total": debit_total,
        "credit_total": credit_total,
        "difference": round(debit_total - credit_total, 2),
        "balanced": abs(debit_total - credit_total) < 0.01,
        "exceptions": int(entries["Deal ID"].nunique()),
    }


def journal_entries_to_csv(entries: pd.DataFrame) -> str:
    """Serialize the journal batch for controller download."""
    return entries.to_csv(index=False, float_format="%.2f")
