# Relationships, lifecycle, and business rules

## Cardinality
- Program 1:N FeeSchedule.
- Student 1:N Enrollment; Program 1:N Enrollment. Student and Program are N:M over time through Enrollment.
- Student 1:N Invoice; Enrollment 1:N Invoice in this synthetic model, with the intended business rule of one invoice per enrollment and term billing event.
- Invoice 1:N InvoiceLine.
- Student 1:N Scholarship; Scholarship 1:1 Eligibility record in this generator.
- Student 1:N Payment.
- Payment 1:N PaymentAllocation; Invoice 1:N PaymentAllocation; InvoiceLine 1:N PaymentAllocation. Payments and invoices are N:M through PaymentAllocation.
- Payment 1:N Refund.
- Any business entity 1:N Event through the polymorphic audit reference (validated at application level).

## Lifecycle assumptions
- Enrollment: ENROLLED -> WITHDRAWN or CANCELLED. Withdrawal/cancellation dates cannot precede enrollment.
- Invoice: OPEN -> PARTIAL -> PAID, or OPEN/PARTIAL -> CANCELLED subject to policy. This generator retains an initial status and calculated balance for the synthetic baseline.
- Payment: PENDING -> SETTLED or FAILED. Only SETTLED payments can be allocated.
- Scholarship: evaluated -> AWARDED or INELIGIBLE.
- Refund: PENDING -> APPROVED or REJECTED.
- Events are append-only; corrections should create new events rather than overwrite prior event history.

## Documented calculation rules
1. Fee schedules are keyed by program and term and must be effective on the invoice date.
2. Invoices are created from the fee lines for an eligible enrollment. Optional lab fees may be omitted deterministically by the seeded generator.
3. Scholarship eligibility: GPA >= 2.50 and enrollment status ENROLLED.
4. Valid scholarship awards are limited to 50% of eligible tuition. The synthetic anomaly deliberately breaks this rule and is labelled.
5. Scholarship credit is recorded as a negative invoice line; invoice gross is the sum of invoice lines.
6. A payment allocation must be positive and must not exceed either available payment amount or the outstanding amount of the target invoice line.
7. A refund must not exceed the payment's net amount paid after earlier refunds.
8. Late fee assumption: 1.5% of overdue outstanding amount, capped at USD 75. The generator records a late-fee field; the full scale's late-fee evaluation can be extended using a chosen as-of date.
9. Withdrawal/cancellation treatment must follow a documented institutional refund policy. This starter project records withdrawal events and status but does not invent a universal tuition refund policy.
10. Reconciliation compares source ledger totals to stored invoice balance. An injected mismatch is expected and explicitly labelled.

## Required anomaly scenarios
- ALLOCATION_EXCEEDS_PAYMENT
- SCHOLARSHIP_EXCEEDS_ELIGIBLE_FEES
- DUPLICATE_INVOICE
- REFUND_EXCEEDS_NET_PAID
- BALANCE_DISAGREES_WITH_LEDGER

`ground_truth.csv/json` is a separate evaluation artifact and must never be joined into model input features during detection.
