"""Deterministic ASC 606 contract-to-ledger exception scanner.

The engine reads the unstructured contract excerpt, applies four explainable
rules, and compares the contract economics with the ERP revenue ledger:

1. 30-day termination for convenience without a substantive penalty
2. Undisclosed free months / price concession in a side letter
3. 90-day money-back trial (cancelable at will)
4. Unfulfilled feature contingency

Every result is reproducible: no LLM, no randomness, and no external calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import re
from typing import Any

from sample_data import AS_OF_DATE

# ---------------------------------------------------------------------------
# Loophole library
# ---------------------------------------------------------------------------

LOOPHOLE_LIBRARY: dict[str, dict[str, str]] = {
    "TERMINATION_CONVENIENCE": {
        "name": "30-Day Termination for Convenience",
        "short": "30-day termination",
        "citation": "ASC 606-10-25-3 through 25-4",
        "description": (
            "A cancellation right with 30 days or less notice and no substantive "
            "penalty limits the enforceable contract term to the notice period."
        ),
    },
    "UNDISCLOSED_FREE_MONTHS": {
        "name": "Undisclosed Free Months Side-Letter",
        "short": "Free months side-letter",
        "citation": "ASC 606-10-32-25 through 32-27 / 606-10-32-36",
        "description": (
            "A side-letter concession reduces the transaction price and must be "
            "allocated across the entire service period, including free months."
        ),
    },
    "MONEY_BACK_TRIAL": {
        "name": "90-Day Money-Back Trial",
        "short": "90-day money-back trial",
        "citation": "ASC 606-10-25-1 / 606-10-55-22 / 606-10-32-25",
        "description": (
            "A cancelable trial with a full refund is not a contract with an "
            "enforceable right to payment until the customer converts."
        ),
    },
    "FEATURE_CONTINGENCY": {
        "name": "Unfulfilled Feature Contingency",
        "short": "Unfulfilled feature",
        "citation": "ASC 606-10-25-14 / 25-19 / 25-30 / 32-36",
        "description": (
            "A distinct, undelivered feature remains a separate performance "
            "obligation. Its allocated transaction price must stay deferred."
        ),
    },
}

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Compliant"]

SEVERITY_THRESHOLDS = [
    (125_000.0, "Critical"),
    (60_000.0, "High"),
    (20_000.0, "Medium"),
    (0.01, "Low"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single rule violation with its evidence and estimated exposure."""

    loophole_id: str
    name: str
    citation: str
    evidence: str
    impact: float
    explanation: str
    confidence: int
    account_hint: str = "Subscription revenue / deferred revenue"


@dataclass
class ScanResult:
    """The complete forensic result for one arrangement."""

    deal: dict[str, Any]
    findings: list[Finding] = field(default_factory=list)
    elapsed_months: int = 0
    overstated_revenue: float = 0.0
    expected_recognized: float = 0.0
    severity: str = "Compliant"
    status: str = "Compliant"
    risk_score: int = 0

    @property
    def deal_id(self) -> str:
        return str(self.deal["deal_id"])

    @property
    def customer(self) -> str:
        return str(self.deal["customer"])

    @property
    def erp_source(self) -> str:
        return str(self.deal["erp_source"])

    @property
    def contract_id(self) -> str:
        return str(self.deal["contract_id"])

    @property
    def recognized_to_date(self) -> float:
        return float(self.deal["recognized_to_date"])

    @property
    def tcv(self) -> float:
        return float(self.deal["tcv"])

    @property
    def monthly_fee(self) -> float:
        return float(self.deal["monthly_fee"])

    @property
    def term_months(self) -> int:
        return int(self.deal["term_months"])

    @property
    def loophole_names(self) -> str:
        if not self.findings:
            return "None - controls passed"
        return " + ".join(finding.name for finding in self.findings)

    @property
    def primary_loophole(self) -> str:
        if not self.findings:
            return "No exception"
        return self.findings[0].name

    @property
    def has_exception(self) -> bool:
        return self.status == "Exception"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

_NUMBER_TOKEN = (
    r"(?:\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
    r"twelve|fifteen|twenty|thirty|forty(?:[- ]five)?|sixty|ninety|"
    r"one\s+hundred\s+twenty)"
)

_WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "forty five": 45,
    "forty-five": 45,
    "sixty": 60,
    "ninety": 90,
    "one hundred twenty": 120,
}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")

_TERM_TRIGGER = re.compile(
    r"(?:(?:may|can|shall be entitled to|has the right to)\s+"
    r"(?:terminate|cancel)[^.]{0,190}?"
    r"(?:for convenience|without cause|at any time))"
    r"|(?:right to terminate[^.]{0,140}?"
    r"(?:for convenience|without cause|at any time))",
    re.IGNORECASE,
)

_NOTICE_DAYS = re.compile(
    rf"(?:upon|after|with(?:in)?|requires?|provides?)\s+"
    rf"(?:at least\s+)?(?P<days>{_NUMBER_TOKEN})\s*"
    rf"(?:\(\d+\))?\s*(?:calendar\s+|business\s+)?days?",
    re.IGNORECASE,
)

_ANY_DAYS = re.compile(
    rf"(?P<days>{_NUMBER_TOKEN})\s*(?:\(\d+\))?\s*"
    rf"(?:calendar\s+|business\s+)?days?",
    re.IGNORECASE,
)

_PENALTY = re.compile(
    r"(early termination (?:fee|charge)|termination (?:fee|charge)|"
    r"unwind (?:fee|charge)|breakage fee|remaining (?:contract )?(?:fees|value)|"
    r"minimum (?:commitment|purchase))",
    re.IGNORECASE,
)

_NEGATION = re.compile(
    r"\b(no|not|none|without|never|shall not|does not|will not|cannot)\b",
    re.IGNORECASE,
)

_TRIAL_DAYS = re.compile(
    rf"(?P<days>{_NUMBER_TOKEN})\s*[- ]day\s*"
    r"(?:money[- ]back|trial|refund|satisfaction guarantee)",
    re.IGNORECASE,
)

_TRIAL_REFUND = re.compile(
    r"(money[- ]back|full refund|refund of all (?:fees|amounts)|"
    r"right of return|satisfaction guarantee)",
    re.IGNORECASE,
)

_FREE_MONTH_PATTERNS = [
    re.compile(
        rf"(?:first|initial)\s+(?P<months>{_NUMBER_TOKEN})\s*"
        r"(?:\(\d+\))?\s*months?[^.]{0,110}?"
        r"(?:free|no charge|no cost|waiv\w*|complimentary)",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<months>{_NUMBER_TOKEN})\s*(?:\(\d+\))?\s*"
        r"(?:free|complimentary|no[- ]cost)\s+months?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:waiv\w*|forgiv\w*|credit(?:ed)?)[^.]{{0,90}}?"
        rf"(?P<months>{_NUMBER_TOKEN})\s*(?:\(\d+\))?\s*months?",
        re.IGNORECASE,
    ),
]

