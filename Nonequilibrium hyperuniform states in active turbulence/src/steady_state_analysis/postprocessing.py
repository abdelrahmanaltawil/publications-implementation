# env imports 
import pathlib
import pandas as pd
import numpy as np
import scipy.fftpack as scipy
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

# local imports
import steady_state_analysis.helpers.axis_formater as formatter


def save_arrays(operators: dict, snapshots: dict, save_path: pathlib.Path) -> list:
    """
    Save operator arrays and snapshots to disk.

    Parameters
    ----------
    operators : dict
        Dictionary of operator arrays to save to the root of save_path.
    snapshots : dict
        Dictionary of snapshot arrays to save in 'snapshots/w_k' subdirectory.
    save_path : pathlib.Path
        Root directory for saving.
    """

    save_path.mkdir(parents=True, exist_ok=True)
    save_path.joinpath("snapshots/w_k").mkdir(parents=True, exist_ok=True)

    for key, value in operators.items():
        np.save(save_path.joinpath(key), value)

    for key, value in snapshots.items():
        np.save(save_path.joinpath("snapshots/w_k/"+key), value)


def save_monitoring_table(monitor_table: pd.DataFrame, save_path: pathlib.Path) -> pd.DataFrame:
    """
    Save the monitoring table to a CSV file.

    Parameters
    ----------
    monitor_table : pd.DataFrame
        Data to save.
    save_path : pathlib.Path
        Root directory to save 'tables/monitoring.csv' in.

    Returns
    -------
    pd.DataFrame
        The saved DataFrame.
    """

    folder_path = save_path.joinpath("tables")
    folder_path.mkdir(parents=True, exist_ok=True)

    monitor_table.to_csv(folder_path.joinpath("monitoring.csv"), index=False)

    return monitor_table


def remove_data(data_path: pathlib.Path) -> None:
    """
    Remove all files in a directory tree.

    Enforces the design pattern where data is only fetched from Neptune.ai
    records and not persisted locally, ensuring metadata provenance.

    Parameters
    ----------
    data_path : pathlib.Path
        Root directory to clean. All files (not directories) are deleted.
    """

    for file_path in data_path.rglob("*"):
        if file_path.is_file():
            file_path.unlink()


