"""
CV/LSV and EIS Analyzer Module

This module provides functionality for analyzing electrochemical data:
- CV/LSV peak detection and parameter extraction
- Randles-Sevcik analysis for diffusion coefficients
- Nicholson method for electron transfer rates
- EIS circuit fitting using Randles equivalent circuit
- LOD/LOQ estimation from baseline noise
"""

from .file_parser import parse_cv_lsv_file, parse_eis_file
from .cv_lsv_analyzer import (
    detect_peaks,
    calculate_randles_sevcik_diffusion,
    calculate_nicholson_k0,
    calculate_lod_loq
)
from .eis_analyzer import fit_eis_circuit, generate_nyquist_bode_data

__all__ = [
    'parse_cv_lsv_file',
    'parse_eis_file',
    'detect_peaks',
    'calculate_randles_sevcik_diffusion',
    'calculate_nicholson_k0',
    'calculate_lod_loq',
    'fit_eis_circuit',
    'generate_nyquist_bode_data'
]