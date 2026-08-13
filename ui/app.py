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
        st.write(counts)

        # Detailed findings
        st.subheader("Validation Findings")
        tabs = st.tabs(["Completeness","Uniqueness","Validity","Consistency","Anomalies","Row Issues"])

        # Completeness
        with tabs[0]:
            fields = completeness.get('fields', {})
            if fields:
                comp_rows = []
                for f,v in fields.items():
                    comp_rows.append({'Field': f, 'Total': v['total'], 'Populated': v['populated'], 'Missing': v['missing'], 'Completeness %': v['completeness_pct']})
                st.dataframe(pd.DataFrame(comp_rows))
            else:
                st.write("No completeness data available.")

        # Uniqueness
        with tabs[1]:
            uni_df = uniqueness.get('row_issues')
            if isinstance(uni_df, pd.DataFrame) and not uni_df.empty:
                st.dataframe(uni_df)
            else:
                st.write("No duplicates found.")

        # Validity
        with tabs[2]:
            val_df = validity.get('row_issues')
            if isinstance(val_df, pd.DataFrame) and not val_df.empty:
                st.dataframe(val_df)
            else:
                st.write("No validity issues found.")

        # Consistency
        with tabs[3]:
            cons_df = consistency.get('row_issues')
            if isinstance(cons_df, pd.DataFrame) and not cons_df.empty:
                st.dataframe(cons_df)
            else:
                st.write("No consistency issues found.")

        # Anomalies
        with tabs[4]:
            an_df = anomalies.get('row_issues')
            if isinstance(an_df, pd.DataFrame) and not an_df.empty:
                st.dataframe(an_df)
            else:
                st.write("No anomalies found.")

        # Row Issues combined
        with tabs[5]:
            combined = []
            for k in ('completeness','uniqueness','validity','consistency','anomalies'):
                r = results.get(k, {})
                df_r = r.get('row_issues')
                if isinstance(df_r, pd.DataFrame) and not df_r.empty:
                    df_copy = df_r.copy()
                    df_copy['category'] = k
                    combined.append(df_copy)
            if combined:
                combined_df = pd.concat(combined, ignore_index=True, sort=False).fillna('')
                st.dataframe(combined_df)
            else:
                st.write("No row-level issues found.")

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
    st.dataframe(ndf.head(10))
else:
    st.info("Please upload a file to begin.")
