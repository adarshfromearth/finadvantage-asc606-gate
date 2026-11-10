"""Sample contract and ERP ledger data for the FinAdvantage ASC 606 demo.

Each deal pairs a structured ERP record (NetSuite / QuickBooks Online) with an
unstructured contract excerpt or sales side-letter. Seven arrangements contain
an ASC 606 loophole; five are clean controls.

The data is entirely fictional and is intended for demonstration purposes only.
"""

from __future__ import annotations

from datetime import date
from typing import Any

# October 2026 month-end close.
AS_OF_DATE = date(2026, 10, 31)

DEALS: list[dict[str, Any]] = [
    {
        "deal_id": "FA-1001",
        "customer": "Northwind Analytics",
        "industry": "Data & Analytics",
        "erp_source": "NetSuite",
        "contract_id": "MSA-NWA-2026-014",
        "document_type": "Executed MSA + Order Form (PDF)",
        "owner": "D. Whitfield",
        "region": "North America",
        "start_date": date(2026, 1, 1),
        "term_months": 36,
        "monthly_fee": 18_500.0,
        "tcv": 666_000.0,
        "billed_to_date": 333_000.0,
        "recognized_to_date": 333_000.0,
        "deferred_revenue": 0.0,
        "contract_text": """
MASTER SUBSCRIPTION AGREEMENT - EXECUTED ORDER FORM
Customer: Northwind Analytics, Inc.
Effective Date: January 1, 2026
Subscription Term: 36 months
Monthly Subscription Fee: $18,500
Total Contract Value: $666,000
Payment Terms: Annual in advance

2.4 TERMINATION FOR CONVENIENCE. Customer may terminate this Agreement for
convenience, in whole or in part, at any time upon thirty (30) days' prior
written notice. No early termination fee, unwind charge, or minimum commitment
shall apply to any such termination.

2.5 EFFECT OF TERMINATION. Prepaid fees for the terminated period shall be
refunded on a pro-rata basis within thirty (30) days after the termination date.

3.1 SERVICES. FinAdvantage will provide the Analytics Cloud subscription and
standard support for the Subscription Term.
""",
        "erp_memo": (
            "NetSuite revenue schedule recognizes 50% of TCV over the first 18 "
            "months. No deferral was posted for the customer's termination right."
        ),
    },
    {
        "deal_id": "FA-1002",
        "customer": "Lumen Retail Group",
        "industry": "Retail & E-commerce",
        "erp_source": "QuickBooks Online",
        "contract_id": "SOW-LRG-2026-031",
        "document_type": "Order Form + Sales Side-Letter (Email)",
        "owner": "M. Okafor",
        "region": "EMEA",
        "start_date": date(2026, 4, 1),
        "term_months": 24,
        "monthly_fee": 100_000.0,
        "tcv": 2_400_000.0,
        "billed_to_date": 700_000.0,
        "recognized_to_date": 700_000.0,
        "deferred_revenue": 0.0,
        "contract_text": """
ORDER FORM - LUMEN RETAIL GROUP
Effective Date: April 1, 2026
Subscription Term: 24 months
Monthly Subscription Fee: $100,000
Total Contract Value: $2,400,000
Payment Terms: Annual in advance

SALES SIDE-LETTER - EMAIL EXCERPT (NOT IN NETSUITE)
From: Marcus Okafor, Account Executive
Date: March 28, 2026
Subject: Lumen - Q1 close concession

"Legal has approved the order form as written. To get this signed before
quarter-end, the first six (6) months are at no charge. It is a one-time
concession, so please do not add it to the order form or the NetSuite billing
schedule - we will true-up at the anniversary."

The executed order form contains no reference to the side-letter, the free
months, or any price concession.
""",
        "erp_memo": (
            "QuickBooks bills $100,000 per month from April 2026 and recognizes "
            "revenue on the same cadence. The six-month concession is absent "
            "from the billing schedule."
        ),
    },
    {
        "deal_id": "FA-1003",
        "customer": "Cobalt Health Systems",
        "industry": "Healthcare",
        "erp_source": "NetSuite",
        "contract_id": "ADD-CBH-2026-007",
        "document_type": "90-Day Trial Addendum (PDF)",
        "owner": "S. Iyer",
        "region": "North America",
        "start_date": date(2026, 8, 15),
        "term_months": 24,
        "monthly_fee": 45_000.0,
        "tcv": 1_080_000.0,
        "billed_to_date": 135_000.0,
        "recognized_to_date": 135_000.0,
        "deferred_revenue": 0.0,
        "contract_text": """
90-DAY MONEY-BACK TRIAL ADDENDUM
Customer: Cobalt Health Systems
Trial Start: August 15, 2026
Trial End: November 13, 2026
Subscription Term (following conversion): 24 months
Monthly Subscription Fee: $45,000
Total Contract Value: $1,080,000

1. TRIAL. During the 90-day trial period, Customer may cancel for any reason
and receive a full refund of all fees paid. The subscription does not become
non-cancelable until Customer provides written conversion notice after the
Trial End.

2. REVENUE. Partner shall not invoice or recognize subscription revenue before
conversion. No performance obligation is considered satisfied during the trial.
""",
        "erp_memo": (
            "NetSuite created a 24-month revenue plan on the trial start date and "
            "has recognized three months of subscription revenue during the trial."
        ),
    },
    {
        "deal_id": "FA-1004",
        "customer": "Vertex Logistics",
        "industry": "Transportation & Logistics",
        "erp_source": "QuickBooks Online",
        "contract_id": "OF-VLX-2025-118",
        "document_type": "Order Form + Product Schedule (PDF)",
        "owner": "R. Castellanos",
        "region": "North America",
        "start_date": date(2025, 5, 1),
        "term_months": 36,
        "monthly_fee": 30_000.0,
        "tcv": 1_080_000.0,
        "billed_to_date": 540_000.0,
        "recognized_to_date": 540_000.0,
        "deferred_revenue": 0.0,
        "contract_text": """
ORDER FORM - VERTEX LOGISTICS
Effective Date: May 1, 2025
Subscription Term: 36 months
Monthly Subscription Fee: $30,000
Total Contract Value: $1,080,000

PRODUCT SCHEDULE
Core Transportation Management subscription is live.

The Advanced Route Optimization module ("ARO"), valued at $240,000, is
scheduled for delivery in Q2 2027. ARO is not yet available, and Customer's
payment obligation for ARO is contingent on written acceptance of the ARO
module. No ARO functionality has been delivered as of the current period end.
""",
        "erp_memo": (
            "QuickBooks recognizes the full $1,080,000 contract value straight-line "
            "over 36 months, including the undelivered ARO module."
        ),
    },
    {
        "deal_id": "FA-1005",
        "customer": "Meridian Fintech",
        "industry": "Financial Services",
        "erp_source": "NetSuite",
        "contract_id": "MSA-MFT-2026-022",
        "document_type": "Executed MSA (PDF)",
        "owner": "J. Park",
        "region": "North America",
        "start_date": date(2026, 3, 1),
        "term_months": 24,
        "monthly_fee": 34_000.0,
        "tcv": 816_000.0,
        "billed_to_date": 408_000.0,
        "recognized_to_date": 408_000.0,
        "deferred_revenue": 0.0,
        "contract_text": """
MASTER SUBSCRIPTION AGREEMENT - MERIDIAN FINTECH
Effective Date: March 1, 2026
Subscription Term: 24 months
Monthly Subscription Fee: $34,000
Total Contract Value: $816,000

7.2 TERMINATION WITHOUT CAUSE. Either party may terminate this Agreement at
any time without cause upon fifteen (15) days' prior written notice. No
termination fee, unwind charge, or minimum commitment applies.

7.3 REFUNDS. Prepaid fees for the terminated period shall be refunded within
30 days after the effective date of termination.

7.4 SURVIVAL. Confidentiality and indemnity obligations survive termination.
""",
        "erp_memo": (
            "NetSuite recognized twelve months of subscription revenue in the "
            "first eight months of the arrangement."
        ),
    },
    {
        "deal_id": "FA-1006",
        "customer": "Apex Manufacturing",
        "industry": "Manufacturing",
        "erp_source": "QuickBooks Online",
        "contract_id": "OF-APX-2026-044",
        "document_type": "Trial Order Form + Refund Guarantee (PDF)",
        "owner": "T. Brennan",
        "region": "North America",
        "start_date": date(2026, 8, 20),
        "term_months": 30,
        "monthly_fee": 19_500.0,
        "tcv": 585_000.0,
        "billed_to_date": 58_500.0,
        "recognized_to_date": 58_500.0,
        "deferred_revenue": 0.0,
        "contract_text": """
TRIAL ORDER FORM - APEX MANUFACTURING
Trial Start: August 20, 2026
Trial End: November 18, 2026
Subscription Term (upon conversion): 30 months
Monthly Subscription Fee: $19,500
Total Contract Value: $585,000

CUSTOMER GUARANTEE. Customer has a 90-day money-back guarantee. If Customer is
not satisfied for any reason during the trial, Customer may cancel and receive
a full refund of all amounts paid. The arrangement is cancelable at will until
the earlier of written conversion or the Trial End.

The order form states that no revenue should be recognized until the customer
converts to a paid subscription.
""",
        "erp_memo": (
            "QuickBooks recognizes $19,500 per month from the trial start date. "
            "Three monthly entries have been posted through October 2026."
        ),
    },
    {
        "deal_id": "FA-1007",
        "customer": "Solstice Media",
        "industry": "Media & Entertainment",
        "erp_source": "NetSuite",
        "contract_id": "SOW-SLM-2026-009",
        "document_type": "Order Form + AE Email Side-Letter",
        "owner": "L. Chen",
        "region": "APAC",
        "start_date": date(2026, 1, 1),
        "term_months": 24,
        "monthly_fee": 52_000.0,
        "tcv": 1_248_000.0,
        "billed_to_date": 520_000.0,
        "recognized_to_date": 520_000.0,
        "deferred_revenue": 0.0,
        "contract_text": """
ORDER FORM - SOLSTICE MEDIA
Effective Date: January 1, 2026
Subscription Term: 24 months
Monthly Subscription Fee: $52,000
Total Contract Value: $1,248,000

SALES SIDE-LETTER - EMAIL EXCERPT
From: L. Chen, Senior Account Executive
Subject: Solstice - onboarding incentive
Date: December 19, 2025

"Finance approved the 24-month term at $52k/month. As discussed, the first
five (5) months of subscription fees are waived and free of charge as an
onboarding incentive. Please don't reflect the waiver in NetSuite - we'll
handle it as a billing credit later."

The executed order form does not disclose the waiver. NetSuite bills and
recognizes $52,000 per month from January 2026.
""",
        "erp_memo": (
            "NetSuite billing schedule begins January 2026 at the full $52,000 "
            "monthly rate. No concession or credit memo is recorded."
        ),
    },
    {
        "deal_id": "FA-1008",
        "customer": "Ironclad Security",
        "industry": "Cybersecurity",
        "erp_source": "NetSuite",
        "contract_id": "MSA-ICS-2026-003",
        "document_type": "Executed MSA + Order Form (PDF)",
        "owner": "A. Novak",
        "region": "North America",
        "start_date": date(2026, 2, 1),
        "term_months": 24,
        "monthly_fee": 26_000.0,
        "tcv": 624_000.0,
        "billed_to_date": 624_000.0,
        "recognized_to_date": 234_000.0,
        "deferred_revenue": 390_000.0,
        "contract_text": """
MASTER SUBSCRIPTION AGREEMENT - IRONCLAD SECURITY
Effective Date: February 1, 2026
Subscription Term: 24 months
Monthly Subscription Fee: $26,000
Total Contract Value: $624,000
Payment Terms: Annual in advance, non-cancelable

3.1 TERM. The Initial Term is 24 months and renews annually unless either party
gives 60 days' notice before renewal.

3.2 TERMINATION FOR CAUSE. Either party may terminate for material breach upon
30 days' written notice and failure to cure.

3.3 FEES. All fees are non-refundable. No free months, side letters, or price
concessions were granted.

4.1 DELIVERY. The Advanced Analytics module, valued at $120,000, was delivered
and accepted on March 15, 2026. All performance obligations are live.
""",
        "erp_memo": (
            "NetSuite recognizes revenue straight-line over 24 months. Deferred "
            "revenue reconciles to the annual billing schedule."
        ),
    },
    {
        "deal_id": "FA-1009",
        "customer": "BlueRidge Healthcare",
        "industry": "Healthcare",
        "erp_source": "QuickBooks Online",
        "contract_id": "OF-BRH-2026-017",
        "document_type": "Order Form (PDF)",
        "owner": "P. Raman",
        "region": "North America",
        "start_date": date(2026, 5, 1),
        "term_months": 12,
        "monthly_fee": 9_500.0,
        "tcv": 114_000.0,
        "billed_to_date": 114_000.0,
        "recognized_to_date": 57_000.0,
        "deferred_revenue": 57_000.0,
        "contract_text": """
ORDER FORM - BLUERIDGE HEALTHCARE
Effective Date: May 1, 2026
Subscription Term: 12 months
Monthly Subscription Fee: $9,500
Total Contract Value: $114,000
Payment Terms: Annual in advance

2.1 FEES. Fees are non-refundable and the contract is non-cancelable except
for cause.

2.2 TERMINATION. Either party may terminate for uncured material breach after
30 days' written notice.

2.3 RENEWAL. The term renews for successive 12-month periods unless either
party provides 60 days' notice.

2.4 DELIVERY. Implementation services were completed and accepted on
April 28, 2026. No contingencies remain.
""",
        "erp_memo": (
            "QuickBooks amortizes the annual invoice over 12 months. Deferred "
            "revenue equals the unearned portion of the invoice."
        ),
    },
    {
        "deal_id": "FA-1010",
        "customer": "Summit Education Group",
        "industry": "Education",
        "erp_source": "NetSuite",
        "contract_id": "MSA-SEG-2026-001",
        "document_type": "Executed MSA (PDF)",
        "owner": "K. Alvarez",
        "region": "North America",
        "start_date": date(2026, 1, 1),
        "term_months": 36,
        "monthly_fee": 14_000.0,
        "tcv": 504_000.0,
        "billed_to_date": 504_000.0,
        "recognized_to_date": 140_000.0,
        "deferred_revenue": 364_000.0,
        "contract_text": """
MASTER SUBSCRIPTION AGREEMENT - SUMMIT EDUCATION GROUP
Effective Date: January 1, 2026
Subscription Term: 36 months
Monthly Subscription Fee: $14,000
Total Contract Value: $504,000
Payment Terms: Annual in advance

5.1 TERM. The Initial Term is 36 months. Thereafter, the Agreement renews
annually unless either party gives 90 days' notice.

5.2 TERMINATION FOR CONVENIENCE. Customer may terminate for convenience only
after the Initial Term upon ninety (90) days' prior written notice and payment
of an early termination fee equal to 50% of the remaining fees.

5.3 TERMINATION FOR CAUSE. Either party may terminate for uncured material
breach upon 30 days' notice.

5.4 FEES. Fees are non-refundable during the Initial Term.
""",
        "erp_memo": (
            "NetSuite recognizes revenue straight-line over 36 months. The "
            "post-term convenience right contains a substantive termination fee."
        ),
    },
    {
        "deal_id": "FA-1011",
        "customer": "Harborline Insurance",
        "industry": "Insurance",
        "erp_source": "QuickBooks Online",
        "contract_id": "OF-HLI-2026-058",
        "document_type": "Order Form + SLA (PDF)",
        "owner": "N. Patel",
        "region": "EMEA",
        "start_date": date(2026, 6, 1),
        "term_months": 18,
        "monthly_fee": 21_000.0,
        "tcv": 378_000.0,
        "billed_to_date": 378_000.0,
        "recognized_to_date": 105_000.0,
        "deferred_revenue": 273_000.0,
        "contract_text": """
ORDER FORM - HARBORLINE INSURANCE
Effective Date: June 1, 2026
Subscription Term: 18 months
Monthly Subscription Fee: $21,000
Total Contract Value: $378,000
Payment Terms: Annual in advance

6.1 TERM. 18-month non-cancelable Initial Term.

6.2 TERMINATION. Termination is permitted only for uncured material breach
following 30 days' written notice.

6.3 SERVICE LEVELS. Service credits are the sole remedy for availability
shortfalls and do not create a refund or termination right.

6.4 FEES. Fees are non-refundable. No trial or refund period applies.
""",
        "erp_memo": (
            "QuickBooks recognizes the arrangement straight-line over 18 months. "
            "No side agreements or billing exceptions were identified."
        ),
    },
    {
        "deal_id": "FA-1012",
        "customer": "Quantum Robotics",
        "industry": "Robotics & AI",
        "erp_source": "NetSuite",
        "contract_id": "MSA-QRB-2025-088",
        "document_type": "Executed MSA + Order Form (PDF)",
        "owner": "E. Fontaine",
        "region": "North America",
        "start_date": date(2025, 11, 1),
        "term_months": 24,
        "monthly_fee": 33_000.0,
        "tcv": 792_000.0,
        "billed_to_date": 792_000.0,
        "recognized_to_date": 396_000.0,
        "deferred_revenue": 396_000.0,
        "contract_text": """
MASTER SUBSCRIPTION AGREEMENT - QUANTUM ROBOTICS
Effective Date: November 1, 2025
Subscription Term: 24 months
Monthly Subscription Fee: $33,000
Total Contract Value: $792,000
Payment Terms: Annual in advance

2.1 TERM. 24-month non-cancelable Initial Term, auto-renewing for 12 months.

2.2 TERMINATION. Either party may terminate only for uncured material breach
upon 30 days' notice.

2.3 DELIVERY. All licensed modules, including the Robotics Fleet Analytics
add-on, were delivered and accepted on October 28, 2025. No feature
contingencies remain.

2.4 FEES. Fees are non-refundable. No free months or sales side-letters exist.
""",
        "erp_memo": (
            "NetSuite recognizes revenue straight-line over 24 months. Deferred "
            "revenue agrees to the remaining contractual service period."
        ),
    },
]


def get_deals() -> list[dict[str, Any]]:
    """Return a defensive copy of the sample deal portfolio."""
    return [dict(deal) for deal in DEALS]
