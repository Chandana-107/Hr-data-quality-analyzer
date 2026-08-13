import pandas as pd
from pathlib import Path
import tempfile

from src.utils.normalization import normalize_dataframe
from src.validators.completeness import run_completeness_checks
from src.validators.uniqueness import run_uniqueness_checks
from src.validators.validity import run_validity_checks
from src.validators.consistency import run_consistency_checks
from src.validators.anomalies import run_anomaly_checks
from src.report.excel_report import generate_report
from src.config.rules import QUALITY_RULES, COUNTRY_CURRENCY_MAP


def make_test_df():
    data = [
        {'employee_id': 'EMP00001', 'first_name': 'Alice', 'last_name': 'A', 'email': 'alice@example.com', 'phone': '+911234567890', 'date_of_birth': '1990-01-01', 'joining_date': '2020-01-01', 'department': 'Engineering', 'department_code': 'ENG', 'country': 'India', 'currency': 'INR', 'salary': 50000, 'manager_id': '', 'employment_status': 'active', 'termination_date': None},
        {'employee_id': 'EMP00002', 'first_name': 'Bob', 'last_name': 'B', 'email': 'bad-email', 'phone': '12345', 'date_of_birth': '2010-01-01', 'joining_date': '2030-01-01', 'department': None, 'department_code': 'XXX', 'country': 'USA', 'currency': 'INR', 'salary': -100, 'manager_id': '', 'employment_status': 'terminated', 'termination_date': '2019-12-31'},
        {'employee_id': 'EMP00002', 'first_name': 'Charlie', 'last_name': 'C', 'email': 'charlie@example.com', 'phone': '+11234567890', 'date_of_birth': '1920-01-01', 'joining_date': '2015-01-01', 'department': 'HR', 'department_code': 'HR', 'country': 'USA', 'currency': 'USD', 'salary': 200000000, 'manager_id': '', 'employment_status': 'active', 'termination_date': None},
        {'employee_id': 'BADID', 'first_name': 'Dave', 'last_name': 'D', 'email': None, 'phone': None, 'date_of_birth': None, 'joining_date': None, 'department': None, 'department_code': None, 'country': None, 'currency': None, 'salary': None, 'manager_id': None, 'employment_status': None, 'termination_date': None},
    ]
    df = pd.DataFrame(data)
    return normalize_dataframe(df)


def test_completeness_and_uniqueness_and_validity_and_consistency_and_anomalies(tmp_path):
    df = make_test_df()
    comp = run_completeness_checks(df)
    assert comp['total_records'] == 4
    # at least one missing email
    assert comp['fields']['email']['missing'] >= 1

    uni = run_uniqueness_checks(df)
    # duplicate employee_id should be detected
    assert uni['failed'] >= 2

    val = run_validity_checks(df, QUALITY_RULES)
    # bad email, bad id, negative salary, huge salary -> failures
    assert val['failed'] >= 4

    cons = run_consistency_checks(df, COUNTRY_CURRENCY_MAP)
    # USA with INR should be flagged
    assert cons['failed'] >= 1

    anom = run_anomaly_checks(df, QUALITY_RULES)
    # salary negative, salary zero not present but high salary and age issues present
    assert anom['failed'] >= 2

    # report generation
    out = tmp_path / 'report.xlsx'
    generate_report(out, df, {'completeness': comp, 'uniqueness': uni, 'validity': val, 'consistency': cons, 'anomalies': anom}, {'generated_at': 'now', 'source_file': 'test', 'total_records': 4, 'overall_score': 50, 'classification': 'NEEDS REVIEW'})
    assert out.exists()
