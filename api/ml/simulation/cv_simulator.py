"""
Cyclic Voltammetry (CV) simulator.

Generates synthetic CV curves using the validated physics layer functions.
The generated curves include realistic noise and baseline drift to simulate
actual instrument output.
"""

import numpy as np
import json
import csv
from pathlib import Path
from typing import Optional
from ..physics.electrochemistry import randles_sevcik_diffusion_coefficient
from ..physics.constants import RANDLES_SEVCIK_CONSTANT


def generate_cv_curve(
    n: int,
    electrode_area_cm2: float,
    scan_rate_V_s: float,
    concentration_mol_cm3: float,
    diffusion_coefficient_cm2_s: float,
    e_start_V: float,
    e_switch_V: float,
    e_formal_V: float,
    noise_std_fraction: float = 0.02,
    random_seed: Optional[int] = None,
) -> dict:
    """
    Generate a realistic CV curve using the Randles-Sevcik equation.

    Creates a full CV curve with forward and reverse sweeps, where the peak
    current magnitude is determined by the Randles-Sevcik equation from the
    physics layer. Includes realistic Gaussian noise and baseline drift.

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
    e_start_V : float
        Starting potential in V
    e_switch_V : float
        Switching potential in V (where the scan reverses direction)
    e_formal_V : float
        Formal potential E° of the redox couple in V
    noise_std_fraction : float, optional
        Noise level as fraction of peak current (default 0.02 = 2%)
    random_seed : int, optional
        Random seed for reproducibility (default None for random)

    Returns
    -------
    dict
        Dictionary containing:
        - 'potential_V': numpy array of potential values in V
        - 'current_A': numpy array of current values in A
        - 'ground_truth': dict with all input parameters used

    Notes
    -----
    The CV curve is generated using a Gaussian peak approximation centered
    around the formal potential. For a reversible system, the peak separation
    is approximately 59/n mV. The peak current is calculated using the
    Randles-Sevcik equation: ip = (2.69e5) * n^(3/2) * A * D^(1/2) * v^(1/2) * C
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    # Calculate peak current using Randles-Sevcik equation
    # ip = (2.69e5) * n^(3/2) * A * D^(1/2) * v^(1/2) * C
    peak_current_A = (
        RANDLES_SEVCIK_CONSTANT
        * (n ** 1.5)
        * electrode_area_cm2
        * np.sqrt(diffusion_coefficient_cm2_s)
        * np.sqrt(scan_rate_V_s)
        * concentration_mol_cm3
    )

    # For a reversible system, peak separation is ~59/n mV
    peak_separation_V = 0.059 / n

    # Peak positions relative to formal potential
    # Oxidation peak at E° + ~28.5/n mV, reduction peak at E° - ~28.5/n mV
    e_ox_peak_V = e_formal_V + (0.0285 / n)
    e_red_peak_V = e_formal_V - (0.0285 / n)

    # Number of points for the scan (use 200 points for good resolution)
    n_points = 200

    # Generate forward sweep (e_start to e_switch)
    potential_forward = np.linspace(e_start_V, e_switch_V, n_points // 2)

    # Generate reverse sweep (e_switch back to e_start)
    potential_reverse = np.linspace(e_switch_V, e_start_V, n_points // 2)

    # Combine forward and reverse sweeps
    potential_V = np.concatenate([potential_forward, potential_reverse])

    # Initialize current array
    current_A = np.zeros_like(potential_V)

    # Peak width parameter (related to scan rate and diffusion)
    # Higher scan rates give broader peaks
    peak_width_V = 0.1 + 0.05 * np.log10(scan_rate_V_s + 0.01)

    # Generate forward sweep current (oxidation peak)
    # Use a normalized Gaussian and scale to match peak_current_A exactly
    forward_gaussian = np.exp(-((potential_forward - e_ox_peak_V) ** 2) / (2 * peak_width_V ** 2))
    current_A[:n_points//2] = peak_current_A * forward_gaussian

    # Generate reverse sweep current (reduction peak)
    # Gaussian peak for reduction (negative current, normalized to peak=-1 at center)
    reverse_gaussian = np.exp(-((potential_reverse - e_red_peak_V) ** 2) / (2 * peak_width_V ** 2))
    current_A[n_points//2:] = -peak_current_A * reverse_gaussian

    # Add baseline drift (small linear drift)
    baseline_drift = np.linspace(0, 0.05 * peak_current_A, n_points)
    current_A += baseline_drift

    # Add Gaussian noise
    noise_std = noise_std_fraction * peak_current_A
    noise = np.random.normal(0, noise_std, n_points)
    current_A += noise

    # Create ground truth dictionary
    ground_truth = {
        'n': n,
        'electrode_area_cm2': electrode_area_cm2,
        'scan_rate_V_s': scan_rate_V_s,
        'concentration_mol_cm3': concentration_mol_cm3,
        'diffusion_coefficient_cm2_s': diffusion_coefficient_cm2_s,
        'e_start_V': e_start_V,
        'e_switch_V': e_switch_V,
        'e_formal_V': e_formal_V,
        'peak_current_A': peak_current_A,
        'noise_std_fraction': noise_std_fraction,
        'random_seed': random_seed,
    }

    return {
        'potential_V': potential_V,
        'current_A': current_A,
        'ground_truth': ground_truth,
    }


def save_cv_curve_to_file(curve_data: dict, filepath: str) -> None:
    """
    Save a CV curve to CSV file with ground truth parameters.

    Writes the CV data in a plausible instrument-export format with
    ground truth parameters saved in a companion JSON file.

    Parameters
    ----------
    curve_data : dict
        Dictionary returned by generate_cv_curve containing:
        - 'potential_V': array of potential values
        - 'current_A': array of current values
        - 'ground_truth': dict with parameters
    filepath : str
        Path where the CSV file should be saved (without extension)
    """
    filepath = Path(filepath)
    csv_path = filepath.with_suffix('.csv')
    json_path = filepath.with_suffix('.json')

    # Write CSV file with header comments
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header comments with ground truth parameters
        writer.writerow(['# CV Curve Simulation Data'])
        writer.writerow([f'# Generated using physics layer Randles-Sevcik equation'])
        writer.writerow([f'# Peak current: {curve_data["ground_truth"]["peak_current_A"]:.6e} A'])
        writer.writerow([f'# Scan rate: {curve_data["ground_truth"]["scan_rate_V_s"]:.3f} V/s'])
        writer.writerow([f'# Concentration: {curve_data["ground_truth"]["concentration_mol_cm3"]:.6e} mol/cm³'])
        writer.writerow([f'# Diffusion coefficient: {curve_data["ground_truth"]["diffusion_coefficient_cm2_s"]:.6e} cm²/s'])
        writer.writerow([f'# Formal potential: {curve_data["ground_truth"]["e_formal_V"]:.3f} V'])
        writer.writerow(['#'])
        writer.writerow(['# Potential (V), Current (A)'])
        
        # Write data
        for E, I in zip(curve_data['potential_V'], curve_data['current_A']):
            writer.writerow([f'{E:.6f}', f'{I:.6e}'])

    # Write companion JSON file with full ground truth
    with open(json_path, 'w') as f:
        json.dump(curve_data['ground_truth'], f, indent=2)

    print(f"CV curve saved to {csv_path}")
    print(f"Ground truth parameters saved to {json_path}")
