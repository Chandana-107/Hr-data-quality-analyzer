import pandas as pd
from datetime import datetime
from typing import Dict, Any
from src.config.rules import QUALITY_RULES


def run_anomaly_checks(df: pd.DataFrame, rules: Dict) -> Dict[str, Any]:
    issues = []
    total = len(df)
    now = pd.Timestamp.now(tz='UTC')
    age_min = rules.get('age', {}).get('min', 18)
    age_max = rules.get('age', {}).get('max', 100)
    salary_min = rules.get('salary', {}).get('min', 0)
    salary_max = rules.get('salary', {}).get('max', 100_000_000)

    for idx, row in df.iterrows():
        emp = row.get('employee_id')
        sal = row.get('salary')
        if pd.notna(sal):
            try:
                s = float(sal)
                if s == 0:
                    issues.append({'employee_id': emp, 'anomaly': 'salary_zero', 'value': s, 'severity': 'HIGH', 'message': 'Salary is zero'})
                if s < 0:
                    issues.append({'employee_id': emp, 'anomaly': 'salary_negative', 'value': s, 'severity': 'CRITICAL', 'message': 'Salary is negative'})
                if s > salary_max:
                    issues.append({'employee_id': emp, 'anomaly': 'salary_unusually_high', 'value': s, 'severity': 'HIGH', 'message': f'Salary above maximum {salary_max}'})
            except Exception:
                issues.append({'employee_id': emp, 'anomaly': 'salary_not_numeric', 'value': sal, 'severity': 'HIGH', 'message': 'Salary is not numeric'})
        # dates
        dob = row.get('date_of_birth')
        if pd.notna(dob):
            try:
                d = pd.to_datetime(dob, errors='coerce', utc=True)
                if d > now:
                    issues.append({'employee_id': emp, 'anomaly': 'dob_in_future', 'value': dob, 'severity': 'HIGH', 'message': 'date_of_birth in future'})
                else:
                    age = int((now - d).days / 365.25)
                    if age < age_min:
                        issues.append({'employee_id': emp, 'anomaly': 'age_too_young', 'value': age, 'severity': 'HIGH', 'message': f'Age < {age_min}'})
                    if age > age_max:
                        issues.append({'employee_id': emp, 'anomaly': 'age_too_old', 'value': age, 'severity': 'MEDIUM', 'message': f'Age > {age_max}'})
            except Exception:
                issues.append({'employee_id': emp, 'anomaly': 'dob_parse_error', 'value': dob, 'severity': 'MEDIUM', 'message': 'DOB parse error'})
        joining = row.get('joining_date')
        if pd.notna(joining):
            try:
                j = pd.to_datetime(joining, errors='coerce', utc=True)
                if j > now:
                    issues.append({'employee_id': emp, 'anomaly': 'joining_in_future', 'value': joining, 'severity': 'HIGH', 'message': 'joining_date in future'})
            except Exception:
                issues.append({'employee_id': emp, 'anomaly': 'joining_parse_error', 'value': joining, 'severity': 'MEDIUM', 'message': 'joining_date parse error'})
        term = row.get('termination_date')
        if pd.notna(term) and pd.notna(joining):
            try:
                t = pd.to_datetime(term, errors='coerce', utc=True)
                j = pd.to_datetime(joining, errors='coerce', utc=True)
                if t < j:
                    issues.append({'employee_id': emp, 'anomaly': 'termination_before_joining', 'value': f'{term} < {joining}', 'severity': 'HIGH', 'message': 'termination_date before joining_date'})
            except Exception:
                issues.append({'employee_id': emp, 'anomaly': 'termination_parse_error', 'value': term, 'severity': 'MEDIUM', 'message': 'termination_date parse error'})

    df_issues = pd.DataFrame(issues)
    failed = len(df_issues)
    score = round(max(0.0, 100.0 * (1 - failed / total)) if total else 100.0, 2)
    return {'total_records': total, 'row_issues': df_issues, 'score': score, 'failed': failed, 'passed': total - failed}
