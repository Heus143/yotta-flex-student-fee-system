import json
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from pathlib import Path
import pandas as pd
from fee_system import generate_dataset

def test_starter_generation_and_required_anomalies(tmp_path):
    out=tmp_path/"output"
    summary=generate_dataset(out,students_n=20,programs_n=3,invoices_n=40,scholarships_n=15,payments_n=50,seed=20261022)
    assert (out/"students.csv").exists()
    assert (out/"student_fee_system.sqlite").exists()
    gt=pd.read_csv(out/"ground_truth.csv")
    expected={"ALLOCATION_EXCEEDS_PAYMENT","SCHOLARSHIP_EXCEEDS_ELIGIBLE_FEES","DUPLICATE_INVOICE","REFUND_EXCEEDS_NET_PAID","BALANCE_DISAGREES_WITH_LEDGER"}
    assert expected.issubset(set(gt.issue_type))
    assert len(pd.read_csv(out/"students.csv"))==20
    assert summary["ground_truth_rows"]==5

def test_fixed_seed_reproducible_core_tables(tmp_path):
    a=tmp_path/"a"; b=tmp_path/"b"
    generate_dataset(a,students_n=10,programs_n=2,invoices_n=12,scholarships_n=5,payments_n=10,seed=20261022)
    generate_dataset(b,students_n=10,programs_n=2,invoices_n=12,scholarships_n=5,payments_n=10,seed=20261022)
    for name in ["students.csv","programs.csv","fee_schedules.csv","enrollments.csv","ground_truth.csv"]:
        assert (a/name).read_bytes()==(b/name).read_bytes()

def test_ids_follow_required_conventions(tmp_path):
    out=tmp_path/"output"
    generate_dataset(out,students_n=5,programs_n=2,invoices_n=6,scholarships_n=2,payments_n=3)
    students=pd.read_csv(out/"students.csv")
    payments=pd.read_csv(out/"payments.csv")
    assert students.student_id.iloc[0]=="STU-000001"
    assert payments.payment_id.iloc[0]=="PAY-2026-000001"
