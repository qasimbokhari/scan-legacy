"""
Generate synthetic test dataset for CV and EIS traces.

This script creates a library of test traces covering realistic scenarios
for later parser validation in Module 3.
"""

import numpy as np
import json
from pathlib import Path
from .cv_simulator import generate_cv_curve, save_cv_curve_to_file
from .eis_simulator import generate_eis_spectrum, save_eis_spectrum_to_file


def generate_frequency_range(decades: int = 6, points_per_decade: int = 10) -> list[float]:
    """
    Generate a logarithmic frequency range for EIS measurements.

    Parameters
    ----------
    decades : int
        Number of decades to span (default 6, from 1e5 to 1e-1 Hz)
    points_per_decade : int
        Number of points per decade (default 10)

    Returns
    -------
    list[float]
        List of frequencies in Hz
    """
    f_max = 1e5
    f_min = f_max / (10 ** decades)
    frequencies = np.logspace(np.log10(f_min), np.log10(f_max), decades * points_per_decade)
    return frequencies.tolist()


def main():
    """Generate the complete test dataset."""
    # Set up directories
    base_dir = Path(__file__).parent.parent.parent.parent
    data_dir = base_dir / 'data' / 'simulated'
    cv_dir = data_dir / 'cv'
    eis_dir = data_dir / 'eis'

    # Create directories
    cv_dir.mkdir(parents=True, exist_ok=True)
    eis_dir.mkdir(parents=True, exist_ok=True)

    # Initialize manifest
    manifest = {
        'description': 'Synthetic electrochemical test dataset generated using validated physics layer',
        'cv_curves': [],
        'eis_spectra': [],
    }

    print("=" * 60)
    print("Generating CV curves with varying scan rates")
    print("=" * 60)

    # Fixed parameters for scan rate variation
    n = 1
    electrode_area_cm2 = 0.2
    concentration_mol_cm3 = 1e-6  # 1 mM
    diffusion_coefficient_cm2_s = 2.0e-6
    e_start_V = -0.2
    e_switch_V = 0.6
    e_formal_V = 0.2

    # Varying scan rates
    scan_rates = [0.01, 0.05, 0.1, 0.2, 0.5]

    for scan_rate in scan_rates:
        print(f"Generating CV curve with scan rate: {scan_rate} V/s")
        cv_data = generate_cv_curve(
            n=n,
            electrode_area_cm2=electrode_area_cm2,
            scan_rate_V_s=scan_rate,
            concentration_mol_cm3=concentration_mol_cm3,
            diffusion_coefficient_cm2_s=diffusion_coefficient_cm2_s,
            e_start_V=e_start_V,
            e_switch_V=e_switch_V,
            e_formal_V=e_formal_V,
            noise_std_fraction=0.02,
            random_seed=42,  # For reproducibility
        )

        idx = scan_rates.index(scan_rate)
        filename = f"cv_scanrate_{idx:02d}"
        filepath = cv_dir / filename
        save_cv_curve_to_file(cv_data, str(filepath))

        manifest['cv_curves'].append({
            'filename': f"{filename}.csv",
            'scenario': 'scan_rate_variation',
            'scan_rate_V_s': scan_rate,
            'scan_rate_label': f"{scan_rate*1000:.0f}mVs",
            'ground_truth': cv_data['ground_truth'],
        })

    print("\n" + "=" * 60)
    print("Generating CV curves with varying concentration")
    print("=" * 60)

    # Fixed parameters for concentration variation
    scan_rate_V_s = 0.1
    concentrations = [0.2e-6, 0.5e-6, 1.0e-6, 2.0e-6, 5.0e-6]  # 0.2 to 5 mM

    for concentration in concentrations:
        print(f"Generating CV curve with concentration: {concentration*1e6:.1f} mM")
        cv_data = generate_cv_curve(
            n=n,
            electrode_area_cm2=electrode_area_cm2,
            scan_rate_V_s=scan_rate_V_s,
            concentration_mol_cm3=concentration,
            diffusion_coefficient_cm2_s=diffusion_coefficient_cm2_s,
            e_start_V=e_start_V,
            e_switch_V=e_switch_V,
            e_formal_V=e_formal_V,
            noise_std_fraction=0.02,
            random_seed=43,
        )

        concentration_mM = concentration * 1e6
        # Use index-based naming to avoid floating point issues
        idx = concentrations.index(concentration)
        filename = f"cv_concentration_{idx:02d}"
        filepath = cv_dir / filename
        save_cv_curve_to_file(cv_data, str(filepath))

        manifest['cv_curves'].append({
            'filename': f"{filename}.csv",
            'scenario': 'concentration_variation',
            'concentration_mol_cm3': concentration,
            'concentration_mM': concentration_mM,
            'ground_truth': cv_data['ground_truth'],
        })

    print("\n" + "=" * 60)
    print("Generating EIS spectra with varying Rct values")
    print("=" * 60)

    # Generate frequency range
    frequencies = generate_frequency_range(decades=6, points_per_decade=10)

    # Fixed parameters for Rct variation
    Rs = 100.0
    Cdl = 1e-6  # 1 µF
    warburg_coefficient = 0.0  # No Warburg for this set

    # Varying Rct values (simulating different electrode fouling/binding states)
    Rct_values = [200.0, 500.0, 1000.0, 2000.0, 5000.0]

    for Rct in Rct_values:
        print(f"Generating EIS spectrum with Rct: {Rct} ohms")
        eis_data = generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=Rs,
            Rct=Rct,
            Cdl=Cdl,
            warburg_coefficient=warburg_coefficient,
            noise_std_fraction=0.02,
            random_seed=44,
        )

        filename = f"eis_rct_{int(Rct)}ohm"
        filepath = eis_dir / filename
        save_eis_spectrum_to_file(eis_data, str(filepath))

        manifest['eis_spectra'].append({
            'filename': f"{filename}.csv",
            'scenario': 'rct_variation',
            'Rct_ohm': Rct,
            'ground_truth': eis_data['ground_truth'],
        })

    print("\n" + "=" * 60)
    print("Generating EIS spectra with/without Warburg element")
    print("=" * 60)

    # Fixed parameters for Warburg comparison
    Rs = 100.0
    Rct = 1000.0
    Cdl = 1e-6

    # Without Warburg
    print("Generating EIS spectrum without Warburg element")
    eis_data_no_warburg = generate_eis_spectrum(
        frequencies_Hz=frequencies,
        Rs=Rs,
        Rct=Rct,
        Cdl=Cdl,
        warburg_coefficient=0.0,
        noise_std_fraction=0.02,
        random_seed=45,
    )

    filename = "eis_no_warburg"
    filepath = eis_dir / filename
    save_eis_spectrum_to_file(eis_data_no_warburg, str(filepath))

    manifest['eis_spectra'].append({
        'filename': f"{filename}.csv",
        'scenario': 'warburg_comparison',
        'has_warburg': False,
        'ground_truth': eis_data_no_warburg['ground_truth'],
    })

    # With Warburg (different magnitudes)
    warburg_coefficients = [50.0, 100.0, 200.0]

    for warburg_coeff in warburg_coefficients:
        print(f"Generating EIS spectrum with Warburg coefficient: {warburg_coeff}")
        eis_data_warburg = generate_eis_spectrum(
            frequencies_Hz=frequencies,
            Rs=Rs,
            Rct=Rct,
            Cdl=Cdl,
            warburg_coefficient=warburg_coeff,
            noise_std_fraction=0.02,
            random_seed=46,
        )

        filename = f"eis_warburg_{int(warburg_coeff)}"
        filepath = eis_dir / filename
        save_eis_spectrum_to_file(eis_data_warburg, str(filepath))

        manifest['eis_spectra'].append({
            'filename': f"{filename}.csv",
            'scenario': 'warburg_comparison',
            'has_warburg': True,
            'warburg_coefficient': warburg_coeff,
            'ground_truth': eis_data_warburg['ground_truth'],
        })

    # Save manifest
    manifest_path = data_dir / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 60)
    print("Dataset generation complete!")
    print("=" * 60)
    print(f"Total CV curves generated: {len(manifest['cv_curves'])}")
    print(f"Total EIS spectra generated: {len(manifest['eis_spectra'])}")
    print(f"Manifest saved to: {manifest_path}")
    print(f"CV data directory: {cv_dir}")
    print(f"EIS data directory: {eis_dir}")


if __name__ == '__main__':
    main()
