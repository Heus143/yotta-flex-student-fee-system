"""Synthetic student fee workflow: deterministic generation, ledger rules, exports and validation."""
from __future__ import annotations
import argparse, hashlib, json, random, sqlite3
from pathlib import Path
from datetime import date, timedelta
import numpy as np
import pandas as pd
from config import *

ENTITY_FILES = {
    "Student": "students.csv", "Program": "programs.csv", "FeeSchedule": "fee_schedules.csv",
    "Enrollment": "enrollments.csv", "Invoice": "invoices.csv", "InvoiceLine": "invoice_lines.csv",
    "Scholarship": "scholarships.csv", "Eligibility": "eligibility.csv", "Payment": "payments.csv",
    "PaymentAllocation": "payment_allocations.csv", "Refund": "refunds.csv"
}
COLUMNS = {
"Student": ["student_id","first_name","last_name","email","date_of_birth","gpa","status","created_at"],
"Program": ["program_id","program_name","level","standard_tuition","active"],
"FeeSchedule": ["fee_schedule_id","program_id","term_id","fee_type","amount","effective_from","effective_to","required"],
"Enrollment": ["enrollment_id","student_id","program_id","term_id","enrollment_date","status","withdrawal_date"],
"Invoice": ["invoice_id","student_id","enrollment_id","term_id","invoice_date","due_date","status","gross_amount","scholarship_credit","late_fee","balance"],
"InvoiceLine": ["invoice_line_id","invoice_id","fee_schedule_id","line_type","description","quantity","unit_amount","line_amount","eligible_for_scholarship"],
"Scholarship": ["scholarship_id","student_id","term_id","scholarship_type","award_amount","award_date","status"],
"Eligibility": ["eligibility_id","scholarship_id","student_id","program_id","term_id","eligible","rule_code","evaluated_at"],
"Payment": ["payment_id","student_id","payment_date","amount","method","status","reference"],
"PaymentAllocation": ["allocation_id","payment_id","invoice_id","invoice_line_id","allocated_amount","allocated_at","status"],
"Refund": ["refund_id","payment_id","student_id","refund_date","amount","reason","status"],
}

def money(x): return round(float(x) + 1e-9, 2)
def fmtid(prefix, n, width=6): return f"{prefix}-{n:0{width}d}"

