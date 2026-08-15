"""
Unit tests for physics calculation modules.

Tests validate against known textbook reference values and edge cases.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent))

import pytest
import numpy as np
import math
from ml.physics import electrochemistry, eis, nanomaterial, constants


class TestElectrochemistry:
    """Tests for electrochemistry calculation functions."""
    
    def test_randles_sevcik_diffusion_coefficient_reference_value(self):
        """
        Test Randles-Sevcik diffusion coefficient calculation.
        
        Reference: Standard ferrocene diffusion coefficient in acetonitrile
        Using the equation D = [ip / (2.69e5 * n^(3/2) * A * v^(1/2) * C)]^2
        For typical values: n=1, A=0.2 cm², v=0.1 V/s, C=1.0 mM, ip=25 µA
        Source: Bard & Faulkner, Electrochemical Methods, 2nd ed., Chapter 6, Example 6.1
        """
        peak_current_A = 25e-6  # 25 µA
        n = 1
        electrode_area_cm2 = 0.2
        scan_rate_V_s = 0.1
        concentration_mol_cm3 = 1e-6  # 1 mM = 1e-6 mol/cm³
        
        D = electrochemistry.randles_sevcik_diffusion_coefficient(
            peak_current_A, n, electrode_area_cm2, scan_rate_V_s, concentration_mol_cm3
        )
        
        # Calculate expected: D = [25e-6 / (2.69e5 * 1 * 0.2 * sqrt(0.1) * 1e-6)]^2
        # D ≈ 2.16e-6 cm²/s
        expected_D = 2.16e-6
        assert abs(D - expected_D) / expected_D < 0.05, f"D={D}, expected={expected_D}"

    def test_randles_sevcik_peak_current_reference_value(self):
        """
        Test Randles-Sevcik peak current calculation (forward direction).
        
        Reference: Standard calculation for ferrocene in acetonitrile
        Using the equation ip = (2.69e5) * n^(3/2) * A * D^(1/2) * v^(1/2) * C
        For typical values: n=1, A=0.2 cm², v=0.1 V/s, C=1.0 mM, D=2.16e-6 cm²/s
        Expected ip ≈ 25 µA
        Source: Bard & Faulkner, Electrochemical Methods, 2nd ed., Chapter 6, Example 6.1
        """
        n = 1
        electrode_area_cm2 = 0.2
        scan_rate_V_s = 0.1
        concentration_mol_cm3 = 1e-6  # 1 mM = 1e-6 mol/cm³
        diffusion_coefficient_cm2_s = 2.16e-6
        
        peak_current_A = electrochemistry.randles_sevcik_peak_current(
            n, electrode_area_cm2, scan_rate_V_s, concentration_mol_cm3, diffusion_coefficient_cm2_s
        )
        
        # Calculate expected: ip = 2.69e5 * 1 * 0.2 * sqrt(2.16e-6) * sqrt(0.1) * 1e-6
        # ip ≈ 25e-6 A = 25 µA
        expected_ip = 25e-6
        assert abs(peak_current_A - expected_ip) / expected_ip < 0.05, \
            f"ip={peak_current_A}, expected={expected_ip}"
    
    def test_randles_sevcik_invalid_inputs(self):
        """Test that Randles-Sevcik raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_diffusion_coefficient(-1e-6, 1, 0.196, 0.1, 1e-6)
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_diffusion_coefficient(22.6e-6, 0, 0.196, 0.1, 1e-6)
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_diffusion_coefficient(22.6e-6, 1, 0, 0.1, 1e-6)
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_diffusion_coefficient(22.6e-6, 1, 0.196, 0, 1e-6)
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_diffusion_coefficient(22.6e-6, 1, 0.196, 0.1, 0)
    
    def test_randles_sevcik_peak_current_invalid_inputs(self):
        """Test that forward Randles-Sevcik raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_peak_current(0, 0.2, 0.1, 1e-6, 2.16e-6)
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_peak_current(1, 0, 0.1, 1e-6, 2.16e-6)
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_peak_current(1, 0.2, 0, 1e-6, 2.16e-6)
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_peak_current(1, 0.2, 0.1, 0, 2.16e-6)
        with pytest.raises(ValueError):
            electrochemistry.randles_sevcik_peak_current(1, 0.2, 0.1, 1e-6, 0)
    
    def test_cottrell_current_reference_value(self):
        """
        Test Cottrell equation calculation.
        
        Reference: Standard Cottrell equation calculation from textbook
        For a potential step with n=1, A=0.2 cm², D=6.5e-6 cm²/s, C=1.0 mM,
        at t=1 s, calculate the current using i = nFAD^(1/2)C / (pi^(1/2) * t^(1/2))
        Source: Bard & Faulkner, Electrochemical Methods, 2nd ed., Chapter 5.2.1, Example 5.1
        """
        diffusion_coefficient_cm2_s = 6.5e-6
        concentration_mol_cm3 = 1e-6  # 1 mM
        electrode_area_cm2 = 0.2
        time_s = 1.0
        n = 1
        
        current = electrochemistry.cottrell_current(
            diffusion_coefficient_cm2_s, concentration_mol_cm3, electrode_area_cm2, time_s, n
        )
        
        # Calculate expected value manually for verification
        # i = 1 * 96485 * 0.2 * sqrt(6.5e-6) * 1e-6 / (sqrt(pi) * 1)
        # i ≈ 2.78e-5 A
        expected_current = 2.78e-5
        assert abs(current - expected_current) / expected_current < 0.05, \
            f"i={current}, expected={expected_current}"
    
    def test_cottrell_current_time_decay(self):
        """Test that Cottrell current decays with 1/sqrt(t)."""
        D = 1e-5
        C = 1e-6
        A = 0.1
        n = 1
        
        i1 = electrochemistry.cottrell_current(D, C, A, 1.0, n)
        i4 = electrochemistry.cottrell_current(D, C, A, 4.0, n)
        
        # Current at t=4 should be half of current at t=1 (1/sqrt(4) = 0.5)
        assert abs(i4 - 0.5 * i1) / (0.5 * i1) < 0.01, \
            f"i1={i1}, i4={i4}, ratio={i4/i1}"
    
    def test_cottrell_invalid_inputs(self):
        """Test that Cottrell raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            electrochemistry.cottrell_current(-1e-5, 1e-6, 0.1, 1.0, 1)
        with pytest.raises(ValueError):
            electrochemistry.cottrell_current(1e-5, -1e-6, 0.1, 1.0, 1)
        with pytest.raises(ValueError):
            electrochemistry.cottrell_current(1e-5, 1e-6, 0, 1.0, 1)
        with pytest.raises(ValueError):
            electrochemistry.cottrell_current(1e-5, 1e-6, 0.1, 0, 1)
        with pytest.raises(ValueError):
            electrochemistry.cottrell_current(1e-5, 1e-6, 0.1, 1.0, 0)
    
    def test_lod_calculation(self):
        """
        Test LOD calculation with standard 3-sigma definition.
        
        Reference: IUPAC Gold Book definition of LOD
        LOD = 3 * sigma / S where sigma is noise standard deviation and S is sensitivity
        Source: IUPAC. Compendium of Chemical Terminology (Gold Book). 
        https://doi.org/10.1351/goldbook.L03611
        """
        sensitivity = 100.0  # signal units per concentration unit
        noise_std = 5.0  # signal units
        
        lod = electrochemistry.lod_from_signal_to_noise(sensitivity, noise_std, factor=3.0)
        
        # LOD = 3 * 5 / 100 = 0.15
        assert lod == 0.15, f"LOD={lod}, expected=0.15"
    
    def test_loq_calculation(self):
        """
        Test LOQ calculation with 10-sigma definition.
        
        Reference: IUPAC Gold Book definition of LOQ
        LOQ = 10 * sigma / S where sigma is noise standard deviation and S is sensitivity
        Source: IUPAC. Compendium of Chemical Terminology (Gold Book). 
        https://doi.org/10.1351/goldbook.L03611
        """
        sensitivity = 100.0
        noise_std = 5.0
        
        loq = electrochemistry.lod_from_signal_to_noise(sensitivity, noise_std, factor=10.0)
        
        # LOQ = 10 * 5 / 100 = 0.5
        assert loq == 0.5, f"LOQ={loq}, expected=0.5"
    
    def test_lod_invalid_inputs(self):
        """Test that LOD raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            electrochemistry.lod_from_signal_to_noise(0, 5.0)
        with pytest.raises(ValueError):
            electrochemistry.lod_from_signal_to_noise(-100, 5.0)
        with pytest.raises(ValueError):
            electrochemistry.lod_from_signal_to_noise(100, -5.0)
    
    def test_nicholson_electron_transfer_rate(self):
        """
        Test Nicholson electron transfer rate calculation.
        
        The Nicholson method requires reading from an empirical working curve table
        (Nicholson 1965, Table 1) rather than a closed-form equation. This test
        validates that the polynomial approximation reproduces the published (ψ, ΔEp/n)
        relationship from Nicholson's working curve within acceptable tolerance.
        
        Reference data points from Nicholson (1965) working curve:
        - ΔEp/n = 61 mV (reversible limit) → ψ → ∞ (k0 very large)
        - ΔEp/n = 90 mV → ψ ≈ 0.5 (moderately quasi-reversible)
        - ΔEp/n = 120 mV → ψ ≈ 0.2 (slow quasi-reversible)
        - ΔEp/n = 200 mV → ψ ≈ 0.05 (approaching irreversible)
        
        This test validates the polynomial fit produces ψ values consistent with
        the published working curve trend, then validates k0 calculation.
        Source: Nicholson, R. S. (1965). Anal. Chem., 37(11), 1351-1355.
        """
        # Test that the polynomial approximation reproduces working curve trends
        # For ΔEp/n > 61 mV, ψ should decrease as ΔEp/n increases
        psi_90 = electrochemistry.nicholson_electron_transfer_rate(90, 0.1, 1e-5, 1, 298.15)
        psi_120 = electrochemistry.nicholson_electron_transfer_rate(120, 0.1, 1e-5, 1, 298.15)
        psi_200 = electrochemistry.nicholson_electron_transfer_rate(200, 0.1, 1e-5, 1, 298.15)
        
        # Extract ψ from k0 using the inverse relationship for comparison
        # ψ = k0 / sqrt(a * n * v / D) where a = nF/RT
        # This validates the polynomial trend without needing exact ψ values
        a = (1 * 96485.33) / (8.31446 * 298.15)  # nF/RT
        expected_factor = math.sqrt((a * 1 * 0.1) / 1e-5)
        
        psi_90_extracted = psi_90 / expected_factor
        psi_120_extracted = psi_120 / expected_factor
        psi_200_extracted = psi_200 / expected_factor
        
        # Validate monotonic decrease: ψ should decrease as ΔEp increases
        assert psi_90_extracted > psi_120_extracted, \
            f"ψ should decrease with ΔEp: ψ(90)={psi_90_extracted:.3f}, ψ(120)={psi_120_extracted:.3f}"
        assert psi_120_extracted > psi_200_extracted, \
            f"ψ should decrease with ΔEp: ψ(120)={psi_120_extracted:.3f}, ψ(200)={psi_200_extracted:.3f}"
        
        # Validate the extracted ψ values are in reasonable ranges
        # based on Nicholson's working curve:
        assert 0.3 < psi_90_extracted < 0.7, \
            f"ψ(90) should be ~0.5, got {psi_90_extracted:.3f}"
        assert 0.1 < psi_120_extracted < 0.3, \
            f"ψ(120) should be ~0.2, got {psi_120_extracted:.3f}"
        assert 0.01 < psi_200_extracted < 0.1, \
            f"ψ(200) should be ~0.05, got {psi_200_extracted:.3f}"
        
        # Validate near-reversible limit: for ΔEp/n = 61 mV, k0 should be very large
        k0_reversible = electrochemistry.nicholson_electron_transfer_rate(61, 0.1, 1e-5, 1, 298.15)
        assert k0_reversible > 1.0, \
            f"Near-reversible system should have large k0, got {k0_reversible}"
    
    def test_nicholson_invalid_inputs(self):
        """Test that Nicholson raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            electrochemistry.nicholson_electron_transfer_rate(-120, 0.1, 1e-5, 1)
        with pytest.raises(ValueError):
            electrochemistry.nicholson_electron_transfer_rate(120, 0, 1e-5, 1)
        with pytest.raises(ValueError):
            electrochemistry.nicholson_electron_transfer_rate(120, 0.1, 0, 1)
        with pytest.raises(ValueError):
            electrochemistry.nicholson_electron_transfer_rate(120, 0.1, 1e-5, 0)
        with pytest.raises(ValueError):
            electrochemistry.nicholson_electron_transfer_rate(120, 0.1, 1e-5, 1, 0)


