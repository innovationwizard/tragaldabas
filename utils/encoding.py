"""Encoding detection utilities"""

from pathlib import Path
from typing import List


def detect_encoding(file_path: Path) -> str:
    """
    Detect file encoding with fallback support
    
    Args:
        file_path: Path to file
        
    Returns:
        Detected encoding string
    """
    # Try chardet if available
    try:
        import chardet
        with open(file_path, 'rb') as f:
            raw_sample = f.read(8192)
        
        result = chardet.detect(raw_sample)
        if result['encoding'] and result['confidence'] > 0.7:
            return result['encoding']
    except ImportError:
        pass
    
    # Fallback: try common encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    
    with open(file_path, 'rb') as f:
        raw_sample = f.read(4096)
    
    # Check for BOM
    if raw_sample.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    
    # Try each encoding
    for encoding in encodings:
        try:
            raw_sample.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Final fallback
    return 'latin-1'

