"""UTF-8 JSON storage with atomic single-file replacement."""
import json
import os
from pathlib import Path
import tempfile


def load_records(path):
    """Return (records, errors). Missing or malformed files are explicit errors."""
    try:
        rows = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as error:
        return [], [f'{path}: {error}']
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return [], [f'{path}: 必須為物件清單。']
    return rows, []


def save_records(path, records):
    """Save a list atomically; failures propagate and leave the original intact."""
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError('資料必須為物件清單。')
    payload = json.dumps(records, ensure_ascii=False, indent=4, allow_nan=False) + '\n'
    path, temporary = Path(path), None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False, suffix='.tmp') as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
