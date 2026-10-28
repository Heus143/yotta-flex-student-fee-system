# Student Tuition Fee Management and Reconciliation System

A Python + SQLite + Pandas implementation aligned to the YottaFlex AI candidate project brief.

## Scope implemented
- Required entities: Student, Program, FeeSchedule, Enrollment, Invoice, InvoiceLine, Scholarship, Eligibility, Payment, PaymentAllocation, Refund.
- Deterministic synthetic data generation with seed `20261022`.
- Configurable starter/full dataset sizes.
- Program/term fee schedules, enrollment, invoices and invoice lines.
- Scholarship eligibility and awards, payment allocation, refunds, late fees, withdrawals and cancellations.
- Five labelled anomaly classes in a separate `ground_truth.csv`.
- CSV exports, SQLite database, JSON metadata, validation report and reproducibility checksums.

## Requirements
- Python 3.10+
- Dependencies: `pandas`, `numpy` (install with `pip install -r requirements.txt`)
- `pytest` is used for tests.

## Quick start
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_project.py --scale starter
```

Generate the full requested baseline:
```bash
python run_project.py --scale full
```

Use custom counts:
```bash
python run_project.py --students 100 --programs 5 --invoices 300 --scholarships 150 --payments 500
```

Validate an existing output directory:
```bash
python run_project.py --validate-only
```

Run tests:
```bash
pytest -q
```

## Scale settings
- `starter`: 100 students, 5 programs, 300 invoices, 150 scholarship awards, 500 payments.
- `full`: 10,000 students, 20 programs, 30,000 invoices, 15,000 scholarship awards, 50,000 payments.
- All generated data uses seed `20261022` by default. The scale controls volume, not the underlying generation rules.

## Output
Generated files are written to `output/`:
- `students.csv`, `programs.csv`, `fee_schedules.csv`, `enrollments.csv`
- `invoices.csv`, `invoice_lines.csv`, `scholarships.csv`, `eligibility.csv`
- `payments.csv`, `payment_allocations.csv`, `refunds.csv`
- `ground_truth.csv` — labelled injected anomalies/expected outcomes; do not use as input features.
- `validation_summary.json`, `source_manifest.json`, `checksums.json`
- `student_fee_system.sqlite` — relational database with primary and foreign key constraints.

## Core accounting conventions
- Money is stored in decimal-like two-decimal numeric values. Production financial systems should use integer minor units or a fixed-precision decimal type; SQLite `REAL` is used here for a portable synthetic-data exercise.
- Invoice gross amount = sum of invoice lines.
- Scholarship credit is represented by a negative invoice line and is capped at eligible tuition fees in the valid baseline.
- Invoice balance = invoice gross total + applicable late fees - valid payment allocations - valid credits/refunds, subject to documented event state.
- Payment allocation must not exceed payment amount or invoice-line outstanding amount in valid records.
- Refunds must not exceed net paid amount in valid records.
- Deliberate negative scenarios are tagged in `ground_truth.csv`; the validation process reports them rather than silently altering unrelated rows.
- State transitions are recorded in `events.csv` to preserve a simple audit trail.

## Important implementation notes / limitations
- This is synthetic data only; no real student data or external dataset is used.
- Fee schedules are effective-dated by program and term.
- The generated edge cases are intentionally invalid and clearly labelled. Baseline records are generated first.
- The duplicate-invoice scenario is intentionally introduced after baseline creation and marked in ground truth.
- A generated dataset is a reviewable synthetic test fixture, not a legally compliant production billing platform.
- Cancellation/refund policy, late-fee rate, scholarship eligibility thresholds, and term dates are explicit assumptions in `config.py`. Update them only with documented rationale.
- Late fees are calculated using a fixed as-of date of 2026-10-28, at 1.5% of overdue outstanding balance, capped at USD 75. This is a synthetic evaluation assumption, not a dynamically updated current date.

## AI assistance disclosure
Keep a copy of the actual prompts used with every AI tool in `docs/AI_PROMPT_HISTORY.md`. Add your own prompts and note what you personally reviewed, changed, ran, and validated. Do not claim tests passed unless you ran them.

## Suggested review sequence
1. Read `docs/DATA_DICTIONARY.md`.
2. Read `docs/RELATIONSHIPS_AND_RULES.md`.
3. Run the starter scale and inspect `output/validation_summary.json`.
4. Run tests with `pytest -q`.
5. Run twice with the same seed and compare `output/checksums.json`.
6. Inspect each anomaly in `output/ground_truth.csv` and confirm the corresponding validation finding.
