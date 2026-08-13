import pandas as pd
from src.utils.normalization import normalize_dataframe
from src.validators.completeness import run_completeness_checks
from src.validators.uniqueness import run_uniqueness_checks
from src.validators.validity import run_validity_checks
from src.validators.consistency import run_consistency_checks
from src.validators.anomalies import run_anomaly_checks
from src.config.rules import QUALITY_RULES, COUNTRY_CURRENCY_MAP


def base_sample_rows():
    return [
        {'employee_id': 'EMP00010', 'first_name': 'E1', 'last_name': 'L1', 'email': ' User@Example.COM ', 'phone': '+911111111111', 'date_of_birth': '1990-01-01', 'joining_date': '2020-01-01', 'department': 'ENG', 'department_code': 'ENG', 'country': 'India', 'currency': 'INR', 'salary': '50000', 'manager_id': '', 'employment_status': 'active', 'termination_date': None},
        {'employee_id': 'EMP00011', 'first_name': 'E2', 'last_name': 'L2', 'email': 'e2@example.com', 'phone': '+11222222222', 'date_of_birth': '1985-05-05', 'joining_date': '2010-06-01', 'department': 'HR', 'department_code': 'HR', 'country': 'USA', 'currency': 'USD', 'salary': 60000, 'manager_id': None, 'employment_status': 'active', 'termination_date': None},
    ]


def test_normalization_trims_and_types():
    rows = base_sample_rows()
    df = pd.DataFrame(rows)
    ndf = normalize_dataframe(df)

    # email trimmed and lowered
    assert ndf.loc[0, 'email'] == 'user@example.com'
    # salary numeric (pandas may use numpy dtypes — check numeric dtype and non-null)
    assert pd.notna(ndf.loc[0, 'salary'])
    assert pd.api.types.is_numeric_dtype(ndf['salary'])
    # dates parsed
    assert pd.api.types.is_datetime64_any_dtype(ndf['date_of_birth'])
    assert pd.api.types.is_datetime64_any_dtype(ndf['joining_date'])


def test_completeness_missing_optional_columns_and_counts():
    # create df with only employee_id and first_name to simulate missing optional columns
    df = pd.DataFrame([{'employee_id': 'EMP00020', 'first_name': 'Solo'}])
    ndf = normalize_dataframe(df)
    comp = run_completeness_checks(ndf)
    # total records should be 1
    assert comp['total_records'] == 1
    # important fields should exist in the report
    for f in ['email', 'phone', 'department', 'department_code', 'salary', 'employee_id']:
        assert f in comp['fields']
    # since only employee_id provided, populated for employee_id should be >=1
    assert comp['fields']['employee_id']['populated'] >= 1


def test_uniqueness_detects_duplicates():
    rows = base_sample_rows()
    # duplicate employee_id and email
    rows.append({'employee_id': 'EMP00010', 'first_name': 'E3', 'last_name': 'L3', 'email': 'user@example.com', 'phone': '+911111111111', 'date_of_birth': None, 'joining_date': None, 'department': None, 'department_code': None, 'country': None, 'currency': None, 'salary': None, 'manager_id': None, 'employment_status': None, 'termination_date': None})
    df = pd.DataFrame(rows)
    ndf = normalize_dataframe(df)
    uni = run_uniqueness_checks(ndf)
    # expecting at least two row issues for duplicates (employee_id and email/phone appear duplicated)
    assert uni['failed'] >= 2
    # duplicate groups summary should include employee_id
    assert 'employee_id' in uni['summary']


