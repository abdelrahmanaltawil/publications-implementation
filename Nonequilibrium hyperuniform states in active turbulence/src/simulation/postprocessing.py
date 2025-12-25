# env imports 
import shutil
import pathlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from neptune.new.types import File
from mpl_toolkits.axes_grid1 import make_axes_locatable


def save_arrays(operators: list, snapshots: list[tuple], headers: list[str], save_path: pathlib.Path) -> list:
    """
    Save operator arrays and simulation snapshots to disk.
    
    Organizes output into folders by quantity type and iteration number.
    
    Parameters
    ----------
    operators : list
        List of (array, name) tuples for spatial/frequency operators.
    snapshots : list[tuple]
        List of tuples (iteration, quantity1, quantity2, ...) from simulation.
    headers : list[str]
        Names for each saved quantity (e.g., ['w_k']).
    save_path : pathlib.Path
        Root directory for saving outputs.
    """

    for i, header in enumerate(headers):
        folder_path = save_path.joinpath("arrays/snapshots/"+header)
        folder_path.mkdir(parents=True, exist_ok=True)

        for snap in snapshots:
            iteration = snap[0]
            quantity = snap[i+1]

            file_name = header+"_"+str(iteration).zfill(8)
            np.save(folder_path.joinpath(file_name), quantity)


    for operator, file_name in operators:
        np.save(save_path.joinpath("arrays/"+file_name), operator)


def save_monitoring_table(monitored_data: list[tuple], headers: list[str], save_path: pathlib.Path) -> pd.DataFrame:
    """
    Save simulation monitoring data to a CSV file.
    
    Creates a table with columns for iteration number and all monitored
    quantities (e.g., simulation time, tau, max velocity, E(k=1)).
    
    Parameters
    ----------
    monitored_data : list[tuple]
        List of monitoring records from the simulation.
    headers : list[str]
        Column names for the output table.
    save_path : pathlib.Path
        Directory to save the CSV file.
    
    Returns
    -------
    pd.DataFrame
        The monitoring data as a pandas DataFrame.
    """

    folder_path = save_path.joinpath("tables")
    folder_path.mkdir(parents=True, exist_ok=True)

    monitor_table = pd.DataFrame(monitored_data, columns=headers)
    monitor_table.to_csv(folder_path.joinpath("monitoring.csv"), index=False)

    return monitor_table


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


def plot_convergence(monitored_data: pd.DataFrame) -> plt.figure:
    """
    Plot simulation convergence diagnostics.
    
    Creates a two-panel plot showing:
    - Top: Maximum velocity U_max vs iterations
    - Bottom: Energy at k=1, E(k=1), vs iterations
    
    Parameters
    ----------
    monitored_data : pd.DataFrame
        Monitoring table with 'Iterations', 'max velocity', 'E(k=1)' columns.
    
    Returns
    -------
    plt.figure
        Matplotlib figure with convergence plots.
    
    Notes
    -----
    E(k=1) should stabilize when steady state is reached.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle', 
        './config/matplotlib/convergence.mplstyle'
        ])

    figure, ax = plt.subplots(2,1)

    ax[0].plot(monitored_data["Iterations"], monitored_data["max velocity"])
    ax[0].set(
        xscale='log', 
        xticklabels=[], 
        ylabel="$U_{max}$"
        )

    ax[1].plot(monitored_data["Iterations"], monitored_data["E(k=1)"])

    ax[1].set(
        xscale='log', 
        xlabel="Iterations", 
        ylabel="$E(k)_{k=1}$"
        )
    
    return figure