from typing import List, Dict, Tuple, Optional
import io
import csv

ENCODINGS = ["utf-8", "cp932", "shift_jis", "latin1"]


def parse_csv_preview(data: bytes, max_rows: int = 5) -> Tuple[List[str], List[Dict[str, Optional[str]]]]:
    """Try multiple encodings to decode CSV bytes and return headers and up to max_rows rows.

    Returns (headers, rows). Headers is a list of fieldnames (may be empty list if none).
    Rows is a list of dicts mapping header -> value. Missing fields map to None.
    """
    last_exc: Optional[Exception] = None
    for enc in ENCODINGS:
        try:
            text = data.decode(enc)
        except Exception as e:  # decoding failed for this encoding
            last_exc = e
            continue

        # Use csv module to parse
        try:
            f = io.StringIO(text)
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows: List[Dict[str, Optional[str]]] = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                # Normalize None values
                norm_row = {k: (v if v != "" else None) for k, v in row.items()} if row else {}
                rows.append(norm_row)
            return headers, rows
        except Exception as e:
            last_exc = e
            continue

    # If all encodings failed, raise the last exception
    raise RuntimeError(f"Failed to parse CSV with available encodings: {last_exc}")
