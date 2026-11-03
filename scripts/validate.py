import os
import csv
import json
import shutil
from typing import Dict, Any, List

def validate_environment_and_data(csv_path: str, config_path: str) -> Dict[str, Any]:
    """
    Validates CSV data, configuration file, models, fonts, and system tools.
    Returns parsed (config, rows) if valid; raises ValueError otherwise.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 1. Check tools
    for tool in ["ffmpeg", "ffprobe"]:
        if not shutil.which(tool):
            raise RuntimeError(f"Required command-line tool '{tool}' not found in PATH.")

    # 2. Check model files
    voice_model = config.get("voice_model", "")
    if not os.path.exists(voice_model):
        raise FileNotFoundError(f"Piper voice model not found: {voice_model}")

    # 3. Check font files
    for font_key in ["font_english", "font_chinese", "font_ipa"]:
        font_path = config.get(font_key, "")
        if font_path and not os.path.exists(font_path):
            raise FileNotFoundError(f"Font file for '{font_key}' not found: {font_path}")

    # 4. Check CSV
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    rows: List[Dict[str, Any]] = []
    seen_ids = set()
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required_cols = {"id", "english", "chinese"}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"CSV missing required columns: {required_cols - set(reader.fieldnames or [])}")

        for line_num, row in enumerate(reader, start=2):
            # Check for completely empty rows
            if not row or not any(row.values()):
                continue

            row_id = (row.get("id") or "").strip()
            english = (row.get("english") or "").strip()
            chinese = (row.get("chinese") or "").strip()

            if not row_id:
                raise ValueError(f"Line {line_num}: Empty 'id'.")
            if row_id in seen_ids:
                raise ValueError(f"Line {line_num}: Duplicate id '{row_id}'.")
            seen_ids.add(row_id)

            if not english:
                raise ValueError(f"Line {line_num}: Empty 'english' sentence.")
            if not chinese:
                raise ValueError(f"Line {line_num}: Empty 'chinese' sentence.")

            pause_sec = (row.get("pause_seconds") or "").strip()
            try:
                pause_val = float(pause_sec) if pause_sec else float(config.get("default_pause_seconds", 4.0))
                if pause_val < 1.0 or pause_val > 15.0:
                    raise ValueError(f"Line {line_num}: 'pause_seconds' must be between 1.0 and 15.0.")
            except ValueError:
                raise ValueError(f"Line {line_num}: Invalid 'pause_seconds' value: '{pause_sec}'")

            rows.append({
                "id": row_id,
                "topic": (row.get("topic") or "daily").strip(),
                "level": (row.get("level") or "A1").strip(),
                "english": english,
                "chinese": chinese,
                "pause_seconds": pause_val
            })

    print(f"Validation passed: {len(rows)} sentences loaded successfully.")
    return {"config": config, "rows": rows}

if __name__ == "__main__":
    import sys
    c_path = "config.json"
    d_path = "data/daily_001.csv"
    if len(sys.argv) > 2:
        c_path = sys.argv[1]
        d_path = sys.argv[2]
    validate_environment_and_data(csv_path=d_path, config_path=c_path)
