"""FinAdvantage ASC 606 Contract-to-Ledger Exception Gate.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from io import BytesIO, StringIO
import html
import re
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from pypdf import PdfReader
import streamlit as st

from executive_report import (
    build_report_data,
    exception_schedule_csv,
    executive_memo_html,
    executive_memo_pdf,
    report_filename,
)
from forensic_scanner import (
    LOOPHOLE_LIBRARY,
    ScanResult,
    portfolio_summary,
    scan_all,
    scan_custom_deal,
)
from journal_generator import (
    generate_journal_entries,
    journal_entries_to_csv,
    journal_totals,
    summarize_journal_entries,
)
from sample_data import AS_OF_DATE, get_deals


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="FinAdvantage | ASC 606 Exception Gate",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
    --fa-deep: #2E1065;
    --fa-indigo: #4C1D95;
    --fa-purple: #6D28D9;
    --fa-lavender: #A78BFA;
    --fa-ink: #0F172A;
    --fa-slate: #64748B;
    --fa-line: #E9E5F7;
    --fa-bg: #F8FAFC;
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    -webkit-font-smoothing: antialiased;
}

html, body { overflow-x: hidden; }

.stApp {
    background:
        radial-gradient(circle at 14% -4%, rgba(109, 40, 217, 0.075), transparent 32rem),
        radial-gradient(circle at 92% 2%, rgba(76, 29, 149, 0.055), transparent 30rem),
        #F8FAFC;
}

#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton {
    display: none !important;
}

.block-container {
    padding: 0 2.5rem 3.4rem 2.5rem;
    max-width: 1480px;
}

/* ---------------------------------------------------------------- Nav bar */
.fa-nav {
    width: 100vw;
    margin-left: calc(50% - 50vw);
    margin-top: -1rem;
    box-sizing: border-box;
    padding: 1.05rem max(2.5rem, calc((100vw - 1480px) / 2 + 2.5rem));
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
    color: #FFFFFF;
    background: linear-gradient(105deg, #2E1065 0%, #4C1D95 52%, #6D28D9 100%);
    box-shadow: 0 14px 40px rgba(46, 16, 101, 0.25);
    position: relative;
    overflow: hidden;
}

.fa-nav:after {
    content: "";
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 84% 12%, rgba(196, 181, 253, 0.28), transparent 30%),
        radial-gradient(circle at 8% 130%, rgba(255, 255, 255, 0.10), transparent 35%);
    pointer-events: none;
}

.fa-brand {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    position: relative;
    z-index: 1;
}

.fa-mark {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(255,255,255,0.22), rgba(255,255,255,0.055));
    border: 1px solid rgba(255,255,255,0.28);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 1.02rem;
    letter-spacing: 0.03em;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.20);
}

.fa-brand-title {
    font-size: 1.27rem;
    font-weight: 800;
    letter-spacing: -0.025em;
    line-height: 1.1;
}

.fa-brand-title .fa-divider {
    color: #C4B5FD;
    font-weight: 400;
    padding: 0 0.18rem;
}

.fa-brand-title .fa-suite {
    color: #EDE9FE;
    font-weight: 500;
    font-size: 1.02rem;
}

.fa-brand-sub {
    color: rgba(255,255,255,0.65);
    font-size: 0.64rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-top: 0.25rem;
}

.fa-nav-right {
    display: flex;
    align-items: center;
    gap: 0.72rem;
    position: relative;
    z-index: 1;
}

.fa-close-chip {
    color: #DDD6FE;
    border: 1px solid rgba(255,255,255,0.18);
    background: rgba(255,255,255,0.065);
    border-radius: 999px;
    padding: 0.42rem 0.68rem;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
}

.fa-soc-badge {
    display: flex;
    align-items: center;
    gap: 0.48rem;
    color: #F5F3FF;
    background: rgba(15, 23, 42, 0.24);
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 999px;
    padding: 0.5rem 0.8rem;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
}

.fa-live-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #4ADE80;
    box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.65);
    animation: faPulse 1.9s infinite;
}

.fa-dot-sep { color: rgba(255,255,255,0.34); }

.fa-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #EDE9FE;
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.22);
    font-size: 0.67rem;
    font-weight: 800;
    letter-spacing: 0.03em;
}

@keyframes faPulse {
    0%   { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.65); }
    70%  { box-shadow: 0 0 0 7px rgba(74, 222, 128, 0); }
    100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }
}

/* ------------------------------------------------------------------- Hero */
.fa-hero {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 2rem;
    padding: 2.25rem 0 1.4rem 0;
}

.fa-eyebrow {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--fa-purple);
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.17em;
    text-transform: uppercase;
}

.fa-eyebrow:before {
    content: "";
    width: 22px;
    height: 2px;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--fa-purple), #C4B5FD);
}

.fa-hero h1 {
    margin: 0.62rem 0 0.55rem 0;
    color: #1E1B4B;
    font-size: clamp(2.05rem, 3.2vw, 2.85rem);
    line-height: 1.03;
    letter-spacing: -0.04em;
    font-weight: 800;
}

.fa-hero h1 span {
    background: linear-gradient(90deg, #4C1D95, #6D28D9 58%, #8B5CF6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.fa-hero p {
    max-width: 770px;
    margin: 0;
    color: #475569;
    font-size: 0.96rem;
    line-height: 1.66;
}

.fa-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.48rem;
    margin-top: 1.05rem;
}

.fa-meta-chip {
    color: #5B21B6;
    background: #F5F3FF;
    border: 1px solid #DDD6FE;
    border-radius: 999px;
    padding: 0.36rem 0.62rem;
    font-size: 0.67rem;
    font-weight: 700;
}

.fa-meta-green {
    color: #166534;
    background: #F0FDF4;
    border-color: #BBF7D0;
}

.fa-hero-side {
    width: 245px;
    flex: 0 0 245px;
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
}

.fa-close-card {
    width: 100%;
    background: rgba(255,255,255,0.82);
    border: 1px solid var(--fa-line);
    border-radius: 14px;
    padding: 0.82rem 0.95rem;
    box-shadow: 0 10px 30px rgba(46, 16, 101, 0.06);
    backdrop-filter: blur(8px);
}

.fa-close-label {
    color: #94A3B8;
    font-size: 0.59rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.fa-close-value {
    color: #1E1B4B;
    font-size: 0.95rem;
    font-weight: 800;
    margin-top: 0.18rem;
}

.fa-close-sub {
    color: #64748B;
    font-size: 0.68rem;
    margin-top: 0.12rem;
}

/* ------------------------------------------------------------------ KPIs */
.fa-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1rem;
    margin: 1.05rem 0 1.55rem 0;
}

.fa-kpi-grid.fa-kpi-grid-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.fa-kpi {
    position: relative;
    overflow: hidden;
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-radius: 16px;
    padding: 1.12rem 1.15rem 0.95rem 1.15rem;
    box-shadow: 0 12px 32px rgba(46, 16, 101, 0.055);
}

.fa-kpi:before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 4px;
    background: linear-gradient(90deg, #2E1065, #6D28D9 72%, #A78BFA);
}

.fa-kpi-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.7rem;
}

.fa-kpi-label {
    color: #64748B;
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.10em;
    text-transform: uppercase;
}

.fa-kpi-icon {
    width: 30px;
    height: 30px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--fa-purple);
    background: #F5F3FF;
    border: 1px solid #EDE9FE;
}

.fa-kpi-icon svg {
    width: 15px;
    height: 15px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.fa-kpi-value {
    color: #1E1B4B;
    font-size: 2rem;
    line-height: 1;
    font-weight: 800;
    letter-spacing: -0.045em;
    margin: 0.56rem 0 0.28rem 0;
    font-variant-numeric: tabular-nums;
}

.fa-kpi-value small {
    color: #64748B;
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: 0;
}

.fa-kpi-foot {
    display: flex;
    align-items: center;
    gap: 0.42rem;
    flex-wrap: wrap;
    color: #64748B;
    font-size: 0.69rem;
}

.fa-kpi-delta {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.21rem 0.45rem;
    color: #5B21B6;
    background: #F5F3FF;
    font-size: 0.62rem;
    font-weight: 800;
    white-space: nowrap;
}

.fa-kpi-delta.warn { color: #B91C1C; background: #FEF2F2; }
.fa-kpi-delta.good { color: #047857; background: #ECFDF5; }

/* --------------------------------------------------------------- Sections */
.fa-section-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1rem;
    margin: 1.45rem 0 0.75rem 0;
}

.fa-section-head h2 {
    margin: 0.18rem 0 0 0;
    color: #1E1B4B;
    font-size: 1.16rem;
    font-weight: 800;
    letter-spacing: -0.025em;
}

.fa-section-head p {
    margin: 0.2rem 0 0 0;
    color: #64748B;
    font-size: 0.78rem;
}

.fa-section-note {
    color: #94A3B8;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    line-height: 1.6;
    text-align: right;
    white-space: nowrap;
}

/* ------------------------------------------------------------------ Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem;
    padding: 0.38rem;
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-radius: 14px;
    box-shadow: 0 10px 28px rgba(46, 16, 101, 0.05);
}

.stTabs [data-baseweb="tab"] {
    height: 44px;
    padding: 0 1.15rem;
    border-radius: 10px;
    color: #64748B;
    font-size: 0.82rem;
    font-weight: 700;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #4C1D95;
    background: #F5F3FF;
}

.stTabs [aria-selected="true"] {
    color: #FFFFFF !important;
    background: linear-gradient(135deg, #4C1D95, #6D28D9) !important;
    box-shadow: 0 6px 16px rgba(76, 29, 149, 0.24);
}

.stTabs [aria-selected="true"] p { color: #FFFFFF !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* --------------------------------------------------------------- Widgets */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-radius: 16px;
    box-shadow: 0 10px 28px rgba(46, 16, 101, 0.045);
}

div[data-baseweb="select"] > div {
    min-height: 42px;
    border-radius: 10px !important;
    border-color: #E2E8F0 !important;
    background: #FBFBFE !important;
}

div[data-baseweb="select"] > div:hover { border-color: #C4B5FD !important; }
div[data-baseweb="select"] > div:focus-within {
    border-color: #6D28D9 !important;
    box-shadow: 0 0 0 3px rgba(109, 40, 217, 0.12) !important;
}

.stTextInput input, .stNumberInput input, .stDateInput input {
    min-height: 42px;
    border-radius: 10px !important;
    border-color: #E2E8F0 !important;
    background: #FBFBFE !important;
}

.stTextArea textarea {
    border-radius: 12px !important;
    border-color: #E2E8F0 !important;
    background: #FBFBFE !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.74rem !important;
    line-height: 1.58 !important;
}

.stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus,
.stTextArea textarea:focus {
    border-color: #6D28D9 !important;
    box-shadow: 0 0 0 3px rgba(109, 40, 217, 0.12) !important;
}

.stTextInput label, .stNumberInput label, .stDateInput label, .stTextArea label,
.stSelectbox label, .stMultiSelect label, .stCheckbox label {
    color: #64748B !important;
    font-size: 0.66rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

.stButton > button {
    border-radius: 10px;
    border: 1px solid #DDD6FE;
    background: #FFFFFF;
    color: #4C1D95;
    font-size: 0.79rem;
    font-weight: 800;
    padding: 0.55rem 0.9rem;
    transition: all 0.15s ease;
}

.stButton > button:hover {
    border-color: #6D28D9;
    background: #F5F3FF;
    color: #4C1D95;
}

.stButton > button[kind="primary"] {
    border: none;
    color: #FFFFFF;
    background: linear-gradient(135deg, #4C1D95, #6D28D9);
    box-shadow: 0 8px 20px rgba(76, 29, 149, 0.22);
}

.stButton > button[kind="primary"]:hover {
    color: #FFFFFF;
    background: linear-gradient(135deg, #2E1065, #6D28D9);
    box-shadow: 0 10px 24px rgba(46, 16, 101, 0.28);
}

.stDownloadButton > button {
    border-radius: 10px;
    border: 1px solid #DDD6FE;
    background: #F5F3FF;
    color: #4C1D95;
    font-size: 0.79rem;
    font-weight: 800;
    padding: 0.55rem 0.9rem;
}

.stDownloadButton > button:hover {
    border-color: #A78BFA;
    background: #EDE9FE;
}

/* ------------------------------------------------------------ Chart cards */
.fa-chart-title {
    color: #1E1B4B;
    font-size: 0.83rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    margin: 0.28rem 0 0.05rem 0;
}

.fa-chart-sub {
    color: #94A3B8;
    font-size: 0.67rem;
    margin-bottom: 0.15rem;
}

/* ---------------------------------------------------------------- Tables */
.fa-table-card {
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-radius: 16px;
    box-shadow: 0 12px 32px rgba(46, 16, 101, 0.05);
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin: 0.45rem 0 0.8rem 0;
}

.fa-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78rem;
}

.fa-table thead th {
    padding: 0.78rem 0.95rem;
    color: #64748B;
    background: #FBFBFE;
    border-bottom: 1px solid var(--fa-line);
    font-size: 0.59rem;
    font-weight: 800;
    letter-spacing: 0.10em;
    text-align: left;
    text-transform: uppercase;
    white-space: nowrap;
}

.fa-table tbody td {
    padding: 0.78rem 0.95rem;
    color: #334155;
    border-bottom: 1px solid #F1F5F9;
    vertical-align: middle;
}

.fa-table tbody tr:last-child td { border-bottom: none; }
.fa-table tbody tr:hover { background: #FCFBFF; }

.fa-table .num {
    color: #1E1B4B;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.fa-table .over { color: #B91C1C; }
.fa-table .zero { color: #94A3B8; }
.fa-table .muted { color: #94A3B8; font-size: 0.66rem; margin-top: 0.1rem; }
.fa-table .customer { color: #1E1B4B; font-weight: 700; }

.fa-table .deal-id {
    color: #6D28D9;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    font-weight: 700;
    white-space: nowrap;
}

/* ---------------------------------------------------------------- Badges */
.fa-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.32rem;
    padding: 0.26rem 0.54rem;
    border: 1px solid transparent;
    border-radius: 999px;
    font-size: 0.60rem;
    font-weight: 800;
    letter-spacing: 0.035em;
    text-transform: uppercase;
    white-space: nowrap;
}

.fa-badge:before {
    content: "";
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: currentColor;
}

.fa-badge.critical { color: #2E1065; background: #EDE9FE; border-color: #C4B5FD; }
.fa-badge.high { color: #6D28D9; background: #F5F3FF; border-color: #DDD6FE; }
.fa-badge.medium { color: #B45309; background: #FFFBEB; border-color: #FDE68A; }
.fa-badge.low { color: #475569; background: #F8FAFC; border-color: #E2E8F0; }
.fa-badge.compliant { color: #047857; background: #ECFDF5; border-color: #BBF7D0; }
.fa-badge.exception { color: #B91C1C; background: #FEF2F2; border-color: #FECACA; }
.fa-badge.review { color: #B45309; background: #FFFBEB; border-color: #FDE68A; }
.fa-badge.pending { color: #6D28D9; background: #F5F3FF; border-color: #DDD6FE; }
.fa-badge.balanced { color: #047857; background: #ECFDF5; border-color: #BBF7D0; }

.fa-cite {
    display: inline-block;
    max-width: 250px;
    color: #5B21B6;
    background: #F5F3FF;
    border: 1px solid #EDE9FE;
    border-radius: 7px;
    padding: 0.22rem 0.42rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    line-height: 1.45;
    white-space: normal;
}

/* -------------------------------------------------------------- Expanders */
div[data-testid="stExpander"] details {
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-radius: 14px;
    box-shadow: 0 6px 18px rgba(46, 16, 101, 0.035);
    margin-bottom: 0.5rem;
    overflow: hidden;
}

div[data-testid="stExpander"] details summary {
    padding: 0.78rem 1rem;
    color: #1E1B4B;
    font-size: 0.79rem;
    font-weight: 700;
}

div[data-testid="stExpander"] details[open] summary {
    border-bottom: 1px solid #F1F5F9;
    background: #FCFBFF;
}

.fa-mini-title {
    color: #1E1B4B;
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    margin: 0.1rem 0 0.55rem 0;
}

.fa-kv-list {
    border-top: 1px dashed #EEF2F7;
}

.fa-kv {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.4rem 0;
    border-bottom: 1px dashed #EEF2F7;
    font-size: 0.72rem;
}

.fa-kv .k { color: #64748B; }
.fa-kv .v {
    color: #1E1B4B;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.69rem;
    font-weight: 600;
    text-align: right;
}
.fa-kv .v.over { color: #B91C1C; }

.fa-doc-chip {
    display: inline-block;
    color: #5B21B6;
    background: #F5F3FF;
    border: 1px solid #DDD6FE;
    border-radius: 999px;
    padding: 0.25rem 0.5rem;
    font-size: 0.6rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}

.fa-evidence {
    max-height: 260px;
    overflow-y: auto;
    padding: 0.78rem 0.85rem;
    color: #3B0764;
    background: linear-gradient(135deg, #F5F3FF, #FAF5FF);
    border: 1px solid #DDD6FE;
    border-left: 4px solid #6D28D9;
    border-radius: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    line-height: 1.58;
    white-space: pre-wrap;
}

.fa-erp-memo {
    margin-top: 0.55rem;
    padding: 0.62rem 0.72rem;
    color: #475569;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 9px;
    font-size: 0.68rem;
    line-height: 1.5;
}

.fa-finding {
    margin-bottom: 0.62rem;
    padding: 0.78rem 0.85rem;
    background: #FCFBFF;
    border: 1px solid #EDE9FE;
    border-radius: 12px;
}

.fa-finding-title {
    display: flex;
    justify-content: space-between;
    gap: 0.65rem;
    color: #4C1D95;
    font-size: 0.77rem;
    font-weight: 800;
}

.fa-finding-amount {
    color: #B91C1C;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    white-space: nowrap;
}

.fa-finding-meta {
    margin-top: 0.22rem;
    color: #7C3AED;
    font-size: 0.57rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.fa-finding-text {
    margin-top: 0.52rem;
    color: #475569;
    font-size: 0.71rem;
    line-height: 1.55;
}

.fa-finding-evidence {
    margin-top: 0.52rem;
    padding: 0.48rem 0.58rem;
    color: #5B21B6;
    background: #F5F3FF;
    border-radius: 7px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    line-height: 1.5;
}

.fa-pass-box {
    padding: 0.95rem 1rem;
    color: #065F46;
    background: #ECFDF5;
    border: 1px solid #BBF7D0;
    border-radius: 11px;
    font-size: 0.75rem;
    line-height: 1.55;
}

.fa-pass-box strong { display: block; font-size: 0.8rem; margin-bottom: 0.2rem; }

.fa-bridge {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.4rem;
    margin-top: 0.65rem;
}

.fa-bridge > div {
    padding: 0.55rem 0.6rem;
    background: #F8FAFC;
    border: 1px solid #EEF2F7;
    border-radius: 9px;
}

.fa-bridge span {
    display: block;
    color: #94A3B8;
    font-size: 0.55rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.fa-bridge b {
    display: block;
    margin-top: 0.18rem;
    color: #1E1B4B;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
}

.fa-bridge b.over { color: #B91C1C; }

/* ---------------------------------------------------------------- Journal */
.fa-validation {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1.5rem;
    margin: 0.3rem 0 0.9rem 0;
    padding: 1rem 1.15rem;
    background: linear-gradient(135deg, #FFFFFF, #FCFBFF);
    border: 1px solid var(--fa-line);
    border-left: 4px solid #6D28D9;
    border-radius: 14px;
    box-shadow: 0 10px 28px rgba(46, 16, 101, 0.045);
}

.fa-validation h3 {
    margin: 0.2rem 0 0.15rem 0;
    color: #1E1B4B;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
}

.fa-validation p { margin: 0; color: #64748B; font-size: 0.72rem; }

.fa-valid-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.45rem 0.72rem;
    color: #047857;
    background: #ECFDF5;
    border: 1px solid #BBF7D0;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    white-space: nowrap;
}

.fa-memo {
    margin: 0.15rem 0 0.65rem 0;
    padding: 0.72rem 0.82rem;
    color: #475569;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 9px;
    font-size: 0.7rem;
    line-height: 1.55;
}

.fa-je-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0.4rem;
}

/* ---------------------------------------------------------------- Sandbox */
.fa-empty {
    padding: 2.1rem 1.6rem;
    text-align: center;
    background: linear-gradient(135deg, #FCFBFF, #F8FAFC);
    border: 1px dashed #C4B5FD;
    border-radius: 16px;
}

.fa-empty-icon {
    width: 52px;
    height: 52px;
    margin: 0 auto 0.75rem auto;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6D28D9;
    background: #F5F3FF;
    border: 1px solid #DDD6FE;
    border-radius: 15px;
}

.fa-empty-icon svg {
    width: 23px;
    height: 23px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.fa-empty h3 { margin: 0 0 0.35rem 0; color: #1E1B4B; font-size: 0.98rem; font-weight: 800; }
.fa-empty p { margin: 0 auto; max-width: 380px; color: #64748B; font-size: 0.76rem; line-height: 1.6; }

.fa-rule-list {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.35rem;
    margin-top: 0.9rem;
}

.fa-rule-pill {
    color: #5B21B6;
    background: #F5F3FF;
    border: 1px solid #DDD6FE;
    border-radius: 999px;
    padding: 0.28rem 0.5rem;
    font-size: 0.58rem;
    font-weight: 700;
}

.fa-result-card {
    padding: 1.1rem 1.15rem 1rem 1.15rem;
    background: linear-gradient(140deg, #2E1065, #4C1D95 62%, #6D28D9);
    border-radius: 16px;
    color: #FFFFFF;
    box-shadow: 0 16px 38px rgba(46, 16, 101, 0.22);
    position: relative;
    overflow: hidden;
    margin-bottom: 0.65rem;
}

.fa-result-card:after {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 92% 4%, rgba(196, 181, 253, 0.28), transparent 32%);
    pointer-events: none;
}

.fa-result-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.8rem;
    position: relative;
    z-index: 1;
}

.fa-result-card .fa-eyebrow { color: #DDD6FE; }
.fa-result-card .fa-eyebrow:before { background: linear-gradient(90deg, #DDD6FE, rgba(255,255,255,0.3)); }
.fa-result-card h2 { margin: 0.42rem 0 0.1rem 0; color: #FFFFFF; font-size: 1.15rem; font-weight: 800; letter-spacing: -0.02em; }
.fa-result-sub { color: rgba(255,255,255,0.64); font-size: 0.66rem; }

.fa-result-amount {
    margin-top: 1.05rem;
    color: #FFFFFF;
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.045em;
    line-height: 1;
    position: relative;
    z-index: 1;
}

.fa-result-label {
    margin-top: 0.3rem;
    color: rgba(255,255,255,0.62);
    font-size: 0.58rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    position: relative;
    z-index: 1;
}

.fa-risk-meter {
    height: 6px;
    margin-top: 0.9rem;
    background: rgba(255,255,255,0.14);
    border-radius: 999px;
    overflow: hidden;
    position: relative;
    z-index: 1;
}

.fa-risk-fill {
    height: 100%;
    background: linear-gradient(90deg, #C4B5FD, #F5F3FF);
    border-radius: 999px;
}

.fa-result-foot {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    margin-top: 0.4rem;
    color: rgba(255,255,255,0.66);
    font-size: 0.61rem;
    position: relative;
    z-index: 1;
}

.fa-sandbox-finding {
    padding: 0.7rem 0.8rem;
    margin-bottom: 0.5rem;
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-radius: 11px;
    box-shadow: 0 6px 16px rgba(46, 16, 101, 0.035);
}

.fa-sandbox-finding .name { color: #4C1D95; font-size: 0.74rem; font-weight: 800; }
.fa-sandbox-finding .citation { color: #7C3AED; font-size: 0.57rem; font-weight: 700; margin-top: 0.16rem; }
.fa-sandbox-finding .body { color: #64748B; font-size: 0.68rem; line-height: 1.5; margin-top: 0.4rem; }

.fa-je-preview {
    margin-top: 0.7rem;
    padding: 0.85rem 0.9rem;
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-radius: 13px;
    box-shadow: 0 8px 22px rgba(46, 16, 101, 0.04);
}

.fa-je-line {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    padding: 0.36rem 0;
    border-bottom: 1px dashed #EEF2F7;
    color: #475569;
    font-size: 0.7rem;
}

.fa-je-line b { color: #1E1B4B; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; }

.fa-je-memo {
    margin-top: 0.55rem;
    color: #64748B;
    font-size: 0.64rem;
    line-height: 1.5;
}

/* ----------------------------------------------------------- Upload panel */
.fa-upload-title h3 {
    margin: 0.28rem 0 0.22rem 0;
    color: #1E1B4B;
    font-size: 0.98rem;
    font-weight: 800;
    letter-spacing: -0.01em;
}

.fa-upload-title p {
    margin: 0;
    max-width: 860px;
    color: #64748B;
    font-size: 0.72rem;
    line-height: 1.6;
}

.fa-upload-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.32rem;
    margin: 0.55rem 0 0.55rem 0;
}

.fa-upload-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.32rem;
    max-width: 100%;
    padding: 0.24rem 0.5rem;
    color: #5B21B6;
    background: #F5F3FF;
    border: 1px solid #DDD6FE;
    border-radius: 999px;
    font-size: 0.58rem;
    font-weight: 600;
    line-height: 1.4;
}

.fa-upload-chip b {
    color: #4C1D95;
    font-size: 0.52rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.fa-upload-guide {
    padding: 0.8rem 0.85rem;
    margin-bottom: 0.65rem;
    background: linear-gradient(145deg, #F5F3FF, #FCFBFF);
    border: 1px solid #DDD6FE;
    border-left: 3px solid #6D28D9;
    border-radius: 11px;
}

.fa-upload-guide-title {
    color: #2E1065;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.fa-upload-guide ul {
    margin: 0.45rem 0 0 0.95rem;
    padding: 0;
}

.fa-upload-guide li {
    margin-bottom: 0.3rem;
    color: #475569;
    font-size: 0.66rem;
    line-height: 1.5;
}

.fa-upload-guide li strong { color: #4C1D95; }

.fa-upload-guide-note {
    margin-top: 0.55rem;
    padding-top: 0.45rem;
    border-top: 1px dashed #DDD6FE;
    color: #7C3AED;
    font-size: 0.58rem;
    line-height: 1.45;
}

.fa-security-banner {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    padding: 0.68rem 0.8rem;
    margin: 0 0 0.7rem 0;
    background: linear-gradient(135deg, #ECFDF5 0%, #F0FDFA 55%, #F5F3FF 100%);
    border: 1px solid #A7F3D0;
    border-left: 3px solid #059669;
    border-radius: 11px;
    color: #065F46;
    font-size: 0.64rem;
    font-weight: 600;
    line-height: 1.6;
    letter-spacing: 0.005em;
    box-shadow: 0 4px 14px rgba(5, 150, 105, 0.07);
}

.fa-security-banner .fa-security-lock {
    flex: 0 0 auto;
    font-size: 0.82rem;
    line-height: 1.25;
}

.fa-security-banner b { color: #047857; font-weight: 800; }

.fa-parse-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.38rem;
    margin: 0.55rem 0 0.15rem 0;
    padding: 0.36rem 0.68rem;
    border-radius: 999px;
    border: 1px solid transparent;
    font-size: 0.64rem;
    font-weight: 800;
    line-height: 1.4;
    letter-spacing: 0.005em;
}

.fa-parse-badge-digital {
    color: #047857;
    background: #ECFDF5;
    border-color: #A7F3D0;
}

.fa-parse-badge-scanned {
    color: #B45309;
    background: #FFFBEB;
    border-color: #FDE68A;
}

.fa-parse-badge-hybrid {
    color: #5B21B6;
    background: #F5F3FF;
    border-color: #DDD6FE;
}

.fa-parse-badge-fallback {
    color: #B91C1C;
    background: #FEF2F2;
    border-color: #FECACA;
}

/* ------------------------------------------------------------- Memo paper */
.fa-memo-paper {
    margin-top: 0.6rem;
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-radius: 18px;
    box-shadow: 0 22px 58px rgba(46, 16, 101, 0.11);
    overflow: hidden;
}

.fa-memo-brandbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1.2rem;
    padding: 1.05rem 1.55rem;
    color: #FFFFFF;
    background: linear-gradient(105deg, #2E1065, #4C1D95 55%, #6D28D9);
}

.fa-memo-brand {
    color: #FFFFFF;
    font-size: 1.02rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.fa-memo-brand span {
    color: #DDD6FE;
    font-weight: 500;
}

.fa-memo-brand-sub {
    margin-top: 0.2rem;
    color: rgba(255,255,255,0.66);
    font-size: 0.5rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

.fa-memo-confidential {
    padding: 0.28rem 0.52rem;
    border: 1px solid rgba(255,255,255,0.32);
    border-radius: 999px;
    color: #FFFFFF;
    font-size: 0.5rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
}

.fa-memo-body { padding: 1.35rem 1.6rem 1.5rem 1.6rem; }

.fa-memo-title {
    margin: 0.28rem 0 0.12rem 0;
    color: #1E1B4B;
    font-size: 1.65rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    line-height: 1.1;
}

.fa-memo-subtitle {
    color: #6D28D9;
    font-size: 0.78rem;
    font-weight: 700;
}

.fa-memo-meta {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.5rem;
    margin: 1rem 0 0.75rem 0;
}

.fa-memo-meta div {
    padding: 0.55rem 0.65rem;
    background: #F8FAFC;
    border: 1px solid var(--fa-line);
    border-radius: 10px;
}

.fa-memo-meta span {
    display: block;
    color: #94A3B8;
    font-size: 0.5rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.fa-memo-meta strong {
    display: block;
    margin-top: 0.2rem;
    color: #1E1B4B;
    font-size: 0.66rem;
}

.fa-memo-rule {
    height: 2px;
    margin: 0.75rem 0 0.1rem 0;
    background: linear-gradient(90deg, #6D28D9, #A78BFA 55%, rgba(167, 139, 250, 0.1));
    border-radius: 999px;
}

.fa-memo-section-title {
    margin: 1.15rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--fa-line);
    color: #4C1D95;
    font-size: 0.64rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.fa-memo-summary {
    margin: 0 0 0.85rem 0;
    color: #334155;
    font-size: 0.79rem;
    line-height: 1.7;
}

.fa-memo-kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.5rem;
}

.fa-memo-kpi {
    padding: 0.62rem 0.68rem;
    background: #FFFFFF;
    border: 1px solid var(--fa-line);
    border-top: 3px solid #6D28D9;
    border-radius: 10px;
}

.fa-memo-kpi .value {
    color: #1E1B4B;
    font-size: 1.2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1;
}

.fa-memo-kpi .label {
    margin-top: 0.28rem;
    color: #64748B;
    font-size: 0.48rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.fa-memo-table-wrap {
    overflow-x: auto;
    border: 1px solid var(--fa-line);
    border-radius: 11px;
}

.fa-memo-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.67rem;
}

.fa-memo-table thead th {
    padding: 0.5rem 0.6rem;
    color: #64748B;
    background: #F5F3FF;
    border-bottom: 1px solid var(--fa-line);
    font-size: 0.52rem;
    font-weight: 800;
    letter-spacing: 0.07em;
    text-align: left;
    text-transform: uppercase;
    white-space: nowrap;
}

.fa-memo-table tbody td {
    padding: 0.5rem 0.6rem;
    color: #334155;
    border-bottom: 1px solid #F1F5F9;
    vertical-align: top;
}

.fa-memo-table tbody tr:last-child td { border-bottom: none; }
.fa-memo-table tbody tr:hover { background: #FCFBFF; }

.fa-memo-table .num {
    color: #1E1B4B;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.fa-memo-table .num.over { color: #B91C1C; }
.fa-memo-strong { color: #1E1B4B; font-weight: 700; }

.fa-memo-cite {
    margin-top: 0.16rem;
    color: #7C3AED;
    font-size: 0.52rem;
    font-weight: 600;
    line-height: 1.35;
}

.fa-memo-action-cell { min-width: 210px; color: #475569; line-height: 1.5; }

.fa-memo-deal {
    color: #6D28D9;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.57rem;
    font-weight: 700;
    white-space: nowrap;
}

.fa-memo-callout {
    padding: 0.72rem 0.82rem;
    color: #475569;
    background: #F5F3FF;
    border: 1px solid #DDD6FE;
    border-left: 4px solid #6D28D9;
    border-radius: 10px;
    font-size: 0.72rem;
    line-height: 1.6;
}

.fa-memo-callout strong { color: #2E1065; }

.fa-memo-actions {
    margin: 0.35rem 0 0 1.1rem;
    padding: 0;
}

.fa-memo-actions li {
    margin-bottom: 0.38rem;
    color: #475569;
    font-size: 0.73rem;
    line-height: 1.6;
}

.fa-memo-signoff {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.2rem;
    margin-top: 0.55rem;
}

.fa-memo-signoff span {
    display: block;
    color: #94A3B8;
    font-size: 0.48rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.fa-memo-signoff strong {
    display: block;
    margin-top: 0.22rem;
    color: #1E1B4B;
    font-size: 0.63rem;
}

.fa-memo-signline {
    height: 1.5rem;
    margin-top: 0.42rem;
    border-bottom: 1px solid #94A3B8;
}

.fa-memo-footer {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    margin-top: 1.3rem;
    padding-top: 0.6rem;
    border-top: 1px solid var(--fa-line);
    color: #94A3B8;
    font-size: 0.52rem;
}

@media (max-width: 900px) {
    .fa-memo-meta, .fa-memo-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .fa-memo-signoff { grid-template-columns: 1fr; }
    .fa-memo-footer { flex-direction: column; gap: 0.3rem; }
}

@media (max-width: 620px) {
    .fa-memo-meta, .fa-memo-kpis { grid-template-columns: 1fr; }
    .fa-memo-body { padding: 1rem; }
    .fa-memo-brandbar { padding: 0.9rem 1rem; }
}

/* ----------------------------------------------------------------- Footer */
.fa-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-top: 2.6rem;
    padding-top: 1.1rem;
    border-top: 1px solid var(--fa-line);
    color: #94A3B8;
    font-size: 0.64rem;
}

.fa-footer strong { color: #64748B; }
.fa-footer-right { display: flex; gap: 0.85rem; white-space: nowrap; }

/* ------------------------------------------------------------- Responsive */
@media (max-width: 1120px) {
    .fa-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .fa-hero { flex-direction: column; align-items: flex-start; }
    .fa-hero-side { width: 100%; flex: 1 1 auto; flex-direction: row; }
    .fa-close-card { flex: 1; }
}

@media (max-width: 900px) {
    .fa-nav { flex-direction: column; align-items: flex-start; }
    .fa-nav-right { flex-wrap: wrap; }
}

@media (max-width: 720px) {
    .block-container { padding: 0 1rem 2.4rem 1rem; }
    .fa-nav { padding: 0.9rem 1rem; }
    .fa-kpi-grid { grid-template-columns: 1fr; }
    .fa-kpi-grid.fa-kpi-grid-3 { grid-template-columns: 1fr; }
    .fa-hero-side { flex-direction: column; }
    .fa-table { font-size: 0.68rem; }
    .fa-table thead th, .fa-table tbody td { padding: 0.62rem 0.65rem; }
    .fa-validation { flex-direction: column; align-items: flex-start; }
    .fa-footer { flex-direction: column; align-items: flex-start; }
    .fa-footer-right { flex-wrap: wrap; }
}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Small presentation helpers
# ---------------------------------------------------------------------------

ICON_SCAN = """<svg viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 16h4"/></svg>"""
ICON_FLAG = """<svg viewBox="0 0 24 24"><path d="M5 21V4"/><path d="M5 5h11l-2 4 2 4H5"/></svg>"""
ICON_DOLLAR = """<svg viewBox="0 0 24 24"><path d="M12 2v20"/><path d="M17 6.5c0-2-2.2-3.5-5-3.5s-5 1.5-5 3.5 2 3 5 3 5 1.5 5 3.5-2.2 3.5-5 3.5-5-1.5-5-3.5"/></svg>"""
ICON_SHIELD = """<svg viewBox="0 0 24 24"><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/></svg>"""


