"""
File parsing utilities for CV/LSV and EIS data files.

Supports .csv, .txt, .xlsx formats with automatic column detection.
"""

import io
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from fastapi import HTTPException
except ImportError:
    # For testing without FastAPI
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: dict):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)


def parse_cv_lsv_file(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse CV/LSV data file and extract potential and current columns.
    
    Auto-detects column names from common variations:
    - Potential: potential, voltage, E, V, potential_V, voltage_V
    - Current: current, i, I, current_A, current_uA, i_uA
    
    Parameters
    ----------
    file_content : bytes
        Raw file content
    filename : str
        Original filename for format detection
    
    Returns
    -------
    dict
        Dictionary with 'potential' and 'current' arrays, plus metadata
    
    Raises
    ------
    HTTPException
        If file cannot be parsed or columns cannot be detected
    """
    try:
        # Determine file format
        if filename.endswith('.csv') or filename.endswith('.txt'):
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(
                    status_code=200,
                    detail={
                        "success": False,
                        "error": "Could not decode file with supported encodings",
                        "error_type": "parse_error"
                    }
                )
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
        else:
            raise HTTPException(
                status_code=200,
                detail={
                    "success": False,
                    "error": f"Unsupported file format: {filename}",
                    "error_type": "parse_error"
                }
            )
        
        # Auto-detect columns
        potential_col, current_col = _detect_cv_lsv_columns(df)
        
        if potential_col is None or current_col is None:
            raise HTTPException(
                status_code=200,
                detail={
                    "success": False,
                    "error": f"Could not detect potential/current columns. Available columns: {list(df.columns)}",
                    "error_type": "parse_error"
                }
            )
        
        # Extract data
        potential = df[potential_col].values
        current = df[current_col].values
        
        # Remove NaN values
        valid_mask = ~(np.isnan(potential) | np.isnan(current))
        potential = potential[valid_mask]
        current = current[valid_mask]
        
        if len(potential) < 10:
            raise HTTPException(
                status_code=200,
                detail={
                    "success": False,
                    "error": f"Insufficient data points after cleaning: {len(potential)} (minimum 10 required)",
                    "error_type": "parse_error"
                }
            )
        
        return {
            'potential': potential.tolist(),
            'current': current.tolist(),
            'potential_units': _detect_units(potential_col),
            'current_units': _detect_units(current_col),
            'n_points': len(potential),
            'potential_column': potential_col,
            'current_column': current_col
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=200,
            detail={
                "success": False,
                "error": f"Error parsing file: {str(e)}",
                "error_type": "parse_error"
            }
        )


def parse_eis_file(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse EIS data file and extract frequency, Z_real, and Z_imag columns.
    
    Auto-detects column names from common variations:
    - Frequency: frequency, freq, f, Frequency_Hz
    - Z_real: Z_real, Zreal, Z', real, Re, Z_re
    - Z_imag: Z_imag, Zimag, Z'', imag, Im, Z_im (negative for capacitive)
    
    Parameters
    ----------
    file_content : bytes
        Raw file content
    filename : str
        Original filename for format detection
    
    Returns
    -------
    dict
        Dictionary with 'frequency', 'Z_real', and 'Z_imag' arrays, plus metadata
    
    Raises
    ------
    HTTPException
        If file cannot be parsed or columns cannot be detected
    """
    try:
        # Determine file format
        if filename.endswith('.csv') or filename.endswith('.txt'):
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(
                    status_code=200,
                    detail={
                        "success": False,
                        "error": "Could not decode file with supported encodings",
                        "error_type": "parse_error"
                    }
                )
        else:
            raise HTTPException(
                status_code=200,
                detail={
                    "success": False,
                    "error": f"Unsupported file format for EIS: {filename} (only .csv and .txt supported)",
                    "error_type": "parse_error"
                }
            )
        
        # Auto-detect columns
        freq_col, z_real_col, z_imag_col = _detect_eis_columns(df)
        
        if freq_col is None or z_real_col is None or z_imag_col is None:
            raise HTTPException(
                status_code=200,
                detail={
                    "success": False,
                    "error": f"Could not detect frequency/Z_real/Z_imag columns. Available columns: {list(df.columns)}",
                    "error_type": "parse_error"
                }
            )
        
        # Extract data
        frequency = df[freq_col].values
        z_real = df[z_real_col].values
        z_imag = df[z_imag_col].values
        
        # Remove NaN values
        valid_mask = ~(np.isnan(frequency) | np.isnan(z_real) | np.isnan(z_imag))
        frequency = frequency[valid_mask]
        z_real = z_real[valid_mask]
        z_imag = z_imag[valid_mask]
        
        if len(frequency) < 5:
            raise HTTPException(
                status_code=200,
                detail={
                    "success": False,
                    "error": f"Insufficient data points after cleaning: {len(frequency)} (minimum 5 required)",
                    "error_type": "parse_error"
                }
            )
        
        return {
            'frequency': frequency.tolist(),
            'Z_real': z_real.tolist(),
            'Z_imag': z_imag.tolist(),
            'n_points': len(frequency),
            'frequency_column': freq_col,
            'z_real_column': z_real_col,
            'z_imag_column': z_imag_col
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=200,
            detail={
                "success": False,
                "error": f"Error parsing EIS file: {str(e)}",
                "error_type": "parse_error"
            }
        )


def _detect_cv_lsv_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Auto-detect potential and current columns in CV/LSV data."""
    columns_lower = [col.lower() for col in df.columns]
    
    # Potential column detection
    potential_keywords = ['potential', 'voltage', 'e', 'v']
    potential_col = None
    for keyword in potential_keywords:
        for i, col in enumerate(columns_lower):
            if keyword in col:
                potential_col = df.columns[i]
                break
        if potential_col:
            break
    
    # Current column detection
    current_keywords = ['current', 'i', 'current_a', 'current_ua', 'i_ua']
    current_col = None
    for keyword in current_keywords:
        for i, col in enumerate(columns_lower):
            if keyword in col and col != potential_col.lower() if potential_col else True:
                current_col = df.columns[i]
                break
        if current_col:
            break
    
    return potential_col, current_col


def _detect_eis_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Auto-detect frequency, Z_real, and Z_imag columns in EIS data."""
    columns_lower = [col.lower() for col in df.columns]
    
    # Frequency column detection
    freq_keywords = ['frequency', 'freq', 'f']
    freq_col = None
    for keyword in freq_keywords:
        for i, col in enumerate(columns_lower):
            if keyword in col:
                freq_col = df.columns[i]
                break
        if freq_col:
            break
    
    # Z_real column detection
    z_real_keywords = ['z_real', 'zreal', "z'", 'real', 're', 'z_re']
    z_real_col = None
    for keyword in z_real_keywords:
        for i, col in enumerate(columns_lower):
            if keyword in col:
                z_real_col = df.columns[i]
                break
        if z_real_col:
            break
    
    # Z_imag column detection
    z_imag_keywords = ['z_imag', 'zimag', 'z"', 'imag', 'im', 'z_im']
    z_imag_col = None
    for keyword in z_imag_keywords:
        for i, col in enumerate(columns_lower):
            if keyword in col:
                z_imag_col = df.columns[i]
                break
        if z_imag_col:
            break
    
    return freq_col, z_real_col, z_imag_col


def _detect_units(column_name: str) -> str:
    """Detect units from column name."""
    column_lower = column_name.lower()
    
    if '_v' in column_lower or 'volt' in column_lower:
        return 'V'
    elif '_a' in column_lower or 'amp' in column_lower:
        return 'A'
    elif '_ua' in column_lower or 'ua' in column_lower:
        return 'µA'
    elif '_ma' in column_lower or 'ma' in column_lower:
        return 'mA'
    else:
        return 'unknown'