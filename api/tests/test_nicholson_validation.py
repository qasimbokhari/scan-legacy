"""
Validation tests for Nicholson electron transfer rate function.

Tests validate the Nicholson implementation against published empirical
equations from Lavagnini et al. (2004), which provide a polynomial fit
to Nicholson's original working curve.

Reference:
Lavagnini, I., Antiochia, R., & Magno, F. (2004). An extended method for
the practical evaluation of the standard rate constant from cyclic
voltammetric data. Electroanalysis, 16(6), 505-506.
DOI: 10.1002/elan.200302851

The Lavagnini equation for Ψ as a function of nΔEp (valid range 63-212 mV):
Ψ = (-0.6288 + 0.0021 * nΔEp) / (1 - 0.017 * nΔEp)

This is a polynomial fit to Nicholson's original working curve from:
Nicholson, R. S. (1965). Theory and Application of Cyclic Voltammetry for
Measurement of Electrode Reaction Kinetics. Analytical Chemistry, 37(11), 1351-1355.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent))

import pytest
import math
from ml.physics.electrochemistry import nicholson_electron_transfer_rate
from ml.physics.constants import FARADAY_CONSTANT, GAS_CONSTANT, PI


def lavagnini_psi(n_delta_ep_mV: float) -> float:
    """
    Calculate Ψ using Lavagnini et al. (2004) empirical equation.
    
    This is the reference polynomial fit to Nicholson's working curve.
    Valid for nΔEp in range 63-212 mV (quasi-reversible regime).
    
    Parameters
    ----------
    n_delta_ep_mV : float
        n * ΔEp in millivolts
        
    Returns
    -------
    float
        Dimensionless kinetic parameter Ψ
    """
    psi = (-0.6288 + 0.0021 * n_delta_ep_mV) / (1 - 0.017 * n_delta_ep_mV)
    return psi


def psi_from_our_implementation(delta_ep_mV: float, n: int) -> float:
    """
    Extract Ψ from our Nicholson implementation by back-calculating.
    
    From the Nicholson equation:
    k0 = Ψ * sqrt(π * D * n * F * v / (R * T))
    
    Rearranging:
    Ψ = k0 / sqrt(π * D * n * F * v / (R * T))
    
    Parameters
    ----------
    delta_ep_mV : float
        Peak separation in mV
    n : int
        Number of electrons
        
    Returns
    -------
    float
        Dimensionless kinetic parameter Ψ
    """
    # Use standard test parameters
    scan_rate_V_s = 0.1  # 0.1 V/s
    diffusion_coefficient_cm2_s = 1e-5  # 1e-5 cm²/s (typical value)
    temperature_K = 298.15  # 25°C
    
    # Calculate k0 using our implementation
    k0 = nicholson_electron_transfer_rate(
        delta_ep_mV=delta_ep_mV,
        scan_rate_V_s=scan_rate_V_s,
        diffusion_coefficient_cm2_s=diffusion_coefficient_cm2_s,
        n=n,
        temperature_K=temperature_K
    )
    
    # Back-calculate Ψ
    psi = k0 / math.sqrt((PI * diffusion_coefficient_cm2_s * n * FARADAY_CONSTANT * scan_rate_V_s) / (GAS_CONSTANT * temperature_K))
    
    return psi


class TestNicholsonPsiValidation:
    """Validate Ψ function against Lavagnini empirical equation."""
    
    @pytest.mark.parametrize("n_delta_ep_mV", [
        70,   # Near reversible limit
        90,   # Typical quasi-reversible
        120,  # Mid-range quasi-reversible
        150,  # Slower kinetics
        180,  # Near irreversible limit
        200,  # Upper range
    ])
    def test_psi_against_lavagnini(self, n_delta_ep_mV):
        """
        Test that our Ψ matches Lavagnini empirical equation within tolerance.
        
        The Lavagnini equation is a widely-accepted polynomial fit to
        Nicholson's original working curve. Our implementation should
        produce Ψ values consistent with this reference.
        
        Using 20% tolerance to account for:
        1. Different Ψ interpolation methods in literature
        2. The Nicholson method's known sensitivity to Ψ determination
        3. Variations in empirical fitting approaches
        """
        # Calculate reference Ψ from Lavagnini equation
        psi_reference = lavagnini_psi(n_delta_ep_mV)
        
        # Calculate Ψ from our implementation (assuming n=1 for simplicity)
        delta_ep_mV = n_delta_ep_mV  # n=1
        psi_ours = psi_from_our_implementation(delta_ep_mV, n=1)
        
        # For near-reversible (small ΔEp), our implementation returns very large Ψ
        # This is physically correct (k0 → ∞ for reversible)
        if n_delta_ep_mV <= 61:
            # Our implementation should return very large Ψ (effectively infinite)
            assert psi_ours > 100, f"For near-reversible (nΔEp={n_delta_ep_mV} mV), Ψ should be very large"
            # Skip percentage comparison for near-reversible case
            return
        
        # For quasi-reversible regime, compare with tolerance
        relative_error = abs(psi_ours - psi_reference) / psi_reference
        
        # Use 20% tolerance - wider than the 10% used for other physics functions
        # due to the Nicholson method's known sensitivity and multiple
        # empirical fitting approaches in the literature
        tolerance = 0.20
        
        assert relative_error <= tolerance, (
            f"Ψ mismatch at nΔEp={n_delta_ep_mV} mV: "
            f"ours={psi_ours:.4f}, reference={psi_reference:.4f}, "
            f"relative_error={relative_error:.2%} (tolerance={tolerance:.0%})"
        )
    
    def test_psi_monotonic_decrease(self):
        """Test that Ψ decreases monotonically as ΔEp increases."""
        psi_values = []
        delta_ep_values = [70, 90, 120, 150, 180, 200]
        
        for delta_ep_mV in delta_ep_values:
            psi = psi_from_our_implementation(delta_ep_mV, n=1)
            psi_values.append(psi)
        
        # Check that each value is less than or equal to the previous
        for i in range(1, len(psi_values)):
            assert psi_values[i] <= psi_values[i-1], (
                f"Ψ should decrease with increasing ΔEp: "
                f"Ψ({delta_ep_values[i-1]} mV)={psi_values[i-1]:.4f} >= "
                f"Ψ({delta_ep_values[i]} mV)={psi_values[i]:.4f}"
            )
    
    def test_k0_units(self):
        """Test that k0 has correct units (cm/s)."""
        # Test with known parameters
        delta_ep_mV = 100  # mV
        scan_rate_V_s = 0.1  # V/s
        diffusion_coefficient_cm2_s = 1e-5  # cm²/s
        n = 1
        temperature_K = 298.15  # K
        
        k0 = nicholson_electron_transfer_rate(
            delta_ep_mV=delta_ep_mV,
            scan_rate_V_s=scan_rate_V_s,
            diffusion_coefficient_cm2_s=diffusion_coefficient_cm2_s,
            n=n,
            temperature_K=temperature_K
        )
        
        # k0 should be positive
        assert k0 > 0, "k0 should be positive"
        
        # Note: k0 can vary widely depending on system kinetics
        # For a quasi-reversible system with ΔEp=100 mV, k0 is typically
        # in the range 0.001-1 cm/s. We just check it's physically reasonable.
        assert k0 > 1e-6, "k0 should be greater than 1e-6 cm/s"
        assert k0 < 1000, "k0 should be less than 1000 cm/s for typical systems"
        
        # Check that k0 scales correctly with scan rate
        k0_double_scan = nicholson_electron_transfer_rate(
            delta_ep_mV=delta_ep_mV,
            scan_rate_V_s=scan_rate_V_s * 2,
            diffusion_coefficient_cm2_s=diffusion_coefficient_cm2_s,
            n=n,
            temperature_K=temperature_K
        )
        
        # k0 should increase with scan rate (by factor of sqrt(2))
        expected_ratio = math.sqrt(2)
        actual_ratio = k0_double_scan / k0
        relative_error = abs(actual_ratio - expected_ratio) / expected_ratio
        
        assert relative_error <= 0.01, (
            f"k0 should scale with sqrt(scan_rate): "
            f"expected_ratio={expected_ratio:.4f}, actual_ratio={actual_ratio:.4f}"
        )


class TestNicholsonPhysicalConstraints:
    """Test physical constraints and edge cases."""
    
    def test_reversible_limit(self):
        """Test that near-reversible systems return very large k0."""
        # ΔEp = 59 mV is the reversible limit for n=1 at 25°C
        k0 = nicholson_electron_transfer_rate(
            delta_ep_mV=59,
            scan_rate_V_s=0.1,
            diffusion_coefficient_cm2_s=1e-5,
            n=1,
            temperature_K=298.15
        )
        
        # Should be very large (effectively infinite)
        assert k0 > 100, "Near-reversible system should have very large k0"
    
    def test_irreversible_limit(self):
        """Test that irreversible systems return small k0."""
        # Large ΔEp indicates slow kinetics
        k0 = nicholson_electron_transfer_rate(
            delta_ep_mV=300,
            scan_rate_V_s=0.1,
            diffusion_coefficient_cm2_s=1e-5,
            n=1,
            temperature_K=298.15
        )
        
        # Should be small
        assert k0 < 0.01, "Irreversible system should have small k0"
    
    def test_temperature_dependence(self):
        """Test that k0 has correct temperature dependence."""
        delta_ep_mV = 100
        scan_rate_V_s = 0.1
        diffusion_coefficient_cm2_s = 1e-5
        n = 1
        
        k0_298K = nicholson_electron_transfer_rate(
            delta_ep_mV=delta_ep_mV,
            scan_rate_V_s=scan_rate_V_s,
            diffusion_coefficient_cm2_s=diffusion_coefficient_cm2_s,
            n=n,
            temperature_K=298.15
        )
        
        k0_308K = nicholson_electron_transfer_rate(
            delta_ep_mV=delta_ep_mV,
            scan_rate_V_s=scan_rate_V_s,
            diffusion_coefficient_cm2_s=diffusion_coefficient_cm2_s,
            n=n,
            temperature_K=308.15
        )
        
        # k0 should decrease with increasing temperature (since a = nF/RT decreases)
        assert k0_308K < k0_298K, "k0 should decrease with increasing temperature"
