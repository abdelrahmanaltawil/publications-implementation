import numpy as np




def parse_snapshots(snapshots_locations: list[str]) -> np.ndarray[int]:
    '''
    Placeholder
    '''

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