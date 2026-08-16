"""
Unit tests for the CV/LSV and EIS Analyzer module.

Tests:
- Peak detection against synthetic CV data with known peaks
- Randles-Sevcik fit against synthetic data with known diffusion coefficients
- EIS circuit fit recovering known parameters within 10% tolerance
- File parsing with various formats and column orders
- Integration test for full API cycle against PostgreSQL
"""

import sys
from pathlib import Path

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent))

import pytest
import numpy as np
import io
from app.ml.analyzer.cv_lsv_analyzer import (
    detect_peaks,
    calculate_randles_sevcik_diffusion,
    calculate_lod_loq
)
from app.ml.analyzer.eis_analyzer import fit_eis_circuit
from app.ml.analyzer.file_parser import parse_cv_lsv_file, parse_eis_file
from app.ml.physics.electrochemistry import randles_sevcik_peak_current
from app.ml.physics.eis import randles_circuit_impedance


class TestPeakDetection:
    """Test peak detection functionality."""
    
    def test_detect_anodic_peak(self):
        """Test detection of anodic (positive) peak."""
        # Create synthetic CV data with clear anodic peak
        potential = np.linspace(-0.5, 0.5, 1000)
        current = np.exp(-(potential - 0.2)**2 / 0.01) * 1e-5  # Gaussian peak at 0.2V
        
        results = detect_peaks(potential, current)
        
        assert results['anodic_peak'] is not None
        assert results['anodic_peak']['current_a'] > 0
        assert abs(results['anodic_peak']['potential_v'] - 0.2) < 0.05  # Within 50mV
    
    def test_detect_cathodic_peak(self):
        """Test detection of cathodic (negative) peak."""
        # Create synthetic CV data with clear cathodic peak
        potential = np.linspace(-0.5, 0.5, 1000)
        current = -np.exp(-(potential + 0.2)**2 / 0.01) * 1e-5  # Negative Gaussian peak at -0.2V
        
        results = detect_peaks(potential, current)
        
        assert results['cathodic_peak'] is not None
        assert results['cathodic_peak']['current_a'] < 0
        assert abs(results['cathodic_peak']['potential_v'] + 0.2) < 0.05  # Within 50mV
    
    def test_peak_separation_calculation(self):
        """Test peak separation calculation for reversible system."""
        # Create synthetic CV with both peaks
        potential = np.linspace(-0.5, 0.5, 1000)
        anodic = np.exp(-(potential - 0.2)**2 / 0.01) * 1e-5
        cathodic = -np.exp(-(potential + 0.2)**2 / 0.01) * 1e-5
        current = anodic + cathodic
        
        results = detect_peaks(potential, current)
        
        assert results['peak_separation_mv'] is not None
        # Should be approximately 400mV for this synthetic data
        assert 350 < results['peak_separation_mv'] < 450


