"""
Simulation package for generating synthetic electrochemical data.

Provides CV and EIS simulators that use the validated physics layer
to generate realistic synthetic traces for testing and validation.
"""

from .cv_simulator import generate_cv_curve, save_cv_curve_to_file
from .eis_simulator import generate_eis_spectrum, save_eis_spectrum_to_file

__all__ = [
    'generate_cv_curve',
    'save_cv_curve_to_file',
    'generate_eis_spectrum',
    'save_eis_spectrum_to_file',
]
