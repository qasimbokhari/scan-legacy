"""
Nanomaterial calculation functions.

Implements standard equations for nanoparticle properties including
diffusion, surface area, and zeta potential corrections.
"""

import math
from .constants import BOLTZMANN_CONSTANT, PI, VACUUM_PERMITTIVITY, ELEMENTARY_CHARGE


def stokes_einstein_diffusion_coefficient(
    temperature_K: float,
    viscosity_Pa_s: float,
    particle_radius_m: float,
) -> float:
    """
    Calculate diffusion coefficient using Stokes-Einstein equation.

    Implements the Stokes-Einstein equation for Brownian motion of spherical particles:
    D = kB*T / (6*pi*eta*r)
    
    where kB is Boltzmann's constant, T is temperature, eta is dynamic viscosity,
    and r is particle radius.
    
    Parameters
    ----------
    temperature_K : float
        Temperature in Kelvin
    viscosity_Pa_s : float
        Dynamic viscosity of the medium in Pa·s
    particle_radius_m : float
        Particle radius in meters
    
    Returns
    -------
    float
        Diffusion coefficient in m²/s
    
    Raises
    ------
    ValueError
        If temperature, viscosity, or radius is negative or zero
    
    References
    ----------
    Einstein, A. (1905). Über die von der molekularkinetischen Theorie der Wärme 
    geforderte Bewegung von in ruhenden Flüssigkeiten suspendierten Teilchen.
    Annalen der Physik, 17, 549-560.
    """
    if temperature_K <= 0:
        raise ValueError("Temperature must be positive")
    if viscosity_Pa_s <= 0:
        raise ValueError("Viscosity must be positive")
    if particle_radius_m <= 0:
        raise ValueError("Particle radius must be positive")
    
    D = (BOLTZMANN_CONSTANT * temperature_K) / (6 * PI * viscosity_Pa_s * particle_radius_m)
    return D


def surface_area_to_volume_ratio(particle_radius_nm: float) -> float:
    """
    Calculate surface area to volume ratio for a spherical nanoparticle.

    For a sphere: SA = 4*pi*r², V = (4/3)*pi*r³
    Therefore: SA/V = 3/r
    
    Parameters
    ----------
    particle_radius_nm : float
        Particle radius in nanometers
    
    Returns
    -------
    float
        Surface area to volume ratio in nm⁻¹
    
    Raises
    ------
    ValueError
        If particle radius is negative or zero
    
    References
    ----------
    Standard geometry formula for spheres.
    """
    if particle_radius_nm <= 0:
        raise ValueError("Particle radius must be positive")
    
    sa_v_ratio = 3.0 / particle_radius_nm
    return sa_v_ratio


def debye_huckel_corrected_zeta_potential(
    raw_zeta_mV: float,
    ionic_strength_mol_L: float,
    temperature_K: float = 298.15,
) -> float:
    """
    Apply Debye-Hückel-based ionic strength correction to zeta potential.

    Applies a correction factor based on the Debye length (κ⁻¹) to account for
    the effect of ionic strength on zeta potential measurements.
    
    The Debye length is calculated as:
    κ⁻¹ = sqrt(ε₀εᵣkT / (2NAe²I))
    
    where ε₀ is vacuum permittivity, εᵣ is relative permittivity of water (~78.5 at 25°C),
    k is Boltzmann's constant, T is temperature, NA is Avogadro's number,
    e is elementary charge, and I is ionic strength.
    
    The correction factor approximates the double layer compression effect:
    higher ionic strength leads to shorter Debye length and reduced zeta potential.
    
    Parameters
    ----------
    raw_zeta_mV : float
        Raw measured zeta potential in millivolts
    ionic_strength_mol_L : float
        Ionic strength of the solution in mol/L
    temperature_K : float, optional
        Temperature in Kelvin, default 298.15 K (25°C)
    
    Returns
    -------
    float
        Corrected zeta potential in millivolts
    
    Raises
    ------
    ValueError
        If ionic strength is negative or temperature is negative or zero
    
    Notes
    -----
    This is an approximation, not an exact physical law. The correction assumes:
    - Dilute electrolyte solution (Debye-Hückel approximation valid)
    - Relative permittivity of water ≈ 78.5 at 25°C
    - Symmetric electrolyte behavior
    - The correction factor is: exp(-κ * a) where a is a characteristic length scale
      (approximated here as 1 nm for typical nanoparticles)
    
    This implementation approximates the double-layer compression effect
    using an exponential decay model based on Debye length. For precise
    corrections requiring the full Henry function (which accounts for
    electrophoretic retardation effects), use numerical evaluation of
    Henry's equation or the limiting cases: Hückel limit (κa ≪ 1, f=1.0)
    and Smoluchowski limit (κa ≫ 1, f=1.5).
    
    References
    ----------
    Debye, P., & Hückel, E. (1923). Zur Theorie der Elektrolyte. 
    Physikalische Zeitschrift, 24, 185-206.
    Hunter, R. J. (1981). Zeta Potential in Colloid Science. Academic Press.
    Henry, D. C. (1931). Proc. R. Soc. Lond. A, 133, 106-129 (Henry function).
    """
    if ionic_strength_mol_L < 0:
        raise ValueError("Ionic strength cannot be negative")
    if temperature_K <= 0:
        raise ValueError("Temperature must be positive")
    
    # If ionic strength is zero, no correction needed
    if ionic_strength_mol_L == 0:
        return raw_zeta_mV
    
    # Relative permittivity of water at 25°C
    epsilon_r = 78.5
    
    # Avogadro's number (mol^-1)
    NA = 6.02214076e23
    
    # Elementary charge (C)
    e = ELEMENTARY_CHARGE
    
    # Calculate Debye length (in meters)
    # κ⁻¹ = sqrt(ε₀εᵣkT / (2NAe²I))
    # Convert ionic strength from mol/L to mol/m³ (multiply by 1000)
    I_m3 = ionic_strength_mol_L * 1000
    
    numerator = VACUUM_PERMITTIVITY * epsilon_r * BOLTZMANN_CONSTANT * temperature_K
    denominator = 2 * NA * (e ** 2) * I_m3
    
    debye_length_m = math.sqrt(numerator / denominator)
    
    # Convert Debye length to nm
    debye_length_nm = debye_length_m * 1e9
    
    # Characteristic length scale (approximate as 1 nm for typical nanoparticles)
    a_nm = 1.0
    
    # Correction factor based on double layer compression
    # Higher ionic strength (shorter Debye length) reduces effective zeta potential
    kappa = 1.0 / debye_length_nm
    correction_factor = math.exp(-kappa * a_nm)
    
    # Apply correction
    corrected_zeta_mV = raw_zeta_mV * correction_factor
    
    return corrected_zeta_mV


