# env imports
import zipfile
import pathlib
import numpy as np

# local imports
import extrema_search.helpers.register as re


def unzip_delete_file(file_path: pathlib.Path) -> None:
    """
    Extract a zip archive and delete the original zip file.
    
    Parameters
    ----------
    file_path : pathlib.Path
        Path to the zip file to extract.
    
    Notes
    -----
    Files are extracted to the current working directory.
    The original zip file is deleted after extraction.
    """

    # unzip
    with zipfile.ZipFile(file_path, 'r') as zip_file:
        zip_file.extractall(".")
        zip_file.close()

    # delete
    file_path.unlink()


def load_arrays(read_path: pathlib.Path, snapshots_locations: list[str]) -> tuple[dict]:
    """
    Load operator arrays and vorticity snapshots from disk.
    
    Parameters
    ----------
    read_path : pathlib.Path
        Directory containing the saved arrays.
    snapshots_locations : list[str]
        List of iteration numbers to load.
    
    Returns
    -------
    operators : dict
        Dictionary mapping operator names to numpy arrays
        (e.g., 'x_vectors', 'k_vectors').
    snapshots : dict
        Dictionary mapping snapshot names to vorticity arrays.
    
    Notes
    -----
    Results are registered in re.register["operators"] and
    re.register["snapshots"] for access by other functions.
    """

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


def extend(w: np.ndarray) -> np.ndarray:
    """
    Tile the vorticity field in a 3x3 grid for periodic boundary handling.
    
    Parameters
    ----------
    w : np.ndarray
        2D vorticity array.
    
    Returns
    -------
    np.ndarray
        Extended array with 9 copies of the original arranged in a 3x3 grid.
    """

    return np.tile(w, (3,3))


def extend_space(axis: np.ndarray) -> tuple[np.ndarray]:
    """
    Extend the spatial axis for periodic tiling.
    
    Creates a 3x extended axis array covering [-2π, 4π] from [0, 2π].
    
    Parameters
    ----------
    axis : np.ndarray
        1D array of original axis values.
    
    Returns
    -------
    X : np.ndarray
        2D meshgrid of extended x-coordinates.
    Y : np.ndarray
        2D meshgrid of extended y-coordinates.
    """

    axis_chunk1 = axis-2*np.pi
    axis_chunk2 = axis+2*np.pi

    axis = np.append(axis_chunk1, [axis, axis_chunk2])
    X, Y = np.meshgrid(axis, axis)
    
    return X, Y


def get_subdomain(x_limit: list, y_limit: list, axis: np.ndarray):
    """
    Find index intervals for a specified subdomain region.
    
    Parameters
    ----------
    x_limit : list
        [x_start, x_end] coordinates of the subdomain.
    y_limit : list
        [y_start, y_end] coordinates of the subdomain.
    axis : np.ndarray
        1D array of axis values (assumes square domain).
    
    Returns
    -------
    tuple
        (x_start_idx, x_end_idx, y_start_idx, y_end_idx) indices.
    """

    index_x = []
    index_y = []

    for index, limit in [(index_x, x_limit), (index_y, y_limit)]:
        n = 0
        for i in range(len(axis)):
            if axis[i] > limit[n]:
                index.append(i)
                n+=1
            
            if n>1:
                break

    return *index_x, *index_y


def filter(w_k, method, kk=None, k=None):
    """
    Apply spectral filtering to the vorticity field.
    
    Filters can be applied in either real space or k-space (Fourier space).
    K-space filtering zeros out high-frequency components above a threshold.
    
    Parameters
    ----------
    w_k : np.ndarray
        Vorticity data (in Fourier space for k-space filtering).
    method : str
        Filter method: "real space" or "k space".
    kk : np.ndarray, optional
        |k|² array for k-space filtering.
    k : int, optional
        Maximum wavenumber to keep (cutoff frequency).
    
    Returns
    -------
    np.ndarray
        Filtered vorticity data.
    
    Raises
    ------
    NotImplementedError
        If method is not "real space" or "k space".
    """

    if method == 'k space':

        # k = int(input('What is the maximum k values you want to keep in the data?'))
        deAlias = kk < (k)**2

        w_k = w_k * deAlias

        return w_k

    elif method == 'real space':
        pass
    else:
        raise NotImplemented("The choice of method is not implemented, choose between 'real space' or 'k space'")
