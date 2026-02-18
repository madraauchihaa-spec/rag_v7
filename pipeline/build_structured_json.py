# pipeline/build_structured_json.py

import os
import json

from .config import REPORT_CONFIG, RAW_DATA_FOLDER, OUTPUT_FOLDER
from .cleaner import remove_noise
from .parser import parse_markdown


def process_all_reports():

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    for filename, config in REPORT_CONFIG.items():

        input_path = os.path.join(RAW_DATA_FOLDER, filename)

        if not os.path.exists(input_path):
            print(f"File not found: {input_path}")
            continue

        with open(input_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        cleaned_content = remove_noise(raw_content)

        structured_records = parse_markdown(cleaned_content, config)

        output_filename = filename.replace(".md", "_structured.json")
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(structured_records, f, indent=4)

        print(f"Processed: {filename} → {output_filename}")


if __name__ == "__main__":
    process_all_reports()