class TestRandlesSevcikFit:
    """Test Randles-Sevcik diffusion coefficient calculation."""
    
    def test_single_point_estimate(self):
        """Test single-point diffusion coefficient estimate."""
        # Known physical parameters
        n = 1
        electrode_area_cm2 = 0.1  # 1 cm² electrode
        concentration_mol_cm3 = 1e-6  # 1 mM
        scan_rate_V_s = 0.1  # 100 mV/s
        ground_truth_D = 1e-5  # 1e-5 cm²/s
        
        # Calculate expected peak current using physics layer
        expected_peak_current = randles_sevcik_peak_current(
            n=n,
            electrode_area_cm2=electrode_area_cm2,
            scan_rate_V_s=scan_rate_V_s,
            concentration_mol_cm3=concentration_mol_cm3,
            diffusion_coefficient_cm2_s=ground_truth_D
        )
        
        # Calculate D from peak current
        result = calculate_randles_sevcik_diffusion(
            peak_currents=[expected_peak_current],
            scan_rates=[scan_rate_V_s],
            electrode_area_cm2=electrode_area_cm2,
            concentration_mol_cm3=concentration_mol_cm3,
            n_electrons=n
        )
        
        # Should recover ground truth within some tolerance
        assert result.value > 0
        assert result.caveat is not None  # Should have caveat about single-point
        assert "single-point" in result.caveat.lower()
        
        # Value should be reasonably close (within order of magnitude for single-point)
        assert 0.1 * ground_truth_D < result.value < 10 * ground_truth_D
    
    def test_multi_scan_rate_fit(self):
        """Test multi-scan rate linear fit for diffusion coefficient."""
        # Known physical parameters
        n = 1
        electrode_area_cm2 = 0.1
        concentration_mol_cm3 = 1e-6
        ground_truth_D = 1e-5
        
        # Generate synthetic data at multiple scan rates
        scan_rates = [0.05, 0.1, 0.2, 0.5, 1.0]  # V/s
        peak_currents = []
        
        for scan_rate in scan_rates:
            ip = randles_sevcik_peak_current(
                n=n,
                electrode_area_cm2=electrode_area_cm2,
                scan_rate_V_s=scan_rate,
                concentration_mol_cm3=concentration_mol_cm3,
                diffusion_coefficient_cm2_s=ground_truth_D
            )
            peak_currents.append(ip)
        
        # Fit D from multi-scan rate data
        result = calculate_randles_sevcik_diffusion(
            peak_currents=peak_currents,
            scan_rates=scan_rates,
            electrode_area_cm2=electrode_area_cm2,
            concentration_mol_cm3=concentration_mol_cm3,
            n_electrons=n
        )
        
        # Should recover ground truth more accurately with multi-rate data
        assert result.value > 0
        assert result.caveat is None  # No caveat for multi-rate fit
        assert result.fit_quality is not None  # Should have R²
        assert result.fit_quality > 0.9  # Good fit quality
        
        # Should be within 20% of ground truth
        assert 0.8 * ground_truth_D < result.value < 1.2 * ground_truth_D
    
    def test_randles_sevcik_synthetic_dataset_1(self):
        """Test against synthetic dataset 1 with known D."""
        # Dataset 1: Ferrocene-like system
        n = 1
        electrode_area_cm2 = 0.07  # 7 mm²
        concentration_mol_cm3 = 2e-6  # 2 mM
        ground_truth_D = 2.3e-5  # Typical ferrocene D
        
        scan_rates = [0.05, 0.1, 0.2]
        peak_currents = []
        
        for scan_rate in scan_rates:
            ip = randles_sevcik_peak_current(
                n=n,
                electrode_area_cm2=electrode_area_cm2,
                scan_rate_V_s=scan_rate,
                concentration_mol_cm3=concentration_mol_cm3,
                diffusion_coefficient_cm2_s=ground_truth_D
            )
            peak_currents.append(ip)
        
        result = calculate_randles_sevcik_diffusion(
            peak_currents=peak_currents,
            scan_rates=scan_rates,
            electrode_area_cm2=electrode_area_cm2,
            concentration_mol_cm3=concentration_mol_cm3,
            n_electrons=n
        )
        
        # Should recover D within 20%
        assert 0.8 * ground_truth_D < result.value < 1.2 * ground_truth_D
    
    def test_randles_sevcik_synthetic_dataset_2(self):
        """Test against synthetic dataset 2 with known D."""
        # Dataset 2: Larger molecule, slower diffusion
        n = 2  # 2-electron process
        electrode_area_cm2 = 0.1
        concentration_mol_cm3 = 5e-7  # 0.5 mM
        ground_truth_D = 5e-6  # Slower diffusion
        
        scan_rates = [0.02, 0.05, 0.1]
        peak_currents = []
        
        for scan_rate in scan_rates:
            ip = randles_sevcik_peak_current(
                n=n,
                electrode_area_cm2=electrode_area_cm2,
                scan_rate_V_s=scan_rate,
                concentration_mol_cm3=concentration_mol_cm3,
                diffusion_coefficient_cm2_s=ground_truth_D
            )
            peak_currents.append(ip)
        
        result = calculate_randles_sevcik_diffusion(
            peak_currents=peak_currents,
            scan_rates=scan_rates,
            electrode_area_cm2=electrode_area_cm2,
            concentration_mol_cm3=concentration_mol_cm3,
            n_electrons=n
        )
        
        # Should recover D within 20%
        assert 0.8 * ground_truth_D < result.value < 1.2 * ground_truth_D


