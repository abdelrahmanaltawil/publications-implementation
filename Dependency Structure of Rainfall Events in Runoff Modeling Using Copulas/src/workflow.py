# imports
import logging
import os
import sys
import yaml
import pathlib
import datetime
import platform
import socket
import getpass
import pandas as pd

# local imports
import preprocessing, algorithm_tasks as algorithm, postprocessing


PHYSICS_COLUMNS = {
    "Imperviousness_h_fraction": "h",
    "Imp_Depression_Storage_Sdi_mm": "Sdi",
    "Pervious_Init_Loss_Sil_mm": "Sil",
    "Ult_Infiltration_fc_mm_hr": "fc",
    "Max_Infiltration_Sm_mm": "Sm",
    "Calc_Time_to_Sat_ts_hr": "ts",
}


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] \033[1m%(module)s\033[0m - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def setup_run_logging(save_path: pathlib.Path) -> None:
    """Configures the file handler to save logs to the run directory."""

    log_path = save_path / "00_run_logs.log"
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(module)s - %(message)s"))
    logging.getLogger().addHandler(file_handler)
    logging.info(f"Experiment results will be saved to: {save_path}")
    

def collect_run_metadata(save_path: pathlib.Path) -> dict:
    """Collects run environment and versioning details."""
    
    metadata = {
        "experiment_id": save_path.parts[-1].split(" -- ")[-1],
        "execution_start_time": datetime.datetime.now().isoformat(),
        "timestamp": datetime.datetime.now().isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "user": getpass.getuser(),
        "hostname": socket.gethostname(),
        "working_directory": os.getcwd(),
        "command": " ".join(sys.argv),
    }

    logging.info("Collecting run environment and versioning details...")
    logging.info(f"Experiment ID: {metadata['experiment_id']} (started at {metadata['execution_start_time']})\n\n")
    
    return metadata




if __name__ == "__main__":

    # load parameters
    with open("data/inputs/config.yaml", "r") as f:
        config = yaml.safe_load(f)

    stations_df = pd.read_csv(config["database"]["stations_meta_data_path"], dtype={"Station_ID": str})
    stations = stations_df.rename(columns={"Station_ID": "id", "Station_Name": "name"}).to_dict("records")

    # preprocessing
    save_dir = preprocessing.create_save_dir(
        base_dir=config["postprocessing"]["save_path"],
        stations=stations
    )

    # logging and metadata collection
    setup_run_logging(save_path=save_dir)
    metadata = collect_run_metadata(save_path=save_dir)


    for station in stations:

        logging.info(f"Starting analysis for station: {station['name']} ({station['id']})")

        physical_params = {param: float(station[col]) for col, param in PHYSICS_COLUMNS.items()}
        ietd = int(station["IETD_Used_hr"])

        rainfall_data = preprocessing.load_data(
                    db_path=config["database"]["db_path"],
                    table_name=config["database"]["table_name"],
                    climate_id=station["id"]
                )

        cleaned_rainfall_data = preprocessing.clean_data(
                    rainfall_data,
                    time_col=config["preprocessing"]["time_col"],
                    rain_col=config["preprocessing"]["rain_col"],
                    winter_months=config["preprocessing"]["winter_months"],
                    remove_outliers=config["preprocessing"]["remove_outliers"]
                )

        events_data = preprocessing.extract_rainfall_events(
                    data=cleaned_rainfall_data,
                    time_col=config["preprocessing"]["time_col"],
                    rain_col=config["preprocessing"]["rain_col"],
                    IETD_threshold=ietd
                )

        if events_data.empty:
            continue

        # algorithm
        copula_model = algorithm.fit_copulas(
                    data=events_data,
                    corr_columns=["Volume (mm)", "Duration (hrs)"],
                    copula_families=config["copula_families"]
                )

        # Derived exponential rates from observed events
        physical_params["lambda_v"] = float(1 / events_data["Volume (mm)"].to_numpy().mean())
        physical_params["lambda_t"] = float(1 / events_data["Duration (hrs)"].to_numpy().mean())

        joint_densities = algorithm.get_copula_joint_density_function(
                    copulas=copula_model[1],
                    lambda_v=physical_params["lambda_v"],
                    lambda_t=physical_params["lambda_t"]
                )

        cdf_results = algorithm.compute_cdf(
                    joint_densities=joint_densities,
                    physical_params=physical_params,
                    analysis_params=config["analysis"],
                    integration_method=config["integration"]["method"],
                    **config["integration"]["kwargs"]
                )

        cdf_results["Analytical"] = algorithm.runoff_volume_cdf_closed_form(
                    physical_params=physical_params,
                    analysis_params=config["analysis"]
                )

        return_period =  algorithm.compute_return_period(
                    cdf_results=cdf_results,
                    analysis_params=config["analysis"]
                )


        if station["id"] in config["sensitivity_analysis"]["station"]:
            bootstrap_results = algorithm.perform_bootstrap_uncertainty_analysis(
                        data=events_data,
                        corr_columns=["Volume (mm)", "Duration (hrs)"],
                        copula_families=config["copula_families"],
                        physical_params=physical_params,
                        analysis_params=config["analysis"],
                        integration_method=config["integration"]["method"],
                        integration_kwargs=config["integration"]["kwargs"],
                        n_bootstrap=config["sensitivity_analysis"]["n_bootstrap"]
                        )

            sensitivity_results = algorithm.perform_sensitivity_analysis(
                        copula_families=config["copula_families"],
                        parameter_range=config["sensitivity_analysis"]["parameter_range"],
                        physical_params=physical_params,
                        analysis_params=config["analysis"],
                        integration_method=config["integration"]["method"],
                        integration_kwargs=config["integration"]["kwargs"]
                    )
        
        else:
            bootstrap_results = None
            sensitivity_results = None
            
        # postprocessing
        postprocessing.save_data(
            datasets = {
                f"01_input_data/01_hourly_rainfall_data.csv": rainfall_data,
                f"01_input_data/02_cleaned_hourly_rainfall_data.csv": cleaned_rainfall_data,
                f"01_input_data/03_rainfall_events_data.csv": events_data,
                f"02_copula_fitting/01_input_ranks.csv": copula_model[0],
                f"02_copula_fitting/02_copula_fit_metrics.csv": copula_model[2],
                f"02_copula_fitting/03_cdf_results.csv": cdf_results,
                f"02_copula_fitting/04_return_periods.csv": return_period,
                f"03_sensitivity__uncertainty_analysis/01_bootstrap_uncertainty.csv": bootstrap_results,
                f"03_sensitivity__uncertainty_analysis/02_sensitivity_analysis.csv": sensitivity_results
            },
            save_path = save_dir / f"{station['name']} - {station['id']}" 
                        if "MULTI-STATIONS" in str(save_dir) else save_dir
        )

        logging.info(f"Analysis completed for station: {station['name']} ({station['id']}).\n")

    # postprocessing
    metadata, experiment_parameters, log_path = postprocessing.save_run_metadata(
                        save_path=save_dir,
                        metadata=metadata,
                        experiment_parameters=config,
                        logger=logging.getLogger()
                    )
                
    logging.info(f"Experiment has ended successfully with elapsed time: {metadata['execution_duration_min']:.2f} min.")
