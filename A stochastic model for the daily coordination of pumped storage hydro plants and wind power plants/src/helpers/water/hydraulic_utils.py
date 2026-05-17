"""Hydraulic utility functions for EcoNex optimization.

Hazen-Williams calculations, pump curve fitting, and piecewise-linear
approximation helpers shared by the water sub-model and validation tests.
"""

import numpy as np
import pyomo.environ as pyo
from scipy.optimize import curve_fit


# ---------------------------------------------------------------------------
# Hazen-Williams helpers
# ---------------------------------------------------------------------------

def calc_K(L, D, R):
    """Hazen-Williams resistance coefficient K = 10.66·L / (R^1.852 · D^4.87)."""
    return (10.66 * L) / ((R ** 1.852) * (D ** 4.87))


def get_pump_curve_points(pump):
    """Extract (flow, head) breakpoints from an EPANET pump object."""
    pts = pump.get_pump_curve().points
    if len(pts) == 1:
        Q0, H0 = pts[0]
        return [(0, H0 * 1.33), (Q0, H0), (2 * Q0, 0)]
    return list(pts)


def create_piecewise_pipe_curve(K, max_flow, num_segments=5):
    """(flow, head_loss) breakpoints for Hazen-Williams PWL: dH = sign(Q)·K·|Q|^1.852."""
    flows = np.linspace(-max_flow, max_flow, num_segments + 1)
    head_losses = np.sign(flows) * K * np.abs(flows) ** 1.852
    return [(round(float(q), 6), round(float(h), 6)) for q, h in zip(flows, head_losses)]


def create_piecewise_pump_curve(pump, num_segments=5):
    """(flow, head_gain) breakpoints for pump curve PWL: H = A - B·Q²."""
    pts = get_pump_curve_points(pump)
    xdata = [p[0] for p in pts]
    ydata = [p[1] for p in pts]

    def pump_func(x, a, b):
        return a - b * x ** 2

    try:
        popt, _ = curve_fit(pump_func, xdata, ydata)
        A, B = popt[0], popt[1]
    except Exception:
        A, B = pts[0][1], 0.1

    cutoff = np.sqrt(A / B) if B > 0 else xdata[-1] * 1.1
    flows = np.linspace(0, cutoff, num_segments + 1)
    heads = A - B * flows ** 2
    return [(round(float(q), 6), round(float(h), 6)) for q, h in zip(flows, heads)]


# ---------------------------------------------------------------------------
# Shared PWL constraint builder (used by water and energy sub-models)
# ---------------------------------------------------------------------------

def add_pwl_constraint(model, name, x_var, y_var, points):
    """Add a piecewise-linear constraint y = f(x) to a Pyomo model.

    Implements SOS2 logic via explicit binary segment variables so the
    model stays compatible with open-source MILP solvers (GLPK, CBC).

    Args:
        model:  Pyomo ConcreteModel to attach components to.
        name:   Unique prefix for all added components.
        x_var:  Pyomo Var (scalar) for the x-axis.
        y_var:  Pyomo Var (scalar) for the y-axis.
        points: List of (x, y) breakpoint tuples in ascending x order.
    """
    n = len(points)
    indices = range(n)
    segments = range(n - 1)

    x_pts = [p[0] for p in points]
    y_pts = [p[1] for p in points]

    w = pyo.Var(indices, bounds=(0, 1))
    model.add_component(f"{name}_w", w)

    z = pyo.Var(segments, domain=pyo.Binary)
    model.add_component(f"{name}_z", z)

    model.add_component(f"{name}_convex",
                        pyo.Constraint(expr=sum(w[k] for k in indices) == 1))
    model.add_component(f"{name}_z_sum",
                        pyo.Constraint(expr=sum(z[k] for k in segments) == 1))

    model.add_component(f"{name}_sos_start",
                        pyo.Constraint(expr=w[0] <= z[0]))
    for k in range(1, n - 1):
        model.add_component(f"{name}_sos_{k}",
                            pyo.Constraint(expr=w[k] <= z[k - 1] + z[k]))
    model.add_component(f"{name}_sos_end",
                        pyo.Constraint(expr=w[n - 1] <= z[n - 2]))

    model.add_component(f"{name}_x_interp",
                        pyo.Constraint(expr=x_var == sum(w[k] * x_pts[k] for k in indices)))
    model.add_component(f"{name}_y_interp",
                        pyo.Constraint(expr=y_var == sum(w[k] * y_pts[k] for k in indices)))