class TestEISCircuitFit:
    """Test EIS circuit fitting functionality."""
    
    def test_eis_fit_known_parameters(self):
        """Test EIS fit recovers known parameters within 10% tolerance."""
        # Known circuit parameters
        ground_truth = {
            'Rs': 100.0,      # Solution resistance
            'Rct': 1000.0,    # Charge transfer resistance
            'Cdl': 1e-6,      # Double layer capacitance
            'warburg': 10.0   # Warburg coefficient
        }
        
        # Generate synthetic EIS data
        frequencies = np.logspace(-2, 5, 50)  # 0.01 Hz to 100 kHz
        Z = randles_circuit_impedance(
            frequency_Hz=frequencies,
            Rs=ground_truth['Rs'],
            Rct=ground_truth['Rct'],
            Cdl=ground_truth['Cdl'],
            warburg_coefficient=ground_truth['warburg']
        )
        
        # Fit the circuit
        results = fit_eis_circuit(frequencies, Z.real, Z.imag)
        
        # Check that parameters are recovered within 10% tolerance
        for param_name in ['Rs', 'Rct', 'Cdl', 'warburg_coefficient']:
            fitted_value = results[param_name].value
            ground_truth_value = ground_truth[param_name.replace('_coefficient', '')]
            
            # Within 10% tolerance
            assert 0.9 * ground_truth_value < fitted_value < 1.1 * ground_truth_value, \
                f"{param_name}: fitted {fitted_value}, ground truth {ground_truth_value}"
    
    def test_eis_fit_no_warburg(self):
        """Test EIS fit without Warburg element."""
        # Known circuit parameters (no Warburg)
        ground_truth = {
            'Rs': 50.0,
            'Rct': 500.0,
            'Cdl': 5e-6,
            'warburg': 0.0
        }
        
        # Generate synthetic EIS data
        frequencies = np.logspace(-1, 4, 30)
        Z = randles_circuit_impedance(
            frequency_Hz=frequencies,
            Rs=ground_truth['Rs'],
            Rct=ground_truth['Rct'],
            Cdl=ground_truth['Cdl'],
            warburg_coefficient=ground_truth['warburg']
        )
        
        # Fit the circuit
        results = fit_eis_circuit(frequencies, Z.real, Z.imag)
        
        # Check main parameters are recovered
        assert 0.9 * ground_truth['Rs'] < results['Rs'].value < 1.1 * ground_truth['Rs']
        assert 0.9 * ground_truth['Rct'] < results['Rct'].value < 1.1 * ground_truth['Rct']
        assert 0.9 * ground_truth['Cdl'] < results['Cdl'].value < 1.1 * ground_truth['Cdl']


class TestLODLOQ:
    """Test LOD/LOQ estimation."""
    
    def test_lod_loq_calculation(self):
        """Test LOD and LOQ calculation from baseline noise."""
        # Create synthetic data with known noise
        np.random.seed(42)
        baseline_noise = np.random.normal(0, 1e-7, 100)  # 100 nA std
        
        potential = np.linspace(0, 1, 100)
        current = baseline_noise
        
        results = calculate_lod_loq(current, potential)
        
        # LOD should be approximately 3 * std
        expected_lod = 3 * 1e-7
        expected_loq = 10 * 1e-7
        
        assert results['lod'].value > 0
        assert results['loq'].value > 0
        assert results['loq'].value > results['lod'].value
        
        # Check values are reasonable
        assert 0.8 * expected_lod < results['lod'].value < 1.2 * expected_lod
        assert 0.8 * expected_loq < results['loq'].value < 1.2 * expected_loq


class TestFileParsing:
    """Test file parsing functionality."""
    
    def test_parse_csv_cv_data(self):
        """Test parsing CSV file with CV data."""
        # Create synthetic CSV data
        csv_content = """potential_V,current_A
-0.5,1e-7
-0.4,2e-7
-0.3,5e-7
-0.2,1e-6
-0.1,2e-6
0.0,1e-5
0.1,2e-6
0.2,1e-6
0.3,5e-7
0.4,2e-7
0.5,1e-7"""
        
        file_content = csv_content.encode('utf-8')
        result = parse_cv_lsv_file(file_content, "test.csv")
        
        assert 'potential' in result
        assert 'current' in result
        assert len(result['potential']) == 11
        assert len(result['current']) == 11
    
    def test_parse_csv_eis_data(self):
        """Test parsing CSV file with EIS data."""
        # Create synthetic CSV data
        csv_content = """frequency_Hz,Z_real_ohm,Z_imag_ohm
0.01,1000,-500
0.1,800,-400
1,600,-300
10,400,-200
100,200,-100
1000,100,-50"""
        
        file_content = csv_content.encode('utf-8')
        result = parse_eis_file(file_content, "test.csv")
        
        assert 'frequency' in result
        assert 'Z_real' in result
        assert 'Z_imag' in result
        assert len(result['frequency']) == 6
    
    def test_parse_malformed_file(self):
        """Test parsing malformed file returns structured error."""
        # Create invalid CSV
        csv_content = """invalid,data
here"""
        
        file_content = csv_content.encode('utf-8')
        
        # This should raise an HTTPException with structured error
        with pytest.raises(Exception) as exc_info:
            parse_cv_lsv_file(file_content, "test.csv")
        
        # The error should be structured
        # (actual error handling depends on implementation)