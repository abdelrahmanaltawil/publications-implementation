# env imports 
import functools
import numpy as np
import concurrent.futures
from itertools import repeat
import scipy.fftpack as scipy
import scipy.stats as scipy_stats

# local imports 
import hyperuniformity_analysis.helpers.register as re


def structure_factor(kx: np.ndarray, ky: np.ndarray, extrema_snapshots: dict) -> np.ndarray:
    """
    Compute the structure factor S(k) for multiple extrema snapshots.
    
    The structure factor measures density fluctuations at different wavenumbers.
    For hyperuniform systems, S(k) → 0 as k → 0.
    
    Uses parallel processing via ThreadPoolExecutor for efficiency.
    
    Parameters
    ----------
    kx : np.ndarray
        x-component of wavenumber grid, shape (N, N).
    ky : np.ndarray
        y-component of wavenumber grid, shape (N, N).
    extrema_snapshots : dict
        Dictionary mapping snapshot names to extrema arrays.
        Each extrema array has shape (M, 3) with columns [x, y, z].
    
    Returns
    -------
    dict
        Dictionary mapping snapshot names to structure factor arrays.
        Each S(k) array has shape (N, N).
        Also registered in re.register["snapshots_structure_factor"].
    """

    snapshots_structure_factor={}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(
            _structure_factor,
            repeat(kx, len(extrema_snapshots.values())),
            repeat(ky, len(extrema_snapshots.values())),
            extrema_snapshots.values()
            )

        for snapshot_key, result in zip(extrema_snapshots.keys(), results):
            snapshots_structure_factor[snapshot_key] = result

    # register
    re.register["snapshots_structure_factor"] = snapshots_structure_factor
    
    return snapshots_structure_factor



def _density_fourier(kx: np.ndarray, ky: np.ndarray, extrema: np.ndarray) -> np.ndarray:
    """
    Compute the Fourier transform of the point density.
    
    Calculates ñ(k) = Σⱼ exp(-i k·rⱼ) where rⱼ are the extrema positions.
    This is the key quantity for computing the structure factor.
    
    Parameters
    ----------
    kx : np.ndarray
        x-component of wavenumber grid, shape (N, N).
    ky : np.ndarray
        y-component of wavenumber grid, shape (N, N).
    extrema : np.ndarray
        Extrema positions, shape (M, 3) with columns [x, y, z].
    
    Returns
    -------
    density : np.ndarray
        Complex Fourier transform of density, shape (N, N).
    N : int
        Number of extrema points.
    """

    density = np.zeros((len(kx), len(kx)), dtype=np.complex64)

    for i in range(len(kx)):
        for j in range(len(kx)):
            if kx[i,j] == 0 or ky[i,j] == 0:
                density[i,j] = 0
            else:  
                density[i,j] = np.sum( np.exp( -1j*( kx[i,j]*extrema[:,0] + ky[i,j]*extrema[:,1] )) )

    return density, len(extrema)


def _structure_factor(kx: np.ndarray, ky: np.ndarray, extrema: np.ndarray) -> np.ndarray:
    """
    Compute the structure factor S(k) for a single set of extrema.
    
    Calculates S(k) = |ñ(k)|² / N where ñ(k) is the Fourier transform
    of the point density and N is the number of points.
    
    Parameters
    ----------
    kx : np.ndarray
        x-component of wavenumber grid.
    ky : np.ndarray
        y-component of wavenumber grid.
    extrema : np.ndarray
        Extrema positions, shape (M, 3).
    
    Returns
    -------
    np.ndarray
        Structure factor S(k), shape same as kx.
    """

    density, N = _density_fourier(
            kx= kx, 
            ky= ky,
            extrema= extrema 
            )

    structure_factor = np.absolute(density)
    structure_factor = structure_factor**2/N

    return structure_factor

    
def radial_profile(kx: np.ndarray, ky: np.ndarray, structure_factor_snapshots: dict) -> np.ndarray:
    """
    Compute the radially-averaged structure factor S(|k|).
    
    Averages the 2D structure factor over angles to obtain S as a 
    function of wavenumber magnitude |k| = √(kx² + ky²).
    
    Parameters
    ----------
    kx : np.ndarray
        x-component of wavenumber grid.
    ky : np.ndarray
        y-component of wavenumber grid.
    structure_factor_snapshots : dict
        Dictionary mapping snapshot names to 2D S(k) arrays.
    
    Returns
    -------
    dict
        Dictionary mapping snapshot names to 1D radial profile arrays.
        Also registered in re.register["snapshots_radial_profile"].
    """

    snapshots_radial_profile={}
    for snapshot_key, snapshot_value in structure_factor_snapshots.items():
        
        radial_profile = _radial_profile(
            kx= kx, 
            ky= ky, 
            structure_factor= snapshot_value,
            )

        snapshots_radial_profile[snapshot_key] = radial_profile
            
    # register
    re.register["snapshots_radial_profile"] = snapshots_radial_profile

    return snapshots_radial_profile


