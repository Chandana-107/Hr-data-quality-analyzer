import pandas as pd
from typing import Dict, Any
from src.config.rules import SEVERITY

DUP_FIELDS = ['employee_id', 'email', 'phone']


def run_uniqueness_checks(df: pd.DataFrame) -> Dict[str, Any]:
    total = len(df)
    issues = []
    summary = {}
    for field in DUP_FIELDS:
        if field not in df.columns:
            summary[field] = {'duplicate_count': 0}
            continue
        dup_mask = df[field].notna() & df[field].astype(str).ne('') & df.duplicated(subset=[field], keep=False)
        dup_df = df.loc[dup_mask, :].copy()
        # group by value and collect employee ids per duplicate value
        groups = dup_df.groupby(field)['employee_id'].apply(lambda s: list(s.dropna().astype(str))).reset_index(name='employee_ids')
        entries = []
        for _, r in groups.iterrows():
            val = r[field]
            emp_ids = r['employee_ids']
            entries.append({'duplicate_type': field, 'duplicate_value': val, 'duplicate_count': len(emp_ids), 'employee_ids': emp_ids, 'severity': SEVERITY.get('duplicate_' + field, 'MEDIUM')})
            for emp in emp_ids:
                issues.append({'field': field, 'value': val, 'employee_id': emp, 'rule': 'duplicate', 'severity': SEVERITY.get('duplicate_' + field, 'MEDIUM'), 'message': f'Duplicate {field}={val} (count {len(emp_ids)})'})
        summary[field] = {'duplicate_groups': entries, 'duplicate_count': len(entries)}

    row_issues_df = pd.DataFrame(issues)
    # score: penalize duplicates; simple: score = 100 * (1 - dup_rows/total)
    dup_rows = len(row_issues_df)
    score = round(max(0.0, 100.0 * (1 - dup_rows / total)) if total else 100.0, 2)

    return {'total_records': total, 'row_issues': row_issues_df, 'summary': summary, 'score': score, 'failed': dup_rows, 'passed': total - dup_rows}