def generate_dataset(outdir="output", students_n=100, programs_n=5, invoices_n=300, scholarships_n=150, payments_n=500, seed=SEED):
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    # 1. Parent/master data first
    students=[]
    first_names=["Aarav","Diya","Ishaan","Meera","Arjun","Anaya","Rohan","Sana","Kiran","Aditi"]
    last_names=["Sharma","Reddy","Patel","Rao","Kumar","Gupta","Singh","Nair","Das","Iyer"]
    for i in range(1, students_n+1):
        students.append(dict(student_id=fmtid("STU",i), first_name=first_names[(i-1)%len(first_names)],
            last_name=last_names[(i*3)%len(last_names)], email=f"student{i:06d}@example.test",
            date_of_birth=str(date(2000,1,1)+timedelta(days=int(rng.integers(0,2500)))),
            gpa=round(float(rng.uniform(1.5,4.0)),2), status="ACTIVE", created_at="2026-01-15"))
    students_df=pd.DataFrame(students, columns=COLUMNS["Student"])
    programs=[]
    for i in range(1, programs_n+1):
        programs.append(dict(program_id=fmtid("PRG",i), program_name=f"Program {i:02d}",
            level=["UNDERGRADUATE","POSTGRADUATE","CERTIFICATE"][i%3],
            standard_tuition=money(2500 + i*175 + (i%4)*100), active=True))
    programs_df=pd.DataFrame(programs, columns=COLUMNS["Program"])
    schedules=[]
    for pi,p in programs_df.iterrows():
        for fee_type, fraction, required in [("TUITION",1.0,True),("REGISTRATION",0.04,True),("LAB",0.06,False)]:
            schedules.append(dict(fee_schedule_id=f"FEE-{pi+1:03d}-{fee_type}", program_id=p.program_id,
                term_id=TERM, fee_type=fee_type, amount=money(float(p.standard_tuition)*fraction),
                effective_from=TERM_START, effective_to=TERM_END, required=required))
    fees_df=pd.DataFrame(schedules, columns=COLUMNS["FeeSchedule"])
    # Enrollments, linked to students/programs
    enrollments=[]
    for i in range(1, max(invoices_n,students_n)+1):
        sid=students_df.iloc[(i-1)%students_n].student_id
        pid=programs_df.iloc[int(rng.integers(0,programs_n))].program_id
        withdrawn=(i%23==0)
        enrollments.append(dict(enrollment_id=fmtid("ENR",i), student_id=sid, program_id=pid, term_id=TERM,
            enrollment_date=str(date(2026,7,1)+timedelta(days=int(rng.integers(0,50)))),
            status="WITHDRAWN" if withdrawn else "ENROLLED",
            withdrawal_date="2026-09-20" if withdrawn else ""))
    enroll_df=pd.DataFrame(enrollments, columns=COLUMNS["Enrollment"])
    # Invoice and lines generated from enrollment + effective fee schedules.
    # Pre-group fee schedules once to avoid filtering the full table per invoice.
    invoice_rows = []
    line_rows = []
    fees_by_program = {
        program_id: group.to_dict("records")
        for program_id, group in fees_df.groupby("program_id", sort=False)
    }

    for i in range(1, invoices_n + 1):
        enr = enroll_df.iloc[(i - 1) % len(enroll_df)]
        program_fees = fees_by_program[enr.program_id]
        invoice_id = f"INV-{enr.student_id}-2026-{i:06d}"
        inv_date = date(2026, 8, 24) + timedelta(days=int(rng.integers(0, 20)))
        line_total = 0.0
        line_no = 0

        for fee in program_fees:
            if not bool(fee["required"]) and rng.random() < 0.35:
                continue
            line_no += 1
            amount = money(fee["amount"])
            line_total += amount
            line_rows.append(dict(
                invoice_line_id=f"LINE-{i:06d}-{line_no:02d}",
                invoice_id=invoice_id,
                fee_schedule_id=fee["fee_schedule_id"],
                line_type=fee["fee_type"],
                description=f"{fee['fee_type'].title()} fee",
                quantity=1,
                unit_amount=amount,
                line_amount=amount,
                eligible_for_scholarship=fee["fee_type"] == "TUITION",
            ))

        invoice_rows.append(dict(
            invoice_id=invoice_id,
            student_id=enr.student_id,
            enrollment_id=enr.enrollment_id,
            term_id=TERM,
            invoice_date=str(inv_date),
            due_date=str(inv_date + timedelta(days=INVOICE_DUE_DAYS)),
            status="OPEN",
            gross_amount=money(line_total),
            scholarship_credit=0.0,
            late_fee=0.0,
            balance=money(line_total),
        ))

    invoices_df = pd.DataFrame(invoice_rows, columns=COLUMNS["Invoice"])
    lines_df = pd.DataFrame(line_rows, columns=COLUMNS["InvoiceLine"])

    # Scholarship awards and deterministic eligibility decisions.
    scholarships = []
    eligibility = []
    tuition_by_program = fees_df[fees_df.fee_type == "TUITION"].set_index("program_id").amount.to_dict()
    students_by_id = students_df.set_index("student_id").to_dict("index")
    enrollment_records = enroll_df.to_dict("records")

    for i in range(1, scholarships_n + 1):
        enr = enrollment_records[(i - 1) % len(enrollment_records)]
        student = students_by_id[enr["student_id"]]
        gpa = float(student["gpa"])
        eligible = bool(gpa >= SCHOLARSHIP_ELIGIBILITY_GPA_MIN and enr["status"] == "ENROLLED")
        tuition = tuition_by_program[enr["program_id"]]
        proposed = money(tuition * float(rng.uniform(0.10, SCHOLARSHIP_MAX_PERCENT)))
        award = money(min(proposed, tuition * SCHOLARSHIP_MAX_PERCENT)) if eligible else 0.0
        schid = f"SCH-2026-{i:06d}"

        scholarships.append(dict(
            scholarship_id=schid,
            student_id=enr["student_id"],
            term_id=TERM,
            scholarship_type=["MERIT", "NEED_BASED", "PROGRAM_GRANT"][i % 3],
            award_amount=award,
            award_date="2026-08-20",
            status="AWARDED" if eligible and award > 0 else "INELIGIBLE",
        ))
        eligibility.append(dict(
            eligibility_id=fmtid("ELG", i),
            scholarship_id=schid,
            student_id=enr["student_id"],
            program_id=enr["program_id"],
            term_id=TERM,
            eligible=eligible,
            rule_code="GPA_AND_ENROLLED" if eligible else (
                "GPA_BELOW_MIN" if gpa < SCHOLARSHIP_ELIGIBILITY_GPA_MIN else "WITHDRAWN"
            ),
            evaluated_at="2026-08-20",
        ))

    scholarships_df = pd.DataFrame(scholarships, columns=COLUMNS["Scholarship"])
    eligibility_df = pd.DataFrame(eligibility, columns=COLUMNS["Eligibility"])

    # Index invoice and tuition-line details once. Append credit lines in bulk
    # rather than repeatedly filtering and concatenating DataFrames.
    invoice_indices_by_student_term = {}
    for idx, inv in invoices_df[["student_id", "term_id"]].iterrows():
        invoice_indices_by_student_term.setdefault((inv["student_id"], inv["term_id"]), []).append(idx)

    invoice_id_by_index = invoices_df["invoice_id"].to_dict()
    tuition_total_by_invoice = (
        lines_df[lines_df["eligible_for_scholarship"] == True]
        .groupby("invoice_id")["line_amount"].sum().to_dict()
    )
    credit_total_by_invoice = {}
    scholarship_credit_rows = []

    for sch in scholarships:
        if sch["status"] != "AWARDED":
            continue
        key = (sch["student_id"], sch["term_id"])
        candidate_indices = invoice_indices_by_student_term.get(key, [])
        if not candidate_indices:
            continue

        idx = candidate_indices[0]
        inv_id = invoice_id_by_index[idx]
        eligible_fee = float(tuition_total_by_invoice.get(inv_id, 0.0))
        already = float(credit_total_by_invoice.get(inv_id, 0.0))
        credit = money(min(float(sch["award_amount"]), max(0.0, eligible_fee + already)))
        if credit <= 0:
            continue

        scholarship_credit_rows.append(dict(
            invoice_line_id=f"LINE-SCH-{sch['scholarship_id']}",
            invoice_id=inv_id,
            fee_schedule_id="",
            line_type="SCHOLARSHIP_CREDIT",
            description=f"Scholarship {sch['scholarship_id']}",
            quantity=1,
            unit_amount=-credit,
            line_amount=-credit,
            eligible_for_scholarship=False,
        ))
        credit_total_by_invoice[inv_id] = money(already - credit)
        invoices_df.at[idx, "scholarship_credit"] = money(
            float(invoices_df.at[idx, "scholarship_credit"]) + credit
        )

    if scholarship_credit_rows:
        lines_df = pd.concat(
            [lines_df, pd.DataFrame(scholarship_credit_rows)],
            ignore_index=True,
        )

    # Recalculate invoice totals after credits
    line_sums=lines_df.groupby("invoice_id").line_amount.sum().to_dict()
    invoices_df["gross_amount"]=invoices_df.invoice_id.map(lambda x: money(line_sums.get(x,0)))
    invoices_df["balance"]=invoices_df.gross_amount
    # Payments; use pre-built indexes to avoid repeatedly scanning all invoices
    # and invoice lines for every payment.
    payment_rows = []
    alloc_rows = []
    payment_remaining = {}

    invoice_indices_by_student = {}
    for idx, inv in invoices_df[["student_id", "invoice_id"]].iterrows():
        invoice_indices_by_student.setdefault(inv["student_id"], []).append(idx)

    positive_lines_by_invoice = {}
    positive_lines = lines_df[lines_df["line_amount"] > 0]
    for row in positive_lines.itertuples(index=False):
        positive_lines_by_invoice.setdefault(row.invoice_id, []).append(
            (row.invoice_line_id, float(row.line_amount))
        )

    invoice_balances = invoices_df["balance"].to_dict()
    invoice_ids = invoices_df["invoice_id"].to_dict()
    invoice_id_to_index = {invoice_id: idx for idx, invoice_id in invoice_ids.items()}

    for i in range(1, payments_n + 1):
        student_id = students_df.iloc[int(rng.integers(0, students_n))].student_id
        amount = money(float(rng.choice([
            rng.uniform(50, 500),
            rng.uniform(500, 1500),
            rng.uniform(1500, 3000),
        ])))
        pid = f"PAY-2026-{i:06d}"
        payment_remaining[pid] = amount
        payment_rows.append(dict(
            payment_id=pid,
            student_id=student_id,
            payment_date=str(date(2026, 8, 25) + timedelta(days=int(rng.integers(0, 120)))),
            amount=amount,
            method=["CARD", "BANK_TRANSFER", "CASH", "UPI"][i % 4],
            status="SETTLED",
            reference=f"REF-{i:08d}",
        ))

        candidate_indices = invoice_indices_by_student.get(student_id, [])
        if not candidate_indices:
            continue

        inv_idx = candidate_indices[int(rng.integers(0, len(candidate_indices)))]
        inv_id = invoice_ids[inv_idx]
        invoice_lines = positive_lines_by_invoice.get(inv_id, [])
        if not invoice_lines:
            continue

        line_id, line_amount = invoice_lines[0]
        allocated = money(min(amount, line_amount, float(invoice_balances[inv_idx])))
        if allocated <= 0:
            continue

        alloc_rows.append(dict(
            allocation_id=f"ALLOC-{pid}-01",
            payment_id=pid,
            invoice_id=inv_id,
            invoice_line_id=line_id,
            allocated_amount=allocated,
            allocated_at=str(date(2026, 9, 1)),
            status="POSTED",
        ))
        payment_remaining[pid] = money(amount - allocated)
        invoice_balances[inv_idx] = money(max(0.0, float(invoice_balances[inv_idx]) - allocated))

        # Calculate late fees as of 2026-10-28
    as_of_date = date(2026, 10, 28)

    for idx, inv in invoices_df.iterrows():
        due_date = date.fromisoformat(inv["due_date"])
        outstanding = max(0.0, float(invoice_balances[idx]))

        if as_of_date > due_date and outstanding > 0:
            fee = money(min(outstanding * LATE_FEE_RATE, LATE_FEE_CAP))
            invoices_df.at[idx, "late_fee"] = fee
            invoice_balances[idx] = money(outstanding + fee)

    invoices_df["balance"] = invoices_df.index.map(invoice_balances)
    payments_df=pd.DataFrame(payment_rows, columns=COLUMNS["Payment"])
    alloc_df=pd.DataFrame(alloc_rows, columns=COLUMNS["PaymentAllocation"])
    # Refunds are valid by construction: only refund a small portion of a settled payment, no more than amount.
    refunds=[]
    for i,pay in enumerate(payment_rows,1):
        if i%37==0:
            refunds.append(dict(refund_id=fmtid("RFD",len(refunds)+1),payment_id=pay["payment_id"],student_id=pay["student_id"],
                refund_date="2026-10-15",amount=money(pay["amount"]*0.10),reason="CUSTOMER_REQUEST",status="APPROVED"))
    refunds_df=pd.DataFrame(refunds, columns=COLUMNS["Refund"])
    # Add deterministic labelled anomalies after valid baseline data has been created.
    gt=[]
    if len(alloc_df)>0:
        row=alloc_df.iloc[0]
        alloc_df.loc[alloc_df.index[0],"allocated_amount"]=money(float(payments_df.loc[payments_df.payment_id==row.payment_id,"amount"].iloc[0])+25)
        affected_invoice_id = row.invoice_id
        invoice_mask = invoices_df["invoice_id"] == affected_invoice_id
        invoices_df.loc[invoice_mask, "balance"] = invoices_df.loc[invoice_mask, "balance"].apply(lambda value: money(float(value) - 25))
        gt.append(dict(issue_id="ISSUE-0001",issue_type="ALLOCATION_EXCEEDS_PAYMENT",entity_type="PaymentAllocation",
            entity_id=row.allocation_id,expected_result="FLAG",rule="Sum of allocations for a payment must not exceed payment amount"))
    if len(scholarships_df)>0 and len(invoices_df)>0:
        row=scholarships_df.iloc[0]
        scholarships_df.loc[0,"award_amount"]=money(float(scholarships_df.loc[0,"award_amount"])+1000000)
        gt.append(dict(issue_id="ISSUE-0002",issue_type="SCHOLARSHIP_EXCEEDS_ELIGIBLE_FEES",entity_type="Scholarship",
            entity_id=row.scholarship_id,expected_result="FLAG",rule="Scholarship award must not exceed eligible fee amount"))
    if len(invoices_df)>0:
        source=invoices_df.iloc[0].to_dict()
        duplicate=source.copy(); duplicate["invoice_id"]=source["invoice_id"]+"-DUP"
        duplicate["balance"] = money(float(duplicate["gross_amount"]) + float(duplicate.get("late_fee", 0)))
        invoices_df=pd.concat([invoices_df,pd.DataFrame([duplicate])],ignore_index=True)
        gt.append(dict(issue_id="ISSUE-0003",issue_type="DUPLICATE_INVOICE",entity_type="Invoice",
            entity_id=duplicate["invoice_id"],expected_result="FLAG",rule="One invoice per enrollment and term billing event"))
    if len(refunds_df)>0:
        refunds_df.loc[0,"amount"]=money(float(refunds_df.loc[0,"amount"])+100000)
        gt.append(dict(issue_id="ISSUE-0004",issue_type="REFUND_EXCEEDS_NET_PAID",entity_type="Refund",
            entity_id=refunds_df.loc[0,"refund_id"],expected_result="FLAG",rule="Refund total must not exceed net settled payment amount"))
    if len(invoices_df)>0:
        invoices_df.loc[0,"balance"]=money(float(invoices_df.loc[0,"balance"])+123.45)
        gt.append(dict(issue_id="ISSUE-0005",issue_type="BALANCE_DISAGREES_WITH_LEDGER",entity_type="Invoice",
            entity_id=invoices_df.loc[0,"invoice_id"],expected_result="FLAG",rule="Stored balance must reconcile to invoice lines and posted allocations"))
    gt_df=pd.DataFrame(gt,columns=["issue_id","issue_type","entity_type","entity_id","expected_result","rule"])
    # Audit event records: append-only descriptions of generated lifecycle events.
    events=[]
    for e in enroll_df.itertuples():
        events.append(dict(event_id=f"EVT-ENR-{e.enrollment_id}",entity_type="Enrollment",entity_id=e.enrollment_id,
            event_type="ENROLLED" if e.status=="ENROLLED" else "WITHDRAWN",event_date=e.withdrawal_date or e.enrollment_date,
            details="Synthetic lifecycle event"))
    for inv in invoices_df.itertuples():
        events.append(dict(event_id=f"EVT-INV-{inv.invoice_id}",entity_type="Invoice",entity_id=inv.invoice_id,
            event_type="INVOICE_GENERATED",event_date=inv.invoice_date,details="Generated from fee schedule"))
    # Export CSVs
    dfs={"Student":students_df,"Program":programs_df,"FeeSchedule":fees_df,"Enrollment":enroll_df,
         "Invoice":invoices_df,"InvoiceLine":lines_df,"Scholarship":scholarships_df,"Eligibility":eligibility_df,
         "Payment":payments_df,"PaymentAllocation":alloc_df,"Refund":refunds_df}
    for entity,df in dfs.items(): df.to_csv(out/ENTITY_FILES[entity],index=False)
    gt_df.to_csv(out/"ground_truth.csv",index=False)
    pd.DataFrame(events).to_csv(out/"events.csv",index=False)
    # JSON exports
    for entity,df in dfs.items(): df.to_json(out/(entity.lower()+"s.json"),orient="records",indent=2)
    gt_df.to_json(out/"ground_truth.json",orient="records",indent=2)
    # SQLite schema / import
    db_path=out/"student_fee_system.sqlite"
    if db_path.exists(): db_path.unlink()
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys=ON")
        create_schema(con)
        for entity,df in dfs.items():
            df.to_sql(entity,con,if_exists="append",index=False)
        pd.DataFrame(events).to_sql("Event",con,if_exists="append",index=False)
    # Validation and checksums
    summary=validate_data(dfs,gt_df)
    (out/"validation_summary.json").write_text(json.dumps(summary,indent=2))
    manifest={"project":"Student Tuition Fee Management and Reconciliation System","seed":seed,"term_id":TERM,
        "external_data_used":False,"generated_at":"DETERMINISTIC_SYNTHETIC_TIMESTAMP",
        "scale":{"students":students_n,"programs":programs_n,"invoices_requested":invoices_n,
                 "scholarships_requested":scholarships_n,"payments_requested":payments_n},
        "files":sorted([p.name for p in out.iterdir() if p.is_file()])}
    (out/"source_manifest.json").write_text(json.dumps(manifest,indent=2))
    checksums={}
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name!="checksums.json":
            checksums[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/"checksums.json").write_text(json.dumps(checksums,indent=2))
    return summary

