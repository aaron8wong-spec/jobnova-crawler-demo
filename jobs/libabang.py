import sys
import os
import logging
import json
import re
from dotenv import load_dotenv

# Get the parent directory
parent_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(os.path.realpath(parent_dir))
sys.path.append(parent_dir)

load_dotenv(".env")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

class API:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating new API instance")
            cls._instance = super(API, cls).__new__(cls)
        return cls._instance

    def analyze(self, item):
        return [20]