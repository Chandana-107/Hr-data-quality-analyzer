import pandas as pd
from typing import List
from datetime import datetime

EXPECTED_COLUMNS = [
    'employee_id', 'first_name', 'last_name', 'email', 'phone', 'date_of_birth',
    'joining_date', 'department', 'department_code', 'country', 'currency',
    'salary', 'manager_id', 'employment_status', 'termination_date'
]


def _safe_parse_date(series: pd.Series) -> pd.Series:
    # pandas now uses strict parsing by default; remove deprecated infer_datetime_format
    return pd.to_datetime(series, errors='coerce')


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # normalize column names
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

    # ensure expected columns exist
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # strip strings
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = df[col].astype('string').str.strip()

    # normalize email
    if 'email' in df.columns:
        df['email'] = df['email'].str.lower()

    # numeric conversions
    if 'salary' in df.columns:
        df['salary'] = pd.to_numeric(df['salary'], errors='coerce')

    # date conversions
    for date_col in ('date_of_birth', 'joining_date', 'termination_date'):
        if date_col in df.columns:
            df[date_col] = _safe_parse_date(df[date_col])

    return df