def create_schema(con):
    # Tables include explicit PK/FK constraints. SQLite uses REAL for synthetic monetary amounts.
    statements=[
    """CREATE TABLE Student(student_id TEXT PRIMARY KEY,first_name TEXT NOT NULL,last_name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,date_of_birth TEXT NOT NULL,gpa REAL NOT NULL CHECK(gpa BETWEEN 0 AND 4),status TEXT NOT NULL CHECK(status IN ('ACTIVE','INACTIVE')),created_at TEXT NOT NULL)""",
    """CREATE TABLE Program(program_id TEXT PRIMARY KEY,program_name TEXT NOT NULL,level TEXT NOT NULL,standard_tuition REAL NOT NULL CHECK(standard_tuition>=0),active INTEGER NOT NULL)""",
    """CREATE TABLE FeeSchedule(fee_schedule_id TEXT PRIMARY KEY,program_id TEXT NOT NULL REFERENCES Program(program_id),term_id TEXT NOT NULL,fee_type TEXT NOT NULL,amount REAL NOT NULL CHECK(amount>=0),effective_from TEXT NOT NULL,effective_to TEXT NOT NULL,required INTEGER NOT NULL)""",
    """CREATE TABLE Enrollment(enrollment_id TEXT PRIMARY KEY,student_id TEXT NOT NULL REFERENCES Student(student_id),program_id TEXT NOT NULL REFERENCES Program(program_id),term_id TEXT NOT NULL,enrollment_date TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('ENROLLED','WITHDRAWN','CANCELLED')),withdrawal_date TEXT)""",
    """CREATE TABLE Invoice(invoice_id TEXT PRIMARY KEY,student_id TEXT NOT NULL REFERENCES Student(student_id),enrollment_id TEXT NOT NULL REFERENCES Enrollment(enrollment_id),term_id TEXT NOT NULL,invoice_date TEXT NOT NULL,due_date TEXT NOT NULL,status TEXT NOT NULL,gross_amount REAL NOT NULL,scholarship_credit REAL NOT NULL,late_fee REAL NOT NULL,balance REAL NOT NULL)""",
    """CREATE TABLE InvoiceLine(invoice_line_id TEXT PRIMARY KEY,invoice_id TEXT NOT NULL REFERENCES Invoice(invoice_id),fee_schedule_id TEXT, line_type TEXT NOT NULL,description TEXT NOT NULL,quantity REAL NOT NULL,unit_amount REAL NOT NULL,line_amount REAL NOT NULL,eligible_for_scholarship INTEGER NOT NULL)""",
    """CREATE TABLE Scholarship(scholarship_id TEXT PRIMARY KEY,student_id TEXT NOT NULL REFERENCES Student(student_id),term_id TEXT NOT NULL,scholarship_type TEXT NOT NULL,award_amount REAL NOT NULL,award_date TEXT NOT NULL,status TEXT NOT NULL)""",
    """CREATE TABLE Eligibility(eligibility_id TEXT PRIMARY KEY,scholarship_id TEXT NOT NULL REFERENCES Scholarship(scholarship_id),student_id TEXT NOT NULL REFERENCES Student(student_id),program_id TEXT NOT NULL REFERENCES Program(program_id),term_id TEXT NOT NULL,eligible INTEGER NOT NULL,rule_code TEXT NOT NULL,evaluated_at TEXT NOT NULL)""",
    """CREATE TABLE Payment(payment_id TEXT PRIMARY KEY,student_id TEXT NOT NULL REFERENCES Student(student_id),payment_date TEXT NOT NULL,amount REAL NOT NULL CHECK(amount>=0),method TEXT NOT NULL,status TEXT NOT NULL,reference TEXT UNIQUE NOT NULL)""",
    """CREATE TABLE PaymentAllocation(allocation_id TEXT PRIMARY KEY,payment_id TEXT NOT NULL REFERENCES Payment(payment_id),invoice_id TEXT NOT NULL REFERENCES Invoice(invoice_id),invoice_line_id TEXT NOT NULL REFERENCES InvoiceLine(invoice_line_id),allocated_amount REAL NOT NULL,allocated_at TEXT NOT NULL,status TEXT NOT NULL)""",
    """CREATE TABLE Refund(refund_id TEXT PRIMARY KEY,payment_id TEXT NOT NULL REFERENCES Payment(payment_id),student_id TEXT NOT NULL REFERENCES Student(student_id),refund_date TEXT NOT NULL,amount REAL NOT NULL CHECK(amount>=0),reason TEXT NOT NULL,status TEXT NOT NULL)""",
    """CREATE TABLE Event(event_id TEXT PRIMARY KEY,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,event_type TEXT NOT NULL,event_date TEXT NOT NULL,details TEXT NOT NULL)"""
    ]
    for s in statements: con.execute(s)

