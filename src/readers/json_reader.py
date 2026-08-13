import json
import pandas as pd
from pathlib import Path


def read_json(path: Path) -> pd.DataFrame:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Accept list of records or dict with top-level key
    if isinstance(data, dict):
        # try common keys
        for k in ('employees', 'data', 'records'):
            if k in data and isinstance(data[k], list):
                data = data[k]
                break
        else:
            # convert single record dict to list
            data = [data]
    return pd.DataFrame(data)
