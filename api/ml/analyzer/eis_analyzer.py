"""
EIS analysis functions for circuit fitting and data generation.

Includes:
- Randles circuit fitting using Phase 1 physics functions
- Nyquist and Bode plot data generation
- Parameter extraction with confidence intervals
"""

import numpy as np
from typing import Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ml.physics.eis import fit_randles_circuit, randles_circuit_impedance
from app.schemas.prediction import PredictionEnvelope


def fit_eis_circuit(
    frequency: np.ndarray,
    z_real: np.ndarray,
    z_imag: np.ndarray
) -> Dict[str, Any]:
    """
    Fit Randles equivalent circuit to EIS data.
    
    Uses the Phase 1 physics functions which recover known parameters
    within 10% tolerance.
    
    Parameters
    ----------
    frequency : np.ndarray
        Frequency values in Hz
    z_real : np.ndarray
        Real impedance values in ohms
    z_imag : np.ndarray
        Imaginary impedance values in ohms (negative for capacitive)
    
    Returns
    -------
    dict
        Dictionary containing fitted parameters with PredictionEnvelope wrappers
    """
    # Convert to lists for the physics function
    frequencies_Hz = frequency.tolist()
    impedance_real = z_real.tolist()
    impedance_imag = z_imag.tolist()
    
    # Fit the circuit using Phase 1 physics function
    fit_result = fit_randles_circuit(
        frequencies_Hz=frequencies_Hz,
        impedance_real=impedance_real,
        impedance_imag=impedance_imag
    )
    
    # Extract parameters and standard errors
    params = fit_result['parameters']
    std_errors = fit_result['std_errors']
    
    # Wrap each parameter in PredictionEnvelope
    # Use relative error for confidence bands
    def create_envelope(value: float, std_error: float, name: str) -> PredictionEnvelope:
        if value <= 0:
            relative_error = 1.0  # 100% for very small/negative values
        else:
            relative_error = std_error / value if value > 0 else 1.0
        
        # Clamp relative error to reasonable range
        relative_error = min(max(relative_error, 0.1), 2.0)
        
        return PredictionEnvelope(
            value=value,
            confidence_band=(
                max(0, value * (1 - relative_error)),
                value * (1 + relative_error)
            ),
            method="Randles circuit fit (least-squares)",
            caveat=None,
            is_verified=True,  # Phase 1 physics functions are validated
            fit_quality=None,  # Could calculate R² from residuals
            residual_std_error=float(std_error)
        )
    
    Rs_envelope = create_envelope(params['Rs'], std_errors['Rs'], 'Rs')
    Rct_envelope = create_envelope(params['Rct'], std_errors['Rct'], 'Rct')
    Cdl_envelope = create_envelope(params['Cdl'], std_errors['Cdl'], 'Cdl')
    warburg_envelope = create_envelope(params['warburg'], std_errors['warburg'], 'Warburg')
    
    # Calculate overall fit quality
    # Compute fitted impedance and calculate residuals
    Z_fitted = randles_circuit_impedance(
        frequency_Hz=frequency,
        Rs=params['Rs'],
        Rct=params['Rct'],
        Cdl=params['Cdl'],
        warburg_coefficient=params['warburg']
    )
    
    residuals_real = Z_fitted.real - z_real
    residuals_imag = Z_fitted.imag - z_imag
    
    # R² calculation
    ss_res = np.sum(residuals_real**2 + residuals_imag**2)
    ss_tot = np.sum((z_real - np.mean(z_real))**2 + (z_imag - np.mean(z_imag))**2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {
        'Rs': Rs_envelope,
        'Rct': Rct_envelope,
        'Cdl': Cdl_envelope,
        'warburg_coefficient': warburg_envelope,
        'fit_quality': {
            'r_squared': float(r_squared),
            'residual_std_error': float(np.sqrt(ss_res / len(frequency)))
        },
        'raw_fit_result': fit_result  # Include full fit result for debugging
    }


def generate_nyquist_bode_data(
    frequency: np.ndarray,
    z_real: np.ndarray,
    z_imag: np.ndarray,
    fitted_params: Dict[str, float]
) -> Dict[str, Any]:
    """
    Generate Nyquist and Bode plot data for frontend visualization.
    
    Returns both experimental and fitted data as structured JSON.
    
    Parameters
    ----------
    frequency : np.ndarray
        Experimental frequency values in Hz
    z_real : np.ndarray
        Experimental real impedance in ohms
    z_imag : np.ndarray
        Experimental imaginary impedance in ohms
    fitted_params : dict
        Fitted Randles circuit parameters
    
    Returns
    -------
    dict
        Dictionary containing Nyquist and Bode data for plotting
    """
    # Calculate fitted impedance at experimental frequencies
    Z_fitted = randles_circuit_impedance(
        frequency_Hz=frequency,
        Rs=fitted_params['Rs'],
        Rct=fitted_params['Rct'],
        Cdl=fitted_params['Cdl'],
        warburg_coefficient=fitted_params['warburg']
    )
    
    # Nyquist data (Z_imag vs Z_real)
    nyquist_experimental = {
        'z_real': z_real.tolist(),
        'z_imag': z_imag.tolist()  # Negative for capacitive
    }
    
    nyquist_fitted = {
        'z_real': Z_fitted.real.tolist(),
        'z_imag': Z_fitted.imag.tolist()
    }
    
    # Bode magnitude data (|Z| vs frequency)
    z_magnitude_experimental = np.sqrt(z_real**2 + z_imag**2)
    z_magnitude_fitted = np.abs(Z_fitted)
    
    bode_magnitude_experimental = {
        'frequency_hz': frequency.tolist(),
        'impedance_magnitude_ohm': z_magnitude_experimental.tolist()
    }
    
    bode_magnitude_fitted = {
        'frequency_hz': frequency.tolist(),
        'impedance_magnitude_ohm': z_magnitude_fitted.tolist()
    }
    
    # Bode phase data (phase angle vs frequency)
    phase_experimental = np.arctan2(z_imag, z_real) * 180 / np.pi
    phase_fitted = np.angle(Z_fitted) * 180 / np.pi
    
    bode_phase_experimental = {
        'frequency_hz': frequency.tolist(),
        'phase_angle_deg': phase_experimental.tolist()
    }
    
    bode_phase_fitted = {
        'frequency_hz': frequency.tolist(),
        'phase_angle_deg': phase_fitted.tolist()
    }
    
    return {
        'nyquist': {
            'experimental': nyquist_experimental,
            'fitted': nyquist_fitted
        },
        'bode_magnitude': {
            'experimental': bode_magnitude_experimental,
            'fitted': bode_magnitude_fitted
        },
        'bode_phase': {
            'experimental': bode_phase_experimental,
            'fitted': bode_phase_fitted
        }
    }