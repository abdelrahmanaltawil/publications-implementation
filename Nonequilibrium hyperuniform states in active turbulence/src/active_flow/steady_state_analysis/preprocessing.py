# env imports
import pathlib
import zipfile
import numpy as np
import pandas as pd

# local imports
import active_flow.steady_state_analysis.helpers.register as re
import active_flow.steady_state_analysis.helpers.check_snapshots as snapshots


def parse_parameters(parameters: dict) -> None:
    '''
    Placeholder
    '''

    parameters["postprocessing"]["snapshots_locations"] = snapshots.parse_snapshots(
        snapshots_locations= parameters["postprocessing"]["snapshots_locations"]
        )


def fetch(experiment_file: object, temp_download_path: pathlib.Path) -> np.ndarray or pd.DataFrame:
    '''
    Placeholder
    '''

    experiment_file.download(destination= temp_download_path)

    # you need to unzip "zip file name can be found in experiment_file path (aka arrays)", 
    # you need to double check it you need extracted path share the same name with the zip file path (in our case arrays)
    # you need to load all arrays "check why we used snapshots in this operation -> Ans: you want to make sure the snapshots are loaded in ascending order in the 
    # dictionary"
    if temp_download_path.glob("*.zip") is not None:
        unzip_delete_file(
            file_path= temp_download_path.glob("*.zip") # full path it will return all unzip file if exits "so make sure you download path does not contain any zip file", 
            # a good design for that is to create a temp file where you download the zip file at
            )
        load_arrays(
            read_path= temp_download_path.joinpath("/arrays"), # should be same as zip file name
            snapshots_locations= None # this a problem you need to solve if you want to do the averaging @NOTE # you do not need it you can sort through json
            # first extract iterations from the names in the formate "iterations = 00000100"
        )


    # no need for unzipping you need only the file name which is found in experiment_file path (aka monitoring)
    elif temp_download_path.glob("*.csv") is not None:
        load_table(
            read_path= temp_download_path.joinpath("/monitoring.csv")
        )

    
def unzip_delete_file(file_path: pathlib.Path) -> None:
    '''
    Placeholder
    '''

    # unzip
    with zipfile.ZipFile(file_path, 'r') as zip_file:
        zip_file.extractall(".")
        zip_file.close()

    # delete
    file_path.unlink()


def load_arrays(read_path: pathlib.Path, snapshots_locations: list[str]) -> tuple[np.ndarray]:
    '''
    Placeholder
    '''

    operators={}
    for path in read_path.glob("*.npy"):
        operators[path.stem] = np.load(path)
    
    snapshots={}
    snapshots_paths =[]

    snapshots_file_pattern = ["*"+str(location).zfill(8)+"*" for location in snapshots_locations]
    for pattern in snapshots_file_pattern:
        snapshots_paths.extend(read_path.joinpath("snapshots/w_k").glob(pattern)) 

    for path in snapshots_paths:
        snapshots[path.stem] = np.load(path)

    # register
    re.register["operators"] = operators
    re.register["snapshots"] = snapshots

    return operators, snapshots


# def load_arrays(read_path: pathlib.Path) -> tuple[np.ndarray]:
#     '''
#     Placeholder
#     '''

#     operators={}
#     for path in read_path.glob("*.npy"):
#         operators[path.stem] = np.load(path)
    
#     snapshots={}
#     snapshots_paths =[]
#     w_k={}
#     extrema={}
#     minima={}
#     maxima={}
#     all_extrema={}

#     for path in read_path.joinpath("/snapshots/w_k").glob("*.npy"):
#         w_k[path.stem] = np.load(path)

#     for path in read_path.joinpath("/snapshots/extrema/all_extrema").glob("*.npy"):
#         extrema[path.stem] = np.load(path)

#     for path in read_path.joinpath("/snapshots/extrema/minima").glob("*.npy"):
#         operators[path.stem] = np.load(path)

#     for path in read_path.joinpath("/snapshots/extrema/maxima").glob("*.npy"):
#         operators[path.stem] = np.load(path)

#     for pattern in snapshots_file_pattern:
#         snapshots_paths.extend(read_path.joinpath("snapshots/w_k").glob(pattern)) 

#     for snapshot in read_path.joinpath("snapshots").glob(".npy"):
#         pass
#         # get file name and extract iteration 
#         # construct the iteration formate
#         # use it as key for the snapshot value

#         # challenge: how you could handle the case where you have extrema values such as minima and maxima and all_extrema 


#     for path in snapshots_paths:
#         snapshots[path.stem] = np.load(path)

#     # register
#     re.register["operators"] = operators
#     re.register["snapshots"] = snapshots

#     return operators, snapshots


def load_table(read_path: pathlib.Path) -> pd.DataFrame:
    '''
    Placeholder
    '''

    monitor_table = pd.read_csv(read_path)

    return monitor_table
    

