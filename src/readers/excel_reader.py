import pandas as pd
from pathlib import Path


def read_excel(path: Path) -> pd.DataFrame:
    """Read an Excel file into a DataFrame. Expects first sheet to contain data."""
    try:
        df = pd.read_excel(path, engine='openpyxl')
    except Exception:
        # try without engine (older pandas)
        df = pd.read_excel(path)
    return df
