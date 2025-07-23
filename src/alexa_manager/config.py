"""
config.py

Configuration loading and constants for the Alexa management script.

This module centralizes configuration logic and constants, separating them from main.py for better maintainability and clarity.
"""

import logging
import os
import sys
from typing import Dict

# Use the built-in tomllib for TOML parsing (Python 3.11+)
if sys.version_info >= (3, 11):
    import tomllib
else:
    raise ImportError("Python 3.11+ is required for tomllib support.")


# NOTE: Logging is set up twice (here and after config loading) to ensure
# that errors during config loading are captured. The initial setup uses INFO
# level, and is updated to DEBUG/INFO after config is loaded. This is intentional.
def setup_initial_logging() -> None:
    """
    Set up a basic logging configuration at INFO level for early-stage logging.

    Returns:
        None
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def update_logging_level(debug: bool) -> None:
    """
    Update the logging level based on the debug flag from the config.

    Args:
        debug (bool): If True, set logging to DEBUG; otherwise, INFO.

    Returns:
        None
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.getLogger().setLevel(level)


def read_toml_file(filepath: str) -> Dict:
    """
    Read a TOML file and return its contents as a dictionary.

    Args:
        filepath (str): Path to the TOML file.

    Returns:
        Dict: Parsed TOML content.

    Raises:
        FileNotFoundError: If the file does not exist.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
    """
    with open(filepath, "rb") as f:
        return tomllib.load(f)


def ensure_user_config_exists(global_path: str, user_path: str) -> None:
    """
    Ensure that the user config file exists by copying from the global config if needed.

    Args:
        global_path (str): Path to the global config file.
        user_path (str): Path to the user config file.

    Returns:
        None
    """
    if not os.path.exists(user_path):
        with (
            open(global_path, "r", encoding="utf-8") as src,
            open(user_path, "w", encoding="utf-8") as dst,
        ):
            dst.write(src.read())


def load_config(
    global_path: str = "config/global_config.toml",
    user_path: str = "config/user_config.toml",
) -> Dict:
    """
    Load and merge configuration from config/global_config.toml and config/user_config.toml.
    Sets up logging at INFO level before config is loaded, then updates log level.

    Args:
        global_path (str): Path to the global config file.
        user_path (str): Path to the user config file.

    Returns:
        Dict: The merged configuration dictionary.

    Raises:
        SystemExit: If config files are malformed or cannot be loaded.
    """
    setup_initial_logging()
    try:
        global_config = read_toml_file(global_path)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        logging.error(f"Error loading {global_path}: {e}")
        sys.exit(1)
    ensure_user_config_exists(global_path, user_path)
    try:
        user_config = read_toml_file(user_path)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        logging.error(f"Error loading {user_path}: {e}")
        sys.exit(1)
    config = {**global_config, **user_config}
    update_logging_level(config.get("DEBUG", False))
    return config


# Load config and constants
config: Dict = load_config()

DEBUG: bool = config["DEBUG"]
SHOULD_SLEEP: bool = config["SHOULD_SLEEP"]
DO_NOT_DELETE: bool = config["DO_NOT_DELETE"]
ALEXA_HOST: str = config["ALEXA_HOST"]
COOKIE: str = config["COOKIE"]
X_AMZN_ALEXA_APP: str = config["X_AMZN_ALEXA_APP"]
CSRF: str = config["CSRF"]
DELETE_SKILL: str = config["DELETE_SKILL"]
USER_AGENT: str = config["USER_AGENT"]
ROUTINE_VERSION: str = config["ROUTINE_VERSION"]
HA_HOST: str = config["HA_HOST"]
HA_API_KEY: str = config["HA_API_KEY"]

DEBUG_FILES: Dict[str, str] = {
    "entities": "entities_debug.json",
    "groups": "groups_debug.json",
    "graphql": "graphql_debug.json",
}

URLS: Dict[str, str] = {
    "GET_ENTITIES": f"https://{ALEXA_HOST}/api/behaviors/entities?skillId=amzn1.ask.1p.smarthome",
    "GET_GROUPS": f"https://{ALEXA_HOST}/api/phoenix/group",
    "DELETE_ENTITIES": f"https://{ALEXA_HOST}/api/phoenix/appliance/{DELETE_SKILL}%3D%3D_",
    "DELETE_GROUP": f"https://{ALEXA_HOST}/api/phoenix/group/",
    "HA_TEMPLATE": f"https://{HA_HOST}/api/template",
}

ALEXA_HEADERS: Dict[str, str] = {
    "Host": ALEXA_HOST,
    "x-amzn-alexa-app": X_AMZN_ALEXA_APP,
    "Connection": "keep-alive",
    "Accept": "application/json; charset=utf-8",
    "User-Agent": USER_AGENT,
    "csrf": CSRF,
    "Cookie": COOKIE,
}

HA_HEADERS: Dict[str, str] = {
    "Authorization": f"Bearer {HA_API_KEY}",
    "Content-Type": "application/json",
}
