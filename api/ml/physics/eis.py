"""
Electrochemical Impedance Spectroscopy (EIS) calculation functions.

Implements Randles circuit impedance calculations and parameter fitting
using standard equivalent circuit models.
"""

import math
from typing import Optional, Dict, Any
import numpy as np
from scipy.optimize import curve_fit
from .constants import PI


def randles_circuit_impedance(
    frequency_Hz: float | np.ndarray,
    Rs: float,
    Rct: float,
    Cdl: float,
    warburg_coefficient: float = 0.0,
) -> complex | np.ndarray:
    """
    Calculate complex impedance for a Randles equivalent circuit.

    The Randles circuit consists of:
    - Rs: Solution resistance (series)
    - Rct: Charge transfer resistance (parallel with Cdl)
    - Cdl: Double layer capacitance (parallel with Rct)
    - Warburg: Diffusion element (optional, in series with Rct)
    
    Total impedance: Z = Rs + Z_parallel
    where Z_parallel = (Rct + Zw) || (1/(j*omega*Cdl))
    and Zw = Warburg impedance = sigma * (1-j) / sqrt(omega)
    
    Parameters
    ----------
    frequency_Hz : float or np.ndarray
        Frequency in Hz (can be scalar or array)
    Rs : float
        Solution resistance in ohms
    Rct : float
        Charge transfer resistance in ohms
    Cdl : float
        Double layer capacitance in farads
    warburg_coefficient : float, optional
        Warburg coefficient (sigma) in ohm·s^(-1/2). Default 0.0 (no Warburg element)
    
    Returns
    -------
    complex or np.ndarray
        Complex impedance in ohms (scalar or array matching input)
    
    Raises
    ------
    ValueError
        If frequency is negative, or if Rs, Rct, Cdl are negative
    
    References
    ----------
    Orazem, M. E., & Tribollet, B. (2017). Electrochemical Impedance Spectroscopy (2nd ed.). Wiley.
    Barsoukov, E., & Macdonald, J. R. (2005). Impedance Spectroscopy: Theory, Experiment, and Applications (2nd ed.). Wiley.
    """
    if Rs < 0:
        raise ValueError("Solution resistance cannot be negative")
    if Rct < 0:
        raise ValueError("Charge transfer resistance cannot be negative")
    if Cdl < 0:
        raise ValueError("Double layer capacitance cannot be negative")
    
    # Convert to numpy array for vectorized operations
    freq = np.asarray(frequency_Hz)
    
    # Check for negative frequencies
    if np.any(freq < 0):
        raise ValueError("Frequency cannot be negative")
    
    # Angular frequency
    omega = 2 * PI * freq
    
    # Warburg impedance: Zw = sigma * (1-j) / sqrt(omega)
    if warburg_coefficient > 0:
        # Handle omega=0 case before division
        omega_safe = np.where(omega > 0, omega, 1.0)  # Avoid division by zero
        Zw = warburg_coefficient * (1 - 1j) / np.sqrt(omega_safe)
        Zw = np.where(omega > 0, Zw, 0)  # At DC, Warburg impedance = 0
    else:
        Zw = 0
    
    # Impedance of Rct + Warburg branch
    Z_ct = Rct + Zw
    
    # Impedance of capacitor branch - handle omega=0 to avoid division by zero
    # At DC (omega=0), capacitor acts as open circuit (infinite impedance)
    omega_safe = np.where(omega > 0, omega, 1.0)  # Avoid division by zero
    Z_C = 1 / (1j * omega_safe * Cdl)
    Z_C = np.where(omega > 0, Z_C, np.inf)
    
    # Handle DC case (frequency = 0) - capacitor acts as open circuit
    # For numerical stability, use np.where to handle omega=0
    Z_parallel = np.where(
        omega > 0,
        (Z_ct * Z_C) / (Z_ct + Z_C),
        Rct  # At DC, Z_parallel = Rct (capacitor open circuit)
    )
    
    # Total impedance
    Z_total = Rs + Z_parallel
    
    # Return scalar if input was scalar
    if np.isscalar(frequency_Hz):
        return complex(Z_total)
    
    return Z_total


