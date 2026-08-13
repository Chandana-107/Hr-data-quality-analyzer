import pandas as pd
from typing import Dict, Any

IMPORTANT_FIELDS = ['email', 'phone', 'department', 'department_code', 'salary', 'employee_id']


def run_completeness_checks(df: pd.DataFrame) -> Dict[str, Any]:
    total = len(df)
    field_results = {}
    row_issues = []
    for field in IMPORTANT_FIELDS:
        if field not in df.columns:
            populated = 0
        else:
            populated = df[field].notna() & (df[field] != '')
            populated_count = int(populated.sum())
        missing_count = total - (populated_count if 'populated_count' in locals() else 0)
        completeness_pct = round((populated_count / total) * 100, 2) if total else 100.0
        field_results[field] = {
            'field': field,
            'total': total,
            'populated': populated_count,
            'missing': missing_count,
            'completeness_pct': completeness_pct
        }
        # row-level missing
        missing_rows = df.loc[~populated, :]
        for idx, row in missing_rows.iterrows():
            row_issues.append({'index': idx, 'employee_id': row.get('employee_id'), 'field': field, 'value': row.get(field)})
        # clear for next iter
        if 'populated_count' in locals():
            del populated_count

    # compute an aggregate completeness score as average completeness
    scores = [v['completeness_pct'] for v in field_results.values()]
    score = round(sum(scores) / len(scores), 2) if scores else 100.0

    row_issues_df = pd.DataFrame(row_issues)

    return {
        'total_records': total,
        'fields': field_results,
        'row_issues': row_issues_df,
        'score': score,
        'passed': total - len(row_issues_df),
        'failed': len(row_issues_df)
    }
