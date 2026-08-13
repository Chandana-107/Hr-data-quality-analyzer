import argparse
import logging
from pathlib import Path
from datetime import datetime

from src.readers.excel_reader import read_excel
from src.readers.json_reader import read_json
from src.readers.xml_reader import read_xml
from src.utils.normalization import normalize_dataframe
from src.config.rules import QUALITY_RULES, COUNTRY_CURRENCY_MAP
from src.validators.completeness import run_completeness_checks
from src.validators.uniqueness import run_uniqueness_checks
from src.validators.validity import run_validity_checks
from src.validators.consistency import run_consistency_checks
from src.validators.anomalies import run_anomaly_checks
from src.report.excel_report import generate_report
from src.utils.logging import configure_logging


def infer_and_read(path: Path):
    ext = path.suffix.lower()
    if ext in ('.xlsx', '.xls'):
        return read_excel(path)
    if ext == '.json':
        return read_json(path)
    if ext == '.xml':
        return read_xml(path)
    raise ValueError(f"Unsupported file extension: {ext}")


def compute_scores(results, weights=None):
    # results is dict with category: {'total','passed','failed','score'}
    if weights is None:
        weights = {"completeness": 0.25, "uniqueness": 0.20, "validity": 0.25, "consistency": 0.15, "anomalies": 0.15}
    total = 0.0
    for k, w in weights.items():
        score = results.get(k, {}).get('score', 100)
        total += score * w
    return round(total, 2)


def classify_score(score, thresholds=None):
    if thresholds is None:
        thresholds = {"EXCELLENT": 95, "GOOD": 90, "NEEDS REVIEW": 75}
    if score >= thresholds["EXCELLENT"]:
        return "EXCELLENT"
    if score >= thresholds["GOOD"]:
        return "GOOD"
    if score >= thresholds["NEEDS REVIEW"]:
        return "NEEDS REVIEW"
    return "NOT READY FOR MIGRATION"


def main():
    configure_logging()
    parser = argparse.ArgumentParser(description="HR Data Quality Analyzer")
    parser.add_argument('--input', '-i', required=True, help='Input file (.xlsx, .json, .xml)')
    parser.add_argument('--output', '-o', required=True, help='Output Excel report (.xlsx)')
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logging.error("Input file not found: %s", input_path)
        raise SystemExit(1)

    try:
        df = infer_and_read(input_path)
    except Exception as e:
        logging.exception("Failed to read input file: %s", e)
        raise SystemExit(1)

    df = normalize_dataframe(df)
    total_records = len(df)
    logging.info("Total records after normalization: %d", total_records)

    results = {}

    completeness = run_completeness_checks(df)
    results['completeness'] = completeness

    uniqueness = run_uniqueness_checks(df)
    results['uniqueness'] = uniqueness

    validity = run_validity_checks(df, QUALITY_RULES)
    results['validity'] = validity

    consistency = run_consistency_checks(df, COUNTRY_CURRENCY_MAP)
    results['consistency'] = consistency

    anomalies = run_anomaly_checks(df, QUALITY_RULES)
    results['anomalies'] = anomalies

    overall_score = compute_scores({
        'completeness': completeness,
        'uniqueness': uniqueness,
        'validity': validity,
        'consistency': consistency,
        'anomalies': anomalies
    })
    classification = classify_score(overall_score)

    meta = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'source_file': str(input_path),
        'total_records': total_records,
        'overall_score': overall_score,
        'classification': classification
    }

    try:
        generate_report(output_path, df, results, meta)
        logging.info("Report written to %s", output_path)
    except Exception as e:
        logging.exception("Failed to write report: %s", e)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
