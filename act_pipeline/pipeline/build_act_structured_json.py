# act_pipeline/pipeline/build_act_structured_json.py

import os
import json
from datetime import datetime

from act_cleaner import clean_act
from act_parser import parse_act

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FOLDER = os.path.join(BASE_DIR, "data", "raw")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "data", "final_structured")


def process_factories_act():

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    input_path = os.path.join(RAW_FOLDER, "factory_act.md")

    with open(input_path, "r", encoding="utf-8") as f:
        raw_content = f.read()

    cleaned = clean_act(raw_content)
    structured_docs = parse_act(cleaned)

    output_data = {
        "metadata": {
            "act_name": "Factories Act, 1948",
            "processed_at": datetime.utcnow().isoformat(),
            "total_units": len(structured_docs),
            "source_type": "PRIMARY",
            "schema_version": "2.0"
        },
        "documents": structured_docs
    }

    output_path = os.path.join(
        OUTPUT_FOLDER,
        "factory_act_structured.json"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

    print(f"Structured JSON created at: {output_path}")
    print(f"Total structured units: {len(structured_docs)}")


if __name__ == "__main__":
    process_factories_act()
