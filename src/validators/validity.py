import re
import pandas as pd
from datetime import datetime
from typing import Dict, Any
from src.config.rules import QUALITY_RULES, SEVERITY

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9\-\s]{7,20}$")


def run_validity_checks(df: pd.DataFrame, rules: Dict) -> Dict[str, Any]:
    issues = []
    total = len(df)
    now = pd.Timestamp.now(tz='UTC')

    emp_pattern = rules.get('employee_id', {}).get('pattern')
    salary_min = rules.get('salary', {}).get('min', None)
    salary_max = rules.get('salary', {}).get('max', None)

    for idx, row in df.iterrows():
        emp = row.get('employee_id')
        # employee id pattern
        if pd.isna(emp) or not isinstance(emp, str) or not emp:
            issues.append({'employee_id': emp, 'field': 'employee_id', 'value': emp, 'rule': 'employee_id_present', 'category': 'validity', 'severity': SEVERITY.get('invalid_employee_id', 'HIGH'), 'message': 'Missing employee_id'})
        else:
            if emp_pattern:
                if not re.match(emp_pattern, str(emp)):
                    issues.append({'employee_id': emp, 'field': 'employee_id', 'value': emp, 'rule': 'employee_id_pattern', 'category': 'validity', 'severity': SEVERITY.get('invalid_employee_id', 'HIGH'), 'message': f'employee_id does not match pattern {emp_pattern}'})

        # email
        email = row.get('email')
        if pd.notna(email) and email != '':
            if not EMAIL_RE.match(str(email)):
                issues.append({'employee_id': emp, 'field': 'email', 'value': email, 'rule': 'email_format', 'category': 'validity', 'severity': SEVERITY.get('invalid_email', 'HIGH'), 'message': 'Invalid email format'})

        # phone
        phone = row.get('phone')
        if pd.notna(phone) and phone != '':
            if not PHONE_RE.match(str(phone)):
                issues.append({'employee_id': emp, 'field': 'phone', 'value': phone, 'rule': 'phone_format', 'category': 'validity', 'severity': 'MEDIUM', 'message': 'Invalid phone format'})

        # salary
        sal = row.get('salary')
        if pd.isna(sal):
            issues.append({'employee_id': emp, 'field': 'salary', 'value': sal, 'rule': 'salary_present', 'category': 'validity', 'severity': SEVERITY.get('invalid_salary', 'HIGH'), 'message': 'Missing salary'})
        else:
            try:
                s = float(sal)
                if salary_min is not None and s < salary_min:
                    issues.append({'employee_id': emp, 'field': 'salary', 'value': sal, 'rule': 'salary_min', 'category': 'validity', 'severity': SEVERITY.get('invalid_salary', 'HIGH'), 'message': f'Salary below minimum {salary_min}'})
                if salary_max is not None and s > salary_max:
                    issues.append({'employee_id': emp, 'field': 'salary', 'value': sal, 'rule': 'salary_max', 'category': 'validity', 'severity': SEVERITY.get('invalid_salary', 'HIGH'), 'message': f'Salary above maximum {salary_max}'})
            except Exception:
                issues.append({'employee_id': emp, 'field': 'salary', 'value': sal, 'rule': 'salary_numeric', 'category': 'validity', 'severity': SEVERITY.get('invalid_salary', 'HIGH'), 'message': 'Salary is not numeric'})

        # dates
        dob = row.get('date_of_birth')
        if pd.notna(dob):
            if pd.isna(pd.to_datetime(dob, errors='coerce', utc=True)):
                issues.append({'employee_id': emp, 'field': 'date_of_birth', 'value': dob, 'rule': 'dob_parse', 'category': 'validity', 'severity': 'HIGH', 'message': 'date_of_birth not parseable'})
            else:
                if pd.to_datetime(dob, errors='coerce', utc=True) > now:
                    issues.append({'employee_id': emp, 'field': 'date_of_birth', 'value': dob, 'rule': 'dob_future', 'category': 'validity', 'severity': 'HIGH', 'message': 'date_of_birth in future'})
        joining = row.get('joining_date')
        if pd.notna(joining):
            if pd.isna(pd.to_datetime(joining, errors='coerce', utc=True)):
                issues.append({'employee_id': emp, 'field': 'joining_date', 'value': joining, 'rule': 'joining_parse', 'category': 'validity', 'severity': 'HIGH', 'message': 'joining_date not parseable'})
            else:
                if pd.to_datetime(joining, errors='coerce', utc=True) > now:
                    issues.append({'employee_id': emp, 'field': 'joining_date', 'value': joining, 'rule': 'joining_future', 'category': 'validity', 'severity': 'HIGH', 'message': 'joining_date in future'})

        term = row.get('termination_date')
        if pd.notna(term) and pd.notna(joining):
            try:
                t = pd.to_datetime(term, errors='coerce', utc=True)
                j = pd.to_datetime(joining, errors='coerce', utc=True)
                if t < j:
                    issues.append({'employee_id': emp, 'field': 'termination_date', 'value': term, 'rule': 'termination_before_joining', 'category': 'validity', 'severity': 'HIGH', 'message': 'termination_date before joining_date'})
            except Exception:
                issues.append({'employee_id': emp, 'field': 'termination_date', 'value': term, 'rule': 'termination_parse', 'category': 'validity', 'severity': 'HIGH', 'message': 'termination_date not parseable'})

    row_issues_df = pd.DataFrame(issues)
    failed = len(row_issues_df)
    score = round(max(0.0, 100.0 * (1 - failed / total)) if total else 100.0, 2)

    return {'total_records': total, 'row_issues': row_issues_df, 'score': score, 'failed': failed, 'passed': total - failed}