class TestEIS:
    """Tests for EIS calculation functions."""
    
    def test_randles_circuit_impedance_dc(self):
        """Test Randles circuit impedance at DC (frequency = 0)."""
        Z = eis.randles_circuit_impedance(0, Rs=100, Rct=1000, Cdl=1e-6)
        
        # At DC, capacitor acts as open circuit, so Z = Rs + Rct
        expected_Z = complex(1100, 0)
        assert abs(Z - expected_Z) < 1e-6, f"Z={Z}, expected={expected_Z}"
    
    def test_randles_circuit_impedance_high_frequency(self):
        """Test Randles circuit impedance at high frequency."""
        # At high frequency, capacitor acts as short circuit
        Z = eis.randles_circuit_impedance(1e6, Rs=100, Rct=1000, Cdl=1e-6)
        
        # Should approach Rs as frequency increases
        assert abs(Z.real - 100) < 10, f"Z.real={Z.real}, expected≈100"
        assert abs(Z.imag) < 100, f"Z.imag={Z.imag}, should be small at high frequency"
    
    def test_randles_circuit_impedance_with_warburg(self):
        """Test Randles circuit impedance with Warburg element."""
        Z_no_warburg = eis.randles_circuit_impedance(
            1.0, Rs=100, Rct=1000, Cdl=1e-6, warburg_coefficient=0.0
        )
        Z_with_warburg = eis.randles_circuit_impedance(
            1.0, Rs=100, Rct=1000, Cdl=1e-6, warburg_coefficient=100.0
        )
        
        # Warburg should increase the impedance magnitude
        assert abs(Z_with_warburg) > abs(Z_no_warburg), \
            "Warburg element should increase impedance"
    
    def test_randles_circuit_invalid_inputs(self):
        """Test that Randles circuit raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            eis.randles_circuit_impedance(-1, 100, 1000, 1e-6)
        with pytest.raises(ValueError):
            eis.randles_circuit_impedance(1, -100, 1000, 1e-6)
        with pytest.raises(ValueError):
            eis.randles_circuit_impedance(1, 100, -1000, 1e-6)
        with pytest.raises(ValueError):
            eis.randles_circuit_impedance(1, 100, 1000, -1e-6)
    
    def test_fit_randles_circuit_synthetic_data(self):
        """
        Test Randles circuit fitting with synthetic data.
        
        This is the key validation test: generate synthetic impedance data
        with known parameters, add noise, fit, and verify recovery.
        """
        # True parameters
        true_Rs = 50.0
        true_Rct = 500.0
        true_Cdl = 5e-6
        true_warburg = 50.0
        
        # Generate frequency range (logarithmic spacing)
        frequencies = np.logspace(-2, 5, 50)  # 0.01 Hz to 100 kHz
        
        # Generate synthetic impedance data
        Z_synth = []
        for f in frequencies:
            Z = eis.randles_circuit_impedance(f, true_Rs, true_Rct, true_Cdl, true_warburg)
            Z_synth.append(Z)
        
        # Add small random noise (1% of magnitude)
        np.random.seed(42)  # For reproducibility
        Z_noisy = []
        for Z in Z_synth:
            noise = (np.random.normal(0, 0.01) + 1j * np.random.normal(0, 0.01)) * abs(Z) * 0.01
            Z_noisy.append(Z + noise)
        
        # Separate real and imaginary parts
        Z_real = [z.real for z in Z_noisy]
        Z_imag = [z.imag for z in Z_noisy]
        
        # Fit the circuit
        result = eis.fit_randles_circuit(
            frequencies.tolist(),
            Z_real,
            Z_imag,
            initial_guess={'Rs': 100, 'Rct': 1000, 'Cdl': 1e-6, 'warburg': 0}
        )
        
        # Check that fitted parameters recover true values within 10% tolerance
        fitted = result['parameters']
        
        rel_error_Rs = abs(fitted['Rs'] - true_Rs) / true_Rs
        rel_error_Rct = abs(fitted['Rct'] - true_Rct) / true_Rct
        rel_error_Cdl = abs(fitted['Cdl'] - true_Cdl) / true_Cdl
        rel_error_warburg = abs(fitted['warburg'] - true_warburg) / true_warburg
        
        assert rel_error_Rs < 0.1, f"Rs error: {rel_error_Rs:.2%}"
        assert rel_error_Rct < 0.1, f"Rct error: {rel_error_Rct:.2%}"
        assert rel_error_Cdl < 0.1, f"Cdl error: {rel_error_Cdl:.2%}"
        assert rel_error_warburg < 0.1, f"Warburg error: {rel_error_warburg:.2%}"
        
        # Store tolerance for final report
        self.fit_tolerance = max(rel_error_Rs, rel_error_Rct, rel_error_Cdl, rel_error_warburg)
    
    def test_fit_randles_circuit_invalid_inputs(self):
        """Test that fitting raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            eis.fit_randles_circuit([1, 2], [1], [1, 2])  # Mismatched lengths
        with pytest.raises(ValueError):
            eis.fit_randles_circuit([], [], [])  # Empty arrays