def _radial_profile(kx: np.ndarray, ky: np.ndarray, structure_factor: np.ndarray) -> np.ndarray:
    """
    Compute the radial profile of a 2D structure factor.
    
    Averages S(kx, ky) in annular bins of constant |k|.
    
    Parameters
    ----------
    kx : np.ndarray
        x-component of wavenumber grid.
    ky : np.ndarray
        y-component of wavenumber grid.
    structure_factor : np.ndarray
        2D structure factor array.
    
    Returns
    -------
    np.ndarray
        1D array of radially-averaged S(|k|) values.
    """

    k_norm = np.sqrt(kx**2 + ky**2)
    dk = abs(k_norm[0,2] - k_norm[0,1])
    k_mods = kx[0,:][kx[0,:] > 0][:-1]

    radial_profile = []
    for r_k in k_mods:
        index = np.where((k_norm >= r_k-(dk/2)) & (k_norm < r_k+(dk/2)))

        k_sum = np.sum(structure_factor[index])
        k_normalized = k_sum/(len(index[0]))

        radial_profile.append(k_normalized)
        
    return np.array(radial_profile)


def linear_curve_fitting(k: np.ndarray, radial_profile_snapshots: dict, k_interval: list[int], symbol: str, normalized: bool = False) -> tuple[float]:
    """
    Fit a power law S(k) ~ k^α to the radial profile data.
    
    Performs linear regression in log-log space to extract the 
    hyperuniformity exponent α. Can average over multiple snapshots.
    
    Parameters
    ----------
    k : np.ndarray
        Wavenumber values.
    radial_profile_snapshots : dict
        Dictionary mapping snapshot names to radial profile data.
    k_interval : list[int]
        [k_min, k_max] range for fitting.
    symbol : str
        Key to select extrema type ("All Extrema", "Minima", "Maxima").
    normalized : bool, optional
        If True, normalize by S(k_max) before fitting. Default False.
    
    Returns
    -------
    average_slop : float
        Fitted exponent α (slope in log-log plot).
    average_y_intercept : float
        Fitted intercept.
    
    Notes
    -----
    - For >6 snapshots: fits the average profile
    - For ≤6 snapshots: averages individual fits
    """

    interval = np.where((k>= k_interval[0]) & (k <= k_interval[1]))
    
    if len(radial_profile_snapshots) > 6:

        accumulated_quantity= np.zeros_like(k)
        for snapshot_key, snapshot_value in radial_profile_snapshots.items():
            if normalized:
                s_k_max = np.max(snapshot_value[symbol])
                snapshot_value_symbol = snapshot_value[symbol]/s_k_max
            else:
                snapshot_value_symbol = snapshot_value[symbol]
                
            accumulated_quantity = accumulated_quantity + snapshot_value_symbol
        
        averaged_quantity = accumulated_quantity/len(radial_profile_snapshots)

        if normalized:
            s_k_max = np.max(averaged_quantity)
            k_max_index = np.where(averaged_quantity == s_k_max)
            k_max = k[k_max_index]
        
            slop, y_intercept, _ = _linear_curve_fitting(
                x= (k/k_max)[interval],
                y= (averaged_quantity/s_k_max)[interval]
            )
        
        else:
            slop, y_intercept, _ = _linear_curve_fitting(
                x= k[interval],
                y= averaged_quantity[interval]
            )
            
        average_slop = slop
        average_y_intercept = y_intercept

    else:
        slops=[]
        y_intercepts=[]
        for snapshot_key, snapshot_value in radial_profile_snapshots.items():

            if normalized:
                s_k_max = np.max(snapshot_value[symbol])
                k_max_index = np.where(snapshot_value[symbol] == s_k_max)
                k_max = k[k_max_index]
            
                slop, y_intercept, _ = _linear_curve_fitting(
                    x= (k/k_max)[interval],
                    y= (snapshot_value[symbol]/s_k_max)[interval]
                    )
            
            else:
                slop, y_intercept, _ = _linear_curve_fitting(
                    x= k[interval],
                    y= snapshot_value[symbol][interval]
                    )

            slops.append(slop)
            y_intercepts.append(y_intercept)

        average_slop = np.average(slops)
        average_y_intercept = np.average(y_intercepts)

    return average_slop, average_y_intercept


def _linear_curve_fitting(x: np.ndarray, y: np.ndarray) -> tuple[float]:
    """
    Perform linear regression on the given data.
    
    Parameters
    ----------
    x : np.ndarray
        Independent variable values.
    y : np.ndarray
        Dependent variable values.
    
    Returns
    -------
    slope : float
        Fitted slope.
    intercept : float
        Fitted y-intercept.
    r_squared : float
        Coefficient of determination R².
    """

    slop, y_intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)

    return slop, y_intercept, r_value**2
