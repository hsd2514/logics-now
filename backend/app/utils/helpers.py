import uuid
from datetime import datetime
from typing import Any, Dict

def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())

def format_currency(amount: float) -> str:
    """Format amount as Indian currency."""
    return f"₹{amount:,.2f}"

def format_percentage(value: float) -> str:
    """Format value as percentage."""
    return f"{value * 100:.1f}%"

def safe_get(data: Dict, *keys, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

def timestamp_now() -> str:
    """Get current timestamp as ISO string."""
    return datetime.now().isoformat()
