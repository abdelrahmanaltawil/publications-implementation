# env imports
import zipfile
import pathlib
import numpy as np

# local imports
import active_flow.extrema_search.helpers.register as re


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


def load_arrays(read_path: pathlib.Path, snapshots_locations: list[str]) -> tuple[dict]:
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


def extend(w: np.ndarray) -> np.ndarray:
    '''
    Placeholder
    '''

    return np.tile(w, (3,3))


def extend_space(axis: np.ndarray) -> tuple[np.ndarray]:
    '''
    Placeholder
    '''

    axis_chunk1 = axis-2*np.pi
    axis_chunk2 = axis+2*np.pi

    axis = np.append(axis_chunk1, [axis, axis_chunk2])
    X, Y = np.meshgrid(axis, axis)
    
    return X, Y


def get_subdomain(x_limit: list, y_limit: list, axis: np.ndarray):
    '''
    return index interval for specified region in the domain

    x_limit  :   list
                specify start and end x coordinate of the subdomain `[x0, xn]`
    y_limit  :   list
                specify start and end y coordinate of the subdomain `[y0, yn]`
    axis    :   ndarray
                axis of the domain, assuming that the we have deal with square 
                domain
    '''

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
    '''
    filtering the data in two approaches
    - In real space: replace every value by the mean value of its neighbors 
    - In k-space: Set high frequency values "k-values" to zero and reconstruct the real space image. High frequency low wave length   
    
    w_k     :   ndarray
                data we want to filter
    method  :   string
                filter method we will follow. Choices either `"real space"` or `"k space"`
    kk      :   ndarray
                If the method is `"k space"` you need to provide the frequency domain discretization matrix
    k       :   int
                upper bound of the allowed frequency
    '''

    if method == 'k space':

        # k = int(input('What is the maximum k values you want to keep in the data?'))
        deAlias = kk < (k)**2

        w_k = w_k * deAlias

        return w_k

    elif method == 'real space':
        pass
    else:
        raise NotImplemented("The choice of method is not implemented, choose between 'real space' or 'k space'")

