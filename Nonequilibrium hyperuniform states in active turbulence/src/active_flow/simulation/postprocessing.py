# env imports 
import shutil
import pathlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from neptune.new.types import File
from mpl_toolkits.axes_grid1 import make_axes_locatable


def save_arrays(operators: list, snapshots: list[tuple], headers: list[str], save_path: pathlib.Path) -> list:
    '''
    Placeholder
    '''

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
    '''
    Placeholder
    '''

    folder_path = save_path.joinpath("tables")
    folder_path.mkdir(parents=True, exist_ok=True)

    monitor_table = pd.DataFrame(monitored_data, columns=headers)
    monitor_table.to_csv(folder_path.joinpath("monitoring.csv"), index=False)

    return monitor_table


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


def plot_convergence(monitored_data: pd.DataFrame) -> plt.figure:
    '''
    Placeholder
    '''

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