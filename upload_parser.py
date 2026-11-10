"""Hybrid PDF/CSV parsing helpers for the FinAdvantage contract uploader."""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
import re
from typing import Any

import pandas as pd
from pypdf import PdfReader

PDF_TEXT_THRESHOLD = 25
PDF_OCR_DPI = 200

LEDGER_ALIASES: dict[str, list[str]] = {
    "customer": ["customer", "customer_name", "client", "client_name", "account", "company"],
    "erp": ["erp_source", "erp", "source_system", "source", "system"],
    "start": ["start_date", "contract_start", "effective_date", "commencement_date", "start"],
    "term": ["term_months", "term", "subscription_term", "months", "term_in_months"],
    "monthly": ["monthly_fee", "monthly_revenue", "mrr", "monthly_amount", "monthly_subscription_fee"],
    "tcv": ["total_contract_value", "tcv", "contract_value", "total_value", "total_contract_amount"],
    "recognized": ["recognized_to_date", "recognized", "erp_recognized", "revenue_recognized", "cumulative_recognized"],
    "text": ["contract_text", "contract_excerpt", "contract_clause", "clause", "excerpt", "notes", "text"],
}
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y", "%Y/%m/%d", "%d-%b-%Y")
MONEY = r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"


def _clean(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t\f\v]+", " ", text)).strip()


def _ocr_page(pdf_bytes: bytes, page_number: int) -> tuple[str, str | None]:
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except Exception as exc:
        return "", f"OCR libraries unavailable ({exc})"
    images = []
    try:
        images = convert_from_bytes(
            pdf_bytes, dpi=PDF_OCR_DPI, first_page=page_number, last_page=page_number,
            fmt="PNG", thread_count=1,
        )
        if not images:
            return "", "page could not be rasterized"
        return _clean(pytesseract.image_to_string(images[0], lang="eng")), None
    except Exception as exc:
        return "", str(exc)
    finally:
        for image in images:
            image.close()


