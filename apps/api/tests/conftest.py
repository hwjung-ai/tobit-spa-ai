"""Test configuration and fixtures."""

import sys
from pathlib import Path

# Add the app root to sys.path so imports work correctly
app_root = Path(__file__).parent.parent
sys.path.insert(0, str(app_root))

# Also add parent directory for 'apps' package
apps_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(apps_root))