_FEATURE_VALUE = re.compile(
    r"(?:module|feature|add-on|functionality)[^.]{0,150}?"
    r"valued at\s*\$(?P<value>[\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

_FEATURE_PENDING = re.compile(
    r"(not yet (?:available|delivered|released)|not delivered|pending|"
    r"scheduled for delivery|targeted (?:release|delivery)|target date|"
    r"future release|roadmap|contingent on|awaiting (?:delivery|acceptance|certification))",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Collapse whitespace and standardize typographic punctuation."""
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    return _WHITESPACE.sub(" ", text).strip()


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in _SENTENCE_SPLIT.split(text) if sentence.strip()]


def _to_int(token: str) -> int:
    token = token.strip().lower().replace("-", " ")
    if token.isdigit():
        return int(token)
    return _WORD_NUMBERS.get(token, 0)


def _snippet(text: str, start: int, end: int, radius: int = 190) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    prefix = "... " if left > 0 else ""
    suffix = " ..." if right < len(text) else ""
    return f"{prefix}{text[left:right].strip()}{suffix}"


def _preceded_by_negation(text: str, start: int, window: int = 42) -> bool:
    return bool(_NEGATION.search(text[max(0, start - window) : start]))


def _months_elapsed(start_date: date, as_of: date) -> int:
    """Count service months on an inclusive calendar-month basis."""
    if as_of < start_date:
        return 0
    months = (as_of.year - start_date.year) * 12 + (as_of.month - start_date.month)
    if as_of.day >= start_date.day:
        months += 1
    return max(0, months)


# ---------------------------------------------------------------------------
# Detection rules
# ---------------------------------------------------------------------------


def _detect_termination(text: str) -> dict[str, Any] | None:
    for sentence in _sentences(text):
        trigger = _TERM_TRIGGER.search(sentence)
        if not trigger:
            continue

        notice_match = _NOTICE_DAYS.search(sentence) or _ANY_DAYS.search(sentence)
        notice_days = _to_int(notice_match.group("days")) if notice_match else 30
        if notice_days <= 0 or notice_days > 30:
            continue

        # A genuine early-termination fee or remaining-value obligation is a
        # substantive penalty and defeats the short-term contract conclusion.
        if _PENALTY.search(sentence) and not _NEGATION.search(sentence):
            continue

        return {
            "notice_days": notice_days,
            "evidence": _snippet(text, trigger.start(), trigger.end()),
            "confidence": 98 if notice_match else 90,
        }
    return None


def _detect_trial(text: str, deal: dict[str, Any], as_of: date) -> dict[str, Any] | None:
    days_match = _TRIAL_DAYS.search(text)
    refund_match = _TRIAL_REFUND.search(text)
    if not days_match or not refund_match:
        return None
    if _preceded_by_negation(text, refund_match.start()):
        return None

    trial_days = _to_int(days_match.group("days"))
    if trial_days < 60:
        return None

    start_date = deal["start_date"]
    trial_end = start_date + timedelta(days=trial_days)
    return {
        "trial_days": trial_days,
        "trial_end": trial_end,
        "evidence": _snippet(text, days_match.start(), refund_match.end()),
        "confidence": 99,
    }


def _detect_free_months(text: str) -> dict[str, Any] | None:
    for pattern in _FREE_MONTH_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        months = _to_int(match.group("months"))
        if months <= 0 or months > 24:
            continue
        if _preceded_by_negation(text, match.start(), window=24):
            continue
        return {
            "free_months": months,
            "evidence": _snippet(text, match.start(), match.end()),
            "confidence": 96,
        }
    return None


def _detect_feature(text: str) -> dict[str, Any] | None:
    value_match = _FEATURE_VALUE.search(text)
    if not value_match:
        return None

    value = float(value_match.group("value").replace(",", ""))
    if value <= 0:
        return None

    window_start = max(0, value_match.start() - 260)
    window_end = min(len(text), value_match.end() + 300)
    pending_match = _FEATURE_PENDING.search(text[window_start:window_end])
    if not pending_match:
        return None

    return {
        "feature_value": value,
        "evidence": _snippet(text, value_match.start(), value_match.end()),
        "confidence": 95,
    }


# ---------------------------------------------------------------------------
# Expected recognition calculation
# ---------------------------------------------------------------------------


def _expected_recognition(
    deal: dict[str, Any],
    elapsed_months: int,
    as_of: date,
    *,
    free_months: int = 0,
    feature_value: float = 0.0,
    trial_days: int = 0,
    termination: bool = False,
) -> float:
    """Return the supportable cumulative revenue under the detected facts."""
    tcv = float(deal["tcv"])
    term_months = max(1, int(deal["term_months"]))
    monthly_fee = float(deal["monthly_fee"])
    start_date = deal["start_date"]

    allocatable = max(0.0, tcv - feature_value)
    effective_term = max(1, term_months + free_months)
    service_months = min(elapsed_months, effective_term)
    expected = (allocatable / effective_term) * service_months

    if trial_days:
        trial_end = start_date + timedelta(days=trial_days)
        if as_of <= trial_end:
            expected = 0.0
        else:
            days_after_trial = (as_of - trial_end).days
            expected = min(expected, monthly_fee * days_after_trial / 30.4375)

    if termination:
        # The enforceable term is the notice period. Revenue cannot run ahead
        # of the monthly service actually delivered under a month-to-month right.
        expected = min(expected, monthly_fee * min(elapsed_months, term_months))

    return round(max(0.0, expected), 2)


def _severity_for(overstated_revenue: float) -> str:
    for threshold, label in SEVERITY_THRESHOLDS:
        if overstated_revenue >= threshold:
            return label
    return "Low"


def _status_for(findings: list[Finding], overstated_revenue: float) -> str:
    if not findings:
        return "Compliant"
    return "Exception" if overstated_revenue > 0.01 else "Review"


def _risk_score_for(overstated_revenue: float, findings: list[Finding]) -> int:
    if not findings:
        return 0
    base = round(overstated_revenue / 1_500)
    type_weight = min(8, len(findings) * 4)
    return int(max(5, min(99, base + type_weight)))


# ---------------------------------------------------------------------------
# Public scanner API
# ---------------------------------------------------------------------------


def scan_deal(deal: dict[str, Any], as_of: date = AS_OF_DATE) -> ScanResult:
    """Scan one arrangement against all four ASC 606 rules."""
    text = _normalize(str(deal["contract_text"]))
    start_date = deal["start_date"]
    elapsed_months = _months_elapsed(start_date, as_of)

    findings: list[Finding] = []
    free_months = 0
    feature_value = 0.0
    trial_days = 0
    termination = False

    termination_hit = _detect_termination(text)
    if termination_hit:
        termination = True
        only_termination = _expected_recognition(
            deal, elapsed_months, as_of, termination=True
        )
        finding = Finding(
            loophole_id="TERMINATION_CONVENIENCE",
            name=LOOPHOLE_LIBRARY["TERMINATION_CONVENIENCE"]["name"],
            citation=LOOPHOLE_LIBRARY["TERMINATION_CONVENIENCE"]["citation"],
            evidence=termination_hit["evidence"],
            impact=round(max(0.0, float(deal["recognized_to_date"]) - only_termination), 2),
            explanation=(
                f"Customer can exit on {termination_hit['notice_days']} days' notice "
                "without a substantive penalty. The ASC 606 enforceable term is "
                "limited to the notice period, so revenue recognized ahead of "
                "delivered monthly service is not supportable."
            ),
            confidence=termination_hit["confidence"],
            account_hint="Defer revenue to match the enforceable monthly term",
        )
        findings.append(finding)

    trial_hit = _detect_trial(text, deal, as_of)
    if trial_hit:
        trial_days = trial_hit["trial_days"]
        only_trial = _expected_recognition(
            deal, elapsed_months, as_of, trial_days=trial_days
        )
        finding = Finding(
            loophole_id="MONEY_BACK_TRIAL",
            name=LOOPHOLE_LIBRARY["MONEY_BACK_TRIAL"]["name"],
            citation=LOOPHOLE_LIBRARY["MONEY_BACK_TRIAL"]["citation"],
            evidence=trial_hit["evidence"],
            impact=round(max(0.0, float(deal["recognized_to_date"]) - only_trial), 2),
            explanation=(
                f"The {trial_days}-day trial is cancelable for a full refund and "
                f"runs through {trial_hit['trial_end']:%b %d, %Y}. No enforceable "
                "contract exists until conversion; all trial-period revenue must "
                "be deferred."
            ),
            confidence=trial_hit["confidence"],
            account_hint="Reverse trial-period subscription revenue",
        )
        findings.append(finding)

    free_hit = _detect_free_months(text)
    if free_hit:
        free_months = free_hit["free_months"]
        only_free = _expected_recognition(
            deal, elapsed_months, as_of, free_months=free_months
        )
        effective_term = int(deal["term_months"]) + free_months
        finding = Finding(
            loophole_id="UNDISCLOSED_FREE_MONTHS",
            name=LOOPHOLE_LIBRARY["UNDISCLOSED_FREE_MONTHS"]["name"],
            citation=LOOPHOLE_LIBRARY["UNDISCLOSED_FREE_MONTHS"]["citation"],
            evidence=free_hit["evidence"],
            impact=round(max(0.0, float(deal["recognized_to_date"]) - only_free), 2),
            explanation=(
                f"The side letter grants {free_months} free months that are absent "
                f"from the ERP. The transaction price must be allocated across "
                f"{effective_term} service months, not the {int(deal['term_months'])} "
                "paid months, which lowers monthly revenue recognition."
            ),
            confidence=free_hit["confidence"],
            account_hint="Reallocate transaction price across free service months",
        )
        findings.append(finding)

    feature_hit = _detect_feature(text)
    if feature_hit:
        feature_value = feature_hit["feature_value"]
        only_feature = _expected_recognition(
            deal, elapsed_months, as_of, feature_value=feature_value
        )
        finding = Finding(
            loophole_id="FEATURE_CONTINGENCY",
            name=LOOPHOLE_LIBRARY["FEATURE_CONTINGENCY"]["name"],
            citation=LOOPHOLE_LIBRARY["FEATURE_CONTINGENCY"]["citation"],
            evidence=feature_hit["evidence"],
            impact=round(max(0.0, float(deal["recognized_to_date"]) - only_feature), 2),
            explanation=(
                f"A distinct feature valued at ${feature_value:,.0f} is not yet "
                "delivered or accepted. Its allocated transaction price remains a "
                "separate performance obligation and must be deferred until the "
                "feature transfers to the customer."
            ),
            confidence=feature_hit["confidence"],
            account_hint="Defer undelivered feature allocation",
        )
        findings.append(finding)

    expected = _expected_recognition(
        deal,
        elapsed_months,
        as_of,
        free_months=free_months,
        feature_value=feature_value,
        trial_days=trial_days,
        termination=termination,
    )
    overstated = round(max(0.0, float(deal["recognized_to_date"]) - expected), 2)
    severity = _severity_for(overstated) if findings else "Compliant"
    status = _status_for(findings, overstated)
    risk_score = _risk_score_for(overstated, findings)

    return ScanResult(
        deal=deal,
        findings=findings,
        elapsed_months=elapsed_months,
        overstated_revenue=overstated,
        expected_recognized=expected,
        severity=severity,
        status=status,
        risk_score=risk_score,
    )


def scan_all(
    deals: list[dict[str, Any]],
    as_of: date = AS_OF_DATE,
) -> list[ScanResult]:
    """Scan a portfolio and sort exceptions by exposure, then deal ID."""
    results = [scan_deal(deal, as_of=as_of) for deal in deals]
    return sorted(
        results,
        key=lambda result: (
            0 if result.has_exception else 1,
            -result.overstated_revenue,
            result.deal_id,
        ),
    )


def scan_custom_deal(
    *,
    contract_text: str,
    customer: str,
    erp_source: str,
    start_date: date,
    term_months: int,
    monthly_fee: float,
    tcv: float,
    recognized_to_date: float,
    as_of: date = AS_OF_DATE,
) -> ScanResult:
    """Build a sandbox deal from user input and run the same deterministic rules."""
    deal: dict[str, Any] = {
        "deal_id": "SBX-001",
        "customer": customer.strip() or "Sandbox Customer",
        "industry": "Live contract sandbox",
        "erp_source": erp_source,
        "contract_id": "SANDBOX-001",
        "document_type": "Pasted contract excerpt",
        "owner": "Sandbox user",
        "region": "Sandbox",
        "start_date": start_date,
        "term_months": max(1, int(term_months)),
        "monthly_fee": max(0.0, float(monthly_fee)),
        "tcv": max(0.0, float(tcv)),
        "billed_to_date": max(0.0, float(recognized_to_date)),
        "recognized_to_date": max(0.0, float(recognized_to_date)),
        "deferred_revenue": max(0.0, float(tcv) - float(recognized_to_date)),
        "contract_text": contract_text,
        "erp_memo": "Live sandbox input - no ERP write-back performed.",
    }
    return scan_deal(deal, as_of=as_of)


def portfolio_summary(results: list[ScanResult]) -> dict[str, float | int]:
    """Return headline metrics used by the executive KPI cards."""
    exceptions = [result for result in results if result.has_exception]
    total_overstated = round(sum(result.overstated_revenue for result in exceptions), 2)
    total_recognized = round(sum(result.recognized_to_date for result in results), 2)
    return {
        "arrangements": len(results),
        "exceptions": len(exceptions),
        "critical": sum(1 for result in exceptions if result.severity == "Critical"),
        "high": sum(1 for result in exceptions if result.severity == "High"),
        "medium": sum(1 for result in exceptions if result.severity == "Medium"),
        "compliant": sum(1 for result in results if result.status == "Compliant"),
        "total_overstated": total_overstated,
        "total_recognized": total_recognized,
        "compliance_rate": round(
            (sum(1 for result in results if result.status == "Compliant") / len(results) * 100)
            if results
            else 0.0,
            1,
        ),
    }