def extract_pdf_document(pdf_bytes: bytes) -> dict[str, Any]:
    """Extract text page by page, auto-switching between digital text and OCR."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                pass
            if reader.is_encrypted:
                raise ValueError("PDF is password protected")
        pages = len(reader.pages)
        parts: list[str] = []
        digital = ocr = failed = 0
        errors: list[str] = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = _clean(page.extract_text() or "")
            except Exception:
                text = ""
            if len(re.sub(r"\s+", "", text)) >= PDF_TEXT_THRESHOLD:
                parts.append(text)
                digital += 1
                continue
            ocr_text, error = _ocr_page(pdf_bytes, number)
            if error:
                failed += 1
                if len(errors) < 4:
                    errors.append(f"Page {number}: {error}")
            if ocr_text:
                parts.append(ocr_text)
                ocr += 1
            elif text:
                parts.append(text)
        if digital and ocr:
            mode, status = "hybrid", "🔄 Auto-Detected: Hybrid PDF (Digital + Scanned Pages Combined)"
        elif ocr:
            mode, status = "scanned", "🔍 Auto-Detected: Scanned Image PDF (OCR Applied)"
        elif digital:
            mode, status = "digital", "⚡ Auto-Detected: Digital Text PDF (Fast Parse)"
        elif failed:
            mode, status = "fallback", "⚠️ Auto-Detected: OCR Unavailable"
        else:
            mode, status = "fallback", "⚠️ Auto-Detected: No Readable Text"
        text = "\n\n".join(part for part in parts if part).strip()
        return {
            "ok": True, "pages": pages, "text": text, "characters": len(text),
            "digital_pages": digital, "ocr_pages": ocr, "ocr_failed_pages": failed,
            "ocr_errors": errors, "mode": mode, "status": status, "error": None,
        }
    except Exception as exc:
        return {
            "ok": False, "pages": 0, "text": "", "characters": 0, "digital_pages": 0,
            "ocr_pages": 0, "ocr_failed_pages": 0, "ocr_errors": [], "mode": "error",
            "status": "Unable to read PDF", "error": str(exc),
        }


def infer_contract_facts(text: str) -> dict[str, Any]:
    """Pull common contract economics out of extracted text."""
    values: dict[str, Any] = {}
    match = re.search(r"(?:^|\n)\s*(?:customer|client|account|prepared\s+for)\s*[:\-]\s*([^\n\r]{2,120})", text, re.I)
    if match:
        values["customer"] = re.sub(r"\s{2,}", " ", match.group(1).strip().strip('"\'"'))[:120]
    match = re.search(r"(?:effective\s+date|start\s+date|commencement\s+date|service\s+start)\s*[:\-]\s*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})", text, re.I)
    if match:
        for fmt in DATE_FORMATS:
            try:
                values["start"] = datetime.strptime(match.group(1), fmt).date()
                break
            except ValueError:
                continue
    match = re.search(r"(?:subscription\s+term|initial\s+term|term(?:\s+length)?)\s*[:\-]\s*(\d{1,3})\s*(?:months?|mo)?\b", text, re.I)
    if match:
        values["term"] = max(1, int(match.group(1)))
    for key, pattern in {
        "monthly": r"(?:monthly\s+(?:subscription\s+)?(?:fee|charge|amount)|mrr)\s*[:\-]?\s*",
        "tcv": r"(?:total\s+contract\s+value|tcv|contract\s+value)\s*[:\-]?\s*",
        "recognized": r"(?:erp\s+(?:has\s+)?recognized(?:\s+to\s+date)?|recognized\s+to\s+date|revenue\s+recognized(?:\s+to\s+date)?)\s*[:\-]?\s*",
    }.items():
        match = re.search(pattern + MONEY, text, re.I)
        if match:
            values[key] = float(match.group(1).replace(",", ""))
    return values


def read_ledger(csv_bytes: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(BytesIO(csv_bytes))
    except Exception:
        return pd.read_csv(BytesIO(csv_bytes), sep=None, engine="python")


def first_ledger_row(frame: pd.DataFrame) -> dict[str, Any]:
    """Map the first ledger row to the custom scan fields."""
    normalized = {re.sub(r"[^a-z0-9]+", "_", str(column).lower()).strip("_"): column for column in frame.columns}
    values: dict[str, Any] = {}
    for field, aliases in LEDGER_ALIASES.items():
        column = next((normalized[a] for a in aliases if a in normalized), None)
        if column is None or frame.empty:
            continue
        raw = frame.iloc[0][column]
        text = str(raw).strip()
        if not text or text.lower() == "nan":
            continue
        if field == "term":
            values[field] = max(1, int(float(re.sub(r"[^0-9.\-]", "", text) or 12)))
        elif field in {"monthly", "tcv", "recognized"}:
            values[field] = float(re.sub(r"[^0-9.\-]", "", text) or 0)
        elif field == "start":
            for fmt in DATE_FORMATS:
                try:
                    values[field] = datetime.strptime(text, fmt).date()
                    break
                except ValueError:
                    continue
        elif field == "erp":
            lowered = text.lower()
            values[field] = "QuickBooks Online" if "quickbook" in lowered or lowered in {"qbo", "qb"} else "NetSuite"
        else:
            values[field] = text
    return values


def make_custom_result(*, contract_text: str, customer: str, erp: str, start: date,
                       term: int, monthly: float, tcv: float, booked: float):
    """Build a single-contract scan using the shared deterministic engine."""
    from forensic_scanner import scan_custom_deal
    return scan_custom_deal(
        contract_text=contract_text, customer=customer, erp_source=erp, start_date=start,
        term_months=max(1, term), monthly_fee=max(0.0, monthly), tcv=max(0.0, tcv),
        recognized_to_date=max(0.0, booked),
    )
