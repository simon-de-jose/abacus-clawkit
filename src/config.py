"""Configuration management for Abacus ClawKit"""

import yaml
from pathlib import Path
from typing import Dict, Any

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Load config
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml"""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

def get_db_path() -> Path:
    """Get database path from config"""
    config = load_config()
    return Path(config["database"]["path"])

def get_import_folder() -> Path:
    """Get import watch folder from config"""
    config = load_config()
    return Path(config["import"]["watch_folder"])

def get_category_taxonomy() -> Dict[str, list]:
    """Get category groups and their subcategories"""
    config = load_config()
    return config["categories"]["groups"]
