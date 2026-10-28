# Data Dictionary

All dates use ISO `YYYY-MM-DD`. Monetary amounts are in USD for this synthetic exercise and rounded to 2 decimals. Required fields are non-null unless the field is explicitly optional. IDs are immutable text keys.

| Entity | Field | Type | Required | Allowed values / validation | Key / uniqueness |
|---|---|---|---|---|---|
| Student | student_id | string | Yes | `STU-` plus six digits | PK, unique |
| Student | first_name, last_name | string | Yes | Non-empty | — |
| Student | email | string | Yes | Synthetic `example.test` address | Unique |
| Student | date_of_birth | date | Yes | ISO date; before creation date | — |
| Student | gpa | decimal | Yes | 0.00–4.00 | — |
| Student | status | enum | Yes | ACTIVE, INACTIVE | — |
| Student | created_at | date | Yes | ISO date | — |
| Program | program_id | string | Yes | `PRG-` plus six digits | PK |
| Program | program_name | string | Yes | Non-empty | — |
| Program | level | enum | Yes | UNDERGRADUATE, POSTGRADUATE, CERTIFICATE | — |
| Program | standard_tuition | money | Yes | >= 0 | USD |
| Program | active | boolean | Yes | true/false | — |
| FeeSchedule | fee_schedule_id | string | Yes | Stable fee identifier | PK |
| FeeSchedule | program_id | string | Yes | Must exist in Program | FK |
| FeeSchedule | term_id | string | Yes | `TERM-YYYY-SEASON` | — |
| FeeSchedule | fee_type | enum | Yes | TUITION, REGISTRATION, LAB | — |
| FeeSchedule | amount | money | Yes | >= 0 | USD |
| FeeSchedule | effective_from, effective_to | date | Yes | start <= end | — |
| FeeSchedule | required | boolean | Yes | true/false | — |
| Enrollment | enrollment_id | string | Yes | `ENR-` plus six digits | PK |
| Enrollment | student_id, program_id | string | Yes | Must exist in parent table | FK |
| Enrollment | term_id | string | Yes | Must match fee term for billing | — |
| Enrollment | enrollment_date | date | Yes | Within plausible registration window | — |
| Enrollment | status | enum | Yes | ENROLLED, WITHDRAWN, CANCELLED | — |
| Enrollment | withdrawal_date | date/string | No | Required for WITHDRAWN; >= enrollment date | — |
| Invoice | invoice_id | string | Yes | `INV-<student-id>-2026-<counter>` | PK |
| Invoice | student_id, enrollment_id | string | Yes | Must match valid parent records | FK |
| Invoice | term_id | string | Yes | Term being billed | — |
| Invoice | invoice_date, due_date | date | Yes | due_date >= invoice_date | — |
| Invoice | status | enum | Yes | OPEN, PAID, PARTIAL, CANCELLED (extension) | — |
| Invoice | gross_amount | money | Yes | Sum of invoice lines, including negative credits | Derived |
| Invoice | scholarship_credit | money | Yes | Sum of scholarship credits | Derived |
| Invoice | late_fee | money | Yes | >= 0; rate/cap documented in config | Derived |
| Invoice | balance | money | Yes | Must reconcile to ledger | Derived; deliberately mismatched case labelled |
| InvoiceLine | invoice_line_id | string | Yes | Stable line ID | PK |
| InvoiceLine | invoice_id | string | Yes | Must exist in Invoice | FK |
| InvoiceLine | fee_schedule_id | string | No | Blank for scholarship credit; otherwise valid fee schedule | Optional FK |
| InvoiceLine | line_type, description | string | Yes | Fee category / explanation | — |
| InvoiceLine | quantity | decimal | Yes | > 0 | — |
| InvoiceLine | unit_amount, line_amount | money | Yes | line_amount = quantity × unit_amount | USD |
| InvoiceLine | eligible_for_scholarship | boolean | Yes | true/false | — |
| Scholarship | scholarship_id | string | Yes | `SCH-2026-` plus six digits | PK |
| Scholarship | student_id | string | Yes | Must exist in Student | FK |
| Scholarship | term_id | string | Yes | Award term | — |
| Scholarship | scholarship_type | enum | Yes | MERIT, NEED_BASED, PROGRAM_GRANT | — |
| Scholarship | award_amount | money | Yes | >= 0; cannot exceed eligible fee in valid records | USD |
| Scholarship | award_date | date | Yes | ISO date | — |
| Scholarship | status | enum | Yes | AWARDED, INELIGIBLE | — |
| Eligibility | eligibility_id | string | Yes | `ELG-` plus six digits | PK |
| Eligibility | scholarship_id, student_id, program_id | string | Yes | Must exist in respective parent | FK |
| Eligibility | term_id | string | Yes | Must align to award and enrollment | — |
| Eligibility | eligible | boolean | Yes | Derived from GPA threshold and enrollment status | Grounded label |
| Eligibility | rule_code | string | Yes | GPA_AND_ENROLLED, GPA_BELOW_MIN, WITHDRAWN | — |
| Eligibility | evaluated_at | date | Yes | ISO date | — |
| Payment | payment_id | string | Yes | `PAY-2026-` plus six digits | PK |
| Payment | student_id | string | Yes | Must exist in Student | FK |
| Payment | payment_date | date | Yes | ISO date | — |
| Payment | amount | money | Yes | >= 0 | USD |
| Payment | method | enum | Yes | CARD, BANK_TRANSFER, CASH, UPI | — |
| Payment | status | enum | Yes | SETTLED (extension: PENDING, FAILED) | — |
| Payment | reference | string | Yes | Unique synthetic reference | Unique |
| PaymentAllocation | allocation_id | string | Yes | `ALLOC-<payment-id>-01` | PK |
| PaymentAllocation | payment_id, invoice_id, invoice_line_id | string | Yes | Must exist in parent tables | FK |
| PaymentAllocation | allocated_amount | money | Yes | > 0 and total <= payment amount in valid data | USD |
| PaymentAllocation | allocated_at | date | Yes | ISO date | — |
| PaymentAllocation | status | enum | Yes | POSTED (extension: REVERSED) | — |
| Refund | refund_id | string | Yes | `RFD-` plus six digits | PK |
| Refund | payment_id, student_id | string | Yes | Must exist in parent tables | FK |
| Refund | refund_date | date | Yes | >= payment date | — |
| Refund | amount | money | Yes | >= 0; cumulative refund <= net paid in valid data | USD |
| Refund | reason | enum | Yes | CUSTOMER_REQUEST | — |
| Refund | status | enum | Yes | APPROVED (extension: PENDING, REJECTED) | — |

## Additional audit entity
`Event(event_id, entity_type, entity_id, event_type, event_date, details)` stores append-only synthetic lifecycle descriptions. The entity ID is polymorphic, so application-level validation checks its target.
