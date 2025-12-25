# env imports 
import functools
import numpy as np
import concurrent.futures
from itertools import repeat
import scipy.fftpack as scipy
import scipy.stats as scipy_stats

# local imports 
# import helpers.register as re
import active_flow.hyperuniformity_analysis.helpers.register as re


# def structure_factor(kx: np.ndarray, ky: np.ndarray, extrema_snapshots: dict) -> np.ndarray:
#     '''
#     Placeholder
#     '''

#     snapshots_structure_factor={}
#     for snapshot_key, snapshot_values in extrema_snapshots.items():
        
#         snapshot_structure_factor={}
#         for key, extrema in snapshot_values.items():
            
#             structure_factor = _structure_factor(
#                 kx= kx, 
#                 ky= ky,
#                 extrema= extrema 
#             )
#             snapshot_structure_factor[key]= structure_factor

#         snapshots_structure_factor[snapshot_key] = snapshot_structure_factor

#     # register
#     re.register["snapshots_structure_factor"] = snapshots_structure_factor
    
#     return snapshots_structure_factor


# def structure_factor(kx: np.ndarray, ky: np.ndarray, extrema_snapshots: dict) -> np.ndarray:
#     '''
#     Placeholder
#     '''

#     snapshots_structure_factor={}
#     for snapshot_key, snapshot_value in extrema_snapshots.items():
            
#         structure_factor = _structure_factor(
#             kx= kx, 
#             ky= ky,
#             extrema= snapshot_value
#         )

#         snapshots_structure_factor[snapshot_key] = structure_factor

#     # register
#     re.register["snapshots_structure_factor"] = snapshots_structure_factor
    
#     return snapshots_structure_factor


def structure_factor(kx: np.ndarray, ky: np.ndarray, extrema_snapshots: dict) -> np.ndarray:
    '''
    Placeholder
    '''

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
    '''
    Placeholder
    '''

    density = np.zeros((len(kx), len(kx)), dtype=np.complex64)

    for i in range(len(kx)):
        for j in range(len(kx)):
            if kx[i,j] == 0 or ky[i,j] == 0:
                density[i,j] = 0
            else:  
                density[i,j] = np.sum( np.exp( -1j*( kx[i,j]*extrema[:,0] + ky[i,j]*extrema[:,1] )) )

    return density, len(extrema)


def _structure_factor(kx: np.ndarray, ky: np.ndarray, extrema: np.ndarray) -> np.ndarray:
    '''
    Placeholder
    '''

    density, N = _density_fourier(
            kx= kx, 
            ky= ky,
            extrema= extrema 
            )

    structure_factor = np.absolute(density)
    structure_factor = structure_factor**2/N

    return structure_factor

    
def radial_profile(kx: np.ndarray, ky: np.ndarray, structure_factor_snapshots: dict) -> np.ndarray:
    '''
    Placeholder
    '''

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
    '''
    Placeholder
    '''

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
    '''
    Placeholder
    '''

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
    '''
    Placeholder
    '''

    slop, y_intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)

    return slop, y_intercept, r_value**2

