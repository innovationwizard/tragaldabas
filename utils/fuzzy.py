"""Fuzzy matching utilities"""

from typing import Dict, List, Optional
from config import settings

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


def fuzzy_match_column(
    column_name: str,
    synonym_dict: Dict[str, List[str]],
    threshold: Optional[int] = None
) -> Optional[str]:
    """
    Fuzzy match column name against synonym dictionary
    
    Args:
        column_name: Column name to match
        synonym_dict: Dictionary of canonical -> synonyms
        threshold: Match threshold (0-100), defaults to config
        
    Returns:
        Canonical name if match found, None otherwise
    """
    if not RAPIDFUZZ_AVAILABLE:
        return None
    
    threshold = threshold or settings.FUZZY_MATCH_THRESHOLD
    
    best_match = None
    best_score = 0
    
    for canonical, synonyms in synonym_dict.items():
        # Check exact match first
        if column_name in synonyms or column_name == canonical:
            return canonical
        
        # Fuzzy match against all synonyms
        for synonym in synonyms:
            score = fuzz.ratio(column_name, synonym)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = canonical
    
    return best_match


def fuzzy_match_string(
    text: str,
    candidates: List[str],
    threshold: int = 80
) -> Optional[str]:
    """
    Fuzzy match a string against a list of candidates
    
    Args:
        text: Text to match
        candidates: List of candidate strings
        threshold: Match threshold (0-100)
        
    Returns:
        Best match if above threshold, None otherwise
    """
    if not RAPIDFUZZ_AVAILABLE or not candidates:
        return None
    
    result = process.extractOne(text, candidates, scorer=fuzz.ratio)
    
    if result and result[1] >= threshold:
        return result[0]
    
    return None

