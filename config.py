"""Documented assumptions and generation scales for the assignment."""
SEED = 20261022
TERM = "TERM-2026-FALL"
TERM_START = "2026-08-24"
TERM_END = "2026-12-18"
INVOICE_DUE_DAYS = 30
LATE_FEE_RATE = 0.015
LATE_FEE_CAP = 75.00
SCHOLARSHIP_ELIGIBILITY_GPA_MIN = 2.5
SCHOLARSHIP_MAX_PERCENT = 0.50
CURRENCY = "USD"

SCALES = {
    "starter": {"students": 100, "programs": 5, "invoices": 300, "scholarships": 150, "payments": 500},
    "full": {"students": 10000, "programs": 20, "invoices": 30000, "scholarships": 15000, "payments": 50000},
}
