# env imports
import pathlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# local imports
import extrema_search.helpers.axis_formater as formatter


def save_arrays(operators: dict, extrema_snapshots: dict, save_path: pathlib.Path) -> list:
    """
    Save operator arrays and extrema snapshots to disk.
    
    Parameters
    ----------
    operators : dict
        Dictionary mapping operator names to numpy arrays.
    extrema_snapshots : dict
        Dictionary with structure {iteration: {'All Extrema': arr, 'Minima': arr, 'Maxima': arr}}.
    save_path : pathlib.Path
        Directory to save files to.
    """

    save_path.mkdir(parents=True, exist_ok=True)
    save_path.joinpath("snapshots/extrema").mkdir(parents=True, exist_ok=True)

    for operator_key, operator_value in operators.items():
        np.save(save_path.joinpath(operator_key), operator_value)


    for extrema_snapshot_key, extrema_snapshot_value in extrema_snapshots.items():

        iteration = extrema_snapshot_key.split("= ")[1].zfill(8)

        np.save(save_path.joinpath("snapshots/extrema/"+"all_extrema_"+iteration), extrema_snapshot_value["All Extrema"])
        np.save(save_path.joinpath("snapshots/extrema/"+"minima_"+iteration), extrema_snapshot_value["Minima"])
        np.save(save_path.joinpath("snapshots/extrema/"+"maxima_"+iteration), extrema_snapshot_value["Maxima"])


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


