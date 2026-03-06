import logging
import os
import json
from datetime import datetime

# Setup logging directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configure main logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "system_v7.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("RAG_V7")

def log_rag_flow(step_name, data):
    """
    Logs a specific step in the RAG pipeline with its corresponding data.
    """
    try:
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, indent=2, default=str)
        else:
            data_str = str(data)
        
        logger.info(f"\n--- [PHASE: {step_name}] ---\n{data_str}\n")
    except Exception as e:
        logger.error(f"Logging error in {step_name}: {e}")
