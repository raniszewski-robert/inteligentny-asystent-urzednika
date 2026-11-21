"""Asystent UDIP – core package (contracts: docs/plan/CONTRACTS.md).

One source of truth for the app and the skills: the skill scripts in .claude/skills/udip-*/scripts are thin CLI
wrappers over these modules. Data files (departments, name lists, letter types) live in udip/data/.
"""
from . import config as _config

_config.load_env()