def esc(value: Any) -> str:
    return html.escape(str(value))


def money(value: float, decimals: int = 0) -> str:
    return f"${value:,.{decimals}f}"


def severity_badge(severity: str) -> str:
    css = {
        "Critical": "critical",
        "High": "high",
        "Medium": "medium",
        "Low": "low",
        "Compliant": "compliant",
    }.get(severity, "low")
    return f'<span class="fa-badge {css}">{esc(severity)}</span>'


def status_badge(status: str) -> str:
    css = {
        "Exception": "exception",
        "Review": "review",
        "Compliant": "compliant",
    }.get(status, "low")
    return f'<span class="fa-badge {css}">{esc(status)}</span>'


def kpi_card(label: str, value: str, foot: str, delta: str = "", tone: str = "", icon: str = ICON_SCAN) -> str:
    delta_html = f'<span class="fa-kpi-delta {tone}">{esc(delta)}</span>' if delta else ""
    return f"""
    <div class="fa-kpi">
        <div class="fa-kpi-top">
            <span class="fa-kpi-label">{esc(label)}</span>
            <span class="fa-kpi-icon">{icon}</span>
        </div>
        <div class="fa-kpi-value">{value}</div>
        <div class="fa-kpi-foot">{delta_html}<span>{esc(foot)}</span></div>
    </div>
    """


