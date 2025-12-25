# env imports
import pathlib 
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.fftpack as scipy
import scipy.stats as scipy_stats

# local imports
import hyperuniformity_analysis.algorithm_tasks as task


def save_arrays(operators: dict, radial_profile_snapshots: dict, extrema_type: str, save_path: pathlib.Path) -> list:
    """
    Save operator arrays and radial profile snapshots to disk.
    
    Parameters
    ----------
    operators : dict
        Dictionary mapping operator names to numpy arrays.
    radial_profile_snapshots : dict
        Dictionary mapping snapshot names to radial profile arrays.
    extrema_type : str
        Type of extrema ("all_extrema", "minima", "maxima").
    save_path : pathlib.Path
        Directory to save files to.
    """

    save_path.mkdir(parents=True, exist_ok=True)
    
    for operator_key, operator_value in operators.items():
        np.save(save_path.joinpath(operator_key), operator_value)


    save_path = save_path.joinpath("snapshots/radial_profile/"+extrema_type)
    save_path.mkdir(parents=True, exist_ok=True)

    for snapshot_key, snapshot_value in radial_profile_snapshots.items():

        iteration = snapshot_key.split("= ")[1].zfill(8)

        np.save(save_path.joinpath(extrema_type+"_"+iteration), snapshot_value)


def remove_data(data_path: pathlib.Path) -> None:
    """
    Remove all files in a directory tree.
    
    This function enforces the design choice that data should only be
    fetched from Neptune.ai experiment runs, not stored locally.
    This ensures metadata provenance is maintained.
    
    Parameters
    ----------
    data_path : pathlib.Path
        Root directory to clean. All files (not directories) are deleted.
    """

    for file_path in data_path.rglob("*"):
        if file_path.is_file():
            file_path.unlink()


def plot_structure_factor_snapshots(structure_factor: dict, symbol: str) -> list[plt.figure]:
    """
    Plot 2D structure factor S(kx, ky) for multiple snapshots.
    
    Creates a 2x3 grid of heatmaps showing the structure factor
    in Fourier space for up to 6 snapshots.
    
    Parameters
    ----------
    structure_factor : dict
        Dictionary mapping snapshot names to 2D S(k) arrays.
    symbol : str
        Label for the extrema type (used in title).
    
    Returns
    -------
    plt.figure
        Matplotlib figure with 2x3 subplot grid.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        './config/matplotlib/snapshots.mplstyle'
        ])

    if len(structure_factor) > 6:
        indices = np.round(np.linspace(0, len(structure_factor)-1, 6)).astype(int)
        structure_factor = {key: value for i, (key, value) in enumerate(structure_factor.items()) if i in indices}
    
    figure, ax = plt.subplots(2,3)
    figure.suptitle(symbol, fontweight="bold")
    
    for i, (key, value) in enumerate(structure_factor.items()):
        
        _plot_structure_factor(
            ax= ax.flatten()[i],
            structure_factor= scipy.fftshift(value),
            iteration= key
            )

    return figure


def _plot_structure_factor(ax: plt.Axes, structure_factor: np.ndarray, iteration: str) -> None:
    """
    Plot a single 2D structure factor heatmap.
    
    Parameters
    ----------
    ax : plt.Axes
        Matplotlib axes to plot on.
    structure_factor : np.ndarray
        2D structure factor array (already fftshifted).
    iteration : str
        Label for the subplot title.
    """

    ax.imshow(
        structure_factor,
        extent=[0, 2*np.pi, 0, 2*np.pi],
        cmap="gray"
        )

    ax.set(
        title= iteration,
        xticks=[0, np.pi, 2*np.pi],
        xticklabels=["$-k$", "0", "$k$"],
        yticks=[0, np.pi, 2*np.pi],
        yticklabels=["", "0", "$k$"]
        )


def plot_radial_profile_snapshots(k_modes: np.ndarray, radial_profile_snapshots: dict, symbol: str) -> plt.figure:
    """
    Plot radially-averaged structure factor S(|k|) vs wavenumber.
    
    For many snapshots (>6), plots individual profiles in gray and
    the average in red. For fewer snapshots, plots each with a legend.
    
    Parameters
    ----------
    k_modes : np.ndarray
        Wavenumber values (x-axis).
    radial_profile_snapshots : dict
        Dictionary mapping snapshot names to 1D S(k) arrays.
    symbol : str
        Extrema type label.
    
    Returns
    -------
    plt.figure
        Matplotlib figure with S(k) scatter plot.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        './config/matplotlib/scatter.mplstyle'
        ])

    figure, ax = plt.subplots()

    if len(radial_profile_snapshots) > 6:

        accumulated_quantity = np.zeros_like(k_modes) 
        for i, (snapshot_key, snapshot_value) in enumerate(radial_profile_snapshots.items()):
            
            ax.plot(
                k_modes,
                snapshot_value, 
                "o",
                markersize=5,
                mfc="none",
                color="lightgray",
                )  
            
            accumulated_quantity = accumulated_quantity + snapshot_value
            if i == len(radial_profile_snapshots)-1: 
                ax.plot(
                    k_modes,
                    accumulated_quantity/len(radial_profile_snapshots), 
                    "o",
                    markersize=5,
                    color="red",
                    label= "Averaged Value"
                    )
                
                save_path = pathlib.Path("./data/hyperuniformity_analysis/arrays/snapshots/radial_profile/averages/"+symbol)
                save_path.mkdir(parents=True, exist_ok=True)
                np.savetxt(
                    fname= save_path.joinpath(symbol+"_radial_profile_mean"),
                    X= accumulated_quantity/len(radial_profile_snapshots)
                    )
    
    else:    
        for snapshot_key, snapshot_value in radial_profile_snapshots.items():

            ax.plot(
                k_modes,
                snapshot_value, 
                "o",
                markersize=5,
                mfc="none",
                label= snapshot_key
                )

    ax.set(
        xlabel= r"$k$",
        ylabel= r"$S(k)$" 
        )

    ax.legend(loc="lower right")

    return figure