def plot_snapshots_location(monitored_data: pd.DataFrame, snapshots_locations: list[int]) -> plt.figure:
    """
    Plot the energy history and highlight selected snapshot locations.

    Parameters
    ----------
    monitored_data : pd.DataFrame
        Table containing 'Iterations' and 'E(k=1)'.
    snapshots_locations : list[int]
        List of iteration numbers corresponding to the snapshots.

    Returns
    -------
    plt.figure
        Matplotlib figure showing the energy evolution and snapshot points.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle', 
        './config/matplotlib/convergence.mplstyle'
        ])

    figure, ax = plt.subplots(figsize=(12,4))

    ax.plot(monitored_data["Iterations"], monitored_data["E(k=1)"])
    
    ax.set(
        xlabel="Iterations", 
        ylabel="$E(k)_{k=1}$"
        )

    snapshots = monitored_data[monitored_data["Iterations"].isin(snapshots_locations)]
    # ax.scatter(snapshots["Iterations"], snapshots["E(k=1)"], zorder=2, label="Snapshots Locations")

    ax.plot(snapshots["Iterations"], snapshots["E(k=1)"], zorder=2, alpha=0.4, color="yellow", lw=10, label="Snapshots Interval")

    ax.legend()

    return figure


def calculate_fields(k_vectors: np.ndarray, snapshots: dict) -> dict:
    """
    Compute derived physical fields from vorticity in Fourier space.

    Calculates velocity (u, v), speed |U|, vorticity ω, stream function ψ, 
    and energy spectrum E(k) for each snapshot.

    Parameters
    ----------
    k_vectors : np.ndarray
        Wavenumber grid (kx, ky).
    snapshots : dict
        Dictionary of vorticity snapshots in Fourier space.

    Returns
    -------
    dict
        Dictionary of computed fields for each snapshot.
    """

    # prepare operators
    ik_x = 1j*k_vectors[:,:,0]
    ik_y = 1j*k_vectors[:,:,1]
    k_modes = np.arange(1, np.max(k_vectors[:,:,0][0]))
    k_norm = np.sqrt(k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2)
    k_square = k_norm**2
    k_square[0,0] = 1
    
    snapshots_fields={}
    for key, w_k in snapshots.items():
        
        w = np.real(scipy.ifft2(w_k))

        psi_k = w_k/k_square
        psi = np.real(scipy.ifft2(psi_k))

        u_k = ik_y*psi_k
        v_k = -ik_x*psi_k
        U_k = np.abs(u_k)**2 + np.abs(v_k)**2

        u = np.real(scipy.ifft2(u_k))
        v = np.real(scipy.ifft2(v_k))
        U = np.sqrt(u**2 + v**2)

        E_k = np.zeros_like(k_modes)
        for i, k in enumerate(k_modes):
            circle = np.where((k_norm >= k) & (k_norm < k+1))

            E_k[i] = 0.5*np.sum(U_k[circle])/len(k_norm[0])**4

        iteration = key.replace("w_k_","").replace(".npy","").lstrip('0')
        iteration = "0" if iteration == "" else iteration
        iteration = "Iteration = " + iteration

        snapshots_fields[iteration] = {
            "$u$": u, 
            "$v$": v, 
            "$|U|$": U, 
            "$\omega$": w, 
            "$\psi$": psi, 
            "$E(k)$": E_k
        }


    return snapshots_fields


def plot_snapshots_fields(x: np.ndarray, y: np.ndarray, snapshots_fields: dict, symbol: str) -> plt.figure:
    """
    Generate a grid of plots for a specific field across multiple snapshots.

    Parameters
    ----------
    x : np.ndarray
        x-coordinates.
    y : np.ndarray
        y-coordinates.
    snapshots_fields : dict
        Dictionary of computed fields for each snapshot.
    symbol : str
        Key of the field to plot (e.g., "$|U|$", "$\omega$").

    Returns
    -------
    plt.figure
        Matplotlib figure containing the subplots.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        './config/matplotlib/snapshots.mplstyle'
        ])

    if len(snapshots_fields) > 6:
        indices = np.round(np.linspace(0, len(snapshots_fields)-1, 6)).astype(int)
        snapshots_fields = {key: value for i, (key, value) in enumerate(snapshots_fields.items()) if i in indices}
    
    figure, ax = plt.subplots(2,3)
    figure.suptitle(symbol, fontweight="bold")

    for i, (snapshot_key, snapshot_value) in enumerate(snapshots_fields.items()):
        
        _plot_fields(
            figure,
            ax= ax.flatten()[i],
            x= x,
            y= y,
            field= snapshot_value[symbol],
            u= snapshot_value["$u$"],
            v= snapshot_value["$v$"],
            iteration= snapshot_key
            )

    return figure


def _plot_fields(figure, ax: plt.Axes, x: np.ndarray, y: np.ndarray, field: np.ndarray, u: np.ndarray, v: np.ndarray, iteration: str) -> plt.figure:
    """
    Helper function to plot a single field with velocity quiver overlay.

    Parameters
    ----------
    figure : plt.Figure
        Parent figure.
    ax : plt.Axes
        Axes to plot on.
    x : np.ndarray
        x-coordinates.
    y : np.ndarray
        y-coordinates.
    field : np.ndarray
        Scalar field to plot (contourf).
    u : np.ndarray
        x-velocity component for quiver.
    v : np.ndarray
        y-velocity component for quiver.
    iteration : str
        Title for the subplot.
    """

    contour = ax.contourf(
        x, 
        y, 
        field, 
        levels=100
        )

    skip=(slice(None,None,10),slice(None,None,10))
    ax.quiver(
        x[skip],
        y[skip],
        u[skip],
        v[skip],
        )

    ax.set(
        title= iteration
        )
    ax.xaxis.set_major_locator(plt.MultipleLocator(np.max(x[0,:])/2))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(formatter.multiple_formatter()))
    ax.yaxis.set_major_locator(plt.MultipleLocator(np.max(y[:,0])/2))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(formatter.multiple_formatter()))

    # cbar
    vmin=np.min(field)
    vmax=np.max(field)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("bottom", size="5%", pad=0.3)
    cbar= figure.colorbar(
        mappable= contour, 
        cax= cax,
        ticks= [vmin, (vmax + vmin)/2, vmax],
        orientation="horizontal"
        )
    cbar.ax.locator_params(nbins=3)

    ax.axes.set_aspect('equal')