def kpi_grid(summary: dict[str, Any]) -> str:
    return f"""
    <div class="fa-kpi-grid">
        {kpi_card("Arrangements Scanned", f"{summary['arrangements']}", "NetSuite + QuickBooks ledger sync", "100% coverage", "good", ICON_SCAN)}
        {kpi_card("Exceptions Flagged", f"{summary['exceptions']}", f"{summary['critical']} critical · {summary['high']} high · {summary['medium']} medium", "Action required", "warn", ICON_FLAG)}
        {kpi_card("Overstated Revenue", money(summary['total_overstated']), "Cumulative through Oct 31, 2026", "Unsupported", "warn", ICON_DOLLAR)}
        {kpi_card("Compliance Rate", f"{summary['compliance_rate']}<small>%</small>", f"{summary['compliant']} of {summary['arrangements']} arrangements clean", "Controls", "good", ICON_SHIELD)}
    </div>
    """


def deal_table_html(results: list[ScanResult]) -> str:
    rows: list[str] = []
    for result in results:
        if result.findings:
            loophole = "<br>".join(esc(finding.name) for finding in result.findings)
        else:
            loophole = '<span class="fa-badge compliant">No exception</span>'
        over_class = "over" if result.overstated_revenue > 0.01 else "zero"
        rows.append(
            f'<tr>'
            f'<td><span class="deal-id">{esc(result.deal_id)}</span><div class="muted">{esc(result.contract_id)}</div></td>'
            f'<td><div class="customer">{esc(result.customer)}</div><div class="muted">{esc(result.deal["industry"])}</div></td>'
            f'<td>{esc(result.erp_source)}<div class="muted">{esc(result.deal["document_type"])}</div></td>'
            f'<td>{loophole}</td>'
            f'<td class="num">{money(result.recognized_to_date)}</td>'
            f'<td class="num {over_class}">{money(result.overstated_revenue)}</td>'
            f'<td>{severity_badge(result.severity)}</td>'
            f'<td>{status_badge(result.status)}</td>'
            f'</tr>'
        )
    return (
        '<div class="fa-table-card"><table class="fa-table"><thead><tr>'
        '<th>Arrangement</th><th>Customer / Industry</th><th>ERP / Evidence</th>'
        '<th>Loophole</th><th>Recognized</th><th>Overstated</th>'
        '<th>Severity</th><th>Status</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table></div>'
    )


