"""
Electrochemistry calculation functions.

All functions implement standard textbook equations from electrochemistry references
such as Bard & Faulkner's "Electrochemical Methods: Fundamentals and Applications".
"""

import math
from typing import Optional
from .constants import FARADAY_CONSTANT, RANDLES_SEVCIK_CONSTANT, PI, GAS_CONSTANT


def randles_sevcik_diffusion_coefficient(
    peak_current_A: float,
    n: int,
    electrode_area_cm2: float,
    scan_rate_V_s: float,
    concentration_mol_cm3: float,
) -> float:
    """
    Calculate diffusion coefficient from Randles-Sevcik equation.

    Implements the Randles-Sevcik equation for cyclic voltammetry:
    ip = (2.69e5) * n^(3/2) * A * D^(1/2) * v^(1/2) * C
    
    Solves for D (diffusion coefficient in cm²/s) given the other parameters.
    
    Parameters
    ----------
    peak_current_A : float
        Peak current in amperes (A)
    n : int
        Number of electrons transferred in the redox reaction
    electrode_area_cm2 : float
        Electrode surface area in cm²
    scan_rate_V_s : float
        Scan rate in V/s
    concentration_mol_cm3 : float
        Bulk concentration of electroactive species in mol/cm³
    
    Returns
    -------
    float
        Diffusion coefficient in cm²/s
    
    Raises
    ------
    ValueError
        If any input is negative or zero where physically invalid
    
    References
    ----------
    Bard, A. J., & Faulkner, L. R. (2000). Electrochemical Methods: 
    Fundamentals and Applications (2nd ed.). Wiley. Chapter 6.
    """
    if peak_current_A <= 0:
        raise ValueError("Peak current must be positive")
    if n <= 0:
        raise ValueError("Number of electrons must be positive")
    if electrode_area_cm2 <= 0:
        raise ValueError("Electrode area must be positive")
    if scan_rate_V_s <= 0:
        raise ValueError("Scan rate must be positive")
    if concentration_mol_cm3 <= 0:
        raise ValueError("Concentration must be positive")
    
    # Rearrange Randles-Sevcik equation to solve for D:
    # D = [ip / (2.69e5 * n^(3/2) * A * v^(1/2) * C)]^2
    numerator = peak_current_A
    denominator = (
        RANDLES_SEVCIK_CONSTANT
        * (n ** 1.5)
        * electrode_area_cm2
        * math.sqrt(scan_rate_V_s)
        * concentration_mol_cm3
    )
    D = (numerator / denominator) ** 2
    return D


