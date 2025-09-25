from typing import List, Tuple, Optional
from .csv_utils import parse_csv_preview


def _detect_unique_candidate(headers: List[str], rows: List[dict]) -> Optional[str]:
    if not headers or not rows:
        return None
    common_candidates = ["id", "ID", "Id", "email", "email_address", "emailAddress", "uuid", "user_id", "username", "user"]
    for cand in common_candidates:
        if cand in headers:
            return cand

    for h in headers:
        vals = [r.get(h) for r in rows if r.get(h) not in (None, "")]
        if not vals:
            continue
        if len(set(vals)) == len(vals):
            return h
    return None


def build_preview_from_bytes(file_bytes: bytes, n_rows: int, template_job_name: Optional[str], unique_override: Optional[str] = None) -> Tuple[List[List[str]], List[str], str, List[str], Optional[str]]:
    """Parse CSV bytes and build preview rows and headers for UI.

    Returns: (display_rows, display_headers, status_msg, header_choices, selected_value)
    """
    if file_bytes is None:
        return [], [], "❌ No CSV file selected or failed to read", [], None

    headers, rows_dicts = parse_csv_preview(file_bytes, max_rows=n_rows)

    # Convert dict rows to list-of-lists preserving header order
    display_rows = []
    for r in rows_dicts:
        display_rows.append([r.get(h, "") or "" for h in headers])

    detected_unique = _detect_unique_candidate(headers, rows_dicts)
    chosen_unique = (unique_override if unique_override not in (None, "") else None) or detected_unique

    display_headers = headers.copy()
    if chosen_unique and chosen_unique in display_headers:
        display_headers.remove(chosen_unique)
        display_headers.insert(0, chosen_unique)
        reordered_rows = []
        for r in rows_dicts:
            reordered_rows.append([r.get(chosen_unique, "") or ""] + [r.get(h, "") or "" for h in display_headers[1:]])
        display_rows = reordered_rows

    display_headers = display_headers + ["_job_template"]
    display_rows = [row + [template_job_name or "<none>"] for row in display_rows]

    status_msg = f"✅ Previewing top {len(display_rows)} rows. Template: {template_job_name or '<none>'}"
    try:
        total_rows = file_bytes.count(b"\n")
        if total_rows > n_rows:
            status_msg += f" — approx total rows: {total_rows}"
    except Exception:
        pass

    header_choices = headers.copy()
    selected_value = chosen_unique if chosen_unique in header_choices else None

    return display_rows, display_headers, status_msg, header_choices, selected_value