def test_validity_invalid_values_and_dates():
    rows = base_sample_rows()
    # add a row with several invalid fields
    rows.append({'employee_id': 'BADID', 'first_name': 'E4', 'last_name': 'L4', 'email': 'not-an-email', 'phone': 'abc', 'date_of_birth': 'not-a-date', 'joining_date': '2099-01-01', 'department': None, 'department_code': None, 'country': 'USA', 'currency': 'INR', 'salary': 'not-a-number', 'manager_id': None, 'employment_status': 'terminated', 'termination_date': '2010-01-01'})
    df = pd.DataFrame(rows)
    ndf = normalize_dataframe(df)
    val = run_validity_checks(ndf, QUALITY_RULES)
    # expect multiple failures due to bad email, phone, salary non-numeric, DOB parse, joining in future, termination before joining/date parse issues
    assert val['failed'] >= 4


def test_consistency_country_currency_and_phone_prefix():
    rows = [
        {'employee_id': 'EMP300', 'first_name': 'C1', 'last_name': 'L', 'email': 'c1@x.com', 'phone': '+919999999999', 'date_of_birth': None, 'joining_date': None, 'department': None, 'department_code': None, 'country': 'India', 'currency': 'USD', 'salary': None, 'manager_id': None, 'employment_status': 'active', 'termination_date': None},
        {'employee_id': 'EMP301', 'first_name': 'C2', 'last_name': 'L', 'email': 'c2@x.com', 'phone': '+441234567890', 'date_of_birth': None, 'joining_date': None, 'department': None, 'department_code': None, 'country': 'UK', 'currency': 'GBP', 'salary': None, 'manager_id': None, 'employment_status': 'active', 'termination_date': None},
    ]
    df = pd.DataFrame(rows)
    ndf = normalize_dataframe(df)
    cons = run_consistency_checks(ndf, COUNTRY_CURRENCY_MAP)
    # first row has country/currency mismatch -> at least 1 failure
    assert cons['failed'] >= 1
    # phone prefix for UK should match +44; second row starts with +44 so should not raise phone prefix issue for that row


def test_anomalies_salary_and_age_checks():
    rows = [
        {'employee_id': 'EMP400', 'first_name': 'A1', 'last_name': 'L', 'email': 'a1@x.com', 'phone': None, 'date_of_birth': '2025-01-01', 'joining_date': '2026-01-01', 'department': None, 'department_code': None, 'country': None, 'currency': None, 'salary': 0, 'manager_id': None, 'employment_status': 'active', 'termination_date': None},
        {'employee_id': 'EMP401', 'first_name': 'A2', 'last_name': 'L', 'email': 'a2@x.com', 'phone': None, 'date_of_birth': '1900-01-01', 'joining_date': '2000-01-01', 'department': None, 'department_code': None, 'country': None, 'currency': None, 'salary': -10, 'manager_id': None, 'employment_status': 'active', 'termination_date': None},
        {'employee_id': 'EMP402', 'first_name': 'A3', 'last_name': 'L', 'email': 'a3@x.com', 'phone': None, 'date_of_birth': '1980-01-01', 'joining_date': '2005-01-01', 'department': None, 'department_code': None, 'country': None, 'currency': None, 'salary': 9999999999, 'manager_id': None, 'employment_status': 'active', 'termination_date': None},
    ]
    df = pd.DataFrame(rows)
    ndf = normalize_dataframe(df)
    anom = run_anomaly_checks(ndf, QUALITY_RULES)
    # expect at least one issue per problematic row
    assert anom['failed'] >= 3


def test_empty_dataframe_behavior():
    df = pd.DataFrame()
    ndf = normalize_dataframe(df)
    # after normalization expected columns exist but no rows
    assert len(ndf) == 0
    comp = run_completeness_checks(ndf)
    # with zero records score should be 100 by convention
    assert comp['score'] == 100.0
    uni = run_uniqueness_checks(ndf)
    assert uni['score'] == 100.0
    val = run_validity_checks(ndf, QUALITY_RULES)
    assert val['score'] == 100.0
    cons = run_consistency_checks(ndf, COUNTRY_CURRENCY_MAP)
    assert cons['score'] == 100.0
    an = run_anomaly_checks(ndf, QUALITY_RULES)
    assert an['score'] == 100.0