def nicholson_electron_transfer_rate(
    delta_ep_mV: float,
    scan_rate_V_s: float,
    diffusion_coefficient_cm2_s: float,
    n: int,
    temperature_K: float = 298.15,
) -> float:
    """
    Calculate heterogeneous electron transfer rate constant using Nicholson method.

    Relates peak separation (ΔEp) to the dimensionless kinetic parameter psi,
    then to the heterogeneous electron transfer rate constant k0.
    
    Uses the Nicholson working curve approximation for psi as a function of ΔEp.
    For reversible systems, ΔEp ≈ 59/n mV. As kinetics become slower, ΔEp increases.
    
    Parameters
    ----------
    delta_ep_mV : float
        Peak separation in millivolts (mV)
    scan_rate_V_s : float
        Scan rate in V/s
    diffusion_coefficient_cm2_s : float
        Diffusion coefficient in cm²/s
    n : int
        Number of electrons transferred
    temperature_K : float, optional
        Temperature in Kelvin, default 298.15 K (25°C)
    
    Returns
    -------
    float
        Heterogeneous electron transfer rate constant k0 in cm/s
    
    Raises
    ------
    ValueError
        If any input is negative or zero where physically invalid
    
    Notes
    -----
    The Nicholson method requires reading from an empirical working curve
    (Nicholson 1965, Table 1) rather than a closed-form equation. This implementation
    uses the Lavagnini et al. (2004) polynomial fit to that published table to approximate
    the relationship between ΔEp/n and the kinetic parameter ψ. The polynomial approximation is:
    ψ = (-0.6288 + 0.0021 * (ΔEp/n)) / (1 - 0.017 * (ΔEp/n))
    for 63 < ΔEp/n < 212 mV (quasi-reversible regime). For ΔEp/n ≤ 61 mV
    (near-reversible), ψ is treated as very large (k0 → ∞) consistent with
    reversible behavior. This empirical equation has been validated against
    the Lavagnini reference with 20% tolerance, accounting for the Nicholson
    method's known sensitivity to Ψ determination and variations in empirical
    fitting approaches in the literature.
    
    References
    ----------
    Nicholson, R. S. (1965). Theory and application of cyclic voltammetry for 
    measurement of electrode reaction kinetics. Analytical Chemistry, 37(11), 1351-1355.
    Lavagnini, I., Antiochia, R., & Magno, F. (2004). An extended method for
    the practical evaluation of the standard rate constant from cyclic
    voltammetric data. Electroanalysis, 16(6), 505-506. DOI: 10.1002/elan.200302851
    Bard & Faulkner, Chapter 6.5.2.
    """
    if delta_ep_mV <= 0:
        raise ValueError("Peak separation must be positive")
    if scan_rate_V_s <= 0:
        raise ValueError("Scan rate must be positive")
    if diffusion_coefficient_cm2_s <= 0:
        raise ValueError("Diffusion coefficient must be positive")
    if n <= 0:
        raise ValueError("Number of electrons must be positive")
    if temperature_K <= 0:
        raise ValueError("Temperature must be positive")
    
    # Convert ΔEp from mV to V for consistency
    delta_ep_V = delta_ep_mV / 1000.0
    
    # Nicholson working curve: psi as function of ΔEp (in mV)
    # This is an empirical relationship from Nicholson's 1965 paper
    # For ΔEp < 200 mV, use polynomial approximation
    delta_ep_mV_normalized = delta_ep_mV / n  # Normalize by n
    
    # Polynomial approximation of Nicholson working curve
    # Use Lavagnini et al. (2004) empirical equation:
    # Ψ = (-0.6288 + 0.0021 * nΔEp) / (1 - 0.017 * nΔEp)
    # Valid for nΔEp in range 63-212 mV (quasi-reversible regime)
    # This is a widely-accepted polynomial fit to Nicholson's original working curve
    
    # Reference: Lavagnini, I., Antiochia, R., & Magno, F. (2004). 
    # An extended method for the practical evaluation of the standard rate 
    # constant from cyclic voltammetric data. Electroanalysis, 16(6), 505-506.
    # DOI: 10.1002/elan.200302851
    
    if delta_ep_mV_normalized <= 61:
        # Near-reversible regime
        # psi → ∞ for reversible (use very large value)
        psi = 1e6
    elif delta_ep_mV_normalized > 212:
        # Irreversible regime - extrapolate using Lavagnini equation
        # (valid up to ~200 mV, but we allow extrapolation)
        psi = (-0.6288 + 0.0021 * delta_ep_mV_normalized) / (1 - 0.017 * delta_ep_mV_normalized)
    else:
        # Quasi-reversible regime - use Lavagnini equation
        psi = (-0.6288 + 0.0021 * delta_ep_mV_normalized) / (1 - 0.017 * delta_ep_mV_normalized)
    
    # Calculate k0 from psi: k0 = Ψ * sqrt(π * D * n * F * v / (R * T))
    # from Nicholson (1965) and Lavagnini et al. (2004)
    
    k0 = psi * math.sqrt((PI * diffusion_coefficient_cm2_s * n * FARADAY_CONSTANT * scan_rate_V_s) / (GAS_CONSTANT * temperature_K))
    
    return k0


def cottrell_current(
    diffusion_coefficient_cm2_s: float,
    concentration_mol_cm3: float,
    electrode_area_cm2: float,
    time_s: float,
    n: int,
) -> float:
    """
    Calculate current using Cottrell equation for potential step experiments.

    Implements the Cottrell equation for chronoamperometry:
    i(t) = n*F*A*D^(1/2)*C / (pi^(1/2) * t^(1/2))
    
    Describes the current decay after a potential step in diffusion-controlled
    electrochemical systems.
    
    Parameters
    ----------
    diffusion_coefficient_cm2_s : float
        Diffusion coefficient in cm²/s
    concentration_mol_cm3 : float
        Bulk concentration in mol/cm³
    electrode_area_cm2 : float
        Electrode area in cm²
    time_s : float
        Time after potential step in seconds
    n : int
        Number of electrons transferred
    
    Returns
    -------
    float
        Current in amperes (A)
    
    Raises
    ------
    ValueError
        If any input is negative or zero where physically invalid
    
    References
    ----------
    Cottrell, F. G. (1903). Derivation of the equation for the current in a 
    diffusion-controlled electrode reaction. Zeitschrift für Physikalische Chemie, 42, 385-431.
    Bard & Faulkner, Chapter 5.2.1.
    """
    if diffusion_coefficient_cm2_s <= 0:
        raise ValueError("Diffusion coefficient must be positive")
    if concentration_mol_cm3 <= 0:
        raise ValueError("Concentration must be positive")
    if electrode_area_cm2 <= 0:
        raise ValueError("Electrode area must be positive")
    if time_s <= 0:
        raise ValueError("Time must be positive")
    if n <= 0:
        raise ValueError("Number of electrons must be positive")
    
    # i(t) = n*F*A*D^(1/2)*C / (pi^(1/2) * t^(1/2))
    current = (
        n
        * FARADAY_CONSTANT
        * electrode_area_cm2
        * math.sqrt(diffusion_coefficient_cm2_s)
        * concentration_mol_cm3
    ) / (math.sqrt(PI) * math.sqrt(time_s))
    
    return current


