# env imports
import yaml
import pathlib
import numpy as np
import neptune.new as neptune

# local imports
import active_flow.steady_state_analysis.preprocessing as preprocessing
import active_flow.steady_state_analysis.helpers.register as re
import active_flow.steady_state_analysis.postprocessing as postprocessing





def run(parameters: dict) -> None:
    '''
    Placeholder
    '''

    run = neptune.init_run(
        tags=["steady state analysis"],
    )
    run_id = run["sys/id"].fetch()

    # Preprocessing
    preprocessing.parse_parameters(parameters)
    re.init_register()

    reference_run = neptune.init_run(
        with_id=parameters["preprocessing"]["experiment_ID"],
        mode="read-only"
    )

    run["parameters"] = reference_run["parameters"].fetch()
    run["parameters/reference_simulation_experiment"] = parameters["preprocessing"]["experiment_ID"]
    run["parameters/snapshots_locations"] = str(parameters["postprocessing"]["snapshots_locations"])

    ## load arrays    
    reference_run["data/arrays"].download(destination=parameters["preprocessing"]["download_path"])
    reference_run.wait()
    preprocessing.unzip_delete_file(
        file_path= pathlib.Path(parameters["preprocessing"]["download_path"]+"/arrays.zip")
    )
    preprocessing.load_arrays(
        read_path= pathlib.Path(parameters["preprocessing"]["download_path"]+"/arrays"),
        snapshots_locations= parameters["postprocessing"]["snapshots_locations"]
    )

    re.register["snapshots"]

    ## load table
    reference_run["data/tables/monitoring"].download(destination= parameters["preprocessing"]["download_path"])
    reference_run.wait()
    monitor_table = preprocessing.load_table(
        read_path= pathlib.Path(parameters["preprocessing"]["download_path"]+"/monitoring.csv"),
    )
    
    reference_run.stop()

    # Postprocessing
    postprocessing.save_arrays(
        operators= re.register["operators"], 
        snapshots= re.register["snapshots"], 
        save_path= pathlib.Path(parameters["postprocessing"]["save_path"]+"/arrays")
    )
    run["data/arrays"].upload_files(parameters["postprocessing"]["save_path"]+"/arrays")

    monitor_table = postprocessing.save_monitoring_table(
        monitor_table= monitor_table,
        save_path= pathlib.Path(parameters["postprocessing"]["save_path"])
        )
    run["data/tables/monitoring"].upload(parameters["postprocessing"]["save_path"]+"/tables/monitoring.csv")
    run.wait()

    postprocessing.remove_data(
        data_path= pathlib.Path(parameters["preprocessing"]["download_path"])
    )
    postprocessing.remove_data(
        data_path= pathlib.Path(parameters["postprocessing"]["save_path"])
    )

    figure = postprocessing.plot_snapshots_location(
        monitored_data= monitor_table,
        snapshots_locations= parameters["postprocessing"]["snapshots_locations"]
    )
    run["plots/snapshots locations"].upload(figure)


    snapshots_fields = postprocessing.calculate_fields(
        k_vectors= re.register["operators"]["k_vectors"],
        snapshots= re.register["snapshots"]
        )

    figure = postprocessing.plot_snapshots_fields(
        x = re.register["operators"]["x_vectors"][:,:,0],
        y = re.register["operators"]["x_vectors"][:,:,1],
        snapshots_fields= snapshots_fields,
        symbol= "$|U|$"
    )
    run["image/velocity snapshots"].upload(figure)

    figure = postprocessing.plot_snapshots_fields(
        x = re.register["operators"]["x_vectors"][:,:,0],
        y = re.register["operators"]["x_vectors"][:,:,1],
        snapshots_fields= snapshots_fields,
        symbol= "$\omega$"
    )
    run["image/vorticity snapshots"].upload(figure)

    figure = postprocessing.plot_snapshots_fields(
        x = re.register["operators"]["x_vectors"][:,:,0],
        y = re.register["operators"]["x_vectors"][:,:,1],
        snapshots_fields= snapshots_fields,
        symbol= "$\psi$"
    )
    run["image/stream snapshots"].upload(figure)


    figure = postprocessing.plot_snapshots_spectra(
        k = np.arange(1, np.max(re.register["operators"]["k_vectors"][:,:,0][0])),
        snapshots_fields=  snapshots_fields,
    )
    run["plots/spectra plot"].upload(figure)

    run.stop()

    return run_id


if __name__ == "__main__":


    with open(pathlib.Path("./parameters/steady_state_analysis.yml"), "r") as file:
        parameters = yaml.safe_load(file)

    run(
        parameters= parameters
    )

