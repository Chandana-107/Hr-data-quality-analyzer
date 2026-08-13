# HR Data Quality Analyzer

A deterministic, rule-based data quality and anomaly detection tool to assess employee datasets before migration.

## Overview

The tool reads employee data in XLSX, JSON or XML formats, normalizes it to a pandas DataFrame and runs a suite of validations:

- Completeness
- Uniqueness
- Validity
- Consistency
- Deterministic anomaly detection

It produces a professional Excel report summarizing findings and row-level issues.

## Installation

1. Create and activate a Python 3.11+ virtual environment
2. pip install -r requirements.txt

## Usage

python -m src.main --input data/employees.xlsx --output reports/data_quality_report.xlsx

## Input schema

Supported columns (case-insensitive): employee_id, first_name, last_name, email, phone, date_of_birth, joining_date, department, department_code, country, currency, salary, manager_id, employment_status, termination_date

Missing optional columns are allowed; the tool reports schema gaps.

## Rules and Configuration

Rules are defined in src/config/rules.py. Examples:

- Employee ID pattern: ^EMP\d{5}$
- Salary min/max: 0 to 100_000_000
- Age min/max: 18 to 100
- Country to currency mapping

Severity mapping is configurable in the same module.

## Output

An Excel workbook with these sheets:
- Executive Summary
- Completeness
- Validation Results
- Duplicates
- Consistency Issues
- Anomalies
- Row Issues
- Source Sample

## Testing

Run pytest from the repository root:

pytest -q

## Performance

The pipeline uses pandas and vectorized operations where possible. For very large files (100k+ rows) ensure sufficient memory and prefer running on a machine with adequate RAM.

## Future enhancements

- Parallelized chunked processing for extremely large datasets
- Config-driven rule sets via YAML/JSON
- More advanced phone & locale validation

