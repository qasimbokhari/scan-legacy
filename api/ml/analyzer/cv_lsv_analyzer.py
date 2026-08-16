"""
CV/LSV analysis functions for peak detection and parameter extraction.

Includes:
- Peak detection (anodic and cathodic)
- Randles-Sevcik analysis for diffusion coefficients
- Nicholson method for electron transfer rate constants
- LOD/LOQ estimation from baseline noise
"""

import numpy as np
from scipy.signal import find_peaks
from scipy.stats import linregress
from typing import Dict, Any, Optional, Tuple
from app.schemas.prediction import PredictionEnvelope
from app.ml.physics.electrochemistry import (
    randles_sevcik_diffusion_coefficient,
    nicholson_electron_transfer_rate
)


def detect_peaks(potential: np.ndarray, current: np.ndarray) -> Dict[str, Any]:
    """
    Detect anodic and cathodic peaks in CV/LSV data.
    
    Parameters
    ----------
    potential : np.ndarray
        Potential values in V
    current : np.ndarray
        Current values in A
    
    Returns
    -------
    dict
        Dictionary containing peak information with PredictionEnvelope wrappers
    """
    # Find anodic peak (positive current)
    anodic_peaks, _ = find_peaks(current, prominence=np.std(current) * 0.5)
    
    # Find cathodic peak (negative current) - invert current for detection
    cathodic_peaks, _ = find_peaks(-current, prominence=np.std(current) * 0.5)
    
    # Extract peak information
    anodic_peak = None
    cathodic_peak = None
    
    if len(anodic_peaks) > 0:
        # Find the highest anodic peak
        max_anodic_idx = anodic_peaks[np.argmax(current[anodic_peaks])]
        anodic_peak = {
            'potential_v': float(potential[max_anodic_idx]),
            'current_a': float(current[max_anodic_idx]),
            'index': int(max_anodic_idx)
        }
    
    if len(cathodic_peaks) > 0:
        # Find the most negative cathodic peak
        min_cathodic_idx = cathodic_peaks[np.argmin(current[cathodic_peaks])]
        cathodic_peak = {
            'potential_v': float(potential[min_cathodic_idx]),
            'current_a': float(current[min_cathodic_idx]),
            'index': int(min_cathodic_idx)
        }
    
    # Calculate peak separation if both peaks exist
    peak_separation_mv = None
    if anodic_peak and cathodic_peak:
        peak_separation_mv = abs(anodic_peak['potential_v'] - cathodic_peak['potential_v']) * 1000
    
    return {
        'anodic_peak': anodic_peak,
        'cathodic_peak': cathodic_peak,
        'peak_separation_mv': peak_separation_mv,
        'n_anodic_peaks': len(anodic_peaks),
        'n_cathodic_peaks': len(cathodic_peaks)
    }


def calculate_randles_sevcik_diffusion(
    peak_currents: list[float],
    scan_rates: list[float],
    electrode_area_cm2: float,
    concentration_mol_cm3: float,
    n_electrons: int = 1
) -> PredictionEnvelope:
    """
    Calculate diffusion coefficient using Randles-Sevcik equation.
    
    For multi-scan rate data: performs linear fit of ip vs sqrt(v)
    For single scan rate: returns single-point estimate with flag
    
    Parameters
    ----------
    peak_currents : list[float]
        Peak currents in A for each scan rate
    scan_rates : list[float]
        Scan rates in V/s
    electrode_area_cm2 : float
        Electrode area in cm²
    concentration_mol_cm3 : float
        Concentration in mol/cm³
    n_electrons : int
        Number of electrons transferred
    
    Returns
    -------
    PredictionEnvelope
        Diffusion coefficient with confidence interval
    """
    if len(peak_currents) != len(scan_rates):
        raise ValueError("Peak currents and scan rates must have same length")
    
    if len(peak_currents) == 0:
        raise ValueError("At least one data point required")
    
    if len(peak_currents) == 1:
        # Single-point estimate - flag as needing multi-rate data
        D = randles_sevcik_diffusion_coefficient(
            peak_current_A=peak_currents[0],
            n=n_electrons,
            electrode_area_cm2=electrode_area_cm2,
            scan_rate_V_s=scan_rates[0],
            concentration_mol_cm3=concentration_mol_cm3
        )
        
        # Large uncertainty for single-point estimate
        confidence_factor = 0.5  # ±50%
        return PredictionEnvelope(
            value=D,
            confidence_band=(D * (1 - confidence_factor), D * (1 + confidence_factor)),
            method="Randles-Sevcik (single-point)",
            caveat="Single-point estimate - multi-scan rate data needed for reliable fit",
            is_verified=True,
            fit_quality=None,
            residual_std_error=None
        )
    
    # Multi-scan rate: perform linear fit of ip vs sqrt(v)
    sqrt_scan_rates = np.sqrt(scan_rates)
    
    # Linear regression: ip = m * sqrt(v) + b
    slope, intercept, r_value, p_value, std_err = linregress(sqrt_scan_rates, peak_currents)
    
    # Calculate D from slope: ip = (2.69e5) * n^(3/2) * A * D^(1/2) * C * sqrt(v)
    # slope = (2.69e5) * n^(3/2) * A * D^(1/2) * C
    # D = [slope / ((2.69e5) * n^(3/2) * A * C)]^2
    
    from app.ml.physics.constants import RANDLES_SEVCIK_CONSTANT
    
    numerator = slope
    denominator = (
        RANDLES_SEVCIK_CONSTANT
        * (n_electrons ** 1.5)
        * electrode_area_cm2
        * concentration_mol_cm3
    )
    
    D = (numerator / denominator) ** 2
    
    # Estimate uncertainty from fit quality
    # Use slope uncertainty to propagate to D uncertainty
    slope_relative_error = std_err / abs(slope) if slope != 0 else 0.5
    D_relative_error = 2 * slope_relative_error  # D ∝ slope²
    
    confidence_band = (
        D * (1 - D_relative_error),
        D * (1 + D_relative_error)
    )
    
    return PredictionEnvelope(
        value=D,
        confidence_band=confidence_band,
        method="Randles-Sevcik (multi-scan rate fit)",
        caveat=None,
        is_verified=True,
        fit_quality=float(r_value ** 2),  # R²
        residual_std_error=float(std_err)
    )


