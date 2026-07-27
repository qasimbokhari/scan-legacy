"""
Physical constants used in electrochemistry, EIS, and nanomaterial calculations.

All values are in SI units unless otherwise noted.
Sources: CODATA 2018, NIST, and standard electrochemistry textbooks.
"""

# Faraday's constant: charge per mole of electrons (C/mol)
FARADAY_CONSTANT = 96485.33212  # C/mol

# Boltzmann constant: J/K
BOLTZMANN_CONSTANT = 1.380649e-23  # J/K

# Gas constant: J/(mol·K)
GAS_CONSTANT = 8.314462618  # J/(mol·K)

# Elementary charge: C
ELEMENTARY_CHARGE = 1.602176634e-19  # C

# Avogadro's number: mol^-1
AVOGADRO_NUMBER = 6.02214076e23  # mol^-1

# Vacuum permittivity: F/m
VACUUM_PERMITTIVITY = 8.8541878128e-12  # F/m

# Pi
PI = 3.141592653589793

# Randles-Sevcik constant for diffusion coefficient calculation
# ip = (2.69e5) * n^(3/2) * A * D^(1/2) * v^(1/2) * C
RANDLES_SEVCIK_CONSTANT = 2.69e5
