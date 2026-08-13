from datetime import datetime

QUALITY_RULES = {
    "salary": {"min": 0, "max": 100_000_000},
    "age": {"min": 18, "max": 100},
    "employee_id": {"pattern": r"^EMP\d{5}$"},
}

COUNTRY_CURRENCY_MAP = {
    "India": "INR",
    "USA": "USD",
    "United States": "USD",
    "UK": "GBP",
    "United Kingdom": "GBP",
    "Germany": "EUR",
    "Japan": "JPY"
}

VALID_DEPARTMENTS = {"ENG", "HR", "FIN", "MKT", "OPS", "IT"}

SEVERITY = {
    'duplicate_employee_id': 'CRITICAL',
    'duplicate_email': 'HIGH',
    'duplicate_phone': 'MEDIUM',
    'invalid_email': 'HIGH',
    'invalid_employee_id': 'HIGH',
    'invalid_salary': 'HIGH',
    'missing_department': 'MEDIUM',
    'missing_phone': 'LOW',
    'country_currency_mismatch': 'HIGH',
    'termination_without_date': 'HIGH',
}
