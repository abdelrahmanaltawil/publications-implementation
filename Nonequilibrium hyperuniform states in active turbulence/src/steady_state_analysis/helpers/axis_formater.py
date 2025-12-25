"""
Matplotlib axis formatters for displaying π-based tick labels.

Provides utilities to format axis ticks as fractions of π (e.g., π/2, 3π/4),
which is natural for periodic domains like [0, 2π].
"""

import numpy as np
import matplotlib.pyplot as plt


def multiple_formatter(denominator=2, number=np.pi, latex='\\pi'):
    """
    Create a formatter function for π-fraction tick labels.
    
    Returns a callable that converts numerical values to LaTeX-formatted
    fractions of π. For example, 1.57 → "$\\frac{\\pi}{2}$".
    
    Parameters
    ----------
    denominator : int, optional
        Denominator for the tick spacing. Default 2.
    number : float, optional
        Base value (typically π). Default np.pi.
    latex : str, optional
        LaTeX string for the base. Default '\\pi'.
    
    Returns
    -------
    callable
        Formatter function for matplotlib FuncFormatter.
    
    Examples
    --------
    >>> ax.xaxis.set_major_formatter(plt.FuncFormatter(multiple_formatter()))
    # Displays ticks as 0, π/2, π, 3π/2, 2π
    """
    def gcd(a, b):
        while b:
            a, b = b, a%b
        return a
    def _multiple_formatter(x, pos):
        den = denominator
        num = int(np.rint(den*x/number))
        com = gcd(num,den)
        (num,den) = (int(num/com),int(den/com))
        if den==1:
            if num==0:
                return r'$0$'
            if num==1:
                return r'$%s$'%latex
            elif num==-1:
                return r'$-%s$'%latex
            else:
                return r'$%s%s$'%(num,latex)
        else:
            if num==1:
                return r'$\frac{%s}{%s}$'%(latex,den)
            elif num==-1:
                return r'$\frac{-%s}{%s}$'%(latex,den)
            else:
                return r'$\frac{%s%s}{%s}$'%(num,latex,den)
    return _multiple_formatter


class Multiple:
    """
    Convenience class for π-fraction axis formatting.
    
    Provides both locator and formatter for matplotlib axes
    in a single object.
    
    Parameters
    ----------
    denominator : int, optional
        Denominator for tick spacing. Default 2.
    number : float, optional
        Base value for ticks. Default np.pi.
    latex : str, optional
        LaTeX representation of base. Default '\\pi'.
    
    Examples
    --------
    >>> m = Multiple(denominator=4)
    >>> ax.xaxis.set_major_locator(m.locator())
    >>> ax.xaxis.set_major_formatter(m.formatter())
    # Displays ticks at π/4 intervals
    """
    
    def __init__(self, denominator=2, number=np.pi, latex='\\pi'):
        self.denominator = denominator
        self.number = number
        self.latex = latex

    def locator(self):
        """Return a MultipleLocator for the configured spacing."""
        return plt.MultipleLocator(self.number / self.denominator)

    def formatter(self):
        """Return a FuncFormatter for π-fraction labels."""
        return plt.FuncFormatter(multiple_formatter(self.denominator, self.number, self.latex))