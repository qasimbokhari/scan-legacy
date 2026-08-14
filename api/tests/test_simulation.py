"""
Unit tests for simulation modules.

Tests validate that the CV and EIS simulators generate realistic data
that is consistent with the physics layer functions.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent))

import pytest
import numpy as np
import json
from ml.simulation import cv_simulator, eis_simulator
from ml.physics import electrochemistry, eis


class TestCVSimulator:
    """Tests for CV simulator."""

    def test_cv_curve_generation(self):
        """Test that CV curve generation produces expected output structure."""
        cv_data = cv_simulator.generate_cv_curve(
            n=1,
            electrode_area_cm2=0.2,
            scan_rate_V_s=0.1,
            concentration_mol_cm3=1e-6,
            diffusion_coefficient_cm2_s=2.0e-6,
            e_start_V=-0.2,
            e_switch_V=0.6,
            e_formal_V=0.2,
            noise_std_fraction=0.02,
            random_seed=42,
        )

        # Check output structure
        assert 'potential_V' in cv_data
        assert 'current_A' in cv_data
        assert 'ground_truth' in cv_data

        # Check array lengths (should be 200 points by default)
        assert len(cv_data['potential_V']) == 200
        assert len(cv_data['current_A']) == 200

        # Check ground truth contains all parameters
        gt = cv_data['ground_truth']
        assert gt['n'] == 1
        assert gt['electrode_area_cm2'] == 0.2
        assert gt['scan_rate_V_s'] == 0.1
        assert gt['concentration_mol_cm3'] == 1e-6
        assert gt['diffusion_coefficient_cm2_s'] == 2.0e-6

    def test_cv_curve_peak_current_consistency(self):
        """
        Test that CV simulator peak current matches Randles-Sevcik equation.

        This validates that the simulator correctly uses the physics layer
        to determine peak current magnitude.
        """
        # Generate CV curve
        cv_data = cv_simulator.generate_cv_curve(
            n=1,
            electrode_area_cm2=0.2,
            scan_rate_V_s=0.1,
            concentration_mol_cm3=1e-6,
            diffusion_coefficient_cm2_s=2.0e-6,
            e_start_V=-0.2,
            e_switch_V=0.6,
            e_formal_V=0.2,
            noise_std_fraction=0.0,  # No noise for this test
            random_seed=42,
        )

        # Extract peak current from generated curve
        peak_current_generated = np.max(cv_data['current_A'])

        # Calculate expected peak current using Randles-Sevcik from ground truth
        expected_peak = cv_data['ground_truth']['peak_current_A']

        # Should match closely when noise is zero
        # Allow 5% tolerance due to discrete sampling not exactly hitting peak center
        assert abs(peak_current_generated - expected_peak) / expected_peak < 0.05

    def test_cv_curve_diffusion_coefficient_recovery(self):
        """
        Test that diffusion coefficient can be recovered from simulated CV.

        Extracts the peak current from a simulated CV curve and uses the
        physics layer's randles_sevcik_diffusion_coefficient function to
        recover the diffusion coefficient. Checks that it matches the ground
        truth within 15% tolerance (allowing for noise).
        """
        # Known parameters
        n = 1
        electrode_area_cm2 = 0.2
        scan_rate_V_s = 0.1
        concentration_mol_cm3 = 1e-6
        true_D = 2.0e-6

        # Generate CV curve with noise
        cv_data = cv_simulator.generate_cv_curve(
            n=n,
            electrode_area_cm2=electrode_area_cm2,
            scan_rate_V_s=scan_rate_V_s,
            concentration_mol_cm3=concentration_mol_cm3,
            diffusion_coefficient_cm2_s=true_D,
            e_start_V=-0.2,
            e_switch_V=0.6,
            e_formal_V=0.2,
            noise_std_fraction=0.02,  # 2% noise
            random_seed=42,
        )

        # Extract peak current from generated curve
        peak_current_extracted = np.max(cv_data['current_A'])

        # Recover diffusion coefficient using physics layer
        recovered_D = electrochemistry.randles_sevcik_diffusion_coefficient(
            peak_current_A=peak_current_extracted,
            n=n,
            electrode_area_cm2=electrode_area_cm2,
            scan_rate_V_s=scan_rate_V_s,
            concentration_mol_cm3=concentration_mol_cm3,
        )

        # Check that recovered D is within 15% of true D
        # (tolerance accounts for noise and peak extraction)
        relative_error = abs(recovered_D - true_D) / true_D
        assert relative_error < 0.15, \
            f"Recovered D={recovered_D:.2e}, true D={true_D:.2e}, error={relative_error:.2%}"

    def test_cv_curve_noise_presence(self):
        """Test that noise is actually present in generated curves."""
        # Generate two curves with same parameters but different seeds
        cv_data1 = cv_simulator.generate_cv_curve(
            n=1,
            electrode_area_cm2=0.2,
            scan_rate_V_s=0.1,
            concentration_mol_cm3=1e-6,
            diffusion_coefficient_cm2_s=2.0e-6,
            e_start_V=-0.2,
            e_switch_V=0.6,
            e_formal_V=0.2,
            noise_std_fraction=0.02,
            random_seed=42,
        )

        cv_data2 = cv_simulator.generate_cv_curve(
            n=1,
            electrode_area_cm2=0.2,
            scan_rate_V_s=0.1,
            concentration_mol_cm3=1e-6,
            diffusion_coefficient_cm2_s=2.0e-6,
            e_start_V=-0.2,
            e_switch_V=0.6,
            e_formal_V=0.2,
            noise_std_fraction=0.02,
            random_seed=43,  # Different seed
        )

        # The curves should be different due to random noise
        assert not np.allclose(cv_data1['current_A'], cv_data2['current_A'])

    def test_cv_curve_reproducibility_with_seed(self):
        """Test that using the same random seed produces identical results."""
        cv_data1 = cv_simulator.generate_cv_curve(
            n=1,
            electrode_area_cm2=0.2,
            scan_rate_V_s=0.1,
            concentration_mol_cm3=1e-6,
            diffusion_coefficient_cm2_s=2.0e-6,
            e_start_V=-0.2,
            e_switch_V=0.6,
            e_formal_V=0.2,
            noise_std_fraction=0.02,
            random_seed=42,
        )

        cv_data2 = cv_simulator.generate_cv_curve(
            n=1,
            electrode_area_cm2=0.2,
            scan_rate_V_s=0.1,
            concentration_mol_cm3=1e-6,
            diffusion_coefficient_cm2_s=2.0e-6,
            e_start_V=-0.2,
            e_switch_V=0.6,
            e_formal_V=0.2,
            noise_std_fraction=0.02,
            random_seed=42,  # Same seed
        )

        # Should be identical
        assert np.allclose(cv_data1['current_A'], cv_data2['current_A'])

    def test_save_cv_curve_to_file(self, tmp_path):
        """Test that CV curve can be saved to file."""
        cv_data = cv_simulator.generate_cv_curve(
            n=1,
            electrode_area_cm2=0.2,
            scan_rate_V_s=0.1,
            concentration_mol_cm3=1e-6,
            diffusion_coefficient_cm2_s=2.0e-6,
            e_start_V=-0.2,
            e_switch_V=0.6,
            e_formal_V=0.2,
            random_seed=42,
        )

        filepath = tmp_path / "test_cv"
        cv_simulator.save_cv_curve_to_file(cv_data, str(filepath))

        # Check that files were created
        assert (tmp_path / "test_cv.csv").exists()
        assert (tmp_path / "test_cv.json").exists()

        # Check that JSON contains ground truth
        with open(tmp_path / "test_cv.json", 'r') as f:
            saved_gt = json.load(f)
        assert saved_gt == cv_data['ground_truth']


class TestEISSimulator:
    """Tests for EIS simulator."""

    def test_eis_spectrum_generation(self):
        """Test that EIS spectrum generation produces expected output structure."""
        frequencies = [1e5, 1e4, 1e3, 1e2, 1e1, 1e0, 1e-1]

        eis_data = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=100.0,
            Rct=1000.0,
            Cdl=1e-6,
            warburg_coefficient=0.0,
            noise_std_fraction=0.02,
            random_seed=42,
        )

        # Check output structure
        assert 'frequency_Hz' in eis_data
        assert 'impedance_real' in eis_data
        assert 'impedance_imag' in eis_data
        assert 'ground_truth' in eis_data

        # Check array lengths
        assert len(eis_data['frequency_Hz']) == len(frequencies)
        assert len(eis_data['impedance_real']) == len(frequencies)
        assert len(eis_data['impedance_imag']) == len(frequencies)

        # Check ground truth contains all parameters
        gt = eis_data['ground_truth']
        assert gt['Rs'] == 100.0
        assert gt['Rct'] == 1000.0
        assert gt['Cdl'] == 1e-6
        assert gt['warburg_coefficient'] == 0.0

    def test_eis_spectrum_impedance_consistency(self):
        """
        Test that EIS simulator impedance matches physics layer calculation.

        This validates that the simulator correctly uses the physics layer
        to calculate impedance values.
        """
        frequencies = [1e5, 1e4, 1e3, 1e2, 1e1, 1e0, 1e-1]
        Rs = 100.0
        Rct = 1000.0
        Cdl = 1e-6

        # Generate EIS spectrum without noise
        eis_data = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=Rs,
            Rct=Rct,
            Cdl=Cdl,
            warburg_coefficient=0.0,
            noise_std_fraction=0.0,  # No noise
            random_seed=42,
        )

        # Calculate expected impedance using physics layer directly
        Z_expected = eis.randles_circuit_impedance(
            np.array(frequencies), Rs, Rct, Cdl, 0.0
        )

        # Should match exactly when noise is zero
        assert np.allclose(eis_data['impedance_real'], Z_expected.real)
        assert np.allclose(eis_data['impedance_imag'], Z_expected.imag)

    def test_eis_spectrum_parameter_recovery(self):
        """
        Test that Randles circuit parameters can be recovered from simulated EIS.

        Uses the physics layer's fit_randles_circuit function to fit the
        simulated spectrum and checks that recovered parameters match the
        ground truth within tolerance.
        """
        # Known parameters
        frequencies = np.logspace(5, -1, 60).tolist()  # 6 decades, 10 points/decade
        true_Rs = 100.0
        true_Rct = 1000.0
        true_Cdl = 1e-6
        true_warburg = 0.0

        # Generate EIS spectrum with noise
        eis_data = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=true_Rs,
            Rct=true_Rct,
            Cdl=true_Cdl,
            warburg_coefficient=true_warburg,
            noise_std_fraction=0.02,  # 2% noise
            random_seed=42,
        )

        # Fit parameters using physics layer
        fit_result = eis.fit_randles_circuit(
            frequencies_Hz=eis_data['frequency_Hz'].tolist(),
            impedance_real=eis_data['impedance_real'].tolist(),
            impedance_imag=eis_data['impedance_imag'].tolist(),
            initial_guess={'Rs': true_Rs, 'Rct': true_Rct, 'Cdl': true_Cdl, 'warburg': true_warburg},
        )

        recovered_params = fit_result['parameters']

        # Check that recovered parameters are within 10% of true values
        # (tolerance accounts for noise)
        relative_error_Rs = abs(recovered_params['Rs'] - true_Rs) / true_Rs
        relative_error_Rct = abs(recovered_params['Rct'] - true_Rct) / true_Rct
        relative_error_Cdl = abs(recovered_params['Cdl'] - true_Cdl) / true_Cdl

        assert relative_error_Rs < 0.10, \
            f"Recovered Rs={recovered_params['Rs']:.2f}, true Rs={true_Rs:.2f}, error={relative_error_Rs:.2%}"
        assert relative_error_Rct < 0.10, \
            f"Recovered Rct={recovered_params['Rct']:.2f}, true Rct={true_Rct:.2f}, error={relative_error_Rct:.2%}"
        assert relative_error_Cdl < 0.10, \
            f"Recovered Cdl={recovered_params['Cdl']:.2e}, true Cdl={true_Cdl:.2e}, error={relative_error_Cdl:.2%}"

    def test_eis_spectrum_with_warburg(self):
        """Test that Warburg element affects the spectrum correctly."""
        frequencies = [1e5, 1e4, 1e3, 1e2, 1e1, 1e0, 1e-1]

        # Generate without Warburg
        eis_no_warburg = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=100.0,
            Rct=1000.0,
            Cdl=1e-6,
            warburg_coefficient=0.0,
            noise_std_fraction=0.0,
            random_seed=42,
        )

        # Generate with Warburg
        eis_with_warburg = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=100.0,
            Rct=1000.0,
            Cdl=1e-6,
            warburg_coefficient=100.0,
            noise_std_fraction=0.0,
            random_seed=42,
        )

        # Warburg should increase impedance magnitude at low frequencies
        # Compare at the lowest frequency
        Z_mag_no_warburg = np.sqrt(
            eis_no_warburg['impedance_real'][-1]**2 +
            eis_no_warburg['impedance_imag'][-1]**2
        )
        Z_mag_with_warburg = np.sqrt(
            eis_with_warburg['impedance_real'][-1]**2 +
            eis_with_warburg['impedance_imag'][-1]**2
        )

        assert Z_mag_with_warburg > Z_mag_no_warburg, \
            "Warburg element should increase impedance at low frequencies"

    def test_eis_spectrum_noise_presence(self):
        """Test that noise is actually present in generated spectra."""
        frequencies = [1e5, 1e4, 1e3, 1e2, 1e1, 1e0, 1e-1]

        # Generate two spectra with same parameters but different seeds
        eis_data1 = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=100.0,
            Rct=1000.0,
            Cdl=1e-6,
            warburg_coefficient=0.0,
            noise_std_fraction=0.02,
            random_seed=42,
        )

        eis_data2 = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=100.0,
            Rct=1000.0,
            Cdl=1e-6,
            warburg_coefficient=0.0,
            noise_std_fraction=0.02,
            random_seed=43,  # Different seed
        )

        # The spectra should be different due to random noise
        assert not np.allclose(eis_data1['impedance_real'], eis_data2['impedance_real'])
        assert not np.allclose(eis_data1['impedance_imag'], eis_data2['impedance_imag'])

    def test_eis_spectrum_reproducibility_with_seed(self):
        """Test that using the same random seed produces identical results."""
        frequencies = [1e5, 1e4, 1e3, 1e2, 1e1, 1e0, 1e-1]

        eis_data1 = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=100.0,
            Rct=1000.0,
            Cdl=1e-6,
            warburg_coefficient=0.0,
            noise_std_fraction=0.02,
            random_seed=42,
        )

        eis_data2 = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=100.0,
            Rct=1000.0,
            Cdl=1e-6,
            warburg_coefficient=0.0,
            noise_std_fraction=0.02,
            random_seed=42,  # Same seed
        )

        # Should be identical
        assert np.allclose(eis_data1['impedance_real'], eis_data2['impedance_real'])
        assert np.allclose(eis_data1['impedance_imag'], eis_data2['impedance_imag'])

    def test_save_eis_spectrum_to_file(self, tmp_path):
        """Test that EIS spectrum can be saved to file."""
        frequencies = [1e5, 1e4, 1e3, 1e2, 1e1, 1e0, 1e-1]

        eis_data = eis_simulator.generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=100.0,
            Rct=1000.0,
            Cdl=1e-6,
            warburg_coefficient=0.0,
            random_seed=42,
        )

        filepath = tmp_path / "test_eis"
        eis_simulator.save_eis_spectrum_to_file(eis_data, str(filepath))

        # Check that files were created
        assert (tmp_path / "test_eis.csv").exists()
        assert (tmp_path / "test_eis.json").exists()

        # Check that JSON contains ground truth
        with open(tmp_path / "test_eis.json", 'r') as f:
            saved_gt = json.load(f)
        assert saved_gt == eis_data['ground_truth']
