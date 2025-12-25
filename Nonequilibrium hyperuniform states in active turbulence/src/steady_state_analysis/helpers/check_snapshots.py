"""
Utilities for parsing and validating snapshot location specifications.
"""

import numpy as np


def parse_snapshots(snapshots_locations: list[str]) -> np.ndarray[int]:
    """
    Parse snapshot location strings into a list of iteration numbers.
    
    Supports both individual values and range specifications.
    Ranges use colon notation: "10000:50000" expands to [10000, 11000, ..., 50000].
    
    Parameters
    ----------
    snapshots_locations : list[str]
        List of location specifications. Each element is either:
        - A single iteration number as string (e.g., "20000")
        - A range specification (e.g., "10000:50000")
    
    Returns
    -------
    list[int]
        List of all iteration numbers after expansion.
    
    Raises
    ------
    ValueError
        If any location is not a multiple of 1000 (snapshots are saved
        every 1000 iterations).
    
    Examples
    --------
    >>> parse_snapshots(["10000", "20000:30000"])
    [10000, 20000, 21000, 22000, ..., 30000]
    """

    locations_parsed=[]
    for location in snapshots_locations:

        if ":" in location:
            start_location, end_location= map(int, location.split(":"))
            locations_period = np.arange(start_location, end_location + 1000, step=1000)
            
            locations_parsed.extend(locations_period)
        else: 
            locations_parsed.append(int(location))
            
    locations_parsed = np.array(locations_parsed)

    if not np.all(locations_parsed % 1000 == 0):
        raise ValueError("Snapshots location should be a factor of 1000, please check your input")

    return list(locations_parsed)