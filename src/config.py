"""Configuration management for Abacus ClawKit"""

import os
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
    """Get database path from env var or config"""
    # Check environment variable first
    env_path = os.getenv("ABACUS_DB_PATH")
    if env_path:
        return Path(env_path)
    
    # Fall back to config
    config = load_config()
    db_path = Path(config["database"]["path"])
    
    # If relative, resolve from project root
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    
    return db_path

def get_import_folder() -> Path:
    """Get import watch folder from env var or config"""
    # Check environment variable first
    env_path = os.getenv("ABACUS_IMPORT_DIR")
    if env_path:
        return Path(env_path)
    
    # Fall back to config
    config = load_config()
    import_path = Path(config["import"]["watch_folder"])
    
    # If relative, resolve from project root
    if not import_path.is_absolute():
        import_path = PROJECT_ROOT / import_path
    
    return import_path

def get_category_taxonomy() -> Dict[str, list]:
    """Get category groups and their subcategories"""
    config = load_config()
    return config["categories"]["groups"]