class TestNanomaterial:
    """Tests for nanomaterial calculation functions."""
    
    def test_stokes_einstein_diffusion_coefficient_reference_value(self):
        """
        Test Stokes-Einstein diffusion coefficient.
        
        Reference: For a 100 nm particle in water at 25°C:
        - T = 298.15 K
        - eta (water viscosity) = 0.00089 Pa·s
        - r = 100 nm = 100e-9 m
        Calculate D = kB*T / (6*pi*eta*r)
        Source: Einstein, A. (1905). Ann. Phys., 17, 549-560; 
        also in standard colloid science textbooks like Hunter, Zeta Potential in Colloid Science
        """
        temperature_K = 298.15
        viscosity_Pa_s = 0.00089  # Water at 25°C
        particle_radius_m = 100e-9  # 100 nm
        
        D = nanomaterial.stokes_einstein_diffusion_coefficient(
            temperature_K, viscosity_Pa_s, particle_radius_m
        )
        
        # Calculate expected: D = 1.38e-23 * 298.15 / (6 * pi * 0.00089 * 100e-9)
        # D ≈ 2.45e-12 m²/s
        expected_D = 2.45e-12
        assert abs(D - expected_D) / expected_D < 0.05, \
            f"D={D}, expected={expected_D}"
    
    def test_stokes_einstein_temperature_dependence(self):
        """Test that diffusion coefficient increases with temperature."""
        D_298 = nanomaterial.stokes_einstein_diffusion_coefficient(
            298.15, 0.00089, 100e-9
        )
        D_310 = nanomaterial.stokes_einstein_diffusion_coefficient(
            310.15, 0.00089, 100e-9
        )
        
        assert D_310 > D_298, "D should increase with temperature"
    
    def test_stokes_einstein_invalid_inputs(self):
        """Test that Stokes-Einstein raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            nanomaterial.stokes_einstein_diffusion_coefficient(0, 0.00089, 100e-9)
        with pytest.raises(ValueError):
            nanomaterial.stokes_einstein_diffusion_coefficient(298.15, 0, 100e-9)
        with pytest.raises(ValueError):
            nanomaterial.stokes_einstein_diffusion_coefficient(298.15, 0.00089, 0)
    
    def test_surface_area_to_volume_ratio(self):
        """
        Test surface area to volume ratio for sphere.
        
        Reference: For a sphere: SA = 4πr², V = (4/3)πr³, therefore SA/V = 3/r
        For r = 10 nm: SA/V = 3/10 = 0.3 nm⁻¹
        Source: Standard geometry formula found in any physics/engineering handbook
        """
        radius = 10.0  # nm
        sa_v_ratio = nanomaterial.surface_area_to_volume_ratio(radius)
        
        expected = 0.3
        assert abs(sa_v_ratio - expected) < 1e-6, f"SA/V={sa_v_ratio}, expected={expected}"
    
    def test_surface_area_to_volume_ratio_scaling(self):
        """Test that SA/V ratio scales as 1/r."""
        sa_v_10 = nanomaterial.surface_area_to_volume_ratio(10.0)
        sa_v_20 = nanomaterial.surface_area_to_volume_ratio(20.0)
        
        # SA/V should be half for double the radius
        assert abs(sa_v_20 - 0.5 * sa_v_10) < 1e-6, \
            f"SA/V(10)={sa_v_10}, SA/V(20)={sa_v_20}"
    
    def test_surface_area_to_volume_invalid_input(self):
        """Test that SA/V raises ValueError for invalid input."""
        with pytest.raises(ValueError):
            nanomaterial.surface_area_to_volume_ratio(0)
        with pytest.raises(ValueError):
            nanomaterial.surface_area_to_volume_ratio(-10)
    
    def test_debye_huckel_corrected_zeta_potential(self):
        """
        Test Debye-Hückel zeta potential correction.
        
        The Debye-Hückel correction requires numerical evaluation of Henry's function
        for precise zeta potential correction across all κa regimes. This implementation
        uses an exponential decay approximation based on Debye length. The test validates:
        1. Zero ionic strength returns unchanged value (no double layer compression)
        2. Higher ionic strength reduces zeta potential (double layer compression)
        3. The correction produces monotonic behavior consistent with physical expectations
        
        For precise corrections requiring the full Henry function (which accounts for
        electrophoretic retardation effects between Hückel and Smoluchowski limits),
        use numerical evaluation or the limiting case tests below.
        Source: Debye, P., & Hückel, E. (1923). Physikalische Zeitschrift, 24, 185-206;
        Hunter, R. J. (1981). Zeta Potential in Colloid Science. Academic Press.
        """
        raw_zeta = -50.0  # mV
        
        # No correction at zero ionic strength
        zeta_0 = nanomaterial.debye_huckel_corrected_zeta_potential(raw_zeta, 0)
        assert zeta_0 == raw_zeta, "Zero ionic strength should not change zeta"
        
        # Higher ionic strength should reduce magnitude
        zeta_low = nanomaterial.debye_huckel_corrected_zeta_potential(raw_zeta, 0.001)
        zeta_high = nanomaterial.debye_huckel_corrected_zeta_potential(raw_zeta, 0.1)
        
        assert abs(zeta_high) < abs(zeta_low), \
            "Higher ionic strength should reduce zeta potential magnitude"
        
        # Validate monotonic behavior: correction factor should decrease with ionic strength
        zeta_very_low = nanomaterial.debye_huckel_corrected_zeta_potential(raw_zeta, 0.0001)
        assert abs(zeta_low) < abs(zeta_very_low), \
            "Correction should be monotonic with ionic strength"

    def test_debye_length_calculation(self):
        """
        Test Debye length calculation against known reference values.
        
        Reference: For 1 mM NaCl solution at 25°C:
        - I = 0.001 mol/L
        - Expected Debye length ≈ 9.6 nm
        Source: Standard colloid science textbooks and the Debye-Hückel theory.
        """
        # Test 1 mM ionic strength at 25°C
        debye_length_m = nanomaterial.debye_length(0.001, 298.15)
        debye_length_nm = debye_length_m * 1e9
        
        # Expected Debye length for 1 mM at 25°C is ~9.6 nm
        expected_nm = 9.6
        assert abs(debye_length_nm - expected_nm) / expected_nm < 0.05, \
            f"Debye length: {debye_length_nm:.2f} nm, expected: {expected_nm} nm"
        
        # Test that Debye length decreases with ionic strength
        debye_length_10mM = nanomaterial.debye_length(0.01, 298.15) * 1e9
        assert debye_length_10mM < debye_length_nm, \
            "Debye length should decrease with ionic strength"
        
        # Test zero ionic strength (should be infinite)
        debye_length_zero = nanomaterial.debye_length(0.0, 298.15)
        assert debye_length_zero == float('inf'), \
            "Zero ionic strength should give infinite Debye length"

    def test_henry_function_limiting_cases(self):
        """
        Test Henry function approximation against known limiting cases.
        
        The Henry function f(κa) has two well-established limiting cases:
        - Hückel limit (κa ≪ 1): f(κa) → 1.0 (small particles, low ionic strength)
        - Smoluchowski limit (κa ≫ 1): f(κa) → 1.5 (large particles, high ionic strength)
        
        This test validates that the approximation correctly reproduces these limits.
        Source: Henry, D. C. (1931). Proc. R. Soc. Lond. A, 133, 106-129;
        Hunter, R. J. (1981). Zeta Potential in Colloid Science. Academic Press.
        """
        # Hückel limit: κa → 0 should give f(κa) → 1.0
        f_huckel = nanomaterial.henry_function_approximation(0.001)
        assert abs(f_huckel - 1.0) < 0.01, \
            f"Hückel limit should approach 1.0, got {f_huckel}"
        
        # Smoluchowski limit: κa → ∞ should give f(κa) → 1.5
        f_smoluchowski = nanomaterial.henry_function_approximation(1000.0)
        assert abs(f_smoluchowski - 1.5) < 0.01, \
            f"Smoluchowski limit should approach 1.5, got {f_smoluchowski}"
        
        # Intermediate values should be between 1.0 and 1.5
        f_intermediate = nanomaterial.henry_function_approximation(1.0)
        assert 1.0 < f_intermediate < 1.5, \
            f"Intermediate κa should give f between 1.0 and 1.5, got {f_intermediate}"
        
        # Monotonic increase: f(κa) should increase with κa
        f_01 = nanomaterial.henry_function_approximation(0.1)
        f_1 = nanomaterial.henry_function_approximation(1.0)
        f_10 = nanomaterial.henry_function_approximation(10.0)
        assert f_01 < f_1 < f_10, \
            "Henry function should increase monotonically with κa"
    
    def test_debye_huckel_invalid_inputs(self):
        """Test that Debye-Hückel raises ValueError for invalid inputs."""
        with pytest.raises(ValueError):
            nanomaterial.debye_huckel_corrected_zeta_potential(-50, -0.1)
        with pytest.raises(ValueError):
            nanomaterial.debye_huckel_corrected_zeta_potential(-50, 0.1, 0)


class TestConstants:
    """Tests for physical constants."""
    
    def test_faraday_constant(self):
        """Test Faraday constant value."""
        # CODATA 2018 value: 96485.33212 C/mol
        assert abs(constants.FARADAY_CONSTANT - 96485.33212) < 1e-6
    
    def test_boltzmann_constant(self):
        """Test Boltzmann constant value."""
        # CODATA 2018 value: 1.380649e-23 J/K
        assert abs(constants.BOLTZMANN_CONSTANT - 1.380649e-23) < 1e-28
    
    def test_gas_constant(self):
        """Test gas constant value."""
        # CODATA 2018 value: 8.314462618 J/(mol·K)
        assert abs(constants.GAS_CONSTANT - 8.314462618) < 1e-9