def plot_point_cloud_snapshots(x_vector: np.ndarray, extrema_snapshots: dict, symbol: str) -> list[plt.figure]:
    """
    Plot 2D point clouds of extrema locations for multiple snapshots.
    
    Creates a 2x3 grid of scatter plots showing vortex center positions.
    
    Parameters
    ----------
    x_vector : np.ndarray
        Spatial coordinate grid for axis formatting.
    extrema_snapshots : dict
        Dictionary mapping iteration labels to extrema data.
    symbol : str
        Key for extrema type ("All Extrema", "Minima", or "Maxima").
    
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
    
    if len(extrema_snapshots) > 6:
        indices = np.round(np.linspace(0, len(extrema_snapshots)-1, 6)).astype(int)
        extrema_snapshots = {key: value for i, (key, value) in enumerate(extrema_snapshots.items()) if i in indices}

    figure, ax = plt.subplots(2,3)
    figure.suptitle(symbol, fontweight="bold")

    for i, (snapshot_key, snapshot_value) in enumerate(extrema_snapshots.items()):

            _plot_point_cloud(
                ax= ax.flatten()[i],
                x_vector= x_vector,
                extrema= snapshot_value[symbol],
                iteration= snapshot_key
                )

    return figure


def _plot_point_cloud(ax: plt.Axes, x_vector: np.ndarray, extrema: np.ndarray, iteration: str) -> None:
    """
    Plot a single point cloud of extrema positions.
    
    Parameters
    ----------
    ax : plt.Axes
        Matplotlib axes to plot on.
    x_vector : np.ndarray
        Spatial coordinates for axis formatting.
    extrema : np.ndarray
        Extrema positions, shape (N, 3) with [x, y, z].
    iteration : str
        Label for the subplot title.
    """

    ax.scatter(
        x= extrema[:,0],
        y= extrema[:,1],
        s= 0.5,
        marker = '.',
        color= "black",
    )

    ax.set(
        title= iteration
        )
    ax.xaxis.set_major_locator(plt.MultipleLocator(np.max(x_vector[:,:,0][0,:])/2))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(formatter.multiple_formatter()))
    ax.yaxis.set_major_locator(plt.MultipleLocator(np.max(x_vector[:,:,1][:,0])/2))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(formatter.multiple_formatter()))


def plot_extrema_count_snapshots(extrema_snapshots: dict) -> plt.figure:
    """
    Plot bar chart comparing extrema counts across snapshots.
    
    Shows counts of all extrema, minima, and maxima for each snapshot.
    
    Parameters
    ----------
    extrema_snapshots : dict
        Dictionary mapping iteration labels to extrema data.
    
    Returns
    -------
    plt.figure
        Matplotlib bar chart figure.
    """

    # define style
    plt.style.use([
        './config/matplotlib/main.mplstyle',
        ])

    if len(extrema_snapshots) > 6:
        indices = np.round(np.linspace(0, len(extrema_snapshots)-1, 6)).astype(int)
        extrema_snapshots = {key: value for i, (key, value) in enumerate(extrema_snapshots.items()) if i in indices}
    
    figure, ax = plt.subplots(figsize=(20,8))

    width = 5
    space = 1
    postions = np.linspace(0+3*width, len(extrema_snapshots)*(3*(width+space)), num= len(extrema_snapshots))
    
    bar_all_extrema = ax.bar(
        x= postions-width,
        height= [len(snapshot["All Extrema"]) for snapshot in extrema_snapshots.values()],
        width= width,
        label= "All Extrema",
        color= "k",
        edgecolor="k"
        )
    ax.bar_label(bar_all_extrema, padding=-40, color="w", fontweight="bold")

    bar_minima = ax.bar(
        x= postions,
        height= [len(snapshot["Minima"]) for snapshot in extrema_snapshots.values()],
        width= width,
        label= "Minima",
        color= "gray",
        edgecolor="k"
        )
    ax.bar_label(bar_minima, padding=-40, color="w", fontweight="bold")

    bar_maxima = ax.bar(
        x= postions+width,
        height= [len(snapshot["Maxima"]) for snapshot in extrema_snapshots.values()],
        width= width,
        label= "Maxima",
        color= "lightgrey",
        edgecolor="k"
        )
    ax.bar_label(bar_maxima, padding=-40, color="w", fontweight="bold")

    ax.set(
        xlabel= "Snapshots",
        ylabel= "Extrema Count",
        xticks=postions,
        xticklabels= extrema_snapshots.keys()
    )
    ax.legend()

    return figure


def _plot_extrema_count(ax: plt.Axes, x: float, extrema_snapshot_value: dict, width: float) -> plt.figure:
    """
    Plot bars for a single snapshot's extrema counts.
    
    Parameters
    ----------
    ax : plt.Axes
        Matplotlib axes to plot on.
    x : float
        X-position for the bar group.
    extrema_snapshot_value : dict
        Dictionary with 'All Extrema', 'Minima', 'Maxima' arrays.
    width : float
        Width of each bar.
    """

    bar_all_extrema = ax.bar(
        x= x,
        height= len(extrema_snapshot_value["All Extrema"]),
        width= width,
        label= "All Extrema",
        color= "k"
        )
    ax.bar_label(bar_all_extrema, padding=-40, color="w", fontweight="bold")

    bar_minima = ax.bar(
        x= x+width,
        height= len(extrema_snapshot_value["Minima"]),
        width= width,
        label= "Minima",
        color= "royalblue"
        )
    ax.bar_label(bar_minima, padding=-40, color="w", fontweight="bold")

    bar_maxima = ax.bar(
        x= x+2*width,
        height= len(extrema_snapshot_value["Maxima"]),
        width= width,
        label= "Maxima",
        color= "lightsteelblue"
        )
    ax.bar_label(bar_maxima, padding=-40, color="w", fontweight="bold")
        

def interactive_point_cloud_plot( x_vector: np.ndarray, extrema_snapshots: np.ndarray, w_snapshots: dict) -> None:
    """
    Create an interactive Plotly figure with vorticity contours.
    
    Includes a dropdown menu to switch between different snapshots.
    
    Parameters
    ----------
    x_vector : np.ndarray
        Spatial coordinate grid.
    extrema_snapshots : np.ndarray
        Dictionary mapping iterations to extrema positions.
    w_snapshots : dict
        Dictionary mapping iterations to vorticity fields.
    
    Returns
    -------
    go.Figure
        Interactive Plotly figure with contour plots.
    """

    if len(extrema_snapshots) > 6:
        indices = np.round(np.linspace(0, len(extrema_snapshots)-1, 6)).astype(int)
        extrema_snapshots = {key: value for i, (key, value) in enumerate(extrema_snapshots.items()) if i in indices}

    figure = go.Figure()

    buttons=[]
    for i, ((extrema_snapshot_key, extrema_snapshot_value),( _, w_snapshot_value)) in enumerate(zip(extrema_snapshots.items(), w_snapshots.items())):

        figure.add_trace(
            go.Contour(
                x= x_vector[:,:,0][0,:],
                y= x_vector[:,:,1][:,0],
                z= w_snapshot_value,
                visible= True if i == len(w_snapshots)-1 else False,
                colorscale="balance"
                )
            )

        buttons.append(dict(
            label=extrema_snapshot_key,
            method="update",
            args=[{
                "visible": np.arange(len(extrema_snapshots)) == i,
                "autosize": False
                }],
            )
        )

    figure.update_layout(
        width= 1000,
        height= 1000,
        updatemenus=[
            go.layout.Updatemenu(
                active=len(w_snapshots)-1,
                buttons= buttons
                )
            ]
        )

    return figure


def interactive_surface_plot(x_vector: np.ndarray, w_snapshots: dict) -> None:
    """
    Create an interactive 3D surface plot of vorticity.
    
    Includes a dropdown menu to switch between different snapshots.
    
    Parameters
    ----------
    x_vector : np.ndarray
        Spatial coordinate grid.
    w_snapshots : dict
        Dictionary mapping iterations to vorticity fields.
    
    Returns
    -------
    go.Figure
        Interactive Plotly 3D surface figure.
    """

    if len(w_snapshots) > 6:
        indices = np.round(np.linspace(0, len(w_snapshots)-1, 6)).astype(int)
        w_snapshots = {key: value for i, (key, value) in enumerate(w_snapshots.items()) if i in indices}

    figure = go.Figure()

    buttons=[]
    for i, (w_snapshot_key, w_snapshot_value) in enumerate(w_snapshots.items()):
        figure.add_trace(
                go.Surface(
                    x= x_vector[:,:,0], 
                    y= x_vector[:,:,1],
                    z= w_snapshot_value,
                    visible= True if i == len(w_snapshots)-1 else False,
                    colorscale="balance"
                )
        )

        buttons.append(dict(
            label=w_snapshot_key,
            method="update",
            args=[{
                "visible": np.arange(len(w_snapshots)) == i,
                "autosize": False
                }]
            )
        )
        
    figure.update_layout(
        width= 1000,
        height= 1000,
        updatemenus=[
            go.layout.Updatemenu(
                active=len(w_snapshots)-1,
                buttons= buttons
                )
            ]
        )

    return figure