def plot_normalized_radial_profile_snapshots(k_modes: np.ndarray, radial_profile_snapshots: dict, symbol: str) -> plt.figure:
    """
    Plot normalized radial profile S(k)/S(k_max) vs k/k_max.
    
    Normalizes each snapshot by its maximum value to enable
    comparison of profile shapes across different conditions.
    
    Parameters
    ----------
    k_modes : np.ndarray
        Wavenumber values.
    radial_profile_snapshots : dict
        Dictionary mapping snapshot names to 1D S(k) arrays.
    symbol : str
        Extrema type label.
    
    Returns
    -------
    plt.figure
        Matplotlib figure with normalized S(k) scatter plot.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        './config/matplotlib/scatter.mplstyle'
        ])

    figure, ax = plt.subplots()

    s_k_max_global=0
    k_max_global=0
    if len(radial_profile_snapshots) > 6:

        accumulated_quantity = np.zeros_like(k_modes) 
        for i, (snapshot_key, snapshot_value) in enumerate(radial_profile_snapshots.items()):
            
            s_k_max = np.max(snapshot_value)
            k_max_index = np.where(snapshot_value == s_k_max)
            k_max = k_modes[k_max_index][0]
            
            ax.plot(
                k_modes/k_max,
                snapshot_value/s_k_max, 
                "o",
                markersize=5,
                mfc="none",
                color="lightgray",
                )  
            
            accumulated_quantity = accumulated_quantity + (snapshot_value/s_k_max)
            if i == len(radial_profile_snapshots)-1: 
                s_k_max = np.max(accumulated_quantity/len(radial_profile_snapshots))
                k_max_index = np.where(accumulated_quantity/len(radial_profile_snapshots) == s_k_max)
                k_max = k_modes[k_max_index][0]

                ax.plot(
                    k_modes/k_max,
                    (accumulated_quantity/len(radial_profile_snapshots)), 
                    "o",
                    markersize=5,
                    color="red",
                    label= "Averaged Value"
                    )

                save_path = pathlib.Path("./data/hyperuniformity_analysis/arrays/snapshots/radial_profile/averages/"+symbol)
                save_path.mkdir(parents=True, exist_ok=True)
                np.savetxt(
                    fname= save_path.joinpath(symbol+"_normalized_radial_profile_mean"),
                    X= accumulated_quantity/len(radial_profile_snapshots)
                    )
                np.savetxt(
                    fname= save_path.joinpath(symbol+"_normalized_k_modes"),
                    X= k_modes/k_max
                    )
            
            if s_k_max > s_k_max_global:
                s_k_max_global = s_k_max
            if k_max > k_max_global:
                k_max_global = k_max
    
    else: 
        for snapshot_key, snapshot_value in radial_profile_snapshots.items():
            
            s_k_max = np.max(snapshot_value)
            k_max_index = np.where(snapshot_value == s_k_max)
            k_max = k_modes[k_max_index][0]
            
            ax.plot(
                k_modes/k_max,
                snapshot_value/s_k_max, 
                "o",
                markersize=5,
                mfc="none",
                label= snapshot_key
                )

            if s_k_max > s_k_max_global:
                s_k_max_global = s_k_max
            if k_max > k_max_global:
                k_max_global = k_max

    ax.set(
        xlabel= r"$k/K$",
        ylabel= r"$N(k)$"
        )

    ax.legend(loc="lower right")

    return figure


def plot_power_law_snapshots(k_modes: np.ndarray, radial_profile_snapshots: dict, symbol: str) -> plt.figure:
    """
    Plot normalized S(k) on log-log axes to visualize power-law behavior.
    
    Log-log plots reveal power-law relationships as straight lines.
    The slope gives the hyperuniformity exponent α in S(k) ~ k^α.
    
    Parameters
    ----------
    k_modes : np.ndarray
        Wavenumber values.
    radial_profile_snapshots : dict
        Dictionary mapping snapshot names to 1D S(k) arrays.
    symbol : str
        Extrema type label.
    
    Returns
    -------
    plt.figure
        Matplotlib figure with log-log S(k) plot.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        './config/matplotlib/scatter.mplstyle'
        ])

    figure, ax = plt.subplots()

    if len(radial_profile_snapshots) > 6:

        accumulated_quantity = np.zeros_like(k_modes) 
        for i, (snapshot_key, snapshot_value) in enumerate(radial_profile_snapshots.items()):
            
            s_k_max = np.max(snapshot_value)
            k_max_index = np.where(snapshot_value == s_k_max)
            k_max = k_modes[k_max_index][0]
            
            ax.plot(
                k_modes/k_max,
                snapshot_value/s_k_max, 
                "o",
                markersize=5,
                mfc="none",
                color="lightgray",
                )  
            
            accumulated_quantity = accumulated_quantity + (snapshot_value/s_k_max)
            if i == len(radial_profile_snapshots)-1: 
                s_k_max = np.max(accumulated_quantity/len(radial_profile_snapshots))
                k_max_index = np.where(accumulated_quantity/len(radial_profile_snapshots) == s_k_max)
                k_max = k_modes[k_max_index][0]

                ax.plot(
                    k_modes/k_max,
                    (accumulated_quantity/len(radial_profile_snapshots)), 
                    "o",
                    markersize=5,
                    color="red",
                    label= "Averaged Value"
                    )
            
    else: 
        for snapshot_key, snapshot_value in radial_profile_snapshots.items():
            
            s_k_max = np.max(snapshot_value)
            k_max_index = np.where(snapshot_value == s_k_max)
            k_max = k_modes[k_max_index][0]
            
            ax.plot(
                k_modes/k_max,
                snapshot_value/s_k_max, 
                "o",
                markersize=5,
                mfc="none",
                label= snapshot_key
                )

    ax.set(
        xscale="log",
        yscale="log",
        xlabel= r"$k/K$",
        ylabel= r"$N(k)$",
        xlim=[1e-2,1],
        ylim= [1e-5,1]
        )


    ax.legend(loc="lower right")

    return figure


