"""
Electrochemical Impedance Spectroscopy (EIS) simulator.

Generates synthetic EIS spectra using the validated physics layer functions.
The generated spectra include realistic noise to simulate actual instrument output.
"""

import numpy as np
import json
import csv
from pathlib import Path
from typing import Optional
from ..physics.eis import randles_circuit_impedance


def generate_eis_spectrum(
    frequencies_Hz: list[float],
    Rs: float,
    Rct: float,
    Cdl: float,
    warburg_coefficient: float = 0.0,
    noise_std_fraction: float = 0.02,
    random_seed: Optional[int] = None,
) -> dict:
    """
    Generate a realistic EIS spectrum using the Randles circuit model.

    Uses the physics layer's randles_circuit_impedance() function to generate
    true impedance values across the frequency range, then adds proportional
    Gaussian noise to both real and imaginary components.

    Parameters
    ----------
    frequencies_Hz : list[float]
        List of frequencies in Hz (should span several decades, e.g., 1e5 to 1e-2 Hz)
    Rs : float
        Solution resistance in ohms
    Rct : float
        Charge transfer resistance in ohms
    Cdl : float
        Double layer capacitance in farads
    warburg_coefficient : float, optional
        Warburg coefficient (sigma) in ohm·s^(-1/2). Default 0.0 (no Warburg element)
    noise_std_fraction : float, optional
        Noise level as fraction of impedance magnitude (default 0.02 = 2%)
    random_seed : int, optional
        Random seed for reproducibility (default None for random)

    Returns
    -------
    dict
        Dictionary containing:
        - 'frequency_Hz': numpy array of frequency values in Hz
        - 'impedance_real': numpy array of real impedance components in ohms
        - 'impedance_imag': numpy array of imaginary impedance components in ohms
        - 'ground_truth': dict with all input parameters used

    Notes
    -----
    The impedance is calculated using the Randles circuit model:
    Z = Rs + (Rct + Zw) || (1/(j*omega*Cdl))
    where Zw is the Warburg impedance (if warburg_coefficient > 0).
    Noise is added proportional to the impedance magnitude at each frequency.
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    # Convert to numpy array
    freq = np.array(frequencies_Hz)

    # Calculate true impedance using physics layer function
    Z_true = randles_circuit_impedance(freq, Rs, Rct, Cdl, warburg_coefficient)

    # Extract real and imaginary components
    Z_real_true = Z_true.real
    Z_imag_true = Z_true.imag

    # Calculate impedance magnitude for noise scaling
    Z_magnitude = np.abs(Z_true)

    # Add proportional Gaussian noise to both components
    noise_std = noise_std_fraction * Z_magnitude
    noise_real = np.random.normal(0, noise_std, len(freq))
    noise_imag = np.random.normal(0, noise_std, len(freq))

    Z_real = Z_real_true + noise_real
    Z_imag = Z_imag_true + noise_imag

    # Create ground truth dictionary
    ground_truth = {
        'Rs': Rs,
        'Rct': Rct,
        'Cdl': Cdl,
        'warburg_coefficient': warburg_coefficient,
        'noise_std_fraction': noise_std_fraction,
        'random_seed': random_seed,
    }

    return {
        'frequency_Hz': freq,
        'impedance_real': Z_real,
        'impedance_imag': Z_imag,
        'ground_truth': ground_truth,
    }


def save_eis_spectrum_to_file(spectrum_data: dict, filepath: str) -> None:
    """
    Save an EIS spectrum to CSV file with ground truth parameters.

    Writes the EIS data in a plausible instrument-export format with
    ground truth parameters saved in a companion JSON file.

    Parameters
    ----------
    spectrum_data : dict
        Dictionary returned by generate_eis_spectrum containing:
        - 'frequency_Hz': array of frequency values
        - 'impedance_real': array of real impedance components
        - 'impedance_imag': array of imaginary impedance components
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
        writer.writerow(['# EIS Spectrum Simulation Data'])
        writer.writerow([f'# Generated using physics layer Randles circuit model'])
        writer.writerow([f'# Solution resistance (Rs): {spectrum_data["ground_truth"]["Rs"]:.3f} ohms'])
        writer.writerow([f'# Charge transfer resistance (Rct): {spectrum_data["ground_truth"]["Rct"]:.3f} ohms'])
        writer.writerow([f'# Double layer capacitance (Cdl): {spectrum_data["ground_truth"]["Cdl"]:.6e} F'])
        if spectrum_data["ground_truth"]["warburg_coefficient"] > 0:
            writer.writerow([f'# Warburg coefficient: {spectrum_data["ground_truth"]["warburg_coefficient"]:.3f} ohm·s^(-1/2)'])
        else:
            writer.writerow(['# Warburg element: not included'])
        writer.writerow(['#'])
        writer.writerow(['# Frequency (Hz), Z_real (Ohm), Z_imag (Ohm)'])
        
        # Write data
        for freq, Z_real, Z_imag in zip(
            spectrum_data['frequency_Hz'],
            spectrum_data['impedance_real'],
            spectrum_data['impedance_imag']
        ):
            writer.writerow([f'{freq:.6e}', f'{Z_real:.6e}', f'{Z_imag:.6e}'])

    # Write companion JSON file with full ground truth
    with open(json_path, 'w') as f:
        json.dump(spectrum_data['ground_truth'], f, indent=2)

    print(f"EIS spectrum saved to {csv_path}")
    print(f"Ground truth parameters saved to {json_path}")
