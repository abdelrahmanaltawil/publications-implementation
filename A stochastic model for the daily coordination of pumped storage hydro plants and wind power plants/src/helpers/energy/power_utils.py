"""Power system utility functions for EcoNex energy optimization.

Linearized AC power flow coefficients, PWL current magnitude segments,
and energy-hub conversion matrix helpers — all implementing the
mathematical tools needed for constraints E6–E13.
"""

import numpy as np


# ---------------------------------------------------------------------------
# Line admittance
# ---------------------------------------------------------------------------

def calc_line_admittance(R: float, X: float) -> tuple[float, float]:
    """Compute series admittance (G, B) from resistance and reactance.

    G = R / (R² + X²),  B = -X / (R² + X²)

    Args:
        R: Series resistance (per-unit or ohms, consistent units).
        X: Series reactance (same units as R).

    Returns:
        (G, B) conductance and susceptance.
    """
    denom = R ** 2 + X ** 2
    return R / denom, -X / denom


# ---------------------------------------------------------------------------
# Linearized AC power flow  (E6)
# ---------------------------------------------------------------------------

def linearized_ac_coefficients(G: float, B: float, U0: float) -> dict:
    """Return the linearization coefficients for E6.

    First-order Taylor expansion around flat start (U0, θ = 0):
        P(n,m) ≈  U0·G·ΔU_nm  -  U0²·B·Δθ_nm
        Q(n,m) ≈ -U0·B·ΔU_nm  -  U0²·G·Δθ_nm

    Args:
        G:  Line conductance.
        B:  Line susceptance.
        U0: Nominal voltage (per-unit, typically 1.0).

    Returns:
        Dict with keys 'P_dU', 'P_dtheta', 'Q_dU', 'Q_dtheta'.
    """
    return {
        "P_dU": U0 * G,
        "P_dtheta": -(U0 ** 2) * B,
        "Q_dU": -U0 * B,
        "Q_dtheta": -(U0 ** 2) * G,
    }


# ---------------------------------------------------------------------------
# PWL current magnitude segments  (E12)
# ---------------------------------------------------------------------------

def create_pwl_current_segments(I_max: float, n_seg: int = 5) -> list[tuple]:
    """Generate (x, x²) breakpoints for PWL approximation of |I|².

    Used with the λ-formulation in E12:
        Î² ≈ Σ_s λ_s · x_s²   subject to Σ λ_s = 1, SOS2.

    Args:
        I_max:  Maximum current magnitude (amps or per-unit).
        n_seg:  Number of PWL segments (breakpoints = n_seg + 1).

    Returns:
        List of (I, I²) tuples as breakpoints.
    """
    breakpoints = np.linspace(0, I_max, n_seg + 1)
    return [(round(float(x), 6), round(float(x ** 2), 6)) for x in breakpoints]


# ---------------------------------------------------------------------------
# Energy-hub conversion matrix  (E1–E2)
# ---------------------------------------------------------------------------

def build_conversion_matrix(technologies: list[dict]) -> np.ndarray:
    """Build the H_tech dispatch-to-output conversion matrix.

    Each technology dict must have keys:
        'name'       - identifier string
        'input'      - energy carrier consumed  ('electricity', 'gas', ...)
        'outputs'    - dict {carrier: efficiency}

    Args:
        technologies: List of technology specification dicts.

    Returns:
        H_tech as a numpy array shaped (n_outputs, n_technologies),
        and a tuple (output_carriers, tech_names) for index mapping.
    """
    output_carriers = sorted({
        carrier
        for tech in technologies
        for carrier in tech.get("outputs", {})
    })
    tech_names = [t["name"] for t in technologies]

    H = np.zeros((len(output_carriers), len(tech_names)))
    for j, tech in enumerate(technologies):
        for carrier, eta in tech.get("outputs", {}).items():
            i = output_carriers.index(carrier)
            H[i, j] = eta

    return H, (output_carriers, tech_names)
