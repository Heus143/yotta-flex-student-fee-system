import sqlite3

conn = sqlite3.connect("output/student_fee_system.sqlite")

query = """
SELECT
    p.payment_id,
    p.amount AS payment_amount,
    a.allocated_amount,
    a.status,
    a.invoice_id
FROM Payment p
JOIN PaymentAllocation a ON p.payment_id = a.payment_id
WHERE p.payment_id = 'PAY-2026-000001'
"""

for row in conn.execute(query):
    print(row)

conn.close()