def calculate_nicholson_k0(
    peak_separation_mv: float,
    scan_rate_V_s: float,
    diffusion_coefficient_cm2_s: float,
    n_electrons: int = 1,
    temperature_K: float = 298.15
) -> PredictionEnvelope:
    """
    Calculate electron transfer rate constant using Nicholson method.
    
    Parameters
    ----------
    peak_separation_mv : float
        Peak separation in mV
    scan_rate_V_s : float
        Scan rate in V/s
    diffusion_coefficient_cm2_s : float
        Diffusion coefficient in cm²/s
    n_electrons : int
        Number of electrons transferred
    temperature_K : float
        Temperature in Kelvin
    
    Returns
    -------
    PredictionEnvelope
        Electron transfer rate constant with caveat about unverified accuracy
    """
    try:
        k0 = nicholson_electron_transfer_rate(
            delta_ep_mV=peak_separation_mv,
            scan_rate_V_s=scan_rate_V_s,
            diffusion_coefficient_cm2_s=diffusion_coefficient_cm2_s,
            n=n_electrons,
            temperature_K=temperature_K
        )
        
        # Large uncertainty due to unverified Nicholson implementation
        confidence_factor = 0.8  # ±80%
        
        return PredictionEnvelope(
            value=k0,
            confidence_band=(
                max(0, k0 * (1 - confidence_factor)),
                k0 * (1 + confidence_factor)
            ),
            method="Nicholson method",
            caveat="Unverified quantitative accuracy - Nicholson implementation not yet validated against reference data",
            is_verified=False,
            fit_quality=None,
            residual_std_error=None
        )
    except Exception as e:
        raise ValueError(f"Nicholson calculation failed: {str(e)}")


def calculate_lod_loq(
    current: np.ndarray,
    potential: np.ndarray,
    baseline_region: Optional[Tuple[float, float]] = None
) -> Dict[str, PredictionEnvelope]:
    """
    Calculate LOD and LOQ from baseline noise.
    
    Parameters
    ----------
    current : np.ndarray
        Current values in A
    potential : np.ndarray
        Potential values in V
    baseline_region : tuple[float, float], optional
        (min_potential, max_potential) defining baseline region.
        If None, uses first 20% of data as baseline.
    
    Returns
    -------
    dict
        Dictionary with LOD and LOQ as PredictionEnvelope objects
    """
    # Determine baseline region
    if baseline_region is None:
        # Use first 20% of data as baseline
        baseline_idx = int(len(current) * 0.2)
        baseline_current = current[:baseline_idx]
    else:
        # Use specified potential range
        baseline_mask = (potential >= baseline_region[0]) & (potential <= baseline_region[1])
        baseline_current = current[baseline_mask]
    
    if len(baseline_current) < 5:
        raise ValueError("Insufficient baseline data points for LOD/LOQ calculation")
    
    # Calculate baseline statistics
    baseline_std = np.std(baseline_current)
    baseline_mean = np.mean(baseline_current)
    
    # LOD = 3 * std, LOQ = 10 * std (standard definition)
    lod = 3 * baseline_std
    loq = 10 * baseline_std
    
    # Confidence intervals (using standard error of the mean)
    n_baseline = len(baseline_current)
    std_error = baseline_std / np.sqrt(n_baseline)
    
    lod_envelope = PredictionEnvelope(
        value=lod,
        confidence_band=(
            max(0, lod - 2 * std_error),
            lod + 2 * std_error
        ),
        method="LOD from baseline noise (3σ)",
        caveat=None,
        is_verified=True,
        fit_quality=None,
        residual_std_error=float(std_error)
    )
    
    loq_envelope = PredictionEnvelope(
        value=loq,
        confidence_band=(
            max(0, loq - 2 * std_error),
            loq + 2 * std_error
        ),
        method="LOQ from baseline noise (10σ)",
        caveat=None,
        is_verified=True,
        fit_quality=None,
        residual_std_error=float(std_error)
    )
    
    return {
        'lod': lod_envelope,
        'loq': loq_envelope,
        'baseline_mean': float(baseline_mean),
        'baseline_std': float(baseline_std),
        'n_baseline_points': n_baseline
    }