def fit_randles_circuit(
    frequencies_Hz: list[float],
    impedance_real: list[float],
    impedance_imag: list[float],
    initial_guess: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Fit Randles circuit parameters to experimental impedance data.

    Uses scipy.optimize.curve_fit to fit Rs, Rct, Cdl, and Warburg coefficient
    to a given set of frequency/impedance data points.
    
    Parameters
    ----------
    frequencies_Hz : list[float]
        List of frequencies in Hz
    impedance_real : list[float]
        List of real impedance components in ohms
    impedance_imag : list[float]
        List of imaginary impedance components in ohms (negative for capacitive)
    initial_guess : dict, optional
        Dictionary with initial guesses for parameters. Keys: 'Rs', 'Rct', 'Cdl', 'warburg'
        If None, uses defaults: Rs=100, Rct=1000, Cdl=1e-6, warburg=0
    
    Returns
    -------
    dict
        Dictionary containing:
        - 'parameters': dict with fitted values (Rs, Rct, Cdl, warburg)
        - 'std_errors': dict with standard errors of fitted parameters
        - 'covariance': covariance matrix from curve_fit
    
    Raises
    ------
    ValueError
        If input arrays have different lengths or are empty
    
    References
    ----------
    Orazem & Tribollet, Chapter 10.
    """
    if len(frequencies_Hz) != len(impedance_real) or len(frequencies_Hz) != len(impedance_imag):
        raise ValueError("All input arrays must have the same length")
    if len(frequencies_Hz) == 0:
        raise ValueError("Input arrays cannot be empty")
    
    # Set default initial guess
    if initial_guess is None:
        initial_guess = {
            'Rs': 100.0,
            'Rct': 1000.0,
            'Cdl': 1e-6,
            'warburg': 0.0,
        }
    
    # Convert to numpy arrays
    freq = np.array(frequencies_Hz)
    Z_real = np.array(impedance_real)
    Z_imag = np.array(impedance_imag)
    
    # Define residual function for least_squares
    def residuals(params):
        Rs, Rct, Cdl, warburg = params
        Z = randles_circuit_impedance(freq, Rs, Rct, Cdl, warburg)
        # Return concatenated residuals (real and imaginary)
        return np.concatenate([Z.real - Z_real, Z.imag - Z_imag])
    
    # Set parameter bounds (all parameters must be non-negative)
    lower_bounds = [0.0, 0.0, 0.0, 0.0]
    upper_bounds = [np.inf, np.inf, np.inf, np.inf]
    
    # Initial parameters
    p0 = np.array([initial_guess['Rs'], initial_guess['Rct'], initial_guess['Cdl'], initial_guess['warburg']])
    
    # Use least_squares for fitting
    from scipy.optimize import least_squares
    
    try:
        result = least_squares(
            residuals,
            p0,
            bounds=(lower_bounds, upper_bounds),
            max_nfev=10000,
        )
        
        popt = result.x
        # Approximate covariance from Jacobian
        if result.jac is not None:
            # Covariance = (J^T J)^-1 * variance
            J = result.jac
            pcov = np.linalg.inv(J.T @ J) * (result.cost / (len(freq) * 2 - 4))
        else:
            pcov = np.eye(4) * 1e-6  # Fallback
            
    except Exception as e:
        raise ValueError(f"Fitting failed: {str(e)}")
    
    # Calculate standard errors from covariance matrix
    perr = np.sqrt(np.diag(pcov))
    
    return {
        'parameters': {
            'Rs': float(popt[0]),
            'Rct': float(popt[1]),
            'Cdl': float(popt[2]),
            'warburg': float(popt[3]),
        },
        'std_errors': {
            'Rs': float(perr[0]),
            'Rct': float(perr[1]),
            'Cdl': float(perr[2]),
            'warburg': float(perr[3]),
        },
        'covariance': pcov.tolist(),
    }
