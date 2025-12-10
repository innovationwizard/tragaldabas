"""Utility modules"""

from .encoding import detect_encoding
from .fuzzy import fuzzy_match_column
from .synonyms import normalize_column_name, COLUMN_SYNONYMS

__all__ = [
    "detect_encoding",
    "fuzzy_match_column",
    "normalize_column_name",
    "COLUMN_SYNONYMS",
]