def plot_k_max_snapshots(k_modes: np.ndarray, radial_profile_snapshots: dict, symbol: str) -> plt.figure:
    """
    Plot bar chart comparing max(S(k)) and k_max across snapshots.
    
    Useful for verifying that the peak wavenumber is consistent
    across different time snapshots.
    
    Parameters
    ----------
    k_modes : np.ndarray
        Wavenumber values.
    radial_profile_snapshots : dict
        Dictionary mapping snapshot names to 1D S(k) arrays.
    symbol : str
        Extrema type label.
    
    Returns
    -------
    plt.figure
        Matplotlib figure with dual-axis bar chart.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        ])

    if len(radial_profile_snapshots) > 6:
        indices = np.round(np.linspace(0, len(radial_profile_snapshots)-1, 6)).astype(int)
        radial_profile_snapshots = {key: value for i, (key, value) in enumerate(radial_profile_snapshots.items()) if i in indices}
    
    figure, ax = plt.subplots(figsize=(20,8))
    ax2 = ax.twinx()

    width = 7
    space = 1
    postions = np.linspace(0+3*width, len(radial_profile_snapshots)*(3*(width+space)), num= len(radial_profile_snapshots))
    
    s_k_max_snapshots=[]
    k_max_snapshots=[]
    for snapshot_key, snapshot_value in radial_profile_snapshots.items():
        
        s_k_max = np.max(snapshot_value)
        k_max_index = np.where(snapshot_value == s_k_max)
        k_max = k_modes[k_max_index][0]

        s_k_max_snapshots.append(round(s_k_max, 3))
        k_max_snapshots.append(k_max)


    bar_s_k_max = ax.bar(
        x= postions-width,
        height= s_k_max_snapshots,
        width= width,
        label= "$\\max(S(k))$",
        color= "k",
        edgecolor="k"
        )
    ax.bar_label(bar_s_k_max, padding=-40, color="w", fontweight="bold")

    bar_k_max = ax2.bar(
        x= postions,
        height= k_max_snapshots,
        width= width,
        label= "$\\max(k)$",
        color= "gray",
        edgecolor="k"
        )
    ax2.bar_label(bar_k_max, padding=-40, color="w", fontweight="bold")

    ax2.set(
        ylabel= "$\\max(k)$",
    )
    ax.set(
        xlabel= "Snapshots",
        ylabel= "$\\max(S(k))$",
        xticks=postions,
        xticklabels= radial_profile_snapshots.keys()
    )
    ax.legend(loc="upper left")
    ax2.legend(loc="upper right")

    return figure


def compare_fitting_intervals(k: np.ndarray, radial_profile_snapshots: dict, intervals: list[list], symbol: str) -> np.ndarray:
    """
    Compare R² values for different fitting intervals.
    
    Helps determine the optimal k-range for power-law fitting
    by showing how the fit quality varies with interval choice.
    
    Parameters
    ----------
    k : np.ndarray
        Wavenumber values.
    radial_profile_snapshots : dict
        Dictionary mapping snapshot names to radial profile data.
    intervals : list[list]
        List of [k_min, k_max] intervals to compare.
    symbol : str
        Extrema type key.
    
    Returns
    -------
    plt.figure
        Matplotlib bar chart of R² values.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        ])
    
    figure, ax = plt.subplots(figsize=(20,8))

    intervals_residuals=[]
    for interval in intervals:
        _, _, residuals = task.linear_curve_fitting(
            k= k,
            radial_profile_snapshots= radial_profile_snapshots, 
            k_interval= interval,
            symbol= symbol
        )

        intervals_residuals.append(residuals)

    width = 7
    space = 1
    postions = np.linspace(0+width, len(intervals_residuals)*((width+space)), num= len(intervals_residuals))
    
    bar_residuals = ax.bar(
        x= postions,
        height= intervals_residuals,
        width= width,
        label= symbol,
        color= "gray",
        edgecolor="k"
        )
    ax.bar_label(bar_residuals, padding=-40, color="w", fontweight="bold")


    ax.set(
        xlabel= "Fitting Intervals",
        ylabel= "Coefficient of Determination $R^2$",
        xticks=postions,
        xticklabels= [f"$k \\in [{interval[0]},{interval[1]}]$" for interval in  intervals]
    )

    return figure


