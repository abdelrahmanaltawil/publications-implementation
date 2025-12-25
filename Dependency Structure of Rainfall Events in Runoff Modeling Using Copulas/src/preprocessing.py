# imports
import logging
import sqlite3
import pathlib
import datetime
import uuid
import pandas as pd

# local imports


def create_save_dir(base_dir: pathlib.Path, stations: list[dict]) -> pathlib.Path:
    """Creates the results directory structure with timestamp and unique ID."""
    
    # create unique save directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = str(uuid.uuid4())[:4]
    if  len(stations) > 1:
        base_name = "MULTI-STATIONS"
    else:
        base_name = f"{stations[0]['name']} - {stations[0]['id']}"
    save_dir = pathlib.Path(base_dir) / f"{base_name} -- {timestamp} -- {run_id}"

    save_dir.mkdir(parents=True, exist_ok=True)

    return save_dir


def load_data(db_path: str, table_name: str, climate_id: list[str]) -> pd.DataFrame:
    """
    Load climate data for specific climate ID from a SQLite database.
    """

    query = f"""
        SELECT climate_id, datetime, value, flag
        FROM {table_name}
        WHERE climate_id = "{climate_id}"
    """

    logging.info(f"Querying {table_name} for climate_id: {climate_id}")
    with sqlite3.connect(db_path) as conn:
        data = pd.read_sql_query(
            query,
            conn,
            parse_dates=["datetime"]
        )

    # Ensure data schema
    data["climate_id"] = data["climate_id"].astype(str)
    data["datetime"] = pd.to_datetime(data["datetime"])
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    data["flag"] = data["flag"].astype(str)

    if data.empty:
        logging.warning("No data returned from the database after filtering.")
    else:
        logging.info(f"Successfully loaded {len(data)} rows for climate_id: {climate_id}")

    return data


def clean_data(
        data: pd.DataFrame, 
        time_col: str, 
        rain_col: str,
        winter_months: list = [11, 12, 1, 2, 3, 4],
        remove_outliers: bool = False
) -> pd.DataFrame:
    """
    Clean the data by removing unnecessary columns, renaming columns, and optionally removing outliers.

    Args:
        data (pd.DataFrame): DataFrame containing the data to be cleaned.
        time_col (str): Name of the column containing timestamps.
        rain_col (str): Name of the column containing rainfall amounts.
        winter_months (list): List of integers representing winter months to exclude.
        remove_outliers (bool): Whether to remove outliers from the data.

    Returns:
        pd.DataFrame: DataFrame containing cleaned data.
    """

    if data.empty:
        logging.warning("No data provided for cleaning.")
        return data

    logging.info(f"Starting data cleaning on {len(data)} rows...")

    # Drop nan and zero rainfall values
    data = data.dropna(subset=[rain_col])
    data = data[data[rain_col] > 0]

    if remove_outliers:
        # Remove outliers using the IQR method
        Q1 = data[rain_col].quantile(0.25)
        Q3 = data[rain_col].quantile(0.75)
        IQR = Q3 - Q1

        # Define outlier bounds
        upper_bound = Q3 + 3 * IQR

        # Identify outliers
        outliers = data[data[rain_col] > upper_bound]
        logging.info(f"Upper Bound for Outliers: {upper_bound}")
        logging.info(f"Number of Outliers detected: {len(outliers)}")

        # Remove outliers  
        data = data[data[rain_col] <= upper_bound]

    # Filter winter months
    data = data[~data[time_col].dt.month.isin(winter_months)]

    # Reset index after cleaning
    data = data.sort_values(by=time_col).reset_index(drop=True)

    if data.empty:
        logging.warning("No data remaining after cleaning process.")
    else:
        logging.info(f"Data cleaning complete. Remaining rows: {len(data)}")

    return data


def extract_rainfall_events(
        data: pd.DataFrame, 
        time_col: str, 
        rain_col: str, 
        IETD_threshold: int = 6
) -> pd.DataFrame:
    """
    Extracts rainfall events from hourly rainfall data using vectorized operations.

    Parameters:
        data (pd.DataFrame): DataFrame containing rainfall data.
        time_col (str): Name of the column containing timestamps.
        rain_col (str): Name of the column containing hourly precipitation values.
        IETD_threshold (int): Inter-event time definition in hours.

    Returns:
        pd.DataFrame: DataFrame containing rainfall events with features including 'Inter-Event Time (hrs)'.
    """

    if data.empty:
        logging.warning("No rainfall data detected for event extraction.")
        return pd.DataFrame()
    
    logging.info(f"Starting rainfall event extraction on {len(data)} rows with IETD={IETD_threshold}h...")

    # Calculate time difference between consecutive rainy hours
    time_diff = data[time_col].diff()
    
    # Identify new events:
    # A new event starts if the gap is larger than IETD_threshold hours.
    # Note: time_diff includes the 1 hour of the next step, so a 6h gap means time_diff=7h.
    # However, standard IETD usually implies "gap > threshold".
    # Logic: If threshold=6, a 6h dry gap breaks the event. 
    # Gap = time_diff - 1 hour. So (time_diff - 1) >= threshold => time_diff > threshold.
    is_new_event = (time_diff > pd.Timedelta(hours=IETD_threshold)) | time_diff.isna()
    
    # Assign Event IDs
    data['event_id'] = is_new_event.cumsum()

    # Aggregate
    # Duration (hrs) = count() -> matches "Net Duration" (number of rainy hours)
    # To match standard "Gross Duration" (End - Start + 1), we would use (max - min).
    # We stick to the previous logic: 'count' of rainy rows.
    aggregations = {
        time_col: ['min', 'max'],
        rain_col: ['sum', 'max', 'count']
    }
    
    events = data.groupby('event_id').agg(aggregations)
    
    # Flatten MultiIndex columns
    events.columns = ['Start Time', 'End Time', 'Volume (mm)', 'Peak Precipitation (mm)', 'Duration (hrs)']
    events = events.reset_index(drop=True)

    # Correct Duration to be Elapsed Time
    # Duration = (End Time - Start Time) + 1 hour (assuming hourly steps)
    events['Duration (hrs)'] = (events['End Time'] - events['Start Time']).dt.total_seconds() / 3600 + 1

    # Calculate Derived Columns
    events['Intensity (mm/hr)'] = events['Volume (mm)'] / events['Duration (hrs)']
    events['IETD (hrs)'] = IETD_threshold

    # --- Inter-Event Time Calculation ---
    if not events.empty:
        prev_end_time = events["End Time"].shift(1)
        inter_event_times = (events["Start Time"] - prev_end_time).dt.total_seconds() / 3600

        # Create temp df to handle year boundary logic
        temp_iet_df = pd.DataFrame({
            "prev_end_year": prev_end_time.dt.year,
            "curr_start_year": events["Start Time"].dt.year,
            "Inter-Event Time (hrs)": inter_event_times
        })
        
        mask_diff_year = temp_iet_df["prev_end_year"] != temp_iet_df["curr_start_year"]
        temp_iet_df.loc[mask_diff_year, "Inter-Event Time (hrs)"] = None

        events["Inter-Event Time (hrs)"] = temp_iet_df["Inter-Event Time (hrs)"]
    
    # Reorder columns to match original output
    cols = [
        "Start Time", "End Time", "Duration (hrs)", "Volume (mm)", 
        "Intensity (mm/hr)", "Peak Precipitation (mm)", 
        "Inter-Event Time (hrs)", "IETD (hrs)"
    ]

    logging.info(f"Extraction complete. Found {len(events)} events.")
    return events[cols]