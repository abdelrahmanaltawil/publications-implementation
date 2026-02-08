
import sys
import os
from pathlib import Path

# Add project root to sys.path
# This assumes conftest.py is in tests/ directory, and project root is one level up
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