def deal_detail(result: ScanResult) -> None:
    ledger_col, evidence_col, finding_col = st.columns([0.95, 1.18, 1.12], gap="large")

    with ledger_col:
        st.markdown('<div class="fa-mini-title">ERP ledger</div>', unsafe_allow_html=True)
        rows = [
            ("ERP source", result.erp_source),
            ("Contract", result.contract_id),
            ("Start date", result.deal["start_date"].strftime("%b %d, %Y")),
            ("Term", f"{result.term_months} months"),
            ("Monthly fee", money(result.monthly_fee, 2)),
            ("Total contract value", money(result.tcv)),
            ("Billed to date", money(result.deal["billed_to_date"])),
            ("ERP recognized", money(result.recognized_to_date)),
            ("Deferred balance", money(result.deal["deferred_revenue"])),
            ("Supportable", money(result.expected_recognized)),
            ("Overstatement", money(result.overstated_revenue)),
        ]
        ledger = "".join(
            f'<div class="fa-kv"><span class="k">{esc(k)}</span><span class="v {"over" if k == "Overstatement" and result.overstated_revenue > 0.01 else ""}">{esc(v)}</span></div>'
            for k, v in rows
        )
        st.markdown(f'<div class="fa-kv-list">{ledger}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="fa-bridge">
                <div><span>Recognized</span><b>{money(result.recognized_to_date)}</b></div>
                <div><span>Supportable</span><b>{money(result.expected_recognized)}</b></div>
                <div><span>Overstated</span><b class="over">{money(result.overstated_revenue)}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with evidence_col:
        st.markdown('<div class="fa-mini-title">Contract evidence</div>', unsafe_allow_html=True)
        st.markdown(
            f'<span class="fa-doc-chip">{esc(result.deal["document_type"])}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="fa-evidence">{esc(result.deal["contract_text"])}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="fa-erp-memo"><strong>ERP memo</strong><br>{esc(result.deal["erp_memo"])}</div>',
            unsafe_allow_html=True,
        )

    with finding_col:
        st.markdown('<div class="fa-mini-title">Forensic findings</div>', unsafe_allow_html=True)
        if not result.findings:
            st.markdown(
                """
                <div class="fa-pass-box">
                    <strong>All four ASC 606 rules passed</strong>
                    Contract language, side-letter evidence, delivery status, and ERP
                    recognition agree. No adjusting journal entry is required.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for finding in result.findings:
                st.markdown(
                    f"""
                    <div class="fa-finding">
                        <div class="fa-finding-title">
                            <span>{esc(finding.name)}</span>
                            <span class="fa-finding-amount">{money(finding.impact, 0)}</span>
                        </div>
                        <div class="fa-finding-meta">{esc(finding.citation)} · {finding.confidence}% rule confidence</div>
                        <div class="fa-finding-text">{esc(finding.explanation)}</div>
                        <div class="fa-finding-evidence">"{esc(finding.evidence)}"</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def exposure_figure(results: list[ScanResult]) -> go.Figure | None:
    totals: dict[str, float] = {}
    for result in results:
        for finding in result.findings:
            totals[finding.name] = totals.get(finding.name, 0.0) + finding.impact
    if not totals:
        return None

    items = sorted(totals.items(), key=lambda pair: pair[1])
    labels = [item[0] for item in items]
    values = [item[1] for item in items]
    palette = ["#C4B5FD", "#A78BFA", "#8B5CF6", "#6D28D9", "#4C1D95"]
    colors = palette[-len(labels):] if len(labels) <= len(palette) else [palette[index % len(palette)] for index in range(len(labels))]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker={"color": colors, "line": {"width": 0}},
            text=[money(value) for value in values],
            textposition="outside",
            textfont={"size": 10, "color": "#4C1D95", "family": "Inter"},
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Exposure: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=300,
        margin={"l": 6, "r": 48, "t": 8, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "size": 10, "color": "#475569"},
        xaxis={
            "showgrid": True,
            "gridcolor": "#EEF2F7",
            "zeroline": False,
            "tickprefix": "$",
            "tickformat": "~s",
            "title": None,
            "range": [0, max(values) * 1.35 if values else 1],
        },
        yaxis={"showgrid": False, "title": None, "tickfont": {"size": 10, "color": "#334155"}},
        showlegend=False,
        bargap=0.38,
    )
    return fig


def severity_figure(results: list[ScanResult]) -> go.Figure | None:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Compliant": 0}
    for result in results:
        counts[result.severity] = counts.get(result.severity, 0) + 1
    labels = [label for label, count in counts.items() if count]
    values = [counts[label] for label in labels]
    if not values:
        return None

    colors = {
        "Critical": "#2E1065",
        "High": "#6D28D9",
        "Medium": "#A78BFA",
        "Low": "#C4B5FD",
        "Compliant": "#E2E8F0",
    }
    exception_count = sum(1 for result in results if result.has_exception)
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.67,
            sort=False,
            marker={"colors": [colors[label] for label in labels], "line": {"color": "#FFFFFF", "width": 2}},
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{value} arrangement(s)<extra></extra>",
        )
    )
    fig.add_annotation(
        text=f"<b>{exception_count}</b><br><span style='font-size:10px;color:#64748B'>exceptions</span>",
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"family": "Inter", "size": 22, "color": "#1E1B4B"},
    )
    fig.update_layout(
        height=300,
        margin={"l": 8, "r": 8, "t": 8, "b": 32},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "size": 10, "color": "#475569"},
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.02,
            "xanchor": "center",
            "x": 0.5,
            "font": {"size": 9, "color": "#64748B"},
            "itemwidth": 30,
        },
    )
    return fig


def journal_summary_html(summary: pd.DataFrame) -> str:
    rows: list[str] = []
    for _, row in summary.iterrows():
        rows.append(
            f'<tr>'
            f'<td><span class="deal-id">{esc(row["JE ID"])}</span></td>'
            f'<td><div class="customer">{esc(row["Customer"])}</div><div class="muted">{esc(row["Deal ID"])}</div></td>'
            f'<td class="num">{money(float(row["Amount"]), 2)}</td>'
            f'<td><span class="fa-cite">{esc(row["ASC 606 Citation"])}</span></td>'
            f'<td>{severity_badge(str(row["Risk Severity"]))}</td>'
            f'<td><span class="fa-badge pending">Pending Approval</span></td>'
            f'<td><span class="fa-badge balanced">Balanced</span></td>'
            f'</tr>'
        )
    return (
        '<div class="fa-table-card"><table class="fa-table"><thead><tr>'
        '<th>Journal Entry</th><th>Customer</th><th>Adjustment</th>'
        '<th>ASC 606 Citation</th><th>Risk</th><th>Controller Queue</th><th>Control</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table></div>'
    )


def journal_lines_html(lines: pd.DataFrame) -> str:
    rows: list[str] = []
    for _, line in lines.iterrows():
        debit = money(float(line["Debit"]), 2) if float(line["Debit"]) else "—"
        credit = money(float(line["Credit"]), 2) if float(line["Credit"]) else "—"
        rows.append(
            f'<tr>'
            f'<td><span class="deal-id">{esc(line["Account Code"])}</span><div class="muted">{esc(line["Account Name"])}</div></td>'
            f'<td class="num">{debit}</td>'
            f'<td class="num">{credit}</td>'
            f'</tr>'
        )
    return (
        '<div class="fa-table-card" style="margin-top:.55rem;"><table class="fa-table"><thead><tr>'
        '<th>Account</th><th>Debit</th><th>Credit</th>'
        '</tr></thead><tbody>'
        + "".join(rows)
        + '</tbody></table></div>'
    )


