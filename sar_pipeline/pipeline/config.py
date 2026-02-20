# pipeline/config.py

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RAW_DATA_FOLDER = os.path.join(BASE_DIR, "data", "raw")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "data", "final_structured")


REPORT_CONFIG = {
    "sar1.md": {
        "report_id": "SAR_001",
        "industry_type": "Chemical",
        "mah_status": "Non_MAH"
    },
    "sar2.md": {
        "report_id": "SAR_002",
        "industry_type": "Engineering",
        "mah_status": "Non_MAH"
    },
    "sar3.md": {
        "report_id": "SAR_003",
        "industry_type": "Agrochemical",
        "mah_status": "MAH"
    }
}


ANNEXURE_TYPE_MAP = {
    "A": "non_compliance",
    "B": "record_verification",
    "C": "management_audit"
}
