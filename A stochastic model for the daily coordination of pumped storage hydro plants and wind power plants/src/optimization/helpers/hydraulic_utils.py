"""Hydraulic utility functions for EcoNex optimization.

Contains helper functions for Hazen-Williams calculations and piecewise linear approximations
for hydraulic components (pipes, pumps).
"""

import numpy as np
from scipy.optimize import curve_fit

def calc_K(L, D, R):
    """Calculate Hazen-Williams coefficient K."""
    alpha = 10.66
    e1 = 1.852
    e2 = 4.87
    return (alpha * L) / ((R**e1) * (D**e2))

def get_pump_curve_points(pump, num_points=3):
    """Extract pump curve points for piecewise approximation."""
    if len(pump.get_pump_curve().points) == 1:
        # Single point curve validation
        A1, B1 = pump.get_pump_curve().points[0]
        # Common EPANET assumption: shutoff head is ~1.33 * design head, max flow is ~2 * design flow
        return [(0, A1 * 1.33), (A1, B1), (2 * A1, 0)]  # Rough approximation
    elif len(pump.get_pump_curve().points) == 3:
        return pump.get_pump_curve().points
    else:
        # Multi-point curve
        return pump.get_pump_curve().points

def create_piecewise_pipe_curve(K, max_flow, num_segments=5):
    """Generate (flow, head_loss) points for pipe PWL approximation."""
    flows = np.linspace(-max_flow, max_flow, num_segments + 1)
    head_losses = np.sign(flows) * K * np.abs(flows)**1.852
    return [(round(float(q), 6), round(float(h), 6)) for q, h in zip(flows, head_losses)]

def create_piecewise_pump_curve(pump, num_segments=5):
    """Generate (flow, head_gain) points for pump PWL approximation."""
    points = get_pump_curve_points(pump)
    
    def pump_func(x, a, b):
        return a - b * x**2
    
    xdata = [p[0] for p in points]
    ydata = [p[1] for p in points]
    
    try:
        popt, _ = curve_fit(pump_func, xdata, ydata)
        A, B = popt[0], popt[1]
    except:
        A, B = points[0][1], 0.1 
        
    cutoff_flow = np.sqrt(A/B) if B > 0 else xdata[-1] * 1.1
    
    flows = np.linspace(0, cutoff_flow, num_segments + 1)
    heads = A - B * flows**2
    return [(round(float(q), 6), round(float(h), 6)) for q, h in zip(flows, heads)]