def validate_data(dfs, gt_df):
    """Validate keys, relationships, and accounting anomalies using actual dataset values."""
    findings = []
    tolerance = 0.01

    # 1. Primary key uniqueness
    pkmap = {
        "Student": "student_id",
        "Program": "program_id",
        "FeeSchedule": "fee_schedule_id",
        "Enrollment": "enrollment_id",
        "Invoice": "invoice_id",
        "InvoiceLine": "invoice_line_id",
        "Scholarship": "scholarship_id",
        "Eligibility": "eligibility_id",
        "Payment": "payment_id",
        "PaymentAllocation": "allocation_id",
        "Refund": "refund_id",
    }

    for entity, pk in pkmap.items():
        duplicates = int(dfs[entity][pk].duplicated().sum())
        if duplicates:
            findings.append({
                "check": "PRIMARY_KEY_UNIQUENESS",
                "entity": entity,
                "count": duplicates,
                "severity": "ERROR",
            })

    # 2. Foreign key integrity
    fk_specs = [
        ("Enrollment", "student_id", "Student", "student_id"),
        ("Enrollment", "program_id", "Program", "program_id"),
        ("FeeSchedule", "program_id", "Program", "program_id"),
        ("Invoice", "student_id", "Student", "student_id"),
        ("Invoice", "enrollment_id", "Enrollment", "enrollment_id"),
        ("InvoiceLine", "invoice_id", "Invoice", "invoice_id"),
        ("Scholarship", "student_id", "Student", "student_id"),
        ("Eligibility", "scholarship_id", "Scholarship", "scholarship_id"),
        ("Eligibility", "student_id", "Student", "student_id"),
        ("Eligibility", "program_id", "Program", "program_id"),
        ("Payment", "student_id", "Student", "student_id"),
        ("PaymentAllocation", "payment_id", "Payment", "payment_id"),
        ("PaymentAllocation", "invoice_id", "Invoice", "invoice_id"),
        ("PaymentAllocation", "invoice_line_id", "InvoiceLine", "invoice_line_id"),
        ("Refund", "payment_id", "Payment", "payment_id"),
        ("Refund", "student_id", "Student", "student_id"),
    ]

    for child, col, parent, parent_col in fk_specs:
        valid_ids = set(dfs[parent][parent_col])
        invalid_mask = ~dfs[child][col].isin(valid_ids)
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            findings.append({
                "check": "FOREIGN_KEY_INTEGRITY",
                "entity": child,
                "field": col,
                "count": invalid_count,
                "severity": "ERROR",
            })

    # 3. Posted payment allocations must not exceed the payment amount.
    payments = dfs["Payment"]
    allocations = dfs["PaymentAllocation"]
    if not allocations.empty:
        posted = allocations[allocations["status"] == "POSTED"]
        allocation_totals = posted.groupby("payment_id")["allocated_amount"].sum()
        payment_amounts = payments.set_index("payment_id")["amount"]
        bad_payment_ids = [
            payment_id
            for payment_id, total in allocation_totals.items()
            if payment_id in payment_amounts.index
            and float(total) > float(payment_amounts.loc[payment_id]) + tolerance
        ]
        if bad_payment_ids:
            findings.append({
                "check": "ALLOCATION_EXCEEDS_PAYMENT",
                "count": len(bad_payment_ids),
                "severity": "ERROR",
                "ids": bad_payment_ids[:20],
            })

    # 4. Duplicate billing event: one invoice per enrollment and term.
    invoices = dfs["Invoice"]
    if not invoices.empty:
        duplicate_mask = invoices.duplicated(
            subset=["enrollment_id", "term_id"], keep=False
        )
        duplicate_ids = invoices.loc[duplicate_mask, "invoice_id"].astype(str).tolist()
        if duplicate_ids:
            findings.append({
                "check": "DUPLICATE_INVOICE",
                "count": len(duplicate_ids),
                "severity": "ERROR",
                "ids": duplicate_ids[:20],
            })

    # 5. Scholarship award must not exceed the student's eligible fees in that term.
    scholarships = dfs["Scholarship"]
    lines = dfs["InvoiceLine"]
    if not scholarships.empty and not invoices.empty and not lines.empty:
        eligible_mask = (
            lines["eligible_for_scholarship"].astype(str).str.lower().isin(["true", "1"])
        )
        eligible_lines = lines[eligible_mask & (lines["line_amount"] > 0)]
        eligible_with_invoice = eligible_lines.merge(
            invoices[["invoice_id", "student_id", "term_id"]],
            on="invoice_id",
            how="inner",
        )
        eligible_totals = (
            eligible_with_invoice.groupby(["student_id", "term_id"])["line_amount"]
            .sum()
            .to_dict()
        )

        bad_scholarships = []
        for row in scholarships.itertuples(index=False):
            eligible_amount = float(
                eligible_totals.get((row.student_id, row.term_id), 0.0)
            )
            if float(row.award_amount) > eligible_amount + tolerance:
                bad_scholarships.append(row.scholarship_id)

        if bad_scholarships:
            findings.append({
                "check": "SCHOLARSHIP_EXCEEDS_ELIGIBLE_FEES",
                "count": len(bad_scholarships),
                "severity": "ERROR",
                "ids": bad_scholarships[:20],
            })

    # 6. Total approved refunds must not exceed the settled payment amount.
    refunds = dfs["Refund"]
    if not refunds.empty and not payments.empty:
        settled_amounts = payments.loc[
            payments["status"] == "SETTLED"
        ].set_index("payment_id")["amount"]
        approved_refunds = refunds[refunds["status"] == "APPROVED"]
        refund_totals = approved_refunds.groupby("payment_id")["amount"].sum()
        bad_refund_ids = []

        for payment_id, total_refunded in refund_totals.items():
            if payment_id in settled_amounts.index:
                if float(total_refunded) > float(settled_amounts.loc[payment_id]) + tolerance:
                    ids = approved_refunds.loc[
                        approved_refunds["payment_id"] == payment_id, "refund_id"
                    ].astype(str).tolist()
                    bad_refund_ids.extend(ids)

        if bad_refund_ids:
            findings.append({
                "check": "REFUND_EXCEEDS_NET_PAID",
                "count": len(bad_refund_ids),
                "severity": "ERROR",
                "ids": bad_refund_ids[:20],
            })

    # 7. Stored balance must equal invoice total plus late fee minus posted allocations.
    if not invoices.empty:
        posted_allocations = allocations[allocations["status"] == "POSTED"]
        allocated_totals = (
            posted_allocations.groupby("invoice_id")["allocated_amount"].sum().to_dict()
            if not posted_allocations.empty else {}
        )
        mismatched_invoice_ids = []

        for row in invoices.itertuples(index=False):
            expected_balance = round(
                float(row.gross_amount)
                + float(row.late_fee)
                - float(allocated_totals.get(row.invoice_id, 0.0)),
                2,
            )
            if abs(float(row.balance) - expected_balance) > tolerance:
                mismatched_invoice_ids.append(row.invoice_id)

        if mismatched_invoice_ids:
            findings.append({
                "check": "BALANCE_DISAGREES_WITH_LEDGER",
                "count": len(mismatched_invoice_ids),
                "severity": "ERROR",
                "ids": mismatched_invoice_ids[:20],
            })

    required_checks = {
        "ALLOCATION_EXCEEDS_PAYMENT",
        "SCHOLARSHIP_EXCEEDS_ELIGIBLE_FEES",
        "DUPLICATE_INVOICE",
        "REFUND_EXCEEDS_NET_PAID",
        "BALANCE_DISAGREES_WITH_LEDGER",
    }
    detected_checks = {finding["check"] for finding in findings}
    detected_anomalies = required_checks.intersection(detected_checks)

    if detected_anomalies:
        status = "COMPLETED_WITH_DETECTED_ANOMALIES"
    elif findings:
        status = "CHECK"
    else:
        status = "PASS"

    return {
        "seed": SEED,
        "status": status,
        "row_counts": {name: int(len(df)) for name, df in dfs.items()},
        "ground_truth_rows": int(len(gt_df)),
        "finding_count": len(findings),
        "findings": findings,
        "note": (
            "Findings are computed from the generated data. "
            "Expected anomaly fixtures are described in ground_truth.csv."
        ),
    }