def render_journal_detail(entries: pd.DataFrame, je_id: str) -> None:
    lines = entries[entries["JE ID"] == je_id]
    if lines.empty:
        return
    first = lines.iloc[0]
    st.markdown(
        f"""
        <div class="fa-je-meta">
            {severity_badge(str(first['Risk Severity']))}
            <span class="fa-badge pending">Pending Controller Approval</span>
            <span class="fa-cite">{esc(first['ASC 606 Citation'])}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="fa-memo">{esc(first["Memo"])}</div>', unsafe_allow_html=True)
    st.markdown(journal_lines_html(lines), unsafe_allow_html=True)
    st.markdown(
        f'<div class="fa-kv" style="margin-top:.55rem;"><span class="k">Prepared by</span><span class="v">{esc(first["Prepared By"])}</span></div>',
        unsafe_allow_html=True,
    )


def sandbox_findings_html(result: ScanResult) -> str:
    if not result.findings:
        return """
        <div class="fa-pass-box" style="margin-top:.6rem;">
            <strong>No exception detected</strong>
            The excerpt and ledger inputs pass all four deterministic ASC 606 rules.
            No adjusting journal entry is required.
        </div>
        """
    cards = []
    for finding in result.findings:
        cards.append(
            f"""
            <div class="fa-sandbox-finding">
                <div class="name">{esc(finding.name)}</div>
                <div class="citation">{esc(finding.citation)} · {finding.confidence}% confidence</div>
                <div class="body">{esc(finding.explanation)}</div>
            </div>
            """
        )
    return "".join(cards)


def render_sandbox_result(result: ScanResult) -> None:
    severity = result.severity
    score = result.risk_score
    st.markdown(
        f"""
        <div class="fa-result-card">
            <div class="fa-result-top">
                <div>
                    <div class="fa-eyebrow">Live scan result</div>
                    <h2>{esc(result.customer)}</h2>
                    <div class="fa-result-sub">{esc(result.erp_source)} · {esc(result.deal['contract_id'])}</div>
                </div>
                {severity_badge(severity)}
            </div>
            <div class="fa-result-amount">{money(result.overstated_revenue, 2)}</div>
            <div class="fa-result-label">Unsupported revenue at risk</div>
            <div class="fa-risk-meter"><div class="fa-risk-fill" style="width:{score}%"></div></div>
            <div class="fa-result-foot"><span>Risk score {score}/100</span><span>{len(result.findings)} finding(s)</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="fa-bridge">
            <div><span>ERP recognized</span><b>{money(result.recognized_to_date)}</b></div>
            <div><span>Supportable</span><b>{money(result.expected_recognized)}</b></div>
            <div><span>Overstated</span><b class="over">{money(result.overstated_revenue)}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(sandbox_findings_html(result), unsafe_allow_html=True)

    if result.has_exception and result.overstated_revenue > 0.01:
        preview = generate_journal_entries([result])
        if not preview.empty:
            first = preview.iloc[0]
            st.markdown(
                f"""
                <div class="fa-je-preview">
                    <div class="fa-mini-title">Proposed adjusting journal entry</div>
                    <div class="fa-je-line"><span>Dr · Subscription Revenue — Adjustment</span><b>{money(result.overstated_revenue, 2)}</b></div>
                    <div class="fa-je-line"><span>Cr · Deferred Revenue — Current</span><b>{money(result.overstated_revenue, 2)}</b></div>
                    <div class="fa-je-memo">{esc(first['Memo'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Controller upload helpers
# ---------------------------------------------------------------------------

SANDBOX_DEFAULT_TEXT = """SALES SIDE-LETTER - EMAIL EXCERPT
Customer: Beacon Cloud Services
Effective Date: January 1, 2026
Subscription Term: 24 months
Monthly Subscription Fee: $20,000
Total Contract Value: $480,000

"To close the quarter, the first 4 months of subscription fees are free of charge.
Please keep this concession off the order form and out of NetSuite."

The order form bills the full $20,000 monthly rate from January 2026.
The ERP has recognized $200,000 through October 2026."""

SANDBOX_DEFAULTS: dict[str, Any] = {
    "sandbox_customer": "Beacon Cloud Services",
    "sandbox_erp": "NetSuite",
    "sandbox_start": date(2026, 1, 1),
    "sandbox_term": 24,
    "sandbox_monthly": 20_000.0,
    "sandbox_tcv": 480_000.0,
    "sandbox_recognized": 200_000.0,
    "sandbox_text": SANDBOX_DEFAULT_TEXT,
}

MONEY_CAPTURE = r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"

LEDGER_COLUMN_ALIASES: dict[str, list[str]] = {
    "sandbox_customer": [
        "customer",
        "customer_name",
        "client",
        "client_name",
        "account",
        "account_name",
        "company",
        "company_name",
    ],
    "sandbox_erp": ["erp_source", "erp", "source_system", "source", "system"],
    "sandbox_start": [
        "start_date",
        "contract_start",
        "contract_start_date",
        "effective_date",
        "commencement_date",
        "start",
    ],
    "sandbox_term": [
        "term_months",
        "term",
        "subscription_term",
        "subscription_term_months",
        "months",
        "term_in_months",
    ],
    "sandbox_monthly": [
        "monthly_fee",
        "monthly_revenue",
        "mrr",
        "monthly_amount",
        "monthly_subscription_fee",
        "subscription_fee",
        "monthly",
    ],
    "sandbox_tcv": [
        "total_contract_value",
        "tcv",
        "contract_value",
        "total_value",
        "total_contract_amount",
    ],
    "sandbox_recognized": [
        "recognized_to_date",
        "recognized",
        "erp_recognized",
        "revenue_recognized",
        "recognized_revenue",
        "cumulative_recognized",
        "recognized_revenue_to_date",
    ],
    "sandbox_text": [
        "contract_text",
        "contract_excerpt",
        "contract_clause",
        "clause",
        "excerpt",
        "side_letter",
        "notes",
        "description",
        "text",
    ],
}

LEDGER_FIELD_LABELS = {
    "sandbox_customer": "Customer",
    "sandbox_erp": "ERP source",
    "sandbox_start": "Start date",
    "sandbox_term": "Term",
    "sandbox_monthly": "Monthly fee",
    "sandbox_tcv": "TCV",
    "sandbox_recognized": "Recognized",
    "sandbox_text": "Contract excerpt",
}

DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y/%m/%d",
    "%d-%b-%Y",
    "%b %d %Y",
    "%B %d %Y",
)


def _normalize_column(name: Any) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())
    return value.strip("_")


def _parse_date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "n/a", "na", "-"}:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        parsed = pd.to_datetime(text, errors="raise")
        return parsed.date()
    except (ValueError, TypeError):
        return None


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "n/a", "na", "-"}:
        return default
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^0-9.\-]", "", text)
    try:
        number = float(text)
    except ValueError:
        return default
    if negative:
        number = -abs(number)
    return number


def _coerce_int(value: Any, default: int) -> int:
    number = _coerce_float(value, float(default))
    try:
        return max(1, int(round(number)))
    except (OverflowError, ValueError):
        return default


def _infer_contract_facts(text: str) -> dict[str, Any]:
    """Pull common contract economics out of extracted PDF text."""
    values: dict[str, Any] = {}

    customer_match = re.search(
        r"(?:^|\n)\s*(?:customer|client|account|prepared\s+for)\s*[:\-]\s*([^\n\r]{2,120})",
        text,
        re.IGNORECASE,
    )
    if customer_match:
        customer = customer_match.group(1).strip().strip('"\'')
        customer = re.sub(r"\s{2,}", " ", customer)[:120]
        if customer:
            values["sandbox_customer"] = customer

    start_match = re.search(
        r"(?:effective\s+date|start\s+date|commencement\s+date|service\s+start)"
        r"\s*[:\-]\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
        text,
        re.IGNORECASE,
    )
    if start_match:
        parsed = _parse_date_value(start_match.group(1))
        if parsed:
            values["sandbox_start"] = parsed

    term_match = re.search(
        r"(?:subscription\s+term|initial\s+term|term(?:\s+length)?)"
        r"\s*[:\-]\s*(\d{1,3})\s*(?:months?|mo)?\b",
        text,
        re.IGNORECASE,
    )
    if term_match:
        values["sandbox_term"] = _coerce_int(term_match.group(1), 24)

    money_fields = {
        "sandbox_monthly": (
            r"(?:monthly\s+(?:subscription\s+)?(?:fee|charge|amount)|mrr)"
            r"\s*[:\-]?\s*"
        ),
        "sandbox_tcv": (
            r"(?:total\s+contract\s+value|tcv|contract\s+value)\s*[:\-]?\s*"
        ),
        "sandbox_recognized": (
            r"(?:erp\s+(?:has\s+)?recognized(?:\s+to\s+date)?|"
            r"recognized\s+to\s+date|revenue\s+recognized(?:\s+to\s+date)?)"
            r"\s*[:\-]?\s*"
        ),
    }
    for key, prefix in money_fields.items():
        match = re.search(prefix + MONEY_CAPTURE, text, re.IGNORECASE)
        if match:
            values[key] = _coerce_float(match.group(1), float(SANDBOX_DEFAULTS[key]))

    return values


PDF_TEXT_THRESHOLD = 25
PDF_OCR_DPI = 200


def _clean_pdf_text(raw: str) -> str:
    """Normalize extracted text and strip control characters."""
    if not raw:
        return ""
    text = raw.replace("\x00", " ")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _meaningful_character_count(text: str) -> int:
    """Count non-whitespace characters used for the digital-vs-OCR decision."""
    return len(re.sub(r"\s+", "", text))


def _ocr_pdf_page(pdf_bytes: bytes, page_number: int) -> tuple[str, str | None]:
    """Rasterize one PDF page in memory and OCR it.

    Returns ``(text, error)``. Missing system binaries or Python packages are
    reported as an error instead of raising, so digital pages still work.
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except Exception as exc:  # pragma: no cover - depends on local install
        return "", f"OCR libraries unavailable ({exc})"

    images = []
    try:
        images = convert_from_bytes(
            pdf_bytes,
            dpi=PDF_OCR_DPI,
            first_page=page_number,
            last_page=page_number,
            fmt="PNG",
            thread_count=1,
        )
        if not images:
            return "", "page could not be rasterized"
        text = pytesseract.image_to_string(images[0], lang="eng")
        return _clean_pdf_text(text), None
    except Exception as exc:  # pragma: no cover - depends on local install
        return "", str(exc)
    finally:
        for image in images:
            try:
                image.close()
            except Exception:
                pass


@st.cache_data(show_spinner=False)
def extract_pdf_document(pdf_bytes: bytes) -> dict[str, Any]:
    """Extract text page by page, auto-switching between digital text and OCR.

    Pages with at least ``PDF_TEXT_THRESHOLD`` non-whitespace characters use
    pypdf's digital text. Sparse pages (scans, photographed addenda, signature
    pages) are rasterized with pdf2image and read with pytesseract. The result
    records which path each page took so the UI can label the document.
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                pass
            if reader.is_encrypted:
                raise ValueError("PDF is password protected")

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise ValueError("PDF contains no pages")

        page_texts: list[str] = []
        digital_pages = 0
        ocr_pages = 0
        ocr_failed_pages = 0
        ocr_errors: list[str] = []

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                digital_text = _clean_pdf_text(page.extract_text() or "")
            except Exception:
                digital_text = ""

            if _meaningful_character_count(digital_text) >= PDF_TEXT_THRESHOLD:
                page_texts.append(digital_text)
                digital_pages += 1
                continue

            ocr_text, ocr_error = _ocr_pdf_page(pdf_bytes, page_number)
            if ocr_error:
                ocr_failed_pages += 1
                if len(ocr_errors) < 4:
                    ocr_errors.append(f"Page {page_number}: {ocr_error}")
            if ocr_text:
                page_texts.append(ocr_text)
                ocr_pages += 1
            elif digital_text:
                # Keep any sparse digital text rather than dropping the page.
                page_texts.append(digital_text)

        text = "\n\n".join(part for part in page_texts if part).strip()

        if digital_pages and ocr_pages:
            mode = "hybrid"
            status = "🔄 Auto-Detected: Hybrid PDF (Digital + Scanned Pages Combined)"
        elif ocr_pages:
            mode = "scanned"
            status = "🔍 Auto-Detected: Scanned Image PDF (OCR Applied)"
        elif digital_pages:
            mode = "digital"
            status = "⚡ Auto-Detected: Digital Text PDF (Fast Parse)"
        elif ocr_failed_pages:
            mode = "fallback"
            status = "⚠️ Auto-Detected: OCR Unavailable"
        else:
            mode = "fallback"
            status = "⚠️ Auto-Detected: No Readable Text"

        return {
            "ok": True,
            "pages": total_pages,
            "text": text,
            "characters": len(text),
            "digital_pages": digital_pages,
            "ocr_pages": ocr_pages,
            "ocr_failed_pages": ocr_failed_pages,
            "ocr_errors": ocr_errors,
            "mode": mode,
            "status": status,
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - depends on malformed PDFs
        return {
            "ok": False,
            "pages": 0,
            "text": "",
            "characters": 0,
            "digital_pages": 0,
            "ocr_pages": 0,
            "ocr_failed_pages": 0,
            "ocr_errors": [],
            "mode": "error",
            "status": "Unable to read PDF",
            "error": str(exc),
        }


def read_ledger_csv(csv_bytes: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(BytesIO(csv_bytes))
    except Exception:
        return pd.read_csv(BytesIO(csv_bytes), sep=None, engine="python")


def map_ledger_row(
    frame: pd.DataFrame, index: int
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Map a ledger CSV row onto the sandbox inputs."""
    normalized = {_normalize_column(column): column for column in frame.columns}
    resolved: dict[str, str] = {}
    for field, aliases in LEDGER_COLUMN_ALIASES.items():
        for alias in aliases:
            column = normalized.get(alias)
            if column is not None:
                resolved[field] = str(column)
                break

    row = frame.iloc[index]
    values: dict[str, Any] = {}

    if "sandbox_customer" in resolved:
        customer = str(row[resolved["sandbox_customer"]]).strip()
        if customer and customer.lower() != "nan":
            values["sandbox_customer"] = customer

    if "sandbox_erp" in resolved:
        erp = str(row[resolved["sandbox_erp"]]).strip()
        if erp and erp.lower() != "nan":
            lowered = erp.lower()
            if "quickbook" in lowered or lowered in {"qbo", "qb"}:
                values["sandbox_erp"] = "QuickBooks Online"
            elif "netsuite" in lowered or lowered == "ns":
                values["sandbox_erp"] = "NetSuite"
            # Unknown labels keep the current ERP selection rather than
            # injecting an option the sandbox selectbox does not contain.

    if "sandbox_start" in resolved:
        parsed = _parse_date_value(row[resolved["sandbox_start"]])
        if parsed:
            values["sandbox_start"] = parsed

    if "sandbox_term" in resolved:
        values["sandbox_term"] = _coerce_int(
            row[resolved["sandbox_term"]], SANDBOX_DEFAULTS["sandbox_term"]
        )

    for key in ("sandbox_monthly", "sandbox_tcv", "sandbox_recognized"):
        if key in resolved:
            values[key] = _coerce_float(
                row[resolved[key]], float(SANDBOX_DEFAULTS[key])
            )

    if "sandbox_text" in resolved:
        text = str(row[resolved["sandbox_text"]]).strip()
        if text and text.lower() != "nan":
            values["sandbox_text"] = text

    missing = [
        LEDGER_FIELD_LABELS[field]
        for field in LEDGER_FIELD_LABELS
        if field not in resolved
    ]
    return values, resolved, missing


def sandbox_csv_template() -> str:
    buffer = StringIO()
    fieldnames = [
        "customer",
        "erp_source",
        "start_date",
        "term_months",
        "monthly_fee",
        "total_contract_value",
        "recognized_to_date",
        "contract_excerpt",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "customer": "Beacon Cloud Services",
            "erp_source": "NetSuite",
            "start_date": "2026-01-01",
            "term_months": 24,
            "monthly_fee": 20000,
            "total_contract_value": 480000,
            "recognized_to_date": 200000,
            "contract_excerpt": (
                "To close the quarter, the first 4 months of subscription fees are "
                "free of charge. Please keep this concession off the order form and "
                "out of NetSuite. The order form bills the full $20,000 monthly rate "
                "from January 2026."
            ),
        }
    )
    return buffer.getvalue()


def apply_sandbox_upload(values: dict[str, Any], notice: str) -> None:
    for key, value in values.items():
        if key in SANDBOX_DEFAULTS and value is not None:
            st.session_state[key] = value
    st.session_state["sandbox_upload_notice"] = notice


def upload_chip_label(key: str, value: Any) -> str:
    if key == "sandbox_start" and isinstance(value, date):
        return value.strftime("%b %d, %Y")
    if key in {"sandbox_monthly", "sandbox_tcv", "sandbox_recognized"}:
        return money(float(value), 2)
    if key == "sandbox_term":
        return f"{int(value)} months"
    text = str(value).replace("\n", " ").strip()
    return text[:64] + ("…" if len(text) > 64 else "")


def memo_findings_html(data: dict[str, Any]) -> str:
    rows: list[str] = []
    for row in data["findings"]:
        rows.append(
            f'<tr>'
            f'<td><div class="fa-memo-strong">{esc(row["loophole"])}</div>'
            f'<div class="fa-memo-cite">{esc(row["citation"])}</div></td>'
            f'<td class="num">{row["count"]}</td>'
            f'<td class="num">{money(row["exposure"])}</td>'
            f'<td>{severity_badge(row["severity"])}</td>'
            f'<td class="fa-memo-action-cell">{esc(row["action"])}</td>'
            f'</tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="5">No ASC 606 exceptions identified.</td></tr>')
    return (
        '<div class="fa-memo-table-wrap"><table class="fa-memo-table"><thead><tr>'
        '<th>Loophole</th><th>Deals</th><th>Exposure</th><th>Severity</th>'
        '<th>Required remediation</th>'
        '</tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"
    )


def memo_exposures_html(data: dict[str, Any]) -> str:
    rows: list[str] = []
    for row in data["exposures"]:
        rows.append(
            f'<tr>'
            f'<td><span class="fa-memo-deal">{esc(row["deal_id"])}</span></td>'
            f'<td><div class="fa-memo-strong">{esc(row["customer"])}</div>'
            f'<div class="fa-memo-cite">{esc(row["erp"])}</div></td>'
            f'<td>{esc(row["loophole"])}</td>'
            f'<td class="num">{money(row["recognized"])}</td>'
            f'<td class="num">{money(row["supportable"])}</td>'
            f'<td class="num over">{money(row["overstated"])}</td>'
            f'<td>{severity_badge(row["severity"])}</td>'
            f'</tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="7">No exceptions in scope.</td></tr>')
    return (
        '<div class="fa-memo-table-wrap"><table class="fa-memo-table"><thead><tr>'
        '<th>Deal</th><th>Customer / ERP</th><th>Loophole</th><th>Recognized</th>'
        '<th>Supportable</th><th>Overstated</th><th>Severity</th>'
        '</tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"
    )


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

results = scan_all(get_deals(), as_of=AS_OF_DATE)
summary = portfolio_summary(results)
entries = generate_journal_entries(results)
journal_sum = summarize_journal_entries(entries)
totals = journal_totals(entries)
report_data = build_report_data(results, summary, totals)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="fa-nav">
        <div class="fa-brand">
            <div class="fa-mark">FA</div>
            <div>
                <div class="fa-brand-title">FinAdvantage <span class="fa-divider">|</span> <span class="fa-suite">AI Digital Controllership</span></div>
                <div class="fa-brand-sub">Revenue assurance for the modern finance stack</div>
            </div>
        </div>
        <div class="fa-nav-right">
            <div class="fa-close-chip">Oct 2026 close</div>
            <div class="fa-soc-badge"><span class="fa-live-dot"></span>SOC 1 Type 2 <span class="fa-dot-sep">•</span> ERP Sync Active</div>
            <div class="fa-avatar">AC</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="fa-hero">
        <div>
            <div class="fa-eyebrow">Revenue assurance · ASC 606</div>
            <h1>Contract-to-Ledger <span>Exception Gate</span></h1>
            <p>
                A deterministic forensic gate between signed contracts, sales side-letters,
                and the ERP revenue schedule. Surface unsupported recognition before the
                month-end journal entries are posted.
            </p>
            <div class="fa-meta-row">
                <span class="fa-meta-chip">Period · Oct 2026</span>
                <span class="fa-meta-chip">{summary['arrangements']} arrangements</span>
                <span class="fa-meta-chip">4 loophole classes</span>
                <span class="fa-meta-chip fa-meta-green">Last sync 4 min ago</span>
            </div>
        </div>
        <div class="fa-hero-side">
            <div class="fa-close-card">
                <div class="fa-close-label">Month-end close</div>
                <div class="fa-close-value">October 2026</div>
                <div class="fa-close-sub">Control window · Oct 31, 2026</div>
            </div>
            <div class="fa-close-card">
                <div class="fa-close-label">Engine status</div>
                <div class="fa-close-value">Deterministic v2.4</div>
                <div class="fa-close-sub">Zero external model calls</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(kpi_grid(summary), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main workflow tabs
# ---------------------------------------------------------------------------

tab_gate, tab_journal, tab_sandbox, tab_memo = st.tabs(
    [
        "Live Exception Gate",
        "Auto-Generated Journal Entries",
        "Live Contract Sandbox",
        "Executive Audit Memo",
    ]
)


# ---------------------------------------------------------------------------
# Tab 1: Live Exception Gate
# ---------------------------------------------------------------------------

with tab_gate:
    with st.container(border=True):
        search_col, erp_col, severity_col, include_col = st.columns([1.25, 0.9, 1.15, 0.75])
        with search_col:
            search_query = st.text_input(
                "Search arrangement",
                placeholder="Customer, deal ID, contract...",
                key="gate_search",
            )
        with erp_col:
            erp_filter = st.selectbox(
                "ERP source",
                ["All sources", "NetSuite", "QuickBooks Online"],
                key="gate_erp",
            )
        with severity_col:
            severity_filter = st.multiselect(
                "Risk severity",
                ["Critical", "High", "Medium", "Low", "Compliant"],
                default=["Critical", "High", "Medium", "Low", "Compliant"],
                key="gate_severity",
            )
        with include_col:
            include_compliant = st.checkbox("Include compliant", value=True, key="gate_compliant")

    normalized_query = search_query.strip().lower()
    filtered: list[ScanResult] = []
    for result in results:
        if not include_compliant and result.status == "Compliant":
            continue
        if erp_filter != "All sources" and result.erp_source != erp_filter:
            continue
        if severity_filter and result.severity not in severity_filter:
            continue
        haystack = " ".join(
            [
                result.deal_id,
                result.customer,
                result.contract_id,
                str(result.deal["industry"]),
                result.loophole_names,
            ]
        ).lower()
        if normalized_query and normalized_query not in haystack:
            continue
        filtered.append(result)

    st.markdown(
        f"""
        <div class="fa-section-head">
            <div>
                <div class="fa-eyebrow">Exception intelligence</div>
                <h2>Portfolio exposure at a glance</h2>
                <p>Contract language matched against the ERP recognition schedule — filtered view.</p>
            </div>
            <div class="fa-section-note">AS OF OCT 31, 2026<br>ENGINE v2.4</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    chart_left, chart_right = st.columns([1.45, 1])
    with chart_left:
        with st.container(border=True):
            st.markdown(
                '<div class="fa-chart-title">Unsupported revenue by loophole</div>'
                '<div class="fa-chart-sub">Rule-level exposure in the current filtered portfolio</div>',
                unsafe_allow_html=True,
            )
            figure = exposure_figure(filtered)
            if figure is not None:
                st.plotly_chart(
                    figure,
                    use_container_width=True,
                    theme=None,
                    config={"displayModeBar": False, "responsive": True},
                )
            else:
                st.markdown(
                    '<div class="fa-pass-box" style="margin:.6rem 0;">No rule-level exposure in this view.</div>',
                    unsafe_allow_html=True,
                )
    with chart_right:
        with st.container(border=True):
            st.markdown(
                '<div class="fa-chart-title">Risk severity mix</div>'
                '<div class="fa-chart-sub">Arrangements by assigned severity</div>',
                unsafe_allow_html=True,
            )
            figure = severity_figure(filtered)
            if figure is not None:
                st.plotly_chart(
                    figure,
                    use_container_width=True,
                    theme=None,
                    config={"displayModeBar": False, "responsive": True},
                )
            else:
                st.markdown(
                    '<div class="fa-pass-box" style="margin:.6rem 0;">No arrangements match the current filters.</div>',
                    unsafe_allow_html=True,
                )

    st.markdown(
        f"""
        <div class="fa-section-head">
            <div>
                <div class="fa-eyebrow">Exception register</div>
                <h2>Contract-to-ledger control results</h2>
                <p>{len(filtered)} of {len(results)} arrangements shown. Expand any line for evidence and the ASC 606 bridge.</p>
            </div>
            <div class="fa-section-note">DETERMINISTIC RULES<br>NO MODEL GUESSWORK</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if filtered:
        st.markdown(deal_table_html(filtered), unsafe_allow_html=True)
        st.markdown(
            '<div class="fa-mini-title" style="margin-top:.9rem;">Deal-level evidence</div>',
            unsafe_allow_html=True,
        )
        for result in filtered:
            severity_label = result.severity if result.has_exception else "Compliant"
            label = f"{result.deal_id}  ·  {result.customer}  —  {severity_label}  ·  {money(result.overstated_revenue)} exposure"
            with st.expander(label):
                deal_detail(result)
    else:
        st.markdown(
            """
            <div class="fa-empty">
                <div class="fa-empty-icon">
                    <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>
                </div>
                <h3>No arrangements match this view</h3>
                <p>Clear the search or widen the severity and ERP filters to see the portfolio again.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 2: Auto-Generated Journal Entries
# ---------------------------------------------------------------------------

with tab_journal:
    st.markdown(
        f"""
        <div class="fa-section-head">
            <div>
                <div class="fa-eyebrow">Month-end close automation</div>
                <h2>Auto-generated adjusting journal entries</h2>
                <p>Balanced reclass entries with audit citations, prepared from the exception gate output.</p>
            </div>
            <div class="fa-section-note">BATCH OCT-2026-ASC606<br>POSTING DATE OCT 31, 2026</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    journal_kpis = f"""
    <div class="fa-kpi-grid fa-kpi-grid-3">
        {kpi_card("Total Adjustment", money(totals['debit_total'], 2), "Debit revenue / credit deferred", "Reclass", "warn", ICON_DOLLAR)}
        {kpi_card("Journal Entries", f"{totals['je_count']}", f"{totals['line_count']} balanced journal lines", "100% balanced", "good", ICON_SCAN)}
        {kpi_card("Control Variance", money(totals['difference'], 2), "Debit total minus credit total", "Cleared", "good", ICON_SHIELD)}
    </div>
    """
    st.markdown(journal_kpis, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="fa-validation">
            <div>
                <div class="fa-eyebrow">Batch control</div>
                <h3>{money(totals['debit_total'], 2)} Dr = {money(totals['credit_total'], 2)} Cr</h3>
                <p>{totals['je_count']} entries · {totals['line_count']} lines · {totals['exceptions']} exception arrangements · Batch OCT-2026-ASC606</p>
            </div>
            <div class="fa-valid-badge">✓ Balanced</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_left, action_right = st.columns([1, 1])
    with action_left:
        st.download_button(
            "Download controller CSV",
            data=journal_entries_to_csv(entries),
            file_name=f"FinAdvantage_ASC606_Journal_Entries_{AS_OF_DATE:%Y%m%d}.csv",
            mime="text/csv",
            width="stretch",
        )
    with action_right:
        if st.button("Run balance validation", width="stretch"):
            if totals["balanced"]:
                st.toast(
                    f"Batch balanced: {money(totals['debit_total'], 2)} Dr = {money(totals['credit_total'], 2)} Cr",
                    icon="✅",
                )
            else:
                st.toast("Balance exception detected. Review the batch before posting.", icon="⚠️")

    st.markdown(
        f"""
        <div class="fa-section-head">
            <div>
                <div class="fa-eyebrow">Controller queue</div>
                <h2>Journal entry register</h2>
                <p>Every entry is two-line, balanced, and carries the specific ASC 606 citation in its memo.</p>
            </div>
            <div class="fa-section-note">{totals['je_count']} ENTRIES<br>PENDING APPROVAL</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if journal_sum.empty:
        st.markdown(
            '<div class="fa-pass-box">No exceptions require an adjusting journal entry for this close.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(journal_summary_html(journal_sum), unsafe_allow_html=True)
        st.markdown(
            '<div class="fa-mini-title" style="margin-top:.9rem;">Entry detail and audit memo</div>',
            unsafe_allow_html=True,
        )
        for _, row in journal_sum.iterrows():
            label = f"{row['JE ID']}  ·  {row['Customer']}  —  {money(float(row['Amount']), 2)}  ·  {row['Risk Severity']}"
            with st.expander(label):
                render_journal_detail(entries, str(row["JE ID"]))

        st.markdown(
            """
            <div class="fa-erp-memo" style="margin-top:.8rem;">
                <strong>Control note.</strong> This demo produces audit-ready adjusting entries but
                does not write back to NetSuite or QuickBooks. Entries remain pending controller
                approval and should be evaluated against the entity's materiality and posting policy.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 3: Live Contract Sandbox
# ---------------------------------------------------------------------------

with tab_sandbox:
    st.markdown(
        """
        <div class="fa-section-head">
            <div>
                <div class="fa-eyebrow">Live contract sandbox</div>
                <h2>Test any clause against the gate</h2>
                <p>Paste a contract excerpt, enter the ledger facts, and run the same four deterministic rules used in the live portfolio.</p>
            </div>
            <div class="fa-section-note">ZERO EXTERNAL CALLS<br>RULE ENGINE v2.4</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Keep widget state stable so uploaded files can populate the sandbox form.
    for state_key, default_value in SANDBOX_DEFAULTS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = default_value

    upload_notice = st.session_state.pop("sandbox_upload_notice", None)
    if upload_notice:
        st.success(upload_notice, icon="📎")

    with st.container(border=True):
        st.markdown(
            '<div class="fa-upload-title">'
            '<div class="fa-eyebrow">Controller upload</div>'
            "<h3>Upload a real PDF contract or CSV ledger</h3>"
            "<p>Drag in a digital, scanned, or hybrid contract PDF or a ledger export. Each PDF page is "
            "auto-detected, OCR is applied only where needed, and the ledger columns are mapped for review.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        upload_col, guide_col = st.columns([1.5, 0.75], gap="large")

        with upload_col:
            st.markdown(
                '<div class="fa-security-banner">'
                '<span class="fa-security-lock">🔒</span>'
                "<span><b>SOC-Compliant Zero Data Retention:</b> Uploaded contracts and ledgers are "
                "processed strictly in volatile RAM and immediately purged upon session close. No files "
                "are written to disk or sent to external AI APIs.</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            uploaded_file = st.file_uploader(
                "Choose a PDF contract or CSV ledger",
                type=["pdf", "csv"],
                key="sandbox_upload_file",
                help="Digital, scanned, and hybrid PDFs are detected page by page. No manual OCR selection is required.",
            )

            if uploaded_file is not None:
                file_name = uploaded_file.name
                if file_name.lower().endswith(".pdf"):
                    extraction = extract_pdf_document(uploaded_file.getvalue())
                    if not extraction["ok"]:
                        st.error(f"Could not read **{file_name}**. {extraction['error']}")
                    else:
                        badge_class = {
                            "digital": "fa-parse-badge-digital",
                            "scanned": "fa-parse-badge-scanned",
                            "hybrid": "fa-parse-badge-hybrid",
                        }.get(extraction["mode"], "fa-parse-badge-fallback")
                        st.markdown(
                            f'<div class="fa-parse-badge {badge_class}">'
                            f'{esc(extraction["status"])}</div>',
                            unsafe_allow_html=True,
                        )
                        page_chips = [
                            f'<span class="fa-upload-chip">{extraction["pages"]} page(s)</span>',
                            f'<span class="fa-upload-chip">{extraction["characters"]:,} characters extracted</span>',
                        ]
                        if extraction["digital_pages"]:
                            page_chips.append(
                                f'<span class="fa-upload-chip"><b>Digital</b> '
                                f'{extraction["digital_pages"]} page(s)</span>'
                            )
                        if extraction["ocr_pages"]:
                            page_chips.append(
                                f'<span class="fa-upload-chip"><b>OCR</b> '
                                f'{extraction["ocr_pages"]} page(s)</span>'
                            )
                        page_chips.append(
                            f'<span class="fa-upload-chip">{esc(file_name)}</span>'
                        )
                        st.markdown(
                            f'<div class="fa-upload-meta">{"".join(page_chips)}</div>',
                            unsafe_allow_html=True,
                        )
                        if extraction["ocr_errors"]:
                            st.warning(
                                "Automatic OCR was unavailable for "
                                f"{extraction['ocr_failed_pages']} page(s) in this environment. "
                                "Digital pages were still parsed and the app remains usable. On Streamlit "
                                "Cloud, `packages.txt` installs `tesseract-ocr` and `poppler-utils` "
                                "automatically. Details: " + "; ".join(extraction["ocr_errors"]),
                                icon="⚠️",
                            )
                        if extraction["characters"] < 40:
                            st.warning(
                                "No readable text was recovered from this PDF. If it is image-only, "
                                "install Tesseract and Poppler locally or deploy to Streamlit Cloud where "
                                "they are installed automatically.",
                                icon="⚠️",
                            )
                        else:
                            st.text_area(
                                "Extracted contract text",
                                value=extraction["text"][:12_000],
                                height=170,
                                disabled=True,
                            )
                            facts = _infer_contract_facts(extraction["text"])
                            if facts:
                                chips = "".join(
                                    f'<span class="fa-upload-chip"><b>{esc(LEDGER_FIELD_LABELS[key])}</b> '
                                    f"{esc(upload_chip_label(key, value))}</span>"
                                    for key, value in facts.items()
                                    if key in LEDGER_FIELD_LABELS
                                )
                                st.markdown(
                                    f'<div class="fa-upload-meta">{chips}</div>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.caption(
                                    "No economics were detected automatically. Load the contract text, "
                                    "then enter the ledger facts below."
                                )
                            if st.button(
                                "Load contract into sandbox",
                                type="primary",
                                width="stretch",
                                key="sandbox_load_pdf",
                            ):
                                values = dict(facts)
                                values["sandbox_text"] = extraction["text"]
                                apply_sandbox_upload(
                                    values,
                                    f"Loaded {file_name} into the sandbox with "
                                    f"{len(facts)} inferred economics field(s).",
                                )
                                st.rerun()
                else:
                    try:
                        frame = read_ledger_csv(uploaded_file.getvalue())
                    except Exception as exc:  # pragma: no cover - malformed CSV
                        st.error(f"Could not read **{file_name}** as a CSV ledger. {exc}")
                    else:
                        if frame.empty:
                            st.warning("This CSV has no data rows.")
                        else:
                            st.caption(
                                f"Previewing {min(len(frame), 25)} of {len(frame)} row(s). "
                                "Column names are matched automatically."
                            )
                            st.dataframe(
                                frame.head(25),
                                use_container_width=True,
                                hide_index=True,
                                height=200,
                            )

                            _, resolved_columns, _ = map_ledger_row(frame, 0)
                            customer_column = resolved_columns.get("sandbox_customer")

                            if len(frame) > 1:
                                if (
                                    "sandbox_csv_row" in st.session_state
                                    and st.session_state["sandbox_csv_row"] >= len(frame)
                                ):
                                    st.session_state["sandbox_csv_row"] = 0

                                def _row_label(index: int) -> str:
                                    label = f"Row {index + 1}"
                                    if customer_column is not None:
                                        customer = str(frame.iloc[index][customer_column]).strip()
                                        if customer and customer.lower() != "nan":
                                            label += f" · {customer}"
                                    return label

                                row_index = st.selectbox(
                                    "Select the ledger row to load",
                                    options=list(range(len(frame))),
                                    format_func=_row_label,
                                    key="sandbox_csv_row",
                                )
                            else:
                                row_index = 0

                            values, resolved, missing = map_ledger_row(frame, row_index)
                            if resolved:
                                chips = "".join(
                                    f'<span class="fa-upload-chip"><b>{esc(LEDGER_FIELD_LABELS[key])}</b> '
                                    f"← {esc(column)}</span>"
                                    for key, column in resolved.items()
                                    if key in LEDGER_FIELD_LABELS
                                )
                                st.markdown(
                                    f'<div class="fa-upload-meta">{chips}</div>',
                                    unsafe_allow_html=True,
                                )
                            if missing:
                                st.caption(
                                    "Not supplied in this CSV (left unchanged): "
                                    + ", ".join(missing)
                                    + "."
                                )
                                if "Contract excerpt" in missing:
                                    st.info(
                                        "No contract excerpt column was detected. The ledger facts can "
                                        "still be loaded, but clause-level exceptions need contract text.",
                                        icon="ℹ️",
                                    )
                            if "sandbox_erp" in resolved and "sandbox_erp" not in values:
                                raw_erp = str(
                                    frame.iloc[row_index][resolved["sandbox_erp"]]
                                ).strip()
                                st.caption(
                                    f"ERP value “{raw_erp}” is not NetSuite or QuickBooks Online; "
                                    "the current ERP selection was kept."
                                )

                            if st.button(
                                "Load ledger row into sandbox",
                                type="primary",
                                width="stretch",
                                key="sandbox_load_csv",
                            ):
                                preserved_excerpt = False
                                if "sandbox_text" not in values:
                                    current_text = str(
                                        st.session_state.get("sandbox_text", "")
                                    ).strip()
                                    if (
                                        not current_text
                                        or current_text == SANDBOX_DEFAULT_TEXT.strip()
                                    ):
                                        customer_value = values.get(
                                            "sandbox_customer",
                                            st.session_state.get("sandbox_customer"),
                                        )
                                        term_value = int(
                                            values.get(
                                                "sandbox_term",
                                                st.session_state.get("sandbox_term", 24),
                                            )
                                        )
                                        monthly_value = float(
                                            values.get(
                                                "sandbox_monthly",
                                                st.session_state.get("sandbox_monthly", 0.0),
                                            )
                                        )
                                        tcv_value = float(
                                            values.get(
                                                "sandbox_tcv",
                                                st.session_state.get("sandbox_tcv", 0.0),
                                            )
                                        )
                                        values["sandbox_text"] = (
                                            "LEDGER IMPORT\n"
                                            f"Customer: {customer_value}\n"
                                            f"Subscription Term: {term_value} months\n"
                                            f"Monthly Subscription Fee: {money(monthly_value, 2)}\n"
                                            f"Total Contract Value: {money(tcv_value, 2)}\n\n"
                                            "No side-letter, trial, or concession clause was supplied "
                                            "with this ledger import."
                                        )
                                    else:
                                        preserved_excerpt = True
                                notice = (
                                    f"Loaded row {row_index + 1} from {file_name} into the sandbox "
                                    f"({len(resolved)} mapped column(s))."
                                )
                                if preserved_excerpt:
                                    notice += (
                                        " The existing contract excerpt was preserved; upload a PDF "
                                        "or paste the clause to replace it."
                                    )
                                apply_sandbox_upload(values, notice)
                                st.rerun()

        with guide_col:
            st.markdown(
                """
                <div class="fa-upload-guide">
                    <div class="fa-upload-guide-title">What happens on load</div>
                    <ul>
                        <li><strong>PDF</strong> pages are auto-detected: digital text where available, OCR only for scanned, photographed, or signature pages.</li>
                        <li><strong>CSV</strong> columns are matched to customer, ERP, dates, term, fees, TCV, and recognized revenue.</li>
                        <li>Nothing is posted — you still review the pre-filled facts and run the scan.</li>
                    </ul>
                    <div class="fa-upload-guide-note">No manual OCR selection. Files stay in volatile RAM and are never written to disk.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.download_button(
                "Download CSV upload template",
                data=sandbox_csv_template(),
                file_name="FinAdvantage_ASC606_Sandbox_Ledger_Template.csv",
                mime="text/csv",
                width="stretch",
                key="sandbox_template_download",
            )

    input_col, result_col = st.columns([1.05, 0.95], gap="large")

    with input_col:
        with st.container(border=True):
            with st.form("sandbox_form"):
                customer_col, erp_col = st.columns([1.35, 0.85])
                with customer_col:
                    sandbox_customer = st.text_input("Customer", key="sandbox_customer")
                with erp_col:
                    sandbox_erp = st.selectbox(
                        "ERP source",
                        ["NetSuite", "QuickBooks Online"],
                        key="sandbox_erp",
                    )

                date_col, term_col, monthly_col = st.columns([1, 0.8, 1])
                with date_col:
                    sandbox_start = st.date_input("Start date", key="sandbox_start")
                with term_col:
                    sandbox_term = st.number_input(
                        "Term (months)",
                        min_value=1,
                        max_value=120,
                        step=1,
                        key="sandbox_term",
                    )
                with monthly_col:
                    sandbox_monthly = st.number_input(
                        "Monthly fee",
                        min_value=0.0,
                        step=1_000.0,
                        format="%.2f",
                        key="sandbox_monthly",
                    )

                tcv_col, recognized_col = st.columns(2)
                with tcv_col:
                    sandbox_tcv = st.number_input(
                        "Total contract value",
                        min_value=0.0,
                        step=10_000.0,
                        format="%.2f",
                        key="sandbox_tcv",
                    )
                with recognized_col:
                    sandbox_recognized = st.number_input(
                        "ERP recognized to date",
                        min_value=0.0,
                        step=5_000.0,
                        format="%.2f",
                        key="sandbox_recognized",
                    )

                sandbox_text = st.text_area(
                    "Contract excerpt",
                    height=270,
                    help="Paste the relevant clause, order-form economics, or sales side-letter.",
                    key="sandbox_text",
                )

                submitted = st.form_submit_button(
                    "Run live exception scan",
                    type="primary",
                    width="stretch",
                )

            if submitted:
                st.session_state["sandbox_result"] = scan_custom_deal(
                    contract_text=sandbox_text,
                    customer=sandbox_customer,
                    erp_source=sandbox_erp,
                    start_date=sandbox_start,
                    term_months=int(sandbox_term),
                    monthly_fee=float(sandbox_monthly),
                    tcv=float(sandbox_tcv),
                    recognized_to_date=float(sandbox_recognized),
                    as_of=AS_OF_DATE,
                )
                st.toast("Live contract scan complete.", icon="🔍")

    with result_col:
        sandbox_result = st.session_state.get("sandbox_result")
        if sandbox_result is None:
            st.markdown(
                """
                <div class="fa-empty">
                    <div class="fa-empty-icon">
                        <svg viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><circle cx="11" cy="14" r="3"/><path d="M13.2 16.2L15 18"/></svg>
                    </div>
                    <h3>Awaiting your contract</h3>
                    <p>Run the prefilled side-letter or paste your own clause. The engine returns findings, the overstated amount, risk severity, and a proposed journal entry.</p>
                    <div class="fa-rule-list">
                        <span class="fa-rule-pill">30-day termination</span>
                        <span class="fa-rule-pill">Free months</span>
                        <span class="fa-rule-pill">90-day trial</span>
                        <span class="fa-rule-pill">Feature contingency</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            render_sandbox_result(sandbox_result)
            if st.button("Clear sandbox result", width="stretch"):
                st.session_state["sandbox_result"] = None
                st.rerun()


# ---------------------------------------------------------------------------
# Tab 4: Executive Audit Memo
# ---------------------------------------------------------------------------

with tab_memo:
    st.markdown(
        """
        <div class="fa-section-head">
            <div>
                <div class="fa-eyebrow">Executive reporting</div>
                <h2>Executive Audit Memo</h2>
                <p>A CFO-ready summary of the October 2026 ASC 606 exception gate, adjustable journal entries, and remediation plan.</p>
            </div>
            <div class="fa-section-note">PREPARED NOV 9, 2026<br>DRAFT FOR CFO REVIEW</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    memo_pdf_bytes = executive_memo_pdf(report_data)
    memo_html_document = executive_memo_html(report_data)
    memo_schedule_csv = exception_schedule_csv(report_data)

    download_pdf, download_html, download_csv = st.columns(3)
    with download_pdf:
        st.download_button(
            "Download memo · PDF",
            data=memo_pdf_bytes,
            file_name=report_filename("pdf"),
            mime="application/pdf",
            type="primary",
            width="stretch",
            key="memo_download_pdf",
        )
    with download_html:
        st.download_button(
            "Download memo · HTML",
            data=memo_html_document,
            file_name=report_filename("html"),
            mime="text/html",
            width="stretch",
            key="memo_download_html",
        )
    with download_csv:
        st.download_button(
            "Download exception schedule · CSV",
            data=memo_schedule_csv,
            file_name="FinAdvantage_ASC606_Exception_Schedule_20261031.csv",
            mime="text/csv",
            width="stretch",
            key="memo_download_csv",
        )

    st.caption(
        "Reports are generated from the current portfolio scan and journal batch. "
        "The PDF is print-ready; the HTML memo is self-contained for audit-committee distribution."
    )

    memo_meta = "".join(
        f'<div><span>{esc(label)}</span><strong>{esc(value)}</strong></div>'
        for label, value in [
            ("Reporting period", report_data["period"]),
            ("As of", report_data["as_of"]),
            ("Prepared", report_data["prepared"]),
            ("Status", report_data["status"]),
        ]
    )
    memo_kpis = "".join(
        f'<div class="fa-memo-kpi"><div class="value">{value}</div>'
        f'<div class="label">{esc(label)}</div></div>'
        for value, label in [
            (report_data["arrangements"], "Arrangements scanned"),
            (report_data["exceptions"], "Exceptions flagged"),
            (money(report_data["overstated"]), "Overstated revenue"),
            (report_data["journal_count"], "Balanced journals"),
        ]
    )
    memo_recommendations = "".join(
        f"<li>{esc(item)}</li>" for item in report_data["recommendations"]
    )
    memo_signoff = "".join(
        f'<div><span>{esc(role)}</span><strong>{esc(name)}</strong>'
        f'<div class="fa-memo-signline"></div></div>'
        for role, name in [
            ("Prepared by", "FinAdvantage AI Digital Controllership"),
            ("Reviewed by", "Revenue Controller"),
            ("Approved by", "Chief Financial Officer"),
        ]
    )

    memo_html_block = f"""
<div class="fa-memo-paper">
    <div class="fa-memo-brandbar">
        <div>
            <div class="fa-memo-brand">FinAdvantage <span>| AI Digital Controllership</span></div>
            <div class="fa-memo-brand-sub">Revenue assurance for the modern finance stack</div>
        </div>
        <div class="fa-memo-confidential">Confidential · Internal use only</div>
    </div>
    <div class="fa-memo-body">
        <div class="fa-eyebrow">Executive reporting</div>
        <h2 class="fa-memo-title">Executive Audit Memo</h2>
        <div class="fa-memo-subtitle">ASC 606 Contract-to-Ledger Exception Gate</div>
        <div class="fa-memo-meta">{memo_meta}</div>
        <div class="fa-memo-rule"></div>
        <div class="fa-memo-section-title">Executive summary</div>
        <p class="fa-memo-summary">{esc(report_data["executive_summary"])}</p>
        <div class="fa-memo-kpis">{memo_kpis}</div>
        <div class="fa-memo-section-title">Findings by ASC 606 loophole</div>
        {memo_findings_html(report_data)}
        <div class="fa-memo-section-title">Largest exposures</div>
        {memo_exposures_html(report_data)}
        <div class="fa-memo-section-title">Journal entry impact</div>
        <div class="fa-memo-callout">
            <strong>Batch {esc(report_data["batch"])}</strong> · {report_data["journal_count"]} entries ·
            {report_data["line_count"]} lines · {money(report_data["debit_total"], 2)} Dr =
            {money(report_data["credit_total"], 2)} Cr · variance {money(report_data["variance"], 2)}.
            Status: <strong>{'Balanced' if report_data["balanced"] else 'Review required'}</strong> and
            pending controller approval. No ERP write-back has been performed.
        </div>
        <div class="fa-memo-section-title">Recommended actions</div>
        <ol class="fa-memo-actions">{memo_recommendations}</ol>
        <div class="fa-memo-section-title">Sign-off</div>
        <div class="fa-memo-signoff">{memo_signoff}</div>
        <div class="fa-memo-footer">
            <span>FinAdvantage AI Digital Controllership · ASC 606 Contract-to-Ledger Exception Gate</span>
            <span>Generated {esc(report_data["prepared"])} · Confidential</span>
        </div>
    </div>
</div>
"""
    st.markdown(memo_html_block, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <div class="fa-footer">
        <div><strong>FinAdvantage AI Digital Controllership</strong> · ASC 606 Contract-to-Ledger Exception Gate · Demo environment</div>
        <div class="fa-footer-right">
            <span>SOC 1 Type 2</span>
            <span>Deterministic engine v2.4</span>
            <span>US-East</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
