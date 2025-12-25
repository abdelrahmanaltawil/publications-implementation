# env imports
import pathlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# local imports
import active_flow.extrema_search.helpers.axis_formater as formatter


def save_arrays(operators: dict, extrema_snapshots: dict, save_path: pathlib.Path) -> list:
    '''
    Placeholder
    '''

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
    '''
    This function is a design choice where we need to enforce the user
    only to fetch data from experiments runs and not locally. 
    
    The argument is, when data is fetched for further analysis we need to
    maintain the metadata experiment that generated the data we want to fetch 
    so we can append these metadata of our new experiment.
    '''

    for file_path in data_path.rglob("*"):
        if file_path.is_file():
            file_path.unlink()


def plot_point_cloud_snapshots(x_vector: np.ndarray, extrema_snapshots: dict, symbol: str) -> list[plt.figure]:
    '''
    Placeholder 
    '''

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
    '''
    Placeholder
    '''

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
    '''
    Placeholder
    '''

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
    '''
    Placeholder
    '''

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
    '''
    Placeholder
    '''

    if len(extrema_snapshots) > 6:
        indices = np.round(np.linspace(0, len(extrema_snapshots)-1, 6)).astype(int)
        extrema_snapshots = {key: value for i, (key, value) in enumerate(extrema_snapshots.items()) if i in indices}

    figure = go.Figure()

    buttons=[]
    # traces=[]
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
        
        # for extrema_key in ["Minima", "Maxima"]:
        #     figure.add_trace(
        #         go.Scatter(
        #             x= extrema_snapshot_value[extrema_key][:,0],
        #             y= extrema_snapshot_value[extrema_key][:,1],
        #             name=snapshot_key,
        #             visible= True if i == len(w_snapshots)-1 else False,
        #             ),
        #             secondary_y=True
        #         )

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
    '''
    Placeholder
    '''

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