def main():
    parser=argparse.ArgumentParser(description="Generate and validate the student fee reconciliation dataset.")
    parser.add_argument("--scale",choices=["starter","full"],default="starter")
    parser.add_argument("--students",type=int); parser.add_argument("--programs",type=int)
    parser.add_argument("--invoices",type=int); parser.add_argument("--scholarships",type=int); parser.add_argument("--payments",type=int)
    parser.add_argument("--seed",type=int,default=SEED); parser.add_argument("--outdir",default="output")
    parser.add_argument("--validate-only",action="store_true")
    args=parser.parse_args()
    if args.validate_only:
        out = Path(args.outdir)
        if not out.is_dir():
            parser.error(f"Output directory not found: {out}")

        dfs = {}
        for entity, filename in ENTITY_FILES.items():
            csv_path = out / filename
            if not csv_path.is_file():
                parser.error(f"Required CSV file not found: {csv_path}")
            dfs[entity] = pd.read_csv(csv_path)

        gt_path = out / "ground_truth.csv"
        if not gt_path.is_file():
            parser.error(f"Required ground truth file not found: {gt_path}")

        gt_df = pd.read_csv(gt_path)
        summary = validate_data(dfs, gt_df)
        (out / "validation_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        print(json.dumps(summary, indent=2))
        print(f"\nValidated existing dataset in: {out.resolve()}")
        return
    defaults=SCALES[args.scale]
    summary=generate_dataset(args.outdir,args.students or defaults["students"],args.programs or defaults["programs"],
        args.invoices or defaults["invoices"],args.scholarships or defaults["scholarships"],
        args.payments or defaults["payments"],args.seed)
    print(json.dumps(summary,indent=2))
    print(f"\nGenerated dataset in: {Path(args.outdir).resolve()}")
if __name__=="__main__": main()
