import sys
from pathlib import Path
# Ensure project root is on sys.path so `from src...` imports work when running `streamlit run ui/app.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import tempfile
import io
import pandas as pd

from src.main import infer_and_read, compute_scores, classify_score
from src.utils.normalization import normalize_dataframe
from src.validators.completeness import run_completeness_checks
from src.validators.uniqueness import run_uniqueness_checks
from src.validators.validity import run_validity_checks
from src.validators.consistency import run_consistency_checks
from src.validators.anomalies import run_anomaly_checks
from src.report.excel_report import generate_report
from src.config.rules import QUALITY_RULES, COUNTRY_CURRENCY_MAP


def _safe_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df safe for Streamlit/pyarrow conversion by coercing non-numeric/non-datetime columns to strings."""
    if not isinstance(df, pd.DataFrame):
        return df
    df2 = df.copy()
    for col in df2.columns:
        try:
            # keep numeric, datetime and boolean dtypes as-is
            if pd.api.types.is_numeric_dtype(df2[col]) or pd.api.types.is_datetime64_any_dtype(df2[col]) or pd.api.types.is_bool_dtype(df2[col]):
                continue
        except Exception:
            # if dtype check fails, coerce to string
            pass
        df2[col] = df2[col].astype(str).fillna("")
    return df2

st.set_page_config(page_title="HR Data Quality Analyzer", layout="wide")

st.title("HR Data Quality Analyzer")
st.write("Upload an employee dataset (XLSX, JSON, XML) and run the built-in validation engine.")

uploaded = st.file_uploader("Upload Employee Dataset", type=["xlsx", "xls", "json", "xml"])

if uploaded is not None:
    # save uploaded file to a temporary file so existing readers can read by path
    suffix = Path(uploaded.name).suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = Path(tmp.name)

    st.markdown(f"**Uploaded file:** {uploaded.name}")

    # try to read using existing infer_and_read
    try:
        df = infer_and_read(tmp_path)
    except Exception as e:
        st.error(f"Failed to read uploaded file: {e}")
        st.stop()

    ndf = normalize_dataframe(df)
    total_records = len(ndf)
    st.info(f"Total Records: {total_records}")

    if st.button("Analyze Data"):
        with st.spinner("Running validations..."):
            completeness = run_completeness_checks(ndf)
            uniqueness = run_uniqueness_checks(ndf)
            validity = run_validity_checks(ndf, QUALITY_RULES)
            consistency = run_consistency_checks(ndf, COUNTRY_CURRENCY_MAP)
            anomalies = run_anomaly_checks(ndf, QUALITY_RULES)

            results = {
                'completeness': completeness,
                'uniqueness': uniqueness,
                'validity': validity,
                'consistency': consistency,
                'anomalies': anomalies,
            }

            overall_score = compute_scores({
                'completeness': completeness,
                'uniqueness': uniqueness,
                'validity': validity,
                'consistency': consistency,
                'anomalies': anomalies,
            })
            classification = classify_score(overall_score)

        # Executive summary cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Records", f"{total_records}")
        c2.metric("Quality Score", f"{overall_score}")
        c3.metric("Classification", classification)
        total_issues = sum([r.get('failed', 0) for r in results.values()])
        c4.metric("Total Issues", f"{total_issues}")

        # Issue counts by category
        st.subheader("Issue counts by category")
        counts = {k: v.get('failed', 0) for k, v in results.items()}
        cols = st.columns(5)
        for i, (k, v) in enumerate(counts.items()):
            cols[i].metric(k.capitalize(), v)

        # Severity visualization and category breakdown
        st.subheader("Issue breakdown")
        # Combine row issues for visualizations and table
        combined = []
        for k in ('completeness','uniqueness','validity','consistency','anomalies'):
            r = results.get(k, {})
            df_r = r.get('row_issues')
            if isinstance(df_r, pd.DataFrame) and not df_r.empty:
                df_copy = df_r.copy()
                df_copy['category'] = k
                # ensure standard columns exist
                if 'severity' not in df_copy.columns:
                    df_copy['severity'] = ''
                if 'employee_id' not in df_copy.columns:
                    df_copy['employee_id'] = df_copy.get('employee_id', '')
                combined.append(df_copy)
        if combined:
            combined_df = pd.concat(combined, ignore_index=True, sort=False)
            # normalize severity blanks
            combined_df['severity'] = combined_df['severity'].fillna('UNKNOWN')
        else:
            combined_df = pd.DataFrame(columns=['employee_id','field','value','rule','category','severity','message'])

        # severity counts
        st.write("Severity distribution")
        if not combined_df.empty:
            sev_counts = combined_df['severity'].value_counts()
            st.bar_chart(sev_counts)
        else:
            st.write("No issues to display.")

        # Filters
        st.subheader("Filters")
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        categories = combined_df['category'].unique().tolist() if not combined_df.empty else []
        selected_categories = filter_col1.multiselect("Category", options=sorted(categories), default=sorted(categories))
        severities = combined_df['severity'].unique().tolist() if not combined_df.empty else []
        selected_severities = filter_col2.multiselect("Severity", options=sorted(severities), default=sorted(severities))
        # employee id filter
        emp_input = filter_col3.text_input("Employee ID contains")
        # department filter (from normalized dataframe)
        dept_options = sorted(ndf['department'].dropna().unique().astype(str).tolist()) if 'department' in ndf.columns else []
        selected_departments = st.multiselect("Department", options=dept_options, default=dept_options)

        # apply filters to combined_df
        display_df = combined_df.copy()
        if selected_categories:
            display_df = display_df[display_df['category'].isin(selected_categories)]
        if selected_severities:
            display_df = display_df[display_df['severity'].isin(selected_severities)]
        if emp_input:
            display_df = display_df[display_df['employee_id'].astype(str).str.contains(emp_input, na=False, case=False)]
        if selected_departments and 'department' in ndf.columns:
            # join with source data to filter by department
            src_depts = ndf[['employee_id','department']].copy()
            src_depts['employee_id'] = src_depts['employee_id'].astype(str)
            display_df = display_df.merge(src_depts, on='employee_id', how='left')
            display_df = display_df[display_df['department'].isin(selected_departments)]

        # Row-level issues table with expanders
        st.subheader("Row-level issues")
        if not display_df.empty:
            st.dataframe(_safe_for_streamlit(display_df.reset_index(drop=True)))

            # allow download as CSV
            csv_bytes = display_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Row Issues CSV", csv_bytes, file_name=f"row_issues_{tmp_path.stem}.csv", mime='text/csv')

            # expandable sections per category
            for cat in sorted(display_df['category'].unique()):
                with st.expander(f"Details: {cat} ({len(display_df[display_df['category']==cat])})"):
                    st.dataframe(_safe_for_streamlit(display_df[display_df['category']==cat].reset_index(drop=True)))
        else:
            st.write("No row-level issues found.")

        # individual category tabs for backwards compatibility
        st.subheader("Per-category details")
        tabs = st.tabs(["Completeness","Uniqueness","Validity","Consistency","Anomalies"])

        # Completeness
        with tabs[0]:
            fields = completeness.get('fields', {})
            if fields:
                comp_rows = []
                for f,v in fields.items():
                    comp_rows.append({'Field': f, 'Total': v['total'], 'Populated': v['populated'], 'Missing': v['missing'], 'Completeness %': v['completeness_pct']})
                st.dataframe(_safe_for_streamlit(pd.DataFrame(comp_rows)))
            else:
                st.write("No completeness data available.")

        # Uniqueness
        with tabs[1]:
            uni_df = uniqueness.get('row_issues')
            if isinstance(uni_df, pd.DataFrame) and not uni_df.empty:
                st.dataframe(_safe_for_streamlit(uni_df.reset_index(drop=True)))
            else:
                st.write("No duplicates found.")

        # Validity
        with tabs[2]:
            val_df = validity.get('row_issues')
            if isinstance(val_df, pd.DataFrame) and not val_df.empty:
                st.dataframe(_safe_for_streamlit(val_df.reset_index(drop=True)))
            else:
                st.write("No validity issues found.")

        # Consistency
        with tabs[3]:
            cons_df = consistency.get('row_issues')
            if isinstance(cons_df, pd.DataFrame) and not cons_df.empty:
                st.dataframe(_safe_for_streamlit(cons_df.reset_index(drop=True)))
            else:
                st.write("No consistency issues found.")

        # Anomalies
        with tabs[4]:
            an_df = anomalies.get('row_issues')
            if isinstance(an_df, pd.DataFrame) and not an_df.empty:
                st.dataframe(_safe_for_streamlit(an_df.reset_index(drop=True)))
            else:
                st.write("No anomalies found.")

        # Generate report and provide download
        try:
            out_tmp = Path(tempfile.gettempdir()) / f"data_quality_report_{tmp_path.stem}.xlsx"
            generate_report(out_tmp, ndf, results, {'generated_at':'ui','source_file':uploaded.name,'total_records':total_records,'overall_score':overall_score,'classification':classification})
            with open(out_tmp, 'rb') as f:
                data = f.read()
            st.download_button("Download Excel Report", data, file_name=f"data_quality_report_{tmp_path.stem}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        except Exception as e:
            st.error(f"Failed to generate/download report: {e}")

    # show small preview of normalized data
    st.subheader("Preview of normalized data (first 10 rows)")
    st.dataframe(_safe_for_streamlit(ndf.head(10).reset_index(drop=True)))
else:
    st.info("Please upload a file to begin.")
