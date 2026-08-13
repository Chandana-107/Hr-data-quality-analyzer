import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path


def read_xml(path: Path) -> pd.DataFrame:
    tree = ET.parse(path)
    root = tree.getroot()
    # try to find repeated child elements
    records = []
    # naive approach: any child-level elements that repeat
    # assume records are grandchildren
    for child in root:
        # if child has children, treat child as a record
        if len(child):
            rec = {elem.tag: (elem.text or '').strip() for elem in child}
            records.append(rec)
    if not records:
        # fallback: root's direct children as records
        for child in root:
            records.append({child.tag: (child.text or '').strip()})
    return pd.DataFrame(records)