def randles_sevcik_peak_current(
    n: int,
    electrode_area_cm2: float,
    scan_rate_V_s: float,
    concentration_mol_cm3: float,
    diffusion_coefficient_cm2_s: float,
) -> float:
    """
    Calculate peak current from Randles-Sevcik equation (forward direction).

    Implements the Randles-Sevcik equation for cyclic voltammetry:
    ip = (2.69e5) * n^(3/2) * A * D^(1/2) * v^(1/2) * C
    
    This is the forward direction: computes peak current given the diffusion
    coefficient and other parameters. Used by the CV simulator.
    
    Parameters
    ----------
    n : int
        Number of electrons transferred in the redox reaction
    electrode_area_cm2 : float
        Electrode surface area in cm²
    scan_rate_V_s : float
        Scan rate in V/s
    concentration_mol_cm3 : float
        Bulk concentration of electroactive species in mol/cm³
    diffusion_coefficient_cm2_s : float
        Diffusion coefficient in cm²/s
    
    Returns
    -------
    float
        Peak current in amperes (A)
    
    Raises
    ------
    ValueError
        If any input is negative or zero where physically invalid
    
    References
    ----------
    Bard, A. J., & Faulkner, L. R. (2000). Electrochemical Methods: 
    Fundamentals and Applications (2nd ed.). Wiley. Chapter 6.
    """
    if n <= 0:
        raise ValueError("Number of electrons must be positive")
    if electrode_area_cm2 <= 0:
        raise ValueError("Electrode area must be positive")
    if scan_rate_V_s <= 0:
        raise ValueError("Scan rate must be positive")
    if concentration_mol_cm3 <= 0:
        raise ValueError("Concentration must be positive")
    if diffusion_coefficient_cm2_s <= 0:
        raise ValueError("Diffusion coefficient must be positive")
    
    # ip = (2.69e5) * n^(3/2) * A * D^(1/2) * v^(1/2) * C
    peak_current_A = (
        RANDLES_SEVCIK_CONSTANT
        * (n ** 1.5)
        * electrode_area_cm2
        * math.sqrt(diffusion_coefficient_cm2_s)
        * math.sqrt(scan_rate_V_s)
        * concentration_mol_cm3
    )
    return peak_current_A


def lod_from_signal_to_noise(
    sensitivity: float,
    noise_std: float,
    factor: float = 3.0,
) -> float:
    """
    Calculate limit of detection (LOD) or limit of quantification (LOQ).

    Computes LOD = factor * noise_std / sensitivity
    Standard definition: factor=3.0 for LOD (3-sigma), factor=10.0 for LOQ (10-sigma).
    
    Parameters
    ----------
    sensitivity : float
        Sensitivity (slope of calibration curve) in signal units per concentration unit
    noise_std : float
        Standard deviation of noise (blank signal) in signal units
    factor : float, optional
        Multiplicative factor for LOD calculation. Default 3.0 for LOD.
        Use 10.0 for LOQ calculation.
    
    Returns
    -------
    float
        Limit of detection in concentration units
    
    Raises
    ------
    ValueError
        If sensitivity is zero or negative, or if noise_std is negative
    
    References
    ----------
    IUPAC. Compendium of Chemical Terminology (Gold Book). 
    https://doi.org/10.1351/goldbook.L03611
    """
    if sensitivity <= 0:
        raise ValueError("Sensitivity must be positive")
    if noise_std < 0:
        raise ValueError("Noise standard deviation cannot be negative")
    
    lod = factor * noise_std / sensitivity
    return lod
