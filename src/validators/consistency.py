import pandas as pd
from typing import Dict, Any
from src.config.rules import COUNTRY_CURRENCY_MAP, SEVERITY

PHONE_PREFIX = {
    'India': '+91',
    'USA': '+1',
    'United States': '+1',
    'UK': '+44',
    'United Kingdom': '+44',
    'Germany': '+49',
    'Japan': '+81'
}


def run_consistency_checks(df: pd.DataFrame, country_currency_map: Dict[str, str]) -> Dict[str, Any]:
    issues = []
    total = len(df)
    for idx, row in df.iterrows():
        emp = row.get('employee_id')
        country = row.get('country')
        currency = row.get('currency')
        joining = row.get('joining_date')
        term = row.get('termination_date')
        # country/currency
        if pd.notna(country) and pd.notna(currency):
            expected = country_currency_map.get(str(country).strip())
            if expected and expected != str(currency).strip():
                issues.append({'employee_id': emp, 'field': 'currency', 'actual': currency, 'expected': expected, 'rule': 'country_currency_mismatch', 'severity': SEVERITY.get('country_currency_mismatch', 'HIGH'), 'message': f'Expected currency: {expected}. Actual: {currency}'})
        # terminated employee without termination date
        status = row.get('employment_status')
        if str(status).strip().lower() == 'terminated' and pd.isna(term):
            issues.append({'employee_id': emp, 'field': 'termination_date', 'actual': term, 'expected': 'present', 'rule': 'termination_without_date', 'severity': SEVERITY.get('termination_without_date', 'HIGH'), 'message': 'Employee marked terminated but termination_date missing'})
        # termination before joining handled in validity but duplicate check
        # phone prefix vs country (best-effort)
        phone = row.get('phone')
        if pd.notna(country) and pd.notna(phone):
            pref = PHONE_PREFIX.get(str(country).strip())
            if pref and isinstance(phone, str) and phone.startswith('+') and not phone.startswith(pref):
                issues.append({'employee_id': emp, 'field': 'phone', 'actual': phone, 'expected': f'start with {pref}', 'rule': 'phone_country_prefix_mismatch', 'severity': 'LOW', 'message': f'Phone {phone} does not match expected prefix {pref} for country {country}'})

    df_issues = pd.DataFrame(issues)
    failed = len(df_issues)
    score = round(max(0.0, 100.0 * (1 - failed / total)) if total else 100.0, 2)
    return {'total_records': total, 'row_issues': df_issues, 'score': score, 'failed': failed, 'passed': total - failed}