def get_trend_line(ax: plt.Axes, k: np.ndarray, extrapolation_line: list) -> plt.figure:
    """
    Add a linear trend line to a plot with annotation.
    
    Draws the fitted line and annotates with the S(k=0) intercept,
    which is the key hyperuniformity indicator.
    
    Parameters
    ----------
    ax : plt.Axes
        Matplotlib axes to draw on.
    k : np.ndarray
        Wavenumber values for the x-axis extent.
    extrapolation_line : list
        [slope, intercept] from linear fit.
    
    Returns
    -------
    plt.Axes
        The modified axes object.
    """

    slop, y_intercept = extrapolation_line
    f = lambda x: slop*x + y_intercept
    ax.plot(
        k,
        f(k),
        "r--"
        )

    ax.annotate(
       "$S(k=0) =$"+" {:.2E}".format(y_intercept),
       xy= (np.mean(k), f(np.mean(k))),
       xytext=(0, -15),
       textcoords='offset points',
       fontsize=12,
       bbox= {
        "boxstyle": "round",
        "facecolor": "white",
        "alpha": 0.8
       }
    )


    return ax


def normalize_snapshots(k: np.ndarray, radial_profile_snapshots: dict, symbol: str) -> dict:
    """
    Normalize radial profiles by their maximum values.
    
    Parameters
    ----------
    k : np.ndarray
        Wavenumber values.
    radial_profile_snapshots : dict
        Dictionary mapping snapshot names to radial profile data.
    symbol : str
        Key to select extrema type from nested dictionaries.
    
    Returns
    -------
    dict
        Dictionary mapping snapshot names to normalized profiles.
    """

    normalized_snapshots = {}
    for i, (snapshot_key, snapshot_value) in enumerate(radial_profile_snapshots.items()):
        
        radial_profile_max = np.max(snapshot_value[symbol])
        k_max_index = np.where(snapshot_value[symbol] == radial_profile_max)
        k_max = k[k_max_index][0]
        
        k/k_max
        
        normalized_snapshots[snapshot_key] = snapshot_value[symbol]/radial_profile_max
    
    
    return normalized_snapshots