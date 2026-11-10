"""Pytest configuration and common fixtures for BAKAI India MCP."""

import sys
from pathlib import Path

# Add project root to sys.path so imports work cleanly in pytest
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