def plot_snapshots_spectra(k: np.ndarray, snapshots_fields: dict) -> plt.figure:
    """
    Plot energy spectra E(k) for snapshots.

    Parameters
    ----------
    k : np.ndarray
        Wavenumber modes.
    snapshots_fields : dict
        Dictionary containing field data including "$E(k)$".

    Returns
    -------
    plt.figure
        Log-log plot of energy spectra.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        './config/matplotlib/scatter.mplstyle'
        ])
    
    figure, ax = plt.subplots()

    if len(snapshots_fields) > 6:
        accumulated_quantity = np.zeros_like(k) 
        for i, (snapshot_key, snapshot_value) in enumerate(snapshots_fields.items()):

            ax.loglog(k, snapshot_value["$E(k)$"], zorder=2, color="lightgray")

            accumulated_quantity = accumulated_quantity + snapshot_value["$E(k)$"]
            if i == len(snapshots_fields)-1: 
                _plot_mean_energy_spectra(
                    ax= ax,
                    k= k,
                    E_k= accumulated_quantity/len(snapshots_fields),
                    )
        
    else:

        for i, (snapshot_key, snapshot_value) in enumerate(snapshots_fields.items()):
            if i == 0: 
                _plot_energy_spectra(
                    ax= ax,
                    k= k,
                    E_k= snapshot_value["$E(k)$"],
                    iteration= snapshot_key
                    )
                continue

            ax.loglog(k, snapshot_value["$E(k)$"], zorder=2, label=snapshot_key)
            
    ax.legend()

    return figure


def _plot_energy_spectra(ax, k: np.ndarray, E_k: np.ndarray, iteration: str) -> plt.figure:
    """
    Helper to plot a single energy spectrum.

    Parameters
    ----------
    ax : plt.Axes
        Axes to plot on.
    k : np.ndarray
        Wavenumber modes.
    E_k : np.ndarray
        Energy spectrum values.
    iteration : str
        Label for the plot.
    """

    ax.loglog(k, E_k, zorder=2, label=iteration)

    ax.set(
        xlabel="$k$",  
        ylabel="$E(k)$", 
        xlim=[1e-1, 1e2], 
        ylim=[1e-6, 1e2]
        )

    # scaling lines and highlight region
    x1 = np.linspace(2, 20, num=50)
    x2 = np.linspace(2, 20, num=50)
    ax.loglog(x1, 1e-4*x1, marker="", linestyle="-", color="k", zorder=3)
    ax.loglog(x2, 1e1*x2**(-5/3), marker="", linestyle="-", color="k", zorder=3)
    ax.text(
        x= 6, 
        y= 1e-4, 
        s= '$k$'
        )
    ax.text(
        x= 6, 
        y= 1e-0, 
        s= '$k^{-5/3}$'
        )

    ax.vlines(x=[33, 40], ymin=1e-6, ymax=1e2, colors='gray', zorder=1)
    ax.axvspan(33, 40, color='gray', zorder=1)


def _plot_mean_energy_spectra(ax, k: np.ndarray, E_k: np.ndarray) -> plt.figure:
    """
    Helper to plot the mean energy spectrum.

    Parameters
    ----------
    ax : plt.Axes
        Axes to plot on.
    k : np.ndarray
        Wavenumber modes.
    E_k : np.ndarray
        Mean energy spectrum values.
    """

    ax.loglog(k, E_k, zorder=2, label="Mean Value", color="red")

    ax.set(
        xlabel="$k$",  
        ylabel="$E(k)$", 
        xlim=[1e-1, 1e2], 
        ylim=[1e-6, 1e2]
        )

    # scaling lines and highlight region
    x1 = np.linspace(2, 20, num=50)
    x2 = np.linspace(2, 20, num=50)
    ax.loglog(x1, 1e-4*x1, marker="", linestyle="-", color="k", zorder=3)
    ax.loglog(x2, 1e1*x2**(-5/3), marker="", linestyle="-", color="k", zorder=3)
    ax.text(
        x= 6, 
        y= 1e-4, 
        s= '$k$'
        )
    ax.text(
        x= 6, 
        y= 1e-0, 
        s= '$k^{-5/3}$'
        )

    ax.vlines(x=[33, 40], ymin=1e-6, ymax=1e2, colors='gray', zorder=1)
    ax.axvspan(33, 40, color='gray', zorder=1)