def debye_length(
    ionic_strength_mol_L: float,
    temperature_K: float = 298.15,
    epsilon_r: float = 78.5,
) -> float:
    """
    Calculate Debye length for a given ionic strength and temperature.

    The Debye length (κ⁻¹) is the characteristic length scale of electrical
    double layer screening in electrolyte solutions.
    
    κ⁻¹ = sqrt(ε₀εᵣkT / (2NAe²I))
    
    Parameters
    ----------
    ionic_strength_mol_L : float
        Ionic strength of the solution in mol/L
    temperature_K : float, optional
        Temperature in Kelvin, default 298.15 K (25°C)
    epsilon_r : float, optional
        Relative permittivity of the solvent, default 78.5 for water at 25°C
    
    Returns
    -------
    float
        Debye length in meters
    
    Raises
    ------
    ValueError
        If ionic strength is negative or temperature is negative or zero
    
    References
    ----------
    Debye, P., & Hückel, E. (1923). Physikalische Zeitschrift, 24, 185-206.
    """
    if ionic_strength_mol_L < 0:
        raise ValueError("Ionic strength cannot be negative")
    if temperature_K <= 0:
        raise ValueError("Temperature must be positive")
    
    # If ionic strength is zero, Debye length is infinite
    if ionic_strength_mol_L == 0:
        return float('inf')
    
    # Avogadro's number (mol^-1)
    NA = 6.02214076e23
    
    # Elementary charge (C)
    e = ELEMENTARY_CHARGE
    
    # Calculate Debye length (in meters)
    # Convert ionic strength from mol/L to mol/m³ (multiply by 1000)
    I_m3 = ionic_strength_mol_L * 1000
    
    numerator = VACUUM_PERMITTIVITY * epsilon_r * BOLTZMANN_CONSTANT * temperature_K
    denominator = 2 * NA * (e ** 2) * I_m3
    
    debye_length_m = math.sqrt(numerator / denominator)
    
    return debye_length_m


def henry_function_approximation(kappa_a: float) -> float:
    """
    Approximate Henry function f(κa) for electrophoretic mobility calculations.

    The Henry function describes the relationship between electrophoretic
    mobility and zeta potential, accounting for double layer retardation effects.
    It has two well-known limiting cases:
    - Hückel limit (κa ≪ 1): f(κa) → 1.0
    - Smoluchowski limit (κa ≫ 1): f(κa) → 1.5
    
    This implementation uses a smooth interpolation between the limits:
    f(κa) = 1.0 + 0.5 * (1 - exp(-κa))
    
    Parameters
    ----------
    kappa_a : float
        Dimensionless parameter κa, where κ is the Debye length inverse
        and a is the particle radius
    
    Returns
    -------
    float
        Henry function value f(κa)
    
    Notes
    -----
    This is an approximation. For precise calculations, numerical evaluation
    of the full Henry integral equation may be required for intermediate κa values.
    
    References
    ----------
    Henry, D. C. (1931). Proc. R. Soc. Lond. A, 133, 106-129.
    Hunter, R. J. (1981). Zeta Potential in Colloid Science. Academic Press.
    """
    if kappa_a < 0:
        raise ValueError("κa must be non-negative")
    
    # Smooth interpolation between Hückel (1.0) and Smoluchowski (1.5) limits
    # f(κa) = 1.0 + 0.5 * (1 - exp(-κa))
    # This gives: f(0) = 1.0, f(∞) = 1.5, and smooth transition
    henry_f = 1.0 + 0.5 * (1 - math.exp(-kappa_a))
    
    return henry_f
