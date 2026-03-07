import sys
import os

# Add backend root to Python path so `from app.xxx` imports work when
# running pytest from the